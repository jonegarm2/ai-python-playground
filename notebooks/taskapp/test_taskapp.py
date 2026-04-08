"""
test_taskapp.py — Unit tests for taskapp (no Gmail credentials needed)

Run:  cd taskapp && python -m pytest test_taskapp.py -v
"""
import importlib
import sys
from pathlib import Path
import pytest

# ── Helpers ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def use_temp_db(tmp_path, monkeypatch):
    """Redirect DB_PATH to a temp file so every test gets a clean database."""
    import db as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test_tasks.db")
    db_mod.init_db()
    yield


# ══════════════════════════════════════════════════════════════════════════════
# commands.py — parse_line
# ══════════════════════════════════════════════════════════════════════════════

class TestParseLineList:
    def test_list(self):
        from commands import parse_line
        cmd = parse_line("LIST")
        assert cmd.action == "LIST"

    def test_list_case_insensitive(self):
        from commands import parse_line
        cmd = parse_line("list")
        assert cmd.action == "LIST"

    def test_help(self):
        from commands import parse_line
        cmd = parse_line("HELP")
        assert cmd.action == "HELP"


class TestParseLineDone:
    def test_done(self):
        from commands import parse_line
        cmd = parse_line("DONE 5")
        assert cmd.action == "DONE"
        assert cmd.task_id == 5

    def test_done_lowercase(self):
        from commands import parse_line
        cmd = parse_line("done 12")
        assert cmd.action == "DONE"
        assert cmd.task_id == 12

    def test_done_no_id(self):
        from commands import parse_line
        cmd = parse_line("DONE")
        assert cmd.action == "UNKNOWN"


class TestParseLineDelete:
    def test_delete(self):
        from commands import parse_line
        cmd = parse_line("DELETE 3")
        assert cmd.action == "DELETE"
        assert cmd.task_id == 3


class TestParseLinePriority:
    def test_priority_high(self):
        from commands import parse_line
        cmd = parse_line("PRIORITY 2 high")
        assert cmd.action == "PRIORITY"
        assert cmd.task_id == 2
        assert cmd.priority == "high"

    def test_priority_alias_h(self):
        from commands import parse_line
        cmd = parse_line("PRIORITY 2 h")
        assert cmd.priority == "high"

    def test_priority_alias_lo(self):
        from commands import parse_line
        cmd = parse_line("PRIORITY 1 lo")
        assert cmd.priority == "low"

    def test_priority_invalid(self):
        from commands import parse_line
        cmd = parse_line("PRIORITY 1 urgent")
        assert cmd.action == "UNKNOWN"
        assert cmd.error


class TestParseLineMove:
    def test_move_to_house(self):
        from commands import parse_line
        cmd = parse_line("MOVE 4 house")
        assert cmd.action == "MOVE"
        assert cmd.task_id == 4
        assert cmd.list_name == "house"

    def test_move_alias_home(self):
        from commands import parse_line
        cmd = parse_line("MOVE 4 home")
        assert cmd.list_name == "house"

    def test_move_alias_w(self):
        from commands import parse_line
        cmd = parse_line("MOVE 4 w")
        assert cmd.list_name == "work"

    def test_move_invalid_list(self):
        from commands import parse_line
        cmd = parse_line("MOVE 4 garden")
        assert cmd.action == "UNKNOWN"


class TestParseLineEdit:
    def test_edit(self):
        from commands import parse_line
        cmd = parse_line("EDIT 3 New task title")
        assert cmd.action == "EDIT"
        assert cmd.task_id == 3
        assert cmd.title == "New task title"


class TestParseLineAdd:
    def test_add_simple(self):
        from commands import parse_line
        cmd = parse_line("ADD Buy milk")
        assert cmd.action == "ADD"
        assert cmd.title == "Buy milk"
        assert cmd.list_name == "work"
        assert cmd.priority == "medium"

    def test_add_with_list(self):
        from commands import parse_line
        cmd = parse_line("ADD Fix faucet #house")
        assert cmd.title == "Fix faucet"
        assert cmd.list_name == "house"

    def test_add_with_priority(self):
        from commands import parse_line
        cmd = parse_line("ADD Finish report !high")
        assert cmd.priority == "high"

    def test_add_with_list_and_priority(self):
        from commands import parse_line
        cmd = parse_line("ADD Prep presentation #work !h")
        assert cmd.list_name == "work"
        assert cmd.priority == "high"

    def test_add_no_title(self):
        from commands import parse_line
        cmd = parse_line("ADD #house !high")
        assert cmd.action == "UNKNOWN"

    def test_add_priority_alias_med(self):
        from commands import parse_line
        cmd = parse_line("ADD Something !med")
        assert cmd.priority == "medium"


class TestParseLineSkips:
    def test_empty_line(self):
        from commands import parse_line
        assert parse_line("") is None

    def test_quoted_line(self):
        from commands import parse_line
        assert parse_line("> DONE 1") is None

    def test_signature_separator(self):
        from commands import parse_line
        assert parse_line("-- ") is None


class TestParseEmailBody:
    def test_multiple_commands(self):
        from commands import parse_email_body
        body = "DONE 1\nDELETE 2\nADD New task #house"
        cmds = parse_email_body(body)
        assert len(cmds) == 3
        assert cmds[0].action == "DONE"
        assert cmds[1].action == "DELETE"
        assert cmds[2].action == "ADD"

    def test_skips_quoted_lines(self):
        from commands import parse_email_body
        body = "> On Mon you wrote:\nDONE 5"
        cmds = parse_email_body(body)
        assert len(cmds) == 1
        assert cmds[0].action == "DONE"


# ══════════════════════════════════════════════════════════════════════════════
# db.py — CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestAddTask:
    def test_add_returns_task(self):
        from db import add_task
        t = add_task("Buy groceries")
        assert t["id"] > 0
        assert t["title"] == "Buy groceries"
        assert t["list"] == "work"
        assert t["priority"] == "medium"
        assert t["status"] == "pending"

    def test_add_with_house_list(self):
        from db import add_task
        t = add_task("Fix sink", list_name="house")
        assert t["list"] == "house"

    def test_add_list_alias_home(self):
        from db import add_task
        t = add_task("Mow lawn", list_name="home")
        assert t["list"] == "house"

    def test_add_invalid_list_raises(self):
        from db import add_task
        with pytest.raises(ValueError):
            add_task("Task", list_name="invalid")


class TestGetTask:
    def test_get_existing(self):
        from db import add_task, get_task
        t = add_task("Test task")
        fetched = get_task(t["id"])
        assert fetched["title"] == "Test task"

    def test_get_nonexistent(self):
        from db import get_task
        assert get_task(9999) is None


class TestListTasks:
    def test_list_pending(self):
        from db import add_task, list_tasks, mark_done
        add_task("Task 1")
        t2 = add_task("Task 2")
        mark_done(t2["id"])
        pending = list_tasks("pending")
        assert len(pending) == 1
        assert pending[0]["title"] == "Task 1"

    def test_list_by_list_name(self):
        from db import add_task, list_tasks
        add_task("Work task", list_name="work")
        add_task("House task", list_name="house")
        work = list_tasks("pending", list_name="work")
        assert all(t["list"] == "work" for t in work)

    def test_list_sorted_by_priority(self):
        from db import add_task, list_tasks
        add_task("Low priority", priority="low")
        add_task("High priority", priority="high")
        tasks = list_tasks("pending", list_name="work")
        assert tasks[0]["priority"] == "high"
        assert tasks[-1]["priority"] == "low"


class TestUpdateTask:
    def test_update_title(self):
        from db import add_task, update_task
        t = add_task("Old title")
        updated = update_task(t["id"], title="New title")
        assert updated["title"] == "New title"

    def test_update_priority(self):
        from db import add_task, update_task
        t = add_task("Task")
        updated = update_task(t["id"], priority="high")
        assert updated["priority"] == "high"

    def test_update_nonexistent(self):
        from db import update_task
        assert update_task(9999, title="x") is None


class TestDeleteTask:
    def test_delete_existing(self):
        from db import add_task, delete_task, get_task
        t = add_task("To delete")
        assert delete_task(t["id"]) is True
        assert get_task(t["id"]) is None

    def test_delete_nonexistent(self):
        from db import delete_task
        assert delete_task(9999) is False


class TestMarkDone:
    def test_mark_done(self):
        from db import add_task, mark_done
        t = add_task("Task")
        done = mark_done(t["id"])
        assert done["status"] == "done"


class TestSetPriority:
    def test_set_priority_low(self):
        from db import add_task, set_priority
        t = add_task("Task")
        updated = set_priority(t["id"], "low")
        assert updated["priority"] == "low"

    def test_set_priority_invalid(self):
        from db import add_task, set_priority
        t = add_task("Task")
        with pytest.raises(ValueError):
            set_priority(t["id"], "urgent")


class TestWeeksPending:
    def test_new_task_zero_weeks(self):
        from db import add_task
        t = add_task("Brand new task")
        assert t["weeks_pending"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# executor.py — execute_command / process_email_body
# ══════════════════════════════════════════════════════════════════════════════

class TestExecuteAdd:
    def test_add_success(self):
        from commands import parse_line
        from executor import execute_command
        result = execute_command(parse_line("ADD Buy milk #house !low"))
        assert result["ok"] is True
        assert "Buy milk" in result["message"]
        assert result["task"]["list"] == "house"

    def test_add_unknown_command(self):
        from commands import parse_line
        from executor import execute_command
        result = execute_command(parse_line("BLAH blah"))
        assert result["ok"] is False


class TestExecuteDone:
    def test_done_success(self):
        from db import add_task
        from commands import parse_line
        from executor import execute_command
        t = add_task("Finish report")
        result = execute_command(parse_line(f"DONE {t['id']}"))
        assert result["ok"] is True
        assert result["task"]["status"] == "done"

    def test_done_not_found(self):
        from commands import parse_line
        from executor import execute_command
        result = execute_command(parse_line("DONE 9999"))
        assert result["ok"] is False
        assert "not found" in result["message"]


class TestExecuteDelete:
    def test_delete_success(self):
        from db import add_task, get_task
        from commands import parse_line
        from executor import execute_command
        t = add_task("Old task")
        result = execute_command(parse_line(f"DELETE {t['id']}"))
        assert result["ok"] is True
        assert get_task(t["id"]) is None

    def test_delete_not_found(self):
        from commands import parse_line
        from executor import execute_command
        result = execute_command(parse_line("DELETE 9999"))
        assert result["ok"] is False


class TestExecuteEdit:
    def test_edit_success(self):
        from db import add_task
        from commands import parse_line
        from executor import execute_command
        t = add_task("Old title")
        result = execute_command(parse_line(f"EDIT {t['id']} New title here"))
        assert result["ok"] is True
        assert result["task"]["title"] == "New title here"


class TestExecutePriority:
    def test_priority_success(self):
        from db import add_task
        from commands import parse_line
        from executor import execute_command
        t = add_task("Task")
        result = execute_command(parse_line(f"PRIORITY {t['id']} high"))
        assert result["ok"] is True
        assert result["task"]["priority"] == "high"


class TestExecuteMove:
    def test_move_success(self):
        from db import add_task
        from commands import parse_line
        from executor import execute_command
        t = add_task("Work task", list_name="work")
        result = execute_command(parse_line(f"MOVE {t['id']} house"))
        assert result["ok"] is True
        assert result["task"]["list"] == "house"


class TestExecuteList:
    def test_list_returns_count(self):
        from db import add_task
        from commands import parse_line
        from executor import execute_command
        add_task("Task A")
        add_task("Task B")
        result = execute_command(parse_line("LIST"))
        assert result["ok"] is True
        assert result.get("list_requested") is True
        assert "2" in result["message"]


class TestExecuteHelp:
    def test_help(self):
        from commands import parse_line
        from executor import execute_command
        result = execute_command(parse_line("HELP"))
        assert result["ok"] is True
        assert result.get("help_requested") is True


class TestProcessEmailBody:
    def test_multiple_commands(self):
        from db import add_task
        from executor import process_email_body
        t1 = add_task("First task")
        t2 = add_task("Second task")
        body = f"DONE {t1['id']}\nDELETE {t2['id']}\nADD Brand new task #house"
        results = process_email_body(body)
        assert len(results) == 3
        assert all(r["ok"] for r in results)

    def test_empty_body(self):
        from executor import process_email_body
        results = process_email_body("")
        assert results == []

    def test_only_quoted_text(self):
        from executor import process_email_body
        body = "> On Monday you wrote:\n> old stuff"
        results = process_email_body(body)
        assert results == []


# ══════════════════════════════════════════════════════════════════════════════
# formatter.py — build_weekly_digest, build_response, build_help_email
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildWeeklyDigest:
    def test_empty_digest(self):
        from formatter import build_weekly_digest
        html, text = build_weekly_digest()
        assert "Your Week Ahead" in html
        assert "YOUR WEEK AHEAD" in text

    def test_digest_includes_task(self):
        from db import add_task
        from formatter import build_weekly_digest
        add_task("Review PRs", list_name="work", priority="high")
        html, text = build_weekly_digest()
        assert "Review PRs" in html
        assert "Review PRs" in text

    def test_digest_separates_lists(self):
        from db import add_task
        from formatter import build_weekly_digest
        add_task("Work thing", list_name="work")
        add_task("House thing", list_name="house")
        html, text = build_weekly_digest()
        assert "WORK" in html or "Work" in html
        assert "HOUSE" in html or "House" in html


class TestBuildResponse:
    def test_success_result(self):
        from formatter import build_response
        results = [{"ok": True, "cmd": "DONE 1", "message": "Marked #1 done: \"Task\""}]
        html, text = build_response(results)
        assert "DONE 1" in html
        assert "DONE 1" in text

    def test_failure_result(self):
        from formatter import build_response
        results = [{"ok": False, "cmd": "DONE 999", "message": "Task #999 not found."}]
        html, text = build_response(results)
        assert "not found" in html or "not found" in text

    def test_empty_results(self):
        from formatter import build_response
        html, text = build_response([])
        assert "No commands found" in html or "No commands found" in text


class TestBuildHelpEmail:
    def test_help_contains_commands(self):
        from formatter import build_help_email
        html, text = build_help_email()
        assert "ADD" in text
        assert "DONE" in text
        assert "DELETE" in text
        assert "PRIORITY" in text
        assert "MOVE" in text
