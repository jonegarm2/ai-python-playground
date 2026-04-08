"""
commands.py — Parse plain-text email reply commands into actions
"""
import re
from dataclasses import dataclass
from typing import Optional


PRIORITY_ALIASES = {
    "h": "high", "hi": "high", "high": "high",
    "m": "medium", "med": "medium", "medium": "medium",
    "l": "low", "lo": "low", "low": "low",
}

LIST_ALIASES = {
    "work": "work", "w": "work", "job": "work", "office": "work",
    "house": "house", "home": "house", "h": "house", "personal": "house",
}

HELP_TEXT = """
📋 Weekly Task Manager — Commands

Tasks belong to one of two lists: WORK or HOUSE.
Incomplete tasks roll over to the next week automatically.

ADD <task> [#work|#house] [!priority]
  Add a new task. Defaults to #work.
  Examples:
    ADD Finish Q2 report #work !high
    ADD Fix the leaky faucet #house !medium
    ADD Call dentist #house

DONE <id>
  Mark a task as complete.
  Example: DONE 5

DELETE <id>
  Delete a task permanently.
  Example: DELETE 3

EDIT <id> <new title>
  Rename a task.
  Example: EDIT 2 Write monthly report instead

PRIORITY <id> <high|medium|low>
  Change a task's priority.
  Example: PRIORITY 4 high

MOVE <id> <work|house>
  Move a task to the other list.
  Example: MOVE 7 house

LIST
  Get your current task list right now.

HELP
  Show this message.
""".strip()


@dataclass
class ParsedCommand:
    action: str       # ADD, DONE, DELETE, EDIT, PRIORITY, MOVE, LIST, HELP, UNKNOWN
    task_id: Optional[int] = None
    title: Optional[str] = None
    list_name: Optional[str] = None
    priority: Optional[str] = None
    raw: str = ""
    error: Optional[str] = None


def parse_line(line: str) -> Optional[ParsedCommand]:
    line = line.strip()
    if not line or line.startswith(">") or line.startswith("--"):
        return None

    raw = line
    upper = line.upper()

    if re.match(r"^LIST\s*$", upper):
        return ParsedCommand(action="LIST", raw=raw)
    if re.match(r"^HELP\s*$", upper):
        return ParsedCommand(action="HELP", raw=raw)

    m = re.match(r"^DONE\s+(\d+)\s*$", upper)
    if m:
        return ParsedCommand(action="DONE", task_id=int(m.group(1)), raw=raw)

    m = re.match(r"^DELETE\s+(\d+)\s*$", upper)
    if m:
        return ParsedCommand(action="DELETE", task_id=int(m.group(1)), raw=raw)

    m = re.match(r"^PRIORITY\s+(\d+)\s+(\S+)\s*$", upper)
    if m:
        p = PRIORITY_ALIASES.get(m.group(2).lower())
        if not p:
            return ParsedCommand(action="UNKNOWN", raw=raw,
                                 error=f"Unknown priority '{m.group(2)}'. Use high/medium/low.")
        return ParsedCommand(action="PRIORITY", task_id=int(m.group(1)), priority=p, raw=raw)

    m = re.match(r"^MOVE\s+(\d+)\s+(\S+)\s*$", line, re.IGNORECASE)
    if m:
        lst = LIST_ALIASES.get(m.group(2).strip().lower())
        if not lst:
            return ParsedCommand(action="UNKNOWN", raw=raw,
                                 error=f"Unknown list '{m.group(2)}'. Use work or house.")
        return ParsedCommand(action="MOVE", task_id=int(m.group(1)), list_name=lst, raw=raw)

    m = re.match(r"^EDIT\s+(\d+)\s+(.+)$", line, re.IGNORECASE)
    if m:
        return ParsedCommand(action="EDIT", task_id=int(m.group(1)),
                             title=m.group(2).strip(), raw=raw)

    m = re.match(r"^ADD\s+(.+)$", line, re.IGNORECASE)
    if m:
        rest = m.group(1)
        list_name = "work"
        priority = "medium"

        # #work or #house
        lst_m = re.search(r"#(\S+)", rest)
        if lst_m:
            lst = LIST_ALIASES.get(lst_m.group(1).lower())
            if lst:
                list_name = lst
            rest = rest.replace(lst_m.group(0), "").strip()

        # !priority
        pri_m = re.search(r"!(\S+)", rest)
        if pri_m:
            p = PRIORITY_ALIASES.get(pri_m.group(1).lower())
            if p:
                priority = p
            rest = rest.replace(pri_m.group(0), "").strip()

        title = re.sub(r"\s+", " ", rest).strip()
        if not title:
            return ParsedCommand(action="UNKNOWN", raw=raw, error="ADD requires a task title.")
        return ParsedCommand(action="ADD", title=title, list_name=list_name,
                             priority=priority, raw=raw)

    return ParsedCommand(action="UNKNOWN", raw=raw,
                         error=f"Unrecognized command: '{line}'. Reply HELP for usage.")


def parse_email_body(body: str) -> list[ParsedCommand]:
    commands = []
    for line in body.splitlines():
        cmd = parse_line(line)
        if cmd is not None:
            commands.append(cmd)
    return commands
