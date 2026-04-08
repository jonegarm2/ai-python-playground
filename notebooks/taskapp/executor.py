"""
executor.py — Execute parsed commands against the database
"""
from commands import ParsedCommand, parse_email_body
from db import add_task, get_task, delete_task, mark_done, set_priority, update_task, list_tasks


def execute_command(cmd: ParsedCommand) -> dict:
    raw = cmd.raw

    if cmd.error or cmd.action == "UNKNOWN":
        return {"cmd": raw, "ok": False, "message": cmd.error or "Unknown command.", "task": None}

    try:
        if cmd.action == "ADD":
            task = add_task(cmd.title, cmd.list_name or "work", cmd.priority or "medium")
            return {
                "cmd": raw, "ok": True,
                "message": f"Added #{task['id']}: \"{task['title']}\" "
                           f"[{task['list']}] [{task['priority']}]",
                "task": task,
            }

        # All remaining actions need an existing task
        if cmd.action in ("DONE", "DELETE", "EDIT", "PRIORITY", "MOVE"):
            task = get_task(cmd.task_id)
            if not task:
                return {"cmd": raw, "ok": False,
                        "message": f"Task #{cmd.task_id} not found.", "task": None}

        if cmd.action == "DONE":
            task = mark_done(cmd.task_id)
            return {"cmd": raw, "ok": True,
                    "message": f"Marked #{cmd.task_id} done: \"{task['title']}\"", "task": task}

        if cmd.action == "DELETE":
            title = task["title"]
            delete_task(cmd.task_id)
            return {"cmd": raw, "ok": True,
                    "message": f"Deleted #{cmd.task_id}: \"{title}\"", "task": None}

        if cmd.action == "EDIT":
            task = update_task(cmd.task_id, title=cmd.title)
            return {"cmd": raw, "ok": True,
                    "message": f"Updated #{cmd.task_id} title to \"{task['title']}\"", "task": task}

        if cmd.action == "PRIORITY":
            task = set_priority(cmd.task_id, cmd.priority)
            return {"cmd": raw, "ok": True,
                    "message": f"Set #{cmd.task_id} priority to {cmd.priority}", "task": task}

        if cmd.action == "MOVE":
            old_list = task["list"]
            task = update_task(cmd.task_id, list=cmd.list_name)
            return {"cmd": raw, "ok": True,
                    "message": f"Moved #{cmd.task_id} from {old_list} → {cmd.list_name}",
                    "task": task}

        if cmd.action == "LIST":
            tasks = list_tasks("pending")
            count = len(tasks)
            return {"cmd": raw, "ok": True,
                    "message": f"You have {count} pending task{'s' if count != 1 else ''}.",
                    "task": None, "list_requested": True}

        if cmd.action == "HELP":
            return {"cmd": raw, "ok": True, "message": "Sending help.",
                    "task": None, "help_requested": True}

    except Exception as e:
        return {"cmd": raw, "ok": False, "message": f"Error: {e}", "task": None}

    return {"cmd": raw, "ok": False, "message": "Unhandled command.", "task": None}


def process_email_body(body: str) -> list[dict]:
    commands = parse_email_body(body)
    return [execute_command(cmd) for cmd in commands]
