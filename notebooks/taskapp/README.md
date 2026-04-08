# Weekly Task Manager

A Python app that emails you your weekly tasks every Monday at 7am MST.
Reply to the email with simple commands to add, complete, delete, and reprioritize tasks.

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Enable the Gmail API

1. Go to https://console.cloud.google.com/
2. Create a new project (or use an existing one)
3. Go to **APIs & Services → Library** and enable **Gmail API**
4. Go to **APIs & Services → Credentials**
5. Click **Create Credentials → OAuth client ID**
   - Application type: **Desktop app**
6. Download the JSON file and save it as `credentials.json` in this folder

### 3. Set your email address

Edit `main.py` and set your email:

```python
TO_EMAIL = "you@gmail.com"
```

Or set the environment variable:

```bash
export TASK_EMAIL="you@gmail.com"
```

### 4. Authenticate (first run)

Run the app once — a browser window will open asking you to authorize Gmail access:

```bash
python main.py send
```

After authorizing, a `token.json` file is saved and reused automatically.

---

## Running the app

### Start the scheduler (runs continuously)

```bash
python main.py
```

This will:
- Send you a digest every **Monday at 7:00am MST**
- Check for reply commands every **5 minutes**

### Manual commands (for testing)

```bash
python main.py send   # Send a digest right now
python main.py poll   # Check for replies right now
```

---

## Email Commands

Reply to any digest email with these commands (one per line):

| Command | Description | Example |
|---|---|---|
| `ADD <task> [#project] [!priority]` | Add a new task | `ADD Buy milk #personal !low` |
| `DONE <id>` | Mark task complete | `DONE 5` |
| `DELETE <id>` | Delete a task | `DELETE 3` |
| `EDIT <id> <new title>` | Rename a task | `EDIT 2 Write monthly report` |
| `PRIORITY <id> <high\|medium\|low>` | Change priority | `PRIORITY 4 high` |
| `PROJECT <id> <name>` | Move to project | `PROJECT 7 personal` |
| `LIST` | Get current task list now | `LIST` |
| `HELP` | Show command reference | `HELP` |

**Priority shortcuts:** `!h` / `!hi` = high, `!m` / `!med` = medium, `!l` / `!lo` = low

---

## Project Structure

```
weekly_tasks/
├── main.py          # Scheduler + entry point
├── db.py            # SQLite database layer (CRUD)
├── commands.py      # Email reply command parser
├── executor.py      # Command → database action
├── formatter.py     # Email HTML/text builder
├── gmail.py         # Gmail API (send + poll)
├── requirements.txt
├── README.md
├── credentials.json # ← you provide this (Gmail OAuth)
├── token.json       # ← auto-generated after first auth
└── tasks.db         # ← auto-generated SQLite database
```

---

## Running as a background service (optional)

### macOS — launchd

Create `~/Library/LaunchAgents/com.weeklytasks.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.weeklytasks</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/path/to/weekly_tasks/main.py</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>EnvironmentVariables</key>
  <dict>
    <key>TASK_EMAIL</key><string>you@gmail.com</string>
  </dict>
</dict>
</plist>
```

Then: `launchctl load ~/Library/LaunchAgents/com.weeklytasks.plist`

### Linux — systemd

```ini
[Unit]
Description=Weekly Task Manager

[Service]
ExecStart=/usr/bin/python3 /path/to/weekly_tasks/main.py
Environment=TASK_EMAIL=you@gmail.com
Restart=always

[Install]
WantedBy=multi-user.target
```
