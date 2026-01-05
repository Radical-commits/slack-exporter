import pytest
import json
from unittest.mock import Mock, mock_open
from datetime import datetime
from slack_exporter import SlackExporter, load_config


class TestSlackExporterInit:
    """Tests for SlackExporter initialization."""

    def test_init_sets_token_and_cookie(self):
        """Test that initialization sets token and cookie correctly."""
        exporter = SlackExporter(token="test_token", cookie="test_cookie")
        assert exporter.token == "test_token"
        assert exporter.cookie == "test_cookie"

    def test_init_sets_base_url(self):
        """Test that initialization sets the correct base URL."""
        exporter = SlackExporter(token="test_token", cookie="test_cookie")
        assert exporter.base_url == "https://slack.com/api"

    def test_init_creates_session_with_headers(self):
        """Test that initialization creates a session with correct headers."""
        exporter = SlackExporter(token="test_token", cookie="test_cookie")
        assert "Authorization" in exporter.session.headers
        assert exporter.session.headers["Authorization"] == "Bearer test_token"
        assert "Cookie" in exporter.session.headers
        assert exporter.session.headers["Cookie"] == "d=test_cookie"

    def test_init_creates_empty_user_cache(self):
        """Test that initialization creates an empty user cache."""
        exporter = SlackExporter(token="test_token", cookie="test_cookie")
        assert exporter.user_cache == {}


class TestMakeRequest:
    """Tests for _make_request method."""

    def test_make_request_success(self, slack_exporter, mocker, mock_response_success):
        """Test successful API request."""
        mock_get = mocker.patch.object(
            slack_exporter.session,
            'get',
            return_value=Mock(json=lambda: mock_response_success)
        )

        result = slack_exporter._make_request("test.endpoint", {"param": "value"})

        assert result == mock_response_success
        mock_get.assert_called_once_with(
            "https://slack.com/api/test.endpoint",
            params={"param": "value"}
        )

    def test_make_request_api_error(self, slack_exporter, mocker, mock_response_error):
        """Test API request with Slack API error."""
        mocker.patch.object(
            slack_exporter.session,
            'get',
            return_value=Mock(json=lambda: mock_response_error)
        )

        with pytest.raises(Exception, match="Slack API error: invalid_auth"):
            slack_exporter._make_request("test.endpoint")

    def test_make_request_network_error(self, slack_exporter, mocker):
        """Test API request with network error."""
        import requests
        mocker.patch.object(
            slack_exporter.session,
            'get',
            side_effect=requests.exceptions.RequestException("Network error")
        )

        with pytest.raises(Exception, match="Request failed"):
            slack_exporter._make_request("test.endpoint")


class TestGetChannelInfo:
    """Tests for get_channel_info method."""

    def test_get_channel_info_success(self, slack_exporter, sample_channel_info, mocker):
        """Test successful channel info retrieval."""
        mocker.patch.object(
            slack_exporter,
            '_make_request',
            return_value={"ok": True, "channel": sample_channel_info}
        )

        result = slack_exporter.get_channel_info("C12345")

        assert result == sample_channel_info

    def test_get_channel_info_empty(self, slack_exporter, mocker):
        """Test channel info retrieval with no channel data."""
        mocker.patch.object(
            slack_exporter,
            '_make_request',
            return_value={"ok": True}
        )

        result = slack_exporter.get_channel_info("C12345")

        assert result == {}


class TestGetUserInfo:
    """Tests for get_user_info method."""

    def test_get_user_info_success(self, slack_exporter, sample_user_info, mocker):
        """Test successful user info retrieval."""
        mocker.patch.object(
            slack_exporter,
            '_make_request',
            return_value={"ok": True, "user": sample_user_info}
        )

        result = slack_exporter.get_user_info("U12345")

        assert result == sample_user_info
        assert slack_exporter.user_cache["U12345"] == sample_user_info

    def test_get_user_info_from_cache(self, slack_exporter, sample_user_info):
        """Test user info retrieval from cache."""
        slack_exporter.user_cache["U12345"] = sample_user_info

        result = slack_exporter.get_user_info("U12345")

        assert result == sample_user_info

    def test_get_user_info_error_returns_empty(self, slack_exporter, mocker):
        """Test user info retrieval error returns empty dict."""
        mocker.patch.object(
            slack_exporter,
            '_make_request',
            side_effect=Exception("API error")
        )

        result = slack_exporter.get_user_info("U12345")

        assert result == {}


class TestGetUserDisplay:
    """Tests for _get_user_display method."""

    def test_get_user_display_bot_message(self, slack_exporter):
        """Test display name for bot messages."""
        message = {"subtype": "bot_message", "username": "TestBot"}

        result = slack_exporter._get_user_display("U12345", message)

        assert result == "TestBot"

    def test_get_user_display_no_user_id(self, slack_exporter):
        """Test display name when no user ID provided."""
        result = slack_exporter._get_user_display("", {})

        assert result == "Unknown User"

    def test_get_user_display_with_real_name(self, slack_exporter, sample_user_info, mocker):
        """Test display name retrieval with real name."""
        mocker.patch.object(slack_exporter, 'get_user_info', return_value=sample_user_info)

        result = slack_exporter._get_user_display("U12345", {})

        assert result == "Test User"

    def test_get_user_display_fallback_to_username(self, slack_exporter, mocker):
        """Test display name fallback to username."""
        user_info = {"name": "testuser", "profile": {}}
        mocker.patch.object(slack_exporter, 'get_user_info', return_value=user_info)

        result = slack_exporter._get_user_display("U12345", {})

        assert result == "testuser"


class TestExtractTextFromBlocks:
    """Tests for _extract_text_from_blocks method."""

    def test_extract_text_simple(self, slack_exporter):
        """Test extracting text from simple blocks."""
        blocks = [
            {
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_section",
                        "elements": [
                            {"type": "text", "text": "Hello world"}
                        ]
                    }
                ]
            }
        ]

        result = slack_exporter._extract_text_from_blocks(blocks)

        assert result == "Hello world"

    def test_extract_text_with_link(self, slack_exporter):
        """Test extracting text with links."""
        blocks = [
            {
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_section",
                        "elements": [
                            {"type": "text", "text": "Check "},
                            {"type": "link", "url": "https://example.com", "text": "this"}
                        ]
                    }
                ]
            }
        ]

        result = slack_exporter._extract_text_from_blocks(blocks)

        assert result == "Check [this](https://example.com)"

    def test_extract_text_empty_blocks(self, slack_exporter):
        """Test extracting text from empty blocks."""
        result = slack_exporter._extract_text_from_blocks([])

        assert result is None


class TestExtractThreadMetadata:
    """Tests for _extract_thread_metadata method."""

    def test_extract_metadata_basic(self, slack_exporter, sample_message, mocker):
        """Test extracting basic thread metadata."""
        mocker.patch.object(slack_exporter, '_get_user_display', return_value="Test User")
        mocker.patch.object(slack_exporter, '_get_thread_participants', return_value=["Test User"])

        result = slack_exporter._extract_thread_metadata(sample_message)

        assert result["thread_id"] == "1234567890.123456"
        assert result["author"] == "Test User"
        assert result["reply_count"] == 0
        assert isinstance(result["timestamp"], datetime)

    def test_extract_metadata_with_replies(self, slack_exporter, sample_message_with_replies, mocker):
        """Test extracting metadata from thread with replies."""
        mocker.patch.object(slack_exporter, '_get_user_display', return_value="Test User")
        mocker.patch.object(slack_exporter, '_get_thread_participants', return_value=["Test User", "User 2"])

        result = slack_exporter._extract_thread_metadata(sample_message_with_replies)

        assert result["reply_count"] == 2


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_success(self, mocker):
        """Test successful config loading."""
        config_data = {
            "slack_token": "xoxc-test",
            "slack_cookie": "xoxd-test",
            "channel_id": "C12345"
        }

        mocker.patch('os.path.exists', return_value=True)
        mocker.patch('builtins.open', mock_open(read_data=json.dumps(config_data)))

        result = load_config("config.json")

        assert result == config_data

    def test_load_config_file_not_found(self, mocker):
        """Test config loading when file doesn't exist."""
        mocker.patch('os.path.exists', return_value=False)

        with pytest.raises(FileNotFoundError, match="Config file 'config.json' not found"):
            load_config("config.json")


class TestFetchMessages:
    """Tests for fetch_messages method."""

    def test_fetch_messages_basic(self, slack_exporter, sample_message, mocker):
        """Test basic message fetching."""
        mock_response = {
            "ok": True,
            "messages": [sample_message],
            "has_more": False
        }
        mocker.patch.object(slack_exporter, '_make_request', return_value=mock_response)

        result = slack_exporter.fetch_messages("C12345", days_back=7, include_replies=False)

        assert len(result) == 1
        assert result[0] == sample_message

    def test_fetch_messages_with_pagination(self, slack_exporter, sample_message, mocker):
        """Test message fetching with pagination."""
        mock_response_1 = {
            "ok": True,
            "messages": [sample_message],
            "has_more": True,
            "response_metadata": {"next_cursor": "cursor123"}
        }
        mock_response_2 = {
            "ok": True,
            "messages": [sample_message],
            "has_more": False
        }

        mocker.patch.object(
            slack_exporter,
            '_make_request',
            side_effect=[mock_response_1, mock_response_2]
        )
        mocker.patch('time.sleep')

        result = slack_exporter.fetch_messages("C12345", days_back=7, include_replies=False)

        assert len(result) == 2


class TestGetThreadParticipants:
    """Tests for _get_thread_participants method."""

    def test_get_participants_parent_only(self, slack_exporter, sample_message, mocker):
        """Test getting participants with only parent message."""
        mocker.patch.object(slack_exporter, '_get_user_display', return_value="User 1")

        result = slack_exporter._get_thread_participants(sample_message)

        assert result == ["User 1"]

    def test_get_participants_with_replies(self, slack_exporter, sample_message_with_replies, mocker):
        """Test getting participants with replies."""
        mocker.patch.object(
            slack_exporter,
            '_get_user_display',
            side_effect=["User 1", "User 2", "User 3"]
        )

        result = slack_exporter._get_thread_participants(sample_message_with_replies)

        assert len(result) == 3
        assert "User 1" in result
        assert "User 2" in result
        assert "User 3" in result
