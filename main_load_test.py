"""
Main comprehensive load test combining all scenarios
"""
from locust import HttpUser, task, between, events
import random
from load_tests.configs.settings import LoadTestConfig
from load_tests.scenarios.auth_load_test import AuthenticationUser
from load_tests.scenarios.crm_load_test import CRMUser
from load_tests.scenarios.calendar_load_test import CalendarUser
from load_tests.scenarios.telephony_load_test import TelephonyUser

class ComprehensiveUser(HttpUser):
    """
    Comprehensive load test user that performs realistic user workflows
    across all major application features
    """
    
    wait_time = between(LoadTestConfig.DEFAULT_WAIT_TIME_MIN, LoadTestConfig.DEFAULT_WAIT_TIME_MAX)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_type = None
        self.delegate_user = None
        
    def on_start(self):
        """Initialize user type and delegate to appropriate scenario"""
        # Randomly assign user type based on realistic usage patterns
        user_types = [
            ("auth", AuthenticationUser, 15),      # 15% - New users/auth testing
            ("crm", CRMUser, 40),                  # 40% - CRM heavy users  
            ("calendar", CalendarUser, 30),        # 30% - Calendar users
            ("telephony", TelephonyUser, 15)       # 15% - Telephony users
        ]
        
        # Weighted random selection
        total_weight = sum(weight for _, _, weight in user_types)
        r = random.randint(1, total_weight)
        
        cumulative_weight = 0
        for user_type, user_class, weight in user_types:
            cumulative_weight += weight
            if r <= cumulative_weight:
                self.user_type = user_type
                # Create delegate user instance
                self.delegate_user = user_class(self.environment)
                # Copy client and other attributes
                self.delegate_user.client = self.client
                self.delegate_user.environment = self.environment
                self.delegate_user.on_start()
                break
    
    @task
    def execute_user_workflow(self):
        """Execute the workflow for the assigned user type"""
        if self.delegate_user:
            # Get all task methods from the delegate user
            task_methods = []
            for attr_name in dir(self.delegate_user):
                attr = getattr(self.delegate_user, attr_name)
                if callable(attr) and hasattr(attr, '_locust_task'):
                    # Weight the task based on its original weight
                    weight = getattr(attr, '_locust_task_weight', 1)
                    task_methods.extend([attr] * weight)
            
            if task_methods:
                # Execute a random task
                task_method = random.choice(task_methods)
                task_method()
    
    def on_stop(self):
        """Cleanup when user stops"""
        if self.delegate_user and hasattr(self.delegate_user, 'on_stop'):
            self.delegate_user.on_stop()

class RealisticWorkflowUser(HttpUser):
    """
    Simulates realistic user workflows that span multiple features
    """
    
    wait_time = between(2, 8)  # Longer wait times for realistic user behavior
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_user = None
        self.crm_user = None
        self.calendar_user = None
        
    def on_start(self):
        """Setup all user types for cross-feature workflows"""
        # Initialize all user types
        self.auth_user = AuthenticationUser(self.environment)
        self.auth_user.client = self.client
        self.auth_user.environment = self.environment
        self.auth_user.on_start()
        
        self.crm_user = CRMUser(self.environment)
        self.crm_user.client = self.client
        self.crm_user.environment = self.environment
        self.crm_user.access_token = self.auth_user.access_token
        
        self.calendar_user = CalendarUser(self.environment)
        self.calendar_user.client = self.client
        self.calendar_user.environment = self.environment
        self.calendar_user.access_token = self.auth_user.access_token
        self.calendar_user.contact_ids = []  # Will be populated from CRM actions
    
    @task(3)
    def complete_customer_intake_workflow(self):
        """Realistic workflow: Customer calls, creates contact, schedules appointment"""
        # 1. Create a new contact (CRM)
        self.crm_user.create_contact()
        
        # Small delay to simulate thinking time
        self.wait()
        
        # 2. Create interaction record
        self.crm_user.create_interaction()
        
        # 3. Schedule follow-up appointment (Calendar)
        if self.crm_user.contact_ids:
            # Link calendar event to the contact
            contact_id = random.choice(self.crm_user.contact_ids)
            self.calendar_user.contact_ids = [contact_id]
            self.calendar_user.create_event()
    
    @task(2)
    def daily_admin_workflow(self):
        """Realistic workflow: Review dashboard, check calendar, update records"""
        # 1. Check CRM dashboard
        self.crm_user.get_crm_dashboard()
        
        self.wait()
        
        # 2. Review today's calendar
        self.calendar_user.get_events_in_range()
        
        self.wait()
        
        # 3. Update some contact records
        if self.crm_user.contact_ids:
            self.crm_user.update_contact()
        
        # 4. Check upcoming events
        self.calendar_user.get_event_statistics()
    
    @task(2)
    def search_and_schedule_workflow(self):
        """Realistic workflow: Search for contact, schedule appointment"""
        # 1. Search for contacts
        self.crm_user.search_contacts()
        
        self.wait()
        
        # 2. Get contact details
        if self.crm_user.contact_ids:
            self.crm_user.get_contact()
            
            self.wait()
            
            # 3. Schedule appointment for this contact
            contact_id = random.choice(self.crm_user.contact_ids)
            self.calendar_user.contact_ids = [contact_id]
            self.calendar_user.create_event()
    
    @task(1)
    def bulk_operations_workflow(self):
        """Realistic workflow: Bulk operations during busy periods"""
        # Create multiple contacts in sequence
        for _ in range(random.randint(2, 5)):
            self.crm_user.create_contact()
            
        # List and review contacts
        self.crm_user.list_contacts()
        
        # Create multiple calendar events
        for _ in range(random.randint(1, 3)):
            self.calendar_user.create_event()

# Event handlers for comprehensive testing
@events.test_start.add_listener
def on_comprehensive_test_start(environment, **kwargs):
    """Setup before comprehensive tests start"""
    print("=" * 60)
    print("STARTING COMPREHENSIVE THANOTOPOLIS LOAD TESTS")
    print("=" * 60)
    print(f"Target: {environment.host}")
    print(f"Rate limit: {LoadTestConfig.RATE_LIMIT_PER_MINUTE} req/min")
    print(f"Max contacts per user: {LoadTestConfig.MAX_CONTACTS_PER_USER}")
    print(f"Max events per user: {LoadTestConfig.MAX_EVENTS_PER_USER}")
    print(f"External services simulation: {LoadTestConfig.SIMULATE_EXTERNAL_SERVICES}")
    print("-" * 60)

@events.test_stop.add_listener 
def on_comprehensive_test_stop(environment, **kwargs):
    """Cleanup and reporting after comprehensive tests"""
    print("\n" + "=" * 60)
    print("COMPREHENSIVE LOAD TEST RESULTS")
    print("=" * 60)
    
    stats = environment.stats.total
    print(f"Total Requests: {stats.num_requests:,}")
    print(f"Total Failures: {stats.num_failures:,}")
    print(f"Failure Rate: {(stats.num_failures/stats.num_requests*100):.2f}%" if stats.num_requests > 0 else "0.00%")
    print(f"Average Response Time: {stats.avg_response_time:.0f}ms")
    print(f"Median Response Time: {stats.median_response_time:.0f}ms")
    print(f"95th Percentile: {stats.get_response_time_percentile(0.95):.0f}ms")
    print(f"99th Percentile: {stats.get_response_time_percentile(0.99):.0f}ms")
    print(f"Requests/sec: {stats.total_rps:.2f}")
    
    print("\nTop Slowest Endpoints:")
    sorted_stats = sorted(environment.stats.entries.values(), 
                         key=lambda x: x.avg_response_time, reverse=True)
    for i, stat in enumerate(sorted_stats[:10]):
        print(f"{i+1}. {stat.name}: {stat.avg_response_time:.0f}ms avg")
    
    print("\nTop Error Endpoints:")
    error_stats = sorted([s for s in environment.stats.entries.values() if s.num_failures > 0],
                        key=lambda x: x.num_failures, reverse=True)
    for i, stat in enumerate(error_stats[:5]):
        print(f"{i+1}. {stat.name}: {stat.num_failures} failures")
    
    print("=" * 60)