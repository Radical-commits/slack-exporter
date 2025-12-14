# Slack Channel Exporter

Export Slack channel messages and thread replies to individual markdown files for easy analysis. Each thread is exported to its own file, perfect for multi-agent AI analysis. Uses browser authentication (token + cookie) to access Slack's API.

## Features

- **Individual thread files**: Each thread exported to separate markdown file
- **Organized structure**: Files organized in `channel/threads/` directories
- **Rich metadata**: Thread ID, participants, reply count, timestamps
- **User name resolution**: Converts user IDs to real names
- **Configurable standalone messages**: Choose whether to export messages without replies
- **Thread reply support**: Fetches all replies with proper hierarchy
- **Markdown output**: Clean format with timestamps and user information
- **Pagination support**: Handles large channels efficiently
- **Rate limiting**: Respectful to Slack's API

## Setup

1. **Install dependencies:**
   ```bash
   source .venv/bin/activate  # Activate virtual environment
   pip install -r requirements.txt
   ```

2. **Get your Slack credentials:**

   To get your browser token and cookie:

   a. Open Slack in your browser and log in

   b. Open Developer Tools (F12 or Right-click → Inspect)

   c. Go to the **Network** tab

   d. Refresh the page or perform an action in Slack

   e. Look for any request to `slack.com/api/` endpoints

   f. In the request headers, find:
      - **Authorization header**: Look for `Bearer xoxc-...` (your token starts with `xoxc-`)
      - **Cookie header**: Look for `d=xoxd-...` (your cookie value starts with `xoxd-`)

   **Important:** Keep these credentials secure and never commit them to version control!

3. **Get the channel ID:**

   - Right-click on the channel name in Slack
   - Select "View channel details"
   - Scroll down - the channel ID is at the bottom (format: C01234567)

## Usage

1. **Copy the example config:**
   ```bash
   cp config.example.json config.json
   ```

2. **Edit `config.json` with your credentials:**
   ```json
   {
     "slack_token": "xoxc-your-token-here",
     "slack_cookie": "xoxd-your-cookie-here",
     "channel_id": "C01234567",
     "days_back": 7,
     "include_replies": true,
     "output_directory": "./exports",
     "include_standalone_messages": false
   }
   ```

3. **Run the exporter:**
   ```bash
   python slack_exporter.py
   ```

## Output Format

### Directory Structure

```
exports/
  channel-name/
    threads/
      thread_1764228850_463429.md
      thread_1764305155_146539.md
      thread_1764401234_567890.md
      ...
```

### Individual Thread File Format

Each thread is exported to its own markdown file with rich metadata:

```markdown
# Thread: Getting error "Manage tags already in progress...

**Thread ID:** 1764228850.463429
**Channel:** #support
**Channel ID:** C01234567
**Started:** 2025-11-27 10:53:40
**Author:** John Doe
**Reply Count:** 15
**Participants:** Jane Smith, John Doe, Bob Johnson

---

## Parent Message

## Support Thread
**2025-11-27 10:53:40**

Reporter: @John Doe
Type: Failure
...

## Replies (15)

  > **John Doe** - 2025-11-27 10:55:22
  >
  > Our automated test failed, so I manually created...

  > **Bob Johnson** - 2025-11-27 11:31:32
  >
  > I can see that it tries to acquire a Redis lock...
```

## Configuration Options

- `slack_token`: Your browser token (xoxc-...) - **Required**
- `slack_cookie`: Your browser cookie (xoxd-...) - **Required**
- `channel_id`: The Slack channel ID to export - **Required**
- `days_back`: Number of days to look back (default: 7)
- `include_replies`: Whether to fetch thread replies (default: true) - **Must be true for thread exports**
- `output_directory`: Where to save export files (default: ./exports)
- `include_standalone_messages`: Whether to export messages without replies (default: false)

## Notes and Limitations

- **Authentication:** Browser tokens expire periodically. If you get authentication errors, fetch new credentials.
- **Rate Limiting:** The script includes delays between API calls to avoid rate limits.
- **Private Channels:** You can only export channels you're a member of.
- **Large Exports:** For channels with thousands of messages, consider using smaller time ranges.
- **Attachments:** File attachments are noted but not downloaded (just filename/URL).

## Troubleshooting

### "Slack API error: invalid_auth"
Your token or cookie has expired. Get fresh credentials from your browser.

### "Slack API error: channel_not_found"
Check that:
- The channel ID is correct
- You're a member of the channel
- You're logged into the correct workspace

### Rate limiting errors
The script includes delays, but if you hit limits, try:
- Reducing the time range
- Running exports less frequently
- Increasing sleep delays in the code

## Security

- Never commit `config.json` to version control
- Keep your tokens and cookies private
- Tokens can access your Slack workspace - treat them like passwords
- Consider using environment variables for credentials in production

## Example Use Cases

- **Multi-agent AI analysis**: Each thread file can be analyzed independently by different AI agents
- **Archive important discussions**: Keep permanent records of critical conversations
- **Analyze team communication patterns**: Study thread participation and response times
- **Create meeting summaries**: Extract key decisions and action items from threads
- **Backup critical channel information**: Preserve important technical discussions
- **Prepare data for ML/AI processing**: Clean, structured format ready for analysis

## Why Individual Thread Files?

The one-thread-per-file approach offers several advantages:

1. **Parallel Processing**: Multiple AI agents can analyze different threads simultaneously
2. **Context Isolation**: Each thread is self-contained with full context
3. **Easy Filtering**: Select specific threads by filename/timestamp/metadata
4. **Manageable Size**: Large channels split into digestible pieces
5. **Better Organization**: Find specific conversations easily by thread ID
