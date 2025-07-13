"""
Load tests for WebSocket endpoints
"""
from locust import User, task, between, events
import websocket
import json
import time
import threading
import random
from queue import Queue
from configs.settings import LoadTestConfig
from utils.auth import auth_manager

class WebSocketClient:
    """WebSocket client wrapper for load testing"""
    
    def __init__(self, url, headers=None):
        self.url = url
        self.headers = headers or []
        self.ws = None
        self.connected = False
        self.message_queue = Queue()
        self.receive_thread = None
        
    def connect(self):
        """Establish WebSocket connection"""
        try:
            self.ws = websocket.WebSocketApp(
                self.url,
                header=self.headers,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            # Start receiving thread
            self.receive_thread = threading.Thread(target=self.ws.run_forever)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            # Wait for connection
            timeout = 5
            start_time = time.time()
            while not self.connected and time.time() - start_time < timeout:
                time.sleep(0.1)
                
            return self.connected
            
        except Exception as e:
            print(f"WebSocket connection error: {e}")
            return False
    
    def on_open(self, ws):
        """Handle connection open"""
        self.connected = True
        
    def on_message(self, ws, message):
        """Handle incoming message"""
        self.message_queue.put(message)
        
    def on_error(self, ws, error):
        """Handle WebSocket error"""
        print(f"WebSocket error: {error}")
        
    def on_close(self, ws, close_status_code, close_msg):
        """Handle connection close"""
        self.connected = False
        
    def send(self, message):
        """Send message through WebSocket"""
        if self.connected and self.ws:
            if isinstance(message, dict):
                message = json.dumps(message)
            self.ws.send(message)
            return True
        return False
    
    def receive(self, timeout=1):
        """Receive message from queue"""
        try:
            message = self.message_queue.get(timeout=timeout)
            return message
        except:
            return None
    
    def close(self):
        """Close WebSocket connection"""
        if self.ws:
            self.ws.close()
            self.connected = False

class WebSocketUser(User):
    """Base WebSocket user for load testing"""
    
    wait_time = between(LoadTestConfig.DEFAULT_WAIT_TIME_MIN, LoadTestConfig.DEFAULT_WAIT_TIME_MAX)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token = None
        self.ws_clients = {}
        
    def on_start(self):
        """Setup authentication"""
        self.access_token = auth_manager.get_or_create_token()
        if not self.access_token:
            print("Failed to authenticate for WebSocket tests")
            self.environment.runner.quit()
    
    def on_stop(self):
        """Cleanup WebSocket connections"""
        for client in self.ws_clients.values():
            client.close()

class ConversationWebSocketUser(WebSocketUser):
    """Test conversation WebSocket endpoint"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conversation_id = None
        
    @task(5)
    def test_conversation_websocket(self):
        """Test real-time conversation WebSocket"""
        # First create a conversation
        if not self.conversation_id:
            self.create_conversation()
            
        if not self.conversation_id:
            return
            
        ws_url = f"{LoadTestConfig.WS_BASE_URL}/api/ws/conversations/{self.conversation_id}"
        headers = [f"Authorization: Bearer {self.access_token}"]
        
        # Track timing
        start_time = time.time()
        
        # Connect to WebSocket
        ws_client = WebSocketClient(ws_url, headers)
        connection_success = ws_client.connect()
        
        if connection_success:
            connect_time = int((time.time() - start_time) * 1000)
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="/api/ws/conversations/[id] [CONNECT]",
                response_time=connect_time,
                response_length=0,
                exception=None,
                context={}
            )
            
            # Send test messages
            for i in range(5):
                message = {
                    "type": "message",
                    "content": f"Test message {i} at {time.time()}",
                    "metadata": {"test": True, "index": i}
                }
                
                send_start = time.time()
                if ws_client.send(message):
                    send_time = int((time.time() - send_start) * 1000)
                    self.environment.events.request.fire(
                        request_type="WebSocket",
                        name="/api/ws/conversations/[id] [SEND]",
                        response_time=send_time,
                        response_length=len(json.dumps(message)),
                        exception=None,
                        context={}
                    )
                
                # Wait for response
                response = ws_client.receive(timeout=2)
                if response:
                    self.environment.events.request.fire(
                        request_type="WebSocket",
                        name="/api/ws/conversations/[id] [RECEIVE]",
                        response_time=0,
                        response_length=len(response),
                        exception=None,
                        context={}
                    )
                
                time.sleep(random.uniform(0.5, 1.5))
            
            # Close connection
            ws_client.close()
            
        else:
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="/api/ws/conversations/[id] [CONNECT]",
                response_time=5000,
                response_length=0,
                exception=Exception("Connection failed"),
                context={}
            )
    
    def create_conversation(self):
        """Create a test conversation"""
        headers = LoadTestConfig.get_headers(self.access_token)
        
        response = self.client.post(
            "/api/conversations",
            json={
                "title": f"WebSocket Test Conversation {random.randint(1, 10000)}",
                "type": "chat",
                "metadata": {"test": True}
            },
            headers=headers,
            catch_response=True
        )
        
        if response.status_code == 201:
            data = response.json()
            self.conversation_id = data.get("id")
            response.success()
        else:
            response.failure(f"Create conversation failed: {response.status_code}")

class VoiceStreamingWebSocketUser(WebSocketUser):
    """Test voice streaming WebSocket endpoints"""
    
    @task(3)
    def test_streaming_stt_websocket(self):
        """Test speech-to-text streaming WebSocket"""
        ws_url = f"{LoadTestConfig.WS_BASE_URL}/api/ws/voice/streaming-stt"
        headers = [f"Authorization: Bearer {self.access_token}"]
        
        start_time = time.time()
        ws_client = WebSocketClient(ws_url, headers)
        
        if ws_client.connect():
            connect_time = int((time.time() - start_time) * 1000)
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="/api/ws/voice/streaming-stt [CONNECT]",
                response_time=connect_time,
                response_length=0,
                exception=None,
                context={}
            )
            
            # Send configuration
            config = {
                "type": "config",
                "config": {
                    "sample_rate": 16000,
                    "encoding": "linear16",
                    "language": "en-US"
                }
            }
            ws_client.send(config)
            
            # Simulate sending audio chunks
            for i in range(10):
                # Simulate audio data (random bytes)
                audio_chunk = {
                    "type": "audio",
                    "audio": random.randbytes(1024).hex()  # Hex encoded audio
                }
                
                send_start = time.time()
                if ws_client.send(audio_chunk):
                    send_time = int((time.time() - send_start) * 1000)
                    self.environment.events.request.fire(
                        request_type="WebSocket",
                        name="/api/ws/voice/streaming-stt [SEND_AUDIO]",
                        response_time=send_time,
                        response_length=1024,
                        exception=None,
                        context={}
                    )
                
                # Check for transcription results
                result = ws_client.receive(timeout=0.5)
                if result:
                    self.environment.events.request.fire(
                        request_type="WebSocket",
                        name="/api/ws/voice/streaming-stt [RECEIVE_TRANSCRIPT]",
                        response_time=0,
                        response_length=len(result),
                        exception=None,
                        context={}
                    )
                
                time.sleep(0.1)  # Simulate real-time audio streaming
            
            ws_client.close()
        else:
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="/api/ws/voice/streaming-stt [CONNECT]",
                response_time=5000,
                response_length=0,
                exception=Exception("Connection failed"),
                context={}
            )

class TelephonyStreamingWebSocketUser(WebSocketUser):
    """Test telephony streaming WebSocket"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_ids = []
    
    @task(2)
    def test_telephony_stream_websocket(self):
        """Test telephony media streaming WebSocket"""
        # Generate a test call ID
        call_id = f"CA{random.randbytes(16).hex()}"
        
        ws_url = f"{LoadTestConfig.WS_BASE_URL}/api/ws/telephony/stream/{call_id}"
        headers = [f"Authorization: Bearer {self.access_token}"]
        
        start_time = time.time()
        ws_client = WebSocketClient(ws_url, headers)
        
        if ws_client.connect():
            connect_time = int((time.time() - start_time) * 1000)
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="/api/ws/telephony/stream/[id] [CONNECT]",
                response_time=connect_time,
                response_length=0,
                exception=None,
                context={}
            )
            
            # Simulate Twilio media stream messages
            # Start message
            start_msg = {
                "event": "start",
                "sequenceNumber": "1",
                "start": {
                    "streamSid": f"MZ{random.randbytes(16).hex()}",
                    "accountSid": "TEST_ACCOUNT_SID",
                    "callSid": call_id
                }
            }
            ws_client.send(start_msg)
            
            # Send media messages
            for i in range(20):
                media_msg = {
                    "event": "media",
                    "sequenceNumber": str(i + 2),
                    "media": {
                        "track": "inbound",
                        "chunk": str(i),
                        "timestamp": str(int(time.time() * 1000)),
                        "payload": random.randbytes(172).hex()  # Base64 encoded audio
                    }
                }
                
                if ws_client.send(media_msg):
                    self.environment.events.request.fire(
                        request_type="WebSocket",
                        name="/api/ws/telephony/stream/[id] [SEND_MEDIA]",
                        response_time=0,
                        response_length=172,
                        exception=None,
                        context={}
                    )
                
                time.sleep(0.02)  # 20ms chunks (typical for telephony)
            
            # Stop message
            stop_msg = {
                "event": "stop",
                "sequenceNumber": "999",
                "stop": {
                    "accountSid": "TEST_ACCOUNT_SID",
                    "callSid": call_id
                }
            }
            ws_client.send(stop_msg)
            
            ws_client.close()
        else:
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="/api/ws/telephony/stream/[id] [CONNECT]",
                response_time=5000,
                response_length=0,
                exception=Exception("Connection failed"),
                context={}
            )

class NotificationWebSocketUser(WebSocketUser):
    """Test notification WebSocket"""
    
    @task(4)
    def test_notification_websocket(self):
        """Test real-time notifications WebSocket"""
        ws_url = f"{LoadTestConfig.WS_BASE_URL}/api/ws/notifications"
        headers = [f"Authorization: Bearer {self.access_token}"]
        
        start_time = time.time()
        ws_client = WebSocketClient(ws_url, headers)
        
        if ws_client.connect():
            connect_time = int((time.time() - start_time) * 1000)
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="/api/ws/notifications [CONNECT]",
                response_time=connect_time,
                response_length=0,
                exception=None,
                context={}
            )
            
            # Subscribe to notification channels
            subscribe_msg = {
                "type": "subscribe",
                "channels": ["general", "calls", "calendar", "crm"]
            }
            ws_client.send(subscribe_msg)
            
            # Keep connection alive and receive notifications
            for i in range(30):  # 30 seconds
                # Send heartbeat
                if i % 10 == 0:
                    heartbeat = {"type": "ping"}
                    ws_client.send(heartbeat)
                
                # Check for notifications
                notification = ws_client.receive(timeout=1)
                if notification:
                    self.environment.events.request.fire(
                        request_type="WebSocket",
                        name="/api/ws/notifications [RECEIVE]",
                        response_time=0,
                        response_length=len(notification),
                        exception=None,
                        context={}
                    )
                
                time.sleep(1)
            
            ws_client.close()
        else:
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="/api/ws/notifications [CONNECT]",
                response_time=5000,
                response_length=0,
                exception=Exception("Connection failed"),
                context={}
            )

class WebSocketLoadTest(User):
    """Combined WebSocket load test scenarios"""
    
    wait_time = between(2, 5)
    tasks = [
        ConversationWebSocketUser,
        VoiceStreamingWebSocketUser,
        TelephonyStreamingWebSocketUser,
        NotificationWebSocketUser
    ]

# Event handlers
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Setup before WebSocket tests start"""
    print("Starting WebSocket load tests...")
    print(f"WebSocket base URL: {LoadTestConfig.WS_BASE_URL}")
    print(f"Heartbeat interval: {LoadTestConfig.WS_HEARTBEAT_INTERVAL}s")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Cleanup after WebSocket tests stop"""
    print("WebSocket load tests completed.")
    print(f"Total WebSocket operations: {environment.stats.total.num_requests}")
    print(f"Total WebSocket failures: {environment.stats.total.num_failures}")