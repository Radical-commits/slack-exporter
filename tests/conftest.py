import pytest
from datetime import datetime
from slack_exporter import SlackExporter


@pytest.fixture
def slack_exporter():
    """Create a SlackExporter instance for testing."""
    return SlackExporter(token="xoxc-test-token", cookie="xoxd-test-cookie")


@pytest.fixture
def sample_message():
    """Create a sample Slack message."""
    return {
        "type": "message",
        "user": "U12345",
        "text": "Hello, this is a test message",
        "ts": "1234567890.123456",
        "thread_ts": "1234567890.123456",
        "reply_count": 0
    }


@pytest.fixture
def sample_message_with_replies():
    """Create a sample Slack message with replies."""
    return {
        "type": "message",
        "user": "U12345",
        "text": "Parent message",
        "ts": "1234567890.123456",
        "thread_ts": "1234567890.123456",
        "reply_count": 2,
        "replies": [
            {
                "type": "message",
                "user": "U67890",
                "text": "Reply 1",
                "ts": "1234567891.123456"
            },
            {
                "type": "message",
                "user": "U11111",
                "text": "Reply 2",
                "ts": "1234567892.123456"
            }
        ]
    }


@pytest.fixture
def sample_user_info():
    """Create sample user info."""
    return {
        "id": "U12345",
        "name": "testuser",
        "real_name": "Test User",
        "profile": {
            "display_name": "Test Display",
            "email": "test@example.com"
        }
    }


@pytest.fixture
def sample_channel_info():
    """Create sample channel info."""
    return {
        "id": "C12345",
        "name": "test-channel",
        "is_channel": True,
        "created": 1234567890,
        "num_members": 10
    }


@pytest.fixture
def mock_response_success():
    """Create a mock successful API response."""
    return {
        "ok": True,
        "messages": [],
        "has_more": False
    }


@pytest.fixture
def mock_response_error():
    """Create a mock error API response."""
    return {
        "ok": False,
        "error": "invalid_auth"
    }
