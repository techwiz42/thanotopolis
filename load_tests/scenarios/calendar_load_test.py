"""
Load tests for calendar endpoints
"""
from locust import HttpUser, task, between, events
import random
from datetime import datetime, timedelta
from configs.settings import LoadTestConfig
from utils.auth import auth_manager

class CalendarUser(HttpUser):
    """Load test user for calendar endpoints"""
    
    wait_time = between(LoadTestConfig.DEFAULT_WAIT_TIME_MIN, LoadTestConfig.DEFAULT_WAIT_TIME_MAX)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token = None
        self.event_ids = []
        self.contact_ids = []
    
    def on_start(self):
        """Setup authentication and initial data"""
        # Get authentication token
        self.access_token = auth_manager.get_or_create_token()
        if not self.access_token:
            print("Failed to authenticate for calendar tests")
            self.environment.runner.quit()
        
        # Create some test contacts for linking to events
        self.create_test_contacts()
    
    def create_test_contacts(self):
        """Create a few test contacts for calendar events"""
        headers = LoadTestConfig.get_headers(self.access_token)
        
        for i in range(5):
            contact_data = LoadTestConfig.get_test_contact_data(random.randint(1, 10000))
            response = self.client.post(
                "/api/crm/contacts",
                json=contact_data,
                headers=headers,
                catch_response=True,
                name="[SETUP] Create test contact"
            )
            if response.status_code == 201:
                data = response.json()
                contact_id = data.get("id")
                if contact_id:
                    self.contact_ids.append(contact_id)
                response.success()
            else:
                response.failure(f"Setup contact creation failed: {response.status_code}")
    
    @task(5)
    def create_event(self):
        """Test creating a calendar event"""
        headers = LoadTestConfig.get_headers(self.access_token)
        
        # Generate random event data
        start_date = datetime.now() + timedelta(days=random.randint(1, 30))
        end_date = start_date + timedelta(hours=random.randint(1, 4))
        
        event_data = {
            "title": f"Test Event {random.randint(1, 10000)}",
            "description": f"Load test event created at {datetime.now().isoformat()}",
            "start_time": start_date.isoformat(),
            "end_time": end_date.isoformat(),
            "event_type": random.choice(["appointment", "service", "meeting", "consultation"]),
            "location": f"Location {random.randint(1, 10)}",
            "reminder_minutes": random.choice([15, 30, 60, 1440]),
            "status": "scheduled"
        }
        
        # Sometimes link to a contact
        if self.contact_ids and random.random() > 0.5:
            event_data["contact_id"] = random.choice(self.contact_ids)
        
        with self.client.post(
            "/api/calendar/events",
            json=event_data,
            headers=headers,
            catch_response=True,
            name="/api/calendar/events [CREATE]"
        ) as response:
            if response.status_code == 201:
                response.success()
                data = response.json()
                event_id = data.get("id")
                if event_id and len(self.event_ids) < LoadTestConfig.MAX_EVENTS_PER_USER:
                    self.event_ids.append(event_id)
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"Create event failed: {response.status_code}")
    
    @task(10)
    def list_events(self):
        """Test listing calendar events"""
        headers = LoadTestConfig.get_headers(self.access_token)
        
        # Random pagination and filters
        params = {
            "page": random.randint(1, 5),
            "page_size": random.choice([10, 20, 50])
        }
        
        # Sometimes add event type filter
        if random.random() > 0.5:
            params["event_type"] = random.choice(["appointment", "service", "meeting", "consultation"])
        
        # Sometimes add status filter
        if random.random() > 0.5:
            params["status"] = random.choice(["scheduled", "completed", "cancelled"])
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        
        with self.client.get(
            f"/api/calendar/events?{query_string}",
            headers=headers,
            catch_response=True,
            name="/api/calendar/events [LIST]"
        ) as response:
            if response.status_code == 200:
                response.success()
                data = response.json()
                # Store some event IDs for other operations
                events = data.get("items", [])
                for event in events[:5]:
                    if event["id"] not in self.event_ids and len(self.event_ids) < LoadTestConfig.MAX_EVENTS_PER_USER:
                        self.event_ids.append(event["id"])
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"List events failed: {response.status_code}")
    
    @task(8)
    def get_events_in_range(self):
        """Test getting events in a date range"""
        headers = LoadTestConfig.get_headers(self.access_token)
        
        # Generate random date range
        start_date = datetime.now() - timedelta(days=random.randint(0, 7))
        end_date = start_date + timedelta(days=random.randint(7, 30))
        
        params = {
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat()
        }
        
        # Sometimes add view type
        if random.random() > 0.5:
            params["view"] = random.choice(["month", "week", "day"])
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        
        with self.client.get(
            f"/api/calendar/events/range?{query_string}",
            headers=headers,
            catch_response=True,
            name="/api/calendar/events/range"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"Get events in range failed: {response.status_code}")
    
    @task(4)
    def update_event(self):
        """Test updating a calendar event"""
        if not self.event_ids:
            self.create_event()
            return
        
        headers = LoadTestConfig.get_headers(self.access_token)
        event_id = random.choice(self.event_ids)
        
        update_data = {
            "notes": f"Updated at {datetime.now().isoformat()}",
            "status": random.choice(["scheduled", "completed", "cancelled"]),
            "reminder_minutes": random.choice([15, 30, 60, 1440])
        }
        
        with self.client.put(
            f"/api/calendar/events/{event_id}",
            json=update_data,
            headers=headers,
            catch_response=True,
            name="/api/calendar/events/[id] [UPDATE]"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                self.event_ids.remove(event_id)
                response.success()
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"Update event failed: {response.status_code}")
    
    @task(2)
    def get_event_statistics(self):
        """Test getting event statistics summary"""
        headers = LoadTestConfig.get_headers(self.access_token)
        
        # Random time period
        period = random.choice(["day", "week", "month", "quarter", "year"])
        
        with self.client.get(
            f"/api/calendar/events/stats/summary?period={period}",
            headers=headers,
            catch_response=True,
            name="/api/calendar/events/stats/summary"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"Get event stats failed: {response.status_code}")
    
    @task(1)
    def delete_event(self):
        """Test deleting a calendar event (less frequent)"""
        if len(self.event_ids) < 5:
            # Keep some events for other operations
            return
        
        headers = LoadTestConfig.get_headers(self.access_token)
        event_id = self.event_ids.pop()
        
        with self.client.delete(
            f"/api/calendar/events/{event_id}",
            headers=headers,
            catch_response=True,
            name="/api/calendar/events/[id] [DELETE]"
        ) as response:
            if response.status_code in [200, 204]:
                response.success()
            elif response.status_code == 404:
                # Already deleted
                response.success()
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"Delete event failed: {response.status_code}")
    
    @task(3)
    def create_recurring_event(self):
        """Test creating a recurring event"""
        headers = LoadTestConfig.get_headers(self.access_token)
        
        start_date = datetime.now() + timedelta(days=random.randint(1, 7))
        end_date = start_date + timedelta(hours=1)
        
        event_data = {
            "title": f"Recurring Event {random.randint(1, 1000)}",
            "description": "Load test recurring event",
            "start_time": start_date.isoformat(),
            "end_time": end_date.isoformat(),
            "event_type": "meeting",
            "recurrence_rule": random.choice([
                "FREQ=DAILY;COUNT=7",
                "FREQ=WEEKLY;BYDAY=MO,WE,FR;COUNT=10",
                "FREQ=MONTHLY;BYMONTHDAY=15;COUNT=6"
            ]),
            "status": "scheduled"
        }
        
        with self.client.post(
            "/api/calendar/events",
            json=event_data,
            headers=headers,
            catch_response=True,
            name="/api/calendar/events [CREATE RECURRING]"
        ) as response:
            if response.status_code == 201:
                response.success()
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"Create recurring event failed: {response.status_code}")
    
    def refresh_token(self):
        """Refresh the authentication token"""
        self.access_token = auth_manager.get_or_create_token()

class CalendarLoadTest(HttpUser):
    """Combined calendar load test scenarios"""
    
    wait_time = between(1, 3)
    tasks = [CalendarUser]

# Event handlers
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Setup before calendar tests start"""
    print("Starting calendar load tests...")
    print(f"Max events per user: {LoadTestConfig.MAX_EVENTS_PER_USER}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Cleanup after calendar tests stop"""
    print("Calendar load tests completed.")
    print(f"Total calendar requests: {environment.stats.total.num_requests}")
    print(f"Total calendar failures: {environment.stats.total.num_failures}")