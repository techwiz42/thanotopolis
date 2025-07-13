"""
Load tests for authentication endpoints
"""
from locust import HttpUser, task, between, events
import random
import string
import time
from configs.settings import LoadTestConfig
from utils.auth import auth_manager

class AuthenticationUser(HttpUser):
    """Load test user for authentication endpoints"""
    
    wait_time = between(LoadTestConfig.DEFAULT_WAIT_TIME_MIN, LoadTestConfig.DEFAULT_WAIT_TIME_MAX)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_email = None
        self.user_password = None
        self.access_token = None
        self.refresh_token = None
        self.organization_name = None
    
    def on_start(self):
        """Setup test user data"""
        # Generate unique user data
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        self.user_email = f"loadtest_{random_suffix}@example.com"
        self.user_password = "TestPassword123!"
        self.organization_name = f"LoadTest Org {random_suffix}"
    
    @task(3)
    def attempt_registration(self):
        """Test user registration (expect failures in load test)"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        with self.client.post(
            "/api/auth/register/token",
            json={
                "email": f"loadtest_{random_suffix}@example.com",
                "username": f"loadtest_{random_suffix}",
                "password": "TestPassword123!",
                "first_name": "Load",
                "last_name": "Test"
            },
            catch_response=True,
            name="/api/auth/register [LOAD_TEST]"
        ) as response:
            if response.status_code == 200:
                response.success()
                data = response.json()
                # Store tokens for future use
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
            elif response.status_code in [400, 409, 422]:
                # Expected failures in load testing environment
                response.success()
            else:
                response.failure(f"Registration failed: {response.status_code}")
    
    @task(5)
    def attempt_login(self):
        """Test user login (expect failures in load test)"""
        
        with self.client.post(
            "/api/auth/login",
            json={
                "email": self.user_email,
                "password": self.user_password
            },
            catch_response=True,
            name="/api/auth/login [LOAD_TEST]"
        ) as response:
            if response.status_code == 200:
                response.success()
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
            elif response.status_code in [401, 404, 422]:
                # Expected failures in load testing - users don't exist
                response.success()
            else:
                response.failure(f"Login failed: {response.status_code}")
    
    @task(2)
    def refresh_access_token(self):
        """Test token refresh"""
        if not self.refresh_token:
            # Need to login first
            self.attempt_login()
            return
        
        with self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": self.refresh_token},
            catch_response=True,
            name="/api/auth/refresh"
        ) as response:
            if response.status_code == 200:
                response.success()
                data = response.json()
                self.access_token = data.get("access_token")
            else:
                response.failure(f"Token refresh failed: {response.status_code}")
    
    @task(4)
    def get_current_user(self):
        """Test getting current user info"""
        if not self.access_token:
            self.attempt_login()
            return
        
        headers = LoadTestConfig.get_headers(self.access_token)
        
        with self.client.get(
            "/api/auth/me",
            headers=headers,
            catch_response=True,
            name="/api/auth/me"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                # Token expired, refresh it
                self.refresh_access_token()
                response.failure("Token expired")
            else:
                response.failure(f"Get user failed: {response.status_code}")
    
    @task(1)
    def logout_user(self):
        """Test user logout"""
        if not self.access_token:
            return
        
        headers = LoadTestConfig.get_headers(self.access_token)
        
        with self.client.post(
            "/api/auth/logout",
            headers=headers,
            catch_response=True,
            name="/api/auth/logout"
        ) as response:
            if response.status_code == 200:
                response.success()
                # Clear tokens after logout
                self.access_token = None
                self.refresh_token = None
            else:
                response.failure(f"Logout failed: {response.status_code}")
    
    @task(2)
    def update_user_profile(self):
        """Test updating user profile"""
        if not self.access_token:
            self.attempt_login()
            return
        
        headers = LoadTestConfig.get_headers(self.access_token)
        
        with self.client.patch(
            "/api/users/me",
            json={
                "first_name": f"Updated{random.randint(1, 1000)}",
                "last_name": "LoadTest"
            },
            headers=headers,
            catch_response=True,
            name="/api/users/me"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                self.refresh_access_token()
                response.failure("Token expired")
            else:
                response.failure(f"Update profile failed: {response.status_code}")

# Note: Use AuthenticationUser class directly for load testing

# Event handlers for test lifecycle
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Setup before test starts"""
    print("Starting authentication load tests...")
    print(f"Target host: {environment.host}")
    print(f"Rate limit consideration: {LoadTestConfig.RATE_LIMIT_PER_MINUTE} req/min")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Cleanup after test stops"""
    print("Authentication load tests completed.")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Average response time: {environment.stats.total.avg_response_time}ms")