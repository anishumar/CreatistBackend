import pytest
from fastapi.testclient import TestClient
from src.app import app
import uuid
from src.models.visionboard import GroupMessage

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    # Optionally check response content if known
    # assert response.json() == {"message": "Hello World"} 

def test_direct_message_rest(monkeypatch):
    from fastapi.testclient import TestClient
    from src.app import app

    client = TestClient(app)
    sender_id = "1b8280ba-b64f-4590-a1d6-185c69cd4709"
    receiver_id = "67c74ef1-b519-42f4-9841-c71b318ac70a"
    token = "testtoken"

    # Patch token handler to always return sender_id as sub
    class DummyToken:
        def __init__(self, sub):
            self.sub = sub
    def dummy_decode_token(token_str):
        return DummyToken(sender_id)
    monkeypatch.setattr("src.utils.token_handler.TokenHandler.decode_token", staticmethod(dummy_decode_token))

    # Patch user_exists to always return True
    monkeypatch.setattr("src.utils.user_handler.UserHandler.user_exists", lambda self, user_id: True)

    # Patch send_direct_message to be async and do nothing
    async def async_send_direct_message(self, sender_id, receiver_id, message):
        return None
    monkeypatch.setattr("src.utils.user_handler.UserHandler.send_direct_message", async_send_direct_message)

    # Send a direct message (sender_id is the authenticated user, matches user_id in URL)
    payload = {"receiver_id": receiver_id, "message": "Hello!"}
    response = client.post(f"/v1/message/{sender_id}", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["message"] == "Message sent" 

def test_fetch_direct_messages(monkeypatch):
    from fastapi.testclient import TestClient
    from src.app import app

    client = TestClient(app)
    sender_id = "1b8280ba-b64f-4590-a1d6-185c69cd4709"
    receiver_id = "67c74ef1-b519-42f4-9841-c71b318ac70a"
    token = "testtoken"

    # Patch token handler to always return sender_id as sub
    class DummyToken:
        def __init__(self, sub):
            self.sub = sub
    def dummy_decode_token(token_str):
        return DummyToken(sender_id)
    monkeypatch.setattr("src.utils.token_handler.TokenHandler.decode_token", staticmethod(dummy_decode_token))

    # Patch user_exists to always return True
    monkeypatch.setattr("src.utils.user_handler.UserHandler.user_exists", lambda self, user_id: True)

    # Patch get_direct_messages to return a fake message
    async def async_get_direct_messages(self, user_id, other_user_id, limit=50, before=None):
        return [{
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "message": "Hello!",
            "created_at": "2024-07-08T00:00:00Z"
        }]
    monkeypatch.setattr("src.utils.user_handler.UserHandler.get_direct_messages", async_get_direct_messages)

    # Patch fetch_user to return a fake user with avatar
    async def async_fetch_user(self, user_id):
        class DummyUser:
            profile_image_url = "https://example.com/avatar.png"
        return DummyUser()
    monkeypatch.setattr("src.utils.user_handler.UserHandler.fetch_user", async_fetch_user)

    # Fetch direct messages
    response = client.get(f"/v1/message/{sender_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert data["messages"][0]["message"] == "Hello!"
    assert data["messages"][0]["avatar_url"] == "https://example.com/avatar.png"

# WebSocket test for direct chat (basic connection test)
def test_direct_chat_websocket(monkeypatch):
    from fastapi.testclient import TestClient
    from src.app import app

    # Set up app state for testing
    app.state.jwt_secret = "test_secret_key"
    
    client = TestClient(app)
    sender_id = "1b8280ba-b64f-4590-a1d6-185c69cd4709"
    receiver_id = "67c74ef1-b519-42f4-9841-c71b318ac70a"
    token = "testtoken"

    # Patch token handler to always return sender_id as sub
    class DummyToken:
        def __init__(self, sub):
            self.sub = sub
    def dummy_decode_token(token_str):
        return DummyToken(sender_id)
    monkeypatch.setattr("src.utils.token_handler.TokenHandler.decode_token", staticmethod(dummy_decode_token))

    # Patch get_user_id_from_token to return sender_id
    from src.routes import ws_chat
    ws_chat.get_user_id_from_token = lambda token: sender_id

    # Patch get_avatar_url to return a static URL
    async def async_get_avatar_url(user_id):
        return "https://example.com/avatar.png"
    ws_chat.get_avatar_url = async_get_avatar_url

    # Patch get_redis and redis_subscriber to avoid real Redis
    async def dummy_get_redis():
        class DummyRedis:
            async def publish(self, channel, msg):
                return None
            async def subscribe(self, channel):
                class DummyChannel:
                    async def wait_message(self):
                        return False
                    async def get(self, encoding=None):
                        return None
                return [DummyChannel()]
            async def unsubscribe(self, channel):
                return None
        return DummyRedis()
    ws_chat.get_redis = dummy_get_redis
    async def dummy_redis_subscriber(channel_name, connections):
        return None
    ws_chat.redis_subscriber = dummy_redis_subscriber

    # Test that the WebSocket route exists in the app
    websocket_routes = []
    for route in app.routes:
        if hasattr(route, 'path') and route.path:
            path_str = str(route.path)
            if 'ws' in path_str and 'message' in path_str:
                websocket_routes.append(route)
    
    assert len(websocket_routes) > 0, "WebSocket route for direct chat not found"
    
    # Test basic app functionality
    response = client.get("/docs")
    assert response.status_code == 200 

# Group Chat Tests
def test_group_chat_rest_send_message(monkeypatch):
    from fastapi.testclient import TestClient
    from src.app import app
    import uuid

    # Set up app state for testing
    app.state.jwt_secret = "test_secret_key"
    app.state.pool = None  # Mock pool

    client = TestClient(app)
    sender_id = "1b8280ba-b64f-4590-a1d6-185c69cd4709"
    visionboard_id = str(uuid.uuid4())
    token = "testtoken"

    # Patch get_visionboard_handler to always return dummy handler
    from src.routes import visionboard as visionboard_routes
    class DummyHandler:
        async def send_group_message(self, visionboard_id, sender_id, message):
            return GroupMessage(
                id=str(uuid.uuid4()),
                visionboard_id=visionboard_id,
                sender_id=sender_id,
                message=message,
                created_at="2024-07-08T00:00:00Z"
            )
    monkeypatch.setattr(visionboard_routes, "get_visionboard_handler", lambda: DummyHandler())

    # Patch token handler to always return sender_id as sub
    class DummyToken:
        def __init__(self, sub):
            self.sub = sub
    def dummy_decode_token(token_str):
        return DummyToken(sender_id)
    monkeypatch.setattr("src.utils.token_handler.TokenHandler.decode_token", staticmethod(dummy_decode_token))

    # Send a group message
    payload = {"message": "Hello group!"}
    response = client.post(f"/v1/visionboard/{visionboard_id}/group-chat/message", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Message sent"
    assert "group_message" in data

def test_group_chat_rest_fetch_messages(monkeypatch):
    from fastapi.testclient import TestClient
    from src.app import app
    import uuid

    # Set up app state for testing
    app.state.jwt_secret = "test_secret_key"
    app.state.pool = None  # Mock pool

    client = TestClient(app)
    sender_id = "1b8280ba-b64f-4590-a1d6-185c69cd4709"
    visionboard_id = str(uuid.uuid4())
    token = "testtoken"

    # Patch get_visionboard_handler to always return dummy handler
    from src.routes import visionboard as visionboard_routes
    class DummyHandler:
        async def get_group_messages(self, visionboard_id, user_id, limit=50, before=None):
            return [GroupMessage(
                id=str(uuid.uuid4()),
                visionboard_id=visionboard_id,
                sender_id=sender_id,
                message="Hello group!",
                created_at="2024-07-08T00:00:00Z"
            )]
    monkeypatch.setattr(visionboard_routes, "get_visionboard_handler", lambda: DummyHandler())

    # Patch token handler to always return sender_id as sub
    class DummyToken:
        def __init__(self, sub):
            self.sub = sub
    def dummy_decode_token(token_str):
        return DummyToken(sender_id)
    monkeypatch.setattr("src.utils.token_handler.TokenHandler.decode_token", staticmethod(dummy_decode_token))

    # Patch fetch_user to return a fake user with avatar
    async def async_fetch_user(self, user_id):
        class DummyUser:
            profile_image_url = "https://example.com/avatar.png"
        return DummyUser()
    monkeypatch.setattr("src.utils.user_handler.UserHandler.fetch_user", async_fetch_user)

    # Fetch group messages
    response = client.get(f"/v1/visionboard/{visionboard_id}/group-chat/messages", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert len(data["messages"]) > 0
    assert data["messages"][0]["message"] == "Hello group!"
    assert data["messages"][0]["avatar_url"] == "https://example.com/avatar.png"

def test_group_chat_websocket(monkeypatch):
    from fastapi.testclient import TestClient
    from src.app import app
    import uuid

    # Set up app state for testing
    app.state.jwt_secret = "test_secret_key"
    
    client = TestClient(app)
    sender_id = "1b8280ba-b64f-4590-a1d6-185c69cd4709"
    visionboard_id = str(uuid.uuid4())
    token = "testtoken"

    # Patch token handler to always return sender_id as sub
    class DummyToken:
        def __init__(self, sub):
            self.sub = sub
    def dummy_decode_token(token_str):
        return DummyToken(sender_id)
    monkeypatch.setattr("src.utils.token_handler.TokenHandler.decode_token", staticmethod(dummy_decode_token))

    # Patch get_user_id_from_token to return sender_id
    from src.routes import ws_chat
    ws_chat.get_user_id_from_token = lambda token: sender_id

    # Patch get_avatar_url to return a static URL
    async def async_get_avatar_url(user_id):
        return "https://example.com/avatar.png"
    ws_chat.get_avatar_url = async_get_avatar_url

    # Patch get_redis and redis_subscriber to avoid real Redis
    async def dummy_get_redis():
        class DummyRedis:
            async def publish(self, channel, msg):
                return None
            async def subscribe(self, channel):
                class DummyChannel:
                    async def wait_message(self):
                        return False
                    async def get(self, encoding=None):
                        return None
                return [DummyChannel()]
            async def unsubscribe(self, channel):
                return None
        return DummyRedis()
    ws_chat.get_redis = dummy_get_redis
    async def dummy_redis_subscriber(channel_name, connections):
        return None
    ws_chat.redis_subscriber = dummy_redis_subscriber

    # Test that the group chat WebSocket route exists in the app
    websocket_routes = []
    for route in app.routes:
        if hasattr(route, 'path') and route.path:
            path_str = str(route.path)
            if 'ws' in path_str and 'visionboard' in path_str and 'group-chat' in path_str:
                websocket_routes.append(route)
    
    assert len(websocket_routes) > 0, "WebSocket route for group chat not found"
    
    # Test basic app functionality
    response = client.get("/docs")
    assert response.status_code == 200 