#!/usr/bin/env python3
"""
Slack Channel Exporter with Config File Support

Exports Slack messages to Markdown format based on config.json settings.
"""

import json
import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class SlackExporter:
    """Handles exporting messages from Slack channels using browser authentication."""

    def __init__(self, token: str, cookie: str):
        """
        Initialize the Slack exporter.

        Args:
            token: Slack browser token (xoxc-...)
            cookie: Slack browser cookie (d=...)
        """
        self.token = token
        self.cookie = cookie
        self.base_url = "https://slack.com/api"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Cookie": f"d={self.cookie}",
            "Content-Type": "application/x-www-form-urlencoded"
        })
        self.user_cache = {}

    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make a request to Slack API.

        Args:
            endpoint: API endpoint (e.g., 'conversations.history')
            params: Query parameters

        Returns:
            Response JSON as dictionary
        """
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get("ok"):
                error_msg = data.get("error", "Unknown error")
                raise Exception(f"Slack API error: {error_msg}")

            return data
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")

    def get_channel_info(self, channel_id: str) -> Dict:
        """
        Get information about a channel.

        Args:
            channel_id: Slack channel ID

        Returns:
            Channel information dictionary
        """
        data = self._make_request("conversations.info", {"channel": channel_id})
        return data.get("channel", {})

    def get_user_info(self, user_id: str) -> Dict:
        """
        Get information about a user.

        Args:
            user_id: Slack user ID

        Returns:
            User information dictionary
        """
        if user_id in self.user_cache:
            return self.user_cache[user_id]

        try:
            data = self._make_request("users.info", {"user": user_id})
            user_info = data.get("user", {})
            self.user_cache[user_id] = user_info
            return user_info
        except:
            return {}

    def fetch_messages(
        self,
        channel_id: str,
        days_back: int = 7,
        include_replies: bool = False
    ) -> List[Dict]:
        """
        Fetch messages from a channel for the specified time period.

        Args:
            channel_id: Slack channel ID
            days_back: Number of days to look back
            include_replies: Whether to fetch thread replies

        Returns:
            List of messages with optional replies
        """
        oldest_timestamp = (datetime.now() - timedelta(days=days_back)).timestamp()

        messages = []
        cursor = None

        print(f"Fetching messages from the last {days_back} days...")

        while True:
            params = {
                "channel": channel_id,
                "oldest": str(oldest_timestamp),
                "limit": 100
            }

            if cursor:
                params["cursor"] = cursor

            data = self._make_request("conversations.history", params)

            batch_messages = data.get("messages", [])
            messages.extend(batch_messages)

            print(f"Fetched {len(batch_messages)} messages (total: {len(messages)})")

            if not data.get("has_more"):
                break

            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

            time.sleep(1)

        messages.sort(key=lambda x: float(x.get("ts", 0)))

        if include_replies:
            messages = self._fetch_replies_for_messages(channel_id, messages)

        return messages

    def _fetch_replies_for_messages(self, channel_id: str, messages: List[Dict]) -> List[Dict]:
        """
        Fetch replies for messages that have threads.

        Args:
            channel_id: Slack channel ID
            messages: List of messages

        Returns:
            Messages with replies added
        """
        print("\nFetching replies for threaded messages...")

        for msg in messages:
            if msg.get("reply_count", 0) > 0:
                thread_ts = msg.get("ts")
                replies = self._fetch_thread_replies(channel_id, thread_ts)
                msg["replies"] = replies
                print(f"Fetched {len(replies)} replies for thread {thread_ts}")
                time.sleep(1)

        return messages

    def _fetch_thread_replies(self, channel_id: str, thread_ts: str) -> List[Dict]:
        """
        Fetch all replies in a thread.

        Args:
            channel_id: Slack channel ID
            thread_ts: Thread parent timestamp

        Returns:
            List of reply messages
        """
        params = {
            "channel": channel_id,
            "ts": thread_ts,
            "limit": 100
        }

        data = self._make_request("conversations.replies", params)

        all_messages = data.get("messages", [])
        return all_messages[1:] if len(all_messages) > 1 else []

    def export_threads_individually(
        self,
        messages: List[Dict],
        output_dir: str,
        channel_name: str,
        channel_id: str,
        days_back: int = 7,
        include_standalone: bool = False
    ):
        """
        Export each thread to its own markdown file.

        Args:
            messages: List of messages to export
            output_dir: Base output directory
            channel_name: Name of the channel
            channel_id: Channel ID
            days_back: Number of days exported
            include_standalone: Whether to export standalone messages without replies
        """
        # Create directory structure
        threads_dir = Path(output_dir) / channel_name / "threads"
        threads_dir.mkdir(parents=True, exist_ok=True)

        # Filter to thread parent messages only
        thread_parents = [
            msg for msg in messages
            if msg.get("thread_ts") == msg.get("ts")
        ]

        exported_count = 0
        skipped_count = 0

        print(f"\nExporting threads to {threads_dir}...")

        for parent_msg in thread_parents:
            replies = parent_msg.get("replies", [])
            has_replies = len(replies) > 0

            # Skip standalone messages if not included
            if not has_replies and not include_standalone:
                skipped_count += 1
                continue

            # Extract metadata
            metadata = self._extract_thread_metadata(parent_msg)
            thread_id = metadata["thread_id"].replace(".", "_")

            # Generate filename
            filename = f"thread_{thread_id}.md"
            file_path = threads_dir / filename

            # Write thread file
            with open(file_path, 'w', encoding='utf-8') as f:
                # Extract first 50 chars of message for title
                text = parent_msg.get("text", "")
                if not text:
                    blocks = parent_msg.get("blocks", [])
                    if blocks:
                        text = self._extract_text_from_blocks(blocks) or ""
                title = text[:50] + "..." if len(text) > 50 else text
                title = title.replace("\n", " ").strip()

                # Write header
                f.write(f"# Thread: {title}\n\n")
                f.write(f"**Thread ID:** {metadata['thread_id']}\n")
                f.write(f"**Channel:** #{channel_name}\n")
                f.write(f"**Channel ID:** {channel_id}\n")
                f.write(f"**Started:** {metadata['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Author:** {metadata['author']}\n")
                f.write(f"**Reply Count:** {metadata['reply_count']}\n")

                if metadata['participants']:
                    participants_str = ", ".join(metadata['participants'])
                    f.write(f"**Participants:** {participants_str}\n")

                f.write("\n---\n\n")

                # Write parent message
                f.write("## Parent Message\n\n")
                self._write_message_md(f, parent_msg, level=0)
                f.write("\n")

                # Write replies
                if has_replies:
                    f.write(f"\n## Replies ({len(replies)})\n\n")
                    for reply in replies:
                        self._write_message_md(f, reply, level=1)
                        f.write("\n")

            exported_count += 1

        print(f"\nExport complete!")
        print(f"  - Total threads found: {len(thread_parents)}")
        print(f"  - Exported: {exported_count} threads")
        if skipped_count > 0:
            print(f"  - Skipped: {skipped_count} standalone messages (no replies)")
        print(f"  - Standalone messages: {'included' if include_standalone else 'excluded'}")
        print(f"  - Location: {threads_dir}")

    def _extract_text_from_blocks(self, blocks: List[Dict]) -> Optional[str]:
        """
        Extract plain text from Slack blocks.

        Args:
            blocks: List of block objects

        Returns:
            Extracted text or None
        """
        text_parts = []

        for block in blocks:
            if block.get("type") == "rich_text":
                for element in block.get("elements", []):
                    if element.get("type") == "rich_text_section":
                        for item in element.get("elements", []):
                            if item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                            elif item.get("type") == "link":
                                link_text = item.get("text", item.get("url", ""))
                                url = item.get("url", "")
                                text_parts.append(f"[{link_text}]({url})")
                            elif item.get("type") == "user":
                                user_id = item.get("user_id", "unknown")
                                user_info = self.get_user_info(user_id)
                                if user_info:
                                    display_name = user_info.get("profile", {}).get("display_name", "")
                                    username = user_info.get("name", "")
                                    user_display = display_name or username or user_id
                                else:
                                    user_display = user_id
                                text_parts.append(f"@{user_display}")
                            elif item.get("type") == "emoji":
                                name = item.get("name", "")
                                text_parts.append(f":{name}:")

        return "".join(text_parts) if text_parts else None

    def _get_user_display(self, user_id: str, message: Dict) -> str:
        """
        Get display name for a user.

        Args:
            user_id: User ID
            message: Message object

        Returns:
            Display name
        """
        if message.get("subtype") == "bot_message":
            return message.get("username", "Bot")

        if not user_id:
            return "Unknown User"

        user_info = self.get_user_info(user_id)
        if user_info:
            real_name = user_info.get("real_name", "")
            display_name = user_info.get("profile", {}).get("display_name", "")
            username = user_info.get("name", "")

            return real_name or display_name or username or f"User {user_id}"

        return f"User {user_id}"

    def _get_thread_participants(self, parent_msg: Dict) -> List[str]:
        """
        Get unique participant names from thread.

        Args:
            parent_msg: Thread parent message

        Returns:
            Sorted list of unique participant names
        """
        participants = set()
        # Add parent author
        parent_user = parent_msg.get("user", "")
        if parent_user:
            participants.add(self._get_user_display(parent_user, parent_msg))

        # Add reply authors
        for reply in parent_msg.get("replies", []):
            reply_user = reply.get("user", "")
            if reply_user:
                participants.add(self._get_user_display(reply_user, reply))

        return sorted(list(participants))

    def _extract_thread_metadata(self, parent_msg: Dict) -> Dict:
        """
        Extract metadata from thread parent message.

        Args:
            parent_msg: Thread parent message

        Returns:
            Dictionary with thread metadata
        """
        ts = parent_msg.get("ts", "")
        try:
            timestamp = datetime.fromtimestamp(float(ts))
        except:
            timestamp = datetime.now()

        return {
            "thread_id": ts,
            "author": self._get_user_display(parent_msg.get("user", ""), parent_msg),
            "timestamp": timestamp,
            "reply_count": len(parent_msg.get("replies", [])),
            "participants": self._get_thread_participants(parent_msg)
        }

    def _write_message_md(
        self,
        file,
        message: Dict,
        level: int = 0
    ):
        """
        Write a single message to the markdown file.

        Args:
            file: File handle
            message: Message dictionary
            level: Indentation level (for replies)
        """
        indent = "  " * level

        # Get user info
        user_id = message.get("user", "")
        username = self._get_user_display(user_id, message)

        # Format timestamp
        ts = message.get("ts", "")
        try:
            timestamp = datetime.fromtimestamp(float(ts)).strftime('%Y-%m-%d %H:%M:%S')
        except:
            timestamp = ts

        # Get message text
        text = message.get("text", "")

        # Try to extract better text from blocks if available
        blocks = message.get("blocks", [])
        if blocks:
            block_text = self._extract_text_from_blocks(blocks)
            if block_text:
                text = block_text

        # Write message header
        if level == 0:
            file.write(f"## {username}\n")
            file.write(f"**{timestamp}**\n\n")
        else:
            file.write(f"{indent}> **{username}** - {timestamp}\n")
            file.write(f"{indent}>\n")

        # Write message content
        if text:
            if level == 0:
                file.write(f"{text}\n")
            else:
                for line in text.split('\n'):
                    file.write(f"{indent}> {line}\n")
                file.write(f"{indent}>\n")

        # Handle files
        files = message.get("files", [])
        if files:
            for file_obj in files:
                file_name = file_obj.get("name", "file")
                file_title = file_obj.get("title", file_name)
                permalink = file_obj.get("permalink", "")
                if level == 0:
                    file.write(f"\n**[File: {file_title}]({permalink})**\n")
                else:
                    file.write(f"{indent}> **[File: {file_title}]({permalink})**\n")


def load_config(config_file: str = "config.json") -> dict:
    """
    Load configuration from JSON file.

    Args:
        config_file: Path to config file

    Returns:
        Configuration dictionary
    """
    if not os.path.exists(config_file):
        raise FileNotFoundError(
            f"Config file '{config_file}' not found. "
            f"Copy config.example.json to config.json and fill in your details."
        )

    with open(config_file, 'r') as f:
        return json.load(f)


def main():
    """Main function to run the exporter with config file."""

    print("Slack Channel Exporter (Config Mode)")
    print("=" * 50)

    # Load config
    try:
        config = load_config()
    except FileNotFoundError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"\nError: Invalid JSON in config file: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract config values
    token = config.get("slack_token")
    cookie = config.get("slack_cookie")
    channel_id = config.get("channel_id")
    days_back = config.get("days_back", 7)
    include_replies = config.get("include_replies", False)
    output_dir = config.get("output_directory", "./exports")

    # Validate required fields
    if not token or not cookie or not channel_id:
        print("\nError: Missing required fields in config.json", file=sys.stderr)
        print("Required: slack_token, slack_cookie, channel_id", file=sys.stderr)
        sys.exit(1)

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Initialize exporter
    exporter = SlackExporter(token, cookie)

    try:
        # Get channel info
        print("\nFetching channel information...")
        channel_info = exporter.get_channel_info(channel_id)
        channel_name = channel_info.get("name", "unknown-channel")
        print(f"Channel: #{channel_name}")

        # Fetch messages
        messages = exporter.fetch_messages(
            channel_id,
            days_back=days_back,
            include_replies=include_replies
        )

        if not messages:
            print("\nNo messages found in the specified time period.")
            return

        # Export threads to individual files
        include_standalone = config.get("include_standalone_messages", False)
        exporter.export_threads_individually(
            messages,
            output_dir,
            channel_name,
            channel_id,
            days_back,
            include_standalone
        )

    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
