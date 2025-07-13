"""
Load tests for CRM endpoints
"""
from locust import HttpUser, task, between, events
import random
import json
from datetime import datetime, timedelta
from configs.settings import LoadTestConfig
from utils.auth import auth_manager

class CRMUser(HttpUser):
    """Load test user for CRM endpoints"""
    
    wait_time = between(LoadTestConfig.DEFAULT_WAIT_TIME_MIN, LoadTestConfig.DEFAULT_WAIT_TIME_MAX)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token = None
        self.contact_ids = []
        self.interaction_ids = []
    
    def on_start(self):
        """Setup authentication and initial data"""
        # Get authentication token
        self.access_token = auth_manager.get_or_create_token()
        if not self.access_token:
            print("Failed to authenticate for CRM tests")
            self.environment.runner.quit()
    
    @task(5)
    def create_contact(self):
        """Test creating a new contact"""
        headers = LoadTestConfig.get_headers(self.access_token)
        contact_data = LoadTestConfig.get_test_contact_data(random.randint(1, 10000))
        
        with self.client.post(
            "/api/crm/contacts",
            json=contact_data,
            headers=headers,
            catch_response=True,
            name="/api/crm/contacts [CREATE]"
        ) as response:
            if response.status_code == 201:
                response.success()
                data = response.json()
                contact_id = data.get("id")
                if contact_id and len(self.contact_ids) < LoadTestConfig.MAX_CONTACTS_PER_USER:
                    self.contact_ids.append(contact_id)
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"Create contact failed: {response.status_code}")
    
    @task(10)
    def list_contacts(self):
        """Test listing contacts with pagination"""
        headers = LoadTestConfig.get_headers(self.access_token)
        
        # Random pagination parameters
        page = random.randint(1, 5)
        page_size = random.choice([10, 20, 50])
        
        with self.client.get(
            f"/api/crm/contacts?page={page}&page_size={page_size}",
            headers=headers,
            catch_response=True,
            name="/api/crm/contacts [LIST]"
        ) as response:
            if response.status_code == 200:
                response.success()
                data = response.json()
                # Store some contact IDs for other operations
                contacts = data.get("items", [])
                for contact in contacts[:5]:
                    if contact["id"] not in self.contact_ids and len(self.contact_ids) < LoadTestConfig.MAX_CONTACTS_PER_USER:
                        self.contact_ids.append(contact["id"])
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"List contacts failed: {response.status_code}")
    
    @task(8)
    def get_contact(self):
        """Test getting a specific contact"""
        if not self.contact_ids:
            self.create_contact()
            return
        
        headers = LoadTestConfig.get_headers(self.access_token)
        contact_id = random.choice(self.contact_ids)
        
        with self.client.get(
            f"/api/crm/contacts/{contact_id}",
            headers=headers,
            catch_response=True,
            name="/api/crm/contacts/[id] [GET]"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Contact was deleted, remove from list
                self.contact_ids.remove(contact_id)
                response.success()
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"Get contact failed: {response.status_code}")
    
    @task(4)
    def update_contact(self):
        """Test updating a contact"""
        if not self.contact_ids:
            self.create_contact()
            return
        
        headers = LoadTestConfig.get_headers(self.access_token)
        contact_id = random.choice(self.contact_ids)
        
        update_data = {
            "notes": f"Updated at {datetime.now().isoformat()}",
            "contract_status": random.choice(["active", "pending", "completed"]),
            "balance_cents": random.randint(0, 1000000)
        }
        
        with self.client.patch(
            f"/api/crm/contacts/{contact_id}",
            json=update_data,
            headers=headers,
            catch_response=True,
            name="/api/crm/contacts/[id] [UPDATE]"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                self.contact_ids.remove(contact_id)
                response.success()
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"Update contact failed: {response.status_code}")
    
    @task(6)
    def search_contacts(self):
        """Test searching contacts"""
        headers = LoadTestConfig.get_headers(self.access_token)
        
        # Random search queries
        search_queries = [
            "Test",
            "Contact",
            "Company",
            "deceased",
            "veteran",
            f"PLOT-{random.randint(1, 100):04d}"
        ]
        query = random.choice(search_queries)
        
        with self.client.get(
            f"/api/crm/contacts/search?q={query}",
            headers=headers,
            catch_response=True,
            name="/api/crm/contacts/search"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"Search contacts failed: {response.status_code}")
    
    @task(3)
    def create_interaction(self):
        """Test creating a contact interaction"""
        if not self.contact_ids:
            self.create_contact()
            return
        
        headers = LoadTestConfig.get_headers(self.access_token)
        contact_id = random.choice(self.contact_ids)
        
        interaction_types = ["phone_call", "email", "meeting", "note"]
        interaction_data = {
            "contact_id": contact_id,
            "interaction_type": random.choice(interaction_types),
            "notes": f"Load test interaction at {datetime.now().isoformat()}",
            "duration_minutes": random.randint(5, 60)
        }
        
        with self.client.post(
            "/api/crm/interactions",
            json=interaction_data,
            headers=headers,
            catch_response=True,
            name="/api/crm/interactions [CREATE]"
        ) as response:
            if response.status_code == 201:
                response.success()
                data = response.json()
                interaction_id = data.get("id")
                if interaction_id:
                    self.interaction_ids.append(interaction_id)
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"Create interaction failed: {response.status_code}")
    
    @task(2)
    def get_crm_dashboard(self):
        """Test getting CRM dashboard statistics"""
        headers = LoadTestConfig.get_headers(self.access_token)
        
        with self.client.get(
            "/api/crm/dashboard",
            headers=headers,
            catch_response=True,
            name="/api/crm/dashboard"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"Get dashboard failed: {response.status_code}")
    
    @task(1)
    def delete_contact(self):
        """Test deleting a contact (less frequent)"""
        if len(self.contact_ids) < 5:
            # Keep some contacts for other operations
            return
        
        headers = LoadTestConfig.get_headers(self.access_token)
        contact_id = self.contact_ids.pop()
        
        with self.client.delete(
            f"/api/crm/contacts/{contact_id}",
            headers=headers,
            catch_response=True,
            name="/api/crm/contacts/[id] [DELETE]"
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
                response.failure(f"Delete contact failed: {response.status_code}")
    
    def refresh_token(self):
        """Refresh the authentication token"""
        self.access_token = auth_manager.get_or_create_token()

class CRMLoadTest(HttpUser):
    """Combined CRM load test scenarios"""
    
    wait_time = between(1, 3)
    tasks = [CRMUser]

# Event handlers
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Setup before CRM tests start"""
    print("Starting CRM load tests...")
    print(f"Max contacts per user: {LoadTestConfig.MAX_CONTACTS_PER_USER}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Cleanup after CRM tests stop"""
    print("CRM load tests completed.")
    print(f"Total CRM requests: {environment.stats.total.num_requests}")
    print(f"Total CRM failures: {environment.stats.total.num_failures}")