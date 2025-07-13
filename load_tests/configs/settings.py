"""
Load test configuration settings
"""
import os
from typing import Dict, Any

class LoadTestConfig:
    # Base URL configuration - automatically detects environment  
    BASE_URL = os.getenv("LOAD_TEST_BASE_URL", "http://localhost:8001")
    
    # Authentication settings - sensible defaults for load testing
    TEST_USER_EMAIL = os.getenv("LOAD_TEST_USER_EMAIL", "loadtest@thanotopolis.com")
    TEST_USER_PASSWORD = os.getenv("LOAD_TEST_USER_PASSWORD", "LoadTest2025!")
    TEST_ORGANIZATION_NAME = os.getenv("LOAD_TEST_ORG_NAME", "Load Testing Organization")
    
    # Load test parameters
    DEFAULT_WAIT_TIME_MIN = 1  # seconds
    DEFAULT_WAIT_TIME_MAX = 3  # seconds
    
    # Request timeouts
    DEFAULT_TIMEOUT = 30  # seconds
    WEBSOCKET_TIMEOUT = 60  # seconds
    
    # Rate limiting consideration
    RATE_LIMIT_PER_MINUTE = 120
    
    # Test data sizes
    BATCH_SIZE = 10
    MAX_CONTACTS_PER_USER = 100
    MAX_EVENTS_PER_USER = 50
    
    # WebSocket settings - automatically converts HTTP to WS URL
    WS_BASE_URL = os.getenv("LOAD_TEST_WS_URL", BASE_URL.replace("https://", "wss://").replace("http://", "ws://"))
    WS_HEARTBEAT_INTERVAL = 30  # seconds
    
    # External service simulation
    SIMULATE_EXTERNAL_SERVICES = os.getenv("SIMULATE_EXTERNAL_SERVICES", "true").lower() == "true"
    
    @staticmethod
    def get_headers(token: str = None) -> Dict[str, str]:
        """Get default headers for requests"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
    
    @staticmethod
    def get_test_contact_data(index: int = 0) -> Dict[str, Any]:
        """Generate test contact data"""
        return {
            "first_name": f"Test{index}",
            "last_name": f"Contact{index}",
            "email": f"test{index}@example.com",
            "phone": f"+1555{index:07d}",
            "company": f"Test Company {index}",
            "deceased_name": f"Deceased {index}",
            "deceased_date_of_birth": "1950-01-01",
            "deceased_date_of_death": "2024-01-01",
            "plot_number": f"PLOT-{index:04d}",
            "service_type": "burial",
            "contract_status": "active",
            "contract_value_cents": 500000,
            "balance_cents": 100000,
            "is_veteran": index % 5 == 0,
            "religious_affiliation": "Non-denominational",
            "cultural_preferences": "Standard service",
            "family_relationship": "Spouse",
            "notes": f"Load test contact {index}"
        }
    
    @staticmethod
    def get_test_event_data(contact_id: str = None, index: int = 0) -> Dict[str, Any]:
        """Generate test event data"""
        return {
            "title": f"Test Event {index}",
            "description": f"Load test event description {index}",
            "start_time": "2025-01-15T10:00:00",
            "end_time": "2025-01-15T11:00:00",
            "event_type": "appointment",
            "contact_id": contact_id,
            "location": f"Test Location {index}",
            "reminder_minutes": 30,
            "status": "scheduled"
        }