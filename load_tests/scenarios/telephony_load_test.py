"""
Load tests for telephony endpoints
"""
from locust import HttpUser, task, between, events
import random
import json
from datetime import datetime, timedelta
from configs.settings import LoadTestConfig
from utils.auth import auth_manager

class TelephonyUser(HttpUser):
    """Load test user for telephony endpoints"""
    
    wait_time = between(LoadTestConfig.DEFAULT_WAIT_TIME_MIN, LoadTestConfig.DEFAULT_WAIT_TIME_MAX)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token = None
        self.call_ids = []
        self.phone_numbers = []
        self.telephony_setup = False
    
    def on_start(self):
        """Setup authentication and initial telephony configuration"""
        # Get authentication token
        self.access_token = auth_manager.get_or_create_token()
        if not self.access_token:
            print("Failed to authenticate for telephony tests")
            self.environment.runner.quit()
        
        # Setup telephony configuration
        self.setup_telephony()
    
    def setup_telephony(self):
        """Setup telephony configuration for testing"""
        headers = LoadTestConfig.get_headers(self.access_token)
        
        if LoadTestConfig.SIMULATE_EXTERNAL_SERVICES:
            # Simulate telephony setup without actual Twilio
            telephony_data = {
                "provider": "twilio",
                "settings": {
                    "account_sid": "TEST_ACCOUNT_SID",
                    "auth_token": "TEST_AUTH_TOKEN",
                    "phone_number": f"+1555{random.randint(1000000, 9999999)}"
                },
                "test_mode": True
            }
        else:
            # Real telephony setup (requires actual Twilio credentials)
            telephony_data = {
                "provider": "twilio",
                "test_mode": False
            }
        
        response = self.client.post(
            "/api/telephony/setup",
            json=telephony_data,
            headers=headers,
            catch_response=True,
            name="[SETUP] Telephony configuration"
        )
        
        if response.status_code in [200, 201]:
            self.telephony_setup = True
            response.success()
        elif response.status_code == 409:
            # Already configured
            self.telephony_setup = True
            response.success()
        else:
            response.failure(f"Telephony setup failed: {response.status_code}")
    
    @task(2)
    def initiate_phone_verification(self):
        """Test initiating phone number verification"""
        if not self.telephony_setup:
            return
        
        headers = LoadTestConfig.get_headers(self.access_token)
        phone_number = f"+1555{random.randint(1000000, 9999999)}"
        
        with self.client.post(
            "/api/telephony/verify/initiate",
            json={"phone_number": phone_number},
            headers=headers,
            catch_response=True,
            name="/api/telephony/verify/initiate"
        ) as response:
            if response.status_code == 200:
                response.success()
                self.phone_numbers.append(phone_number)
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            elif response.status_code == 429:
                # Rate limited
                response.success()
            else:
                response.failure(f"Initiate verification failed: {response.status_code}")
    
    @task(1)
    def confirm_phone_verification(self):
        """Test confirming phone verification"""
        if not self.phone_numbers:
            return
        
        headers = LoadTestConfig.get_headers(self.access_token)
        phone_number = random.choice(self.phone_numbers)
        
        # Simulate verification code
        verification_code = f"{random.randint(100000, 999999)}"
        
        with self.client.post(
            "/api/telephony/verify/confirm",
            json={
                "phone_number": phone_number,
                "verification_code": verification_code
            },
            headers=headers,
            catch_response=True,
            name="/api/telephony/verify/confirm"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 400:
                # Invalid code, expected in testing
                response.success()
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"Confirm verification failed: {response.status_code}")
    
    @task(10)
    def list_calls(self):
        """Test listing telephony calls"""
        headers = LoadTestConfig.get_headers(self.access_token)
        
        # Random filters
        params = {
            "page": random.randint(1, 5),
            "page_size": random.choice([10, 20, 50])
        }
        
        # Sometimes add status filter
        if random.random() > 0.5:
            params["status"] = random.choice(["in-progress", "completed", "failed", "busy", "no-answer"])
        
        # Sometimes add date range
        if random.random() > 0.5:
            start_date = datetime.now() - timedelta(days=7)
            params["start_date"] = start_date.date().isoformat()
            params["end_date"] = datetime.now().date().isoformat()
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        
        with self.client.get(
            f"/api/telephony/calls?{query_string}",
            headers=headers,
            catch_response=True,
            name="/api/telephony/calls [LIST]"
        ) as response:
            if response.status_code == 200:
                response.success()
                data = response.json()
                # Store some call IDs for other operations
                calls = data.get("items", [])
                for call in calls[:10]:
                    if call["id"] not in self.call_ids:
                        self.call_ids.append(call["id"])
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"List calls failed: {response.status_code}")
    
    @task(8)
    def get_call_details(self):
        """Test getting specific call details"""
        if not self.call_ids:
            # Create simulated call data
            self.simulate_call_data()
            return
        
        headers = LoadTestConfig.get_headers(self.access_token)
        call_id = random.choice(self.call_ids)
        
        with self.client.get(
            f"/api/telephony/calls/{call_id}",
            headers=headers,
            catch_response=True,
            name="/api/telephony/calls/[id]"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                self.call_ids.remove(call_id)
                response.success()
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"Get call details failed: {response.status_code}")
    
    @task(3)
    def simulate_incoming_call_webhook(self):
        """Simulate Twilio incoming call webhook"""
        if not self.telephony_setup or not LoadTestConfig.SIMULATE_EXTERNAL_SERVICES:
            return
        
        # Simulate Twilio webhook data
        webhook_data = {
            "CallSid": f"CA{random.randbytes(32).hex()}",
            "From": f"+1555{random.randint(1000000, 9999999)}",
            "To": f"+1555{random.randint(1000000, 9999999)}",
            "CallStatus": "ringing",
            "Direction": "inbound",
            "AccountSid": "TEST_ACCOUNT_SID",
            "CallerName": f"Test Caller {random.randint(1, 100)}"
        }
        
        with self.client.post(
            "/api/telephony/webhook/incoming-call",
            data=webhook_data,  # Form data, not JSON
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            catch_response=True,
            name="/api/telephony/webhook/incoming-call"
        ) as response:
            if response.status_code == 200:
                response.success()
                # Store the call ID
                if "CallSid" in webhook_data:
                    self.call_ids.append(webhook_data["CallSid"])
            elif response.status_code == 401:
                # Webhooks might not require auth
                response.success()
            else:
                response.failure(f"Webhook failed: {response.status_code}")
    
    @task(4)
    def get_call_transcription(self):
        """Test getting call transcription"""
        if not self.call_ids:
            return
        
        headers = LoadTestConfig.get_headers(self.access_token)
        call_id = random.choice(self.call_ids)
        
        with self.client.get(
            f"/api/telephony/calls/{call_id}/transcription",
            headers=headers,
            catch_response=True,
            name="/api/telephony/calls/[id]/transcription"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # No transcription available
                response.success()
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"Get transcription failed: {response.status_code}")
    
    @task(2)
    def get_call_analytics(self):
        """Test getting call analytics"""
        headers = LoadTestConfig.get_headers(self.access_token)
        
        # Random time period
        period = random.choice(["day", "week", "month"])
        
        with self.client.get(
            f"/api/telephony/analytics?period={period}",
            headers=headers,
            catch_response=True,
            name="/api/telephony/analytics"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                self.refresh_token()
                response.failure("Token expired")
            else:
                response.failure(f"Get analytics failed: {response.status_code}")
    
    def simulate_call_data(self):
        """Create simulated call records for testing"""
        headers = LoadTestConfig.get_headers(self.access_token)
        
        for i in range(5):
            call_data = {
                "call_sid": f"CA{random.randbytes(16).hex()}",
                "from_number": f"+1555{random.randint(1000000, 9999999)}",
                "to_number": f"+1555{random.randint(1000000, 9999999)}",
                "status": random.choice(["completed", "in-progress", "failed"]),
                "duration": random.randint(10, 600),
                "direction": random.choice(["inbound", "outbound"]),
                "start_time": (datetime.now() - timedelta(hours=random.randint(1, 72))).isoformat()
            }
            
            # This endpoint might not exist, but simulating the pattern
            response = self.client.post(
                "/api/telephony/calls/simulate",
                json=call_data,
                headers=headers,
                catch_response=True,
                name="[SIMULATE] Create call data"
            )
            
            if response.status_code in [200, 201]:
                self.call_ids.append(call_data["call_sid"])
                response.success()
            else:
                response.failure(f"Simulate call failed: {response.status_code}")
    
    def refresh_token(self):
        """Refresh the authentication token"""
        self.access_token = auth_manager.get_or_create_token()

class TelephonyLoadTest(HttpUser):
    """Combined telephony load test scenarios"""
    
    wait_time = between(1, 3)
    tasks = [TelephonyUser]

# Event handlers
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Setup before telephony tests start"""
    print("Starting telephony load tests...")
    print(f"Simulating external services: {LoadTestConfig.SIMULATE_EXTERNAL_SERVICES}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Cleanup after telephony tests stop"""
    print("Telephony load tests completed.")
    print(f"Total telephony requests: {environment.stats.total.num_requests}")
    print(f"Total telephony failures: {environment.stats.total.num_failures}")