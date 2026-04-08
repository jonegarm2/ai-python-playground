"""
formatter.py — Build weekly digest and response emails
"""
from db import list_tasks
from commands import HELP_TEXT

PRIORITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}
PRIORITY_COLOR  = {"high": "#dc2626", "medium": "#d97706", "low": "#16a34a"}


# ── Weekly Digest ─────────────────────────────────────────────────────────────

def build_weekly_digest() -> tuple[str, str]:
    tasks = list_tasks(status="pending")
    work_tasks  = [t for t in tasks if t["list"] == "work"]
    house_tasks = [t for t in tasks if t["list"] == "house"]

    html = _digest_html(work_tasks, house_tasks)
    text = _digest_text(work_tasks, house_tasks)
    return html, text


def _rollover_badge_html(weeks: int) -> str:
    if weeks == 0:
        return ""
    label = f"↩ rolled over {weeks}w" if weeks > 1 else "↩ rolled over"
    return (f'<span style="font-size:11px;background:#fef3c7;color:#92400e;'
            f'padding:1px 6px;border-radius:10px;margin-left:6px">{label}</span>')


def _section_html(title: str, emoji: str, tasks: list, color: str) -> str:
    if not tasks:
        no_tasks = (
            f'<tr><td colspan="3" style="padding:12px;color:#9ca3af;font-style:italic">'
            f'No pending tasks 🎉</td></tr>'
        )
        rows = no_tasks
    else:
        rows = ""
        for t in tasks:
            pc = PRIORITY_COLOR[t["priority"]]
            pe = PRIORITY_EMOJI[t["priority"]]
            badge = _rollover_badge_html(t.get("weeks_pending", 0))
            rows += f"""
            <tr style="border-top:1px solid #f3f4f6">
              <td style="padding:8px 12px;color:#9ca3af;font-size:12px;width:36px">#{t['id']}</td>
              <td style="padding:8px 12px;color:#111827">
                {t['title']}{badge}
              </td>
              <td style="padding:8px 12px;text-align:right;white-space:nowrap">
                <span style="color:{pc};font-size:12px">{pe} {t['priority']}</span>
              </td>
            </tr>"""

    pending_rolled = sum(1 for t in tasks if t.get("weeks_pending", 0) > 0)
    rolled_note = (
        f' <span style="font-size:12px;color:#92400e">· {pending_rolled} rolled over</span>'
        if pending_rolled else ""
    )

    return f"""
    <div style="margin-bottom:24px">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <span style="font-size:18px">{emoji}</span>
        <h3 style="margin:0;color:{color};font-size:15px;text-transform:uppercase;
                   letter-spacing:.05em">{title}</h3>
        <span style="color:#6b7280;font-size:13px">({len(tasks)} task{'s' if len(tasks) != 1 else ''})</span>
        {rolled_note}
      </div>
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">
        {rows}
      </table>
    </div>"""


def _digest_html(work: list, house: list) -> str:
    total = len(work) + len(house)
    high  = sum(1 for t in work + house if t["priority"] == "high")

    work_section  = _section_html("Work",         "💼", work,  "#1d4ed8")
    house_section = _section_html("House",        "🏠", house, "#15803d")

    return f"""
<!DOCTYPE html>
<html>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
             color:#111827;max-width:600px;margin:0 auto;padding:20px">

  <h2 style="margin:0 0 4px">📋 Your Week Ahead</h2>
  <p style="color:#6b7280;margin:0 0 24px;font-size:14px">
    {total} task{'s' if total != 1 else ''} pending
    {'· <span style="color:#dc2626">'+str(high)+' high priority</span>' if high else ''}
    · Incomplete tasks roll over automatically
  </p>

  {work_section}
  {house_section}

  <div style="margin-top:8px;padding:16px;background:#f9fafb;
              border-radius:8px;font-size:13px;color:#374151">
    <strong>Reply with commands:</strong><br><br>
    <code>ADD Fix kitchen sink #house !high</code><br>
    <code>ADD Finish report #work !medium</code><br>
    <code>DONE 3</code> &nbsp;·&nbsp;
    <code>DELETE 5</code> &nbsp;·&nbsp;
    <code>EDIT 2 New title</code><br>
    <code>PRIORITY 4 high</code> &nbsp;·&nbsp;
    <code>MOVE 6 house</code> &nbsp;·&nbsp;
    <code>LIST</code><br><br>
    Reply <strong>HELP</strong> for full command reference.
  </div>

</body>
</html>"""


def _digest_text(work: list, house: list) -> str:
    lines = ["📋 YOUR WEEK AHEAD", "=" * 44]

    for section_name, tasks in [("💼 WORK", work), ("🏠 HOUSE", house)]:
        lines.append(f"\n{section_name}  ({len(tasks)} tasks)")
        lines.append("-" * 44)
        if not tasks:
            lines.append("  No pending tasks 🎉")
        for t in tasks:
            rollover = f"  [rolled over {t['weeks_pending']}w]" if t.get("weeks_pending") else ""
            lines.append(
                f"  #{t['id']}  {PRIORITY_EMOJI[t['priority']]} {t['title']}{rollover}"
            )

    lines += [
        "",
        "─" * 44,
        "COMMANDS:",
        "  ADD <task> [#work|#house] [!priority]",
        "  DONE <id>  |  DELETE <id>  |  EDIT <id> <title>",
        "  PRIORITY <id> <high|medium|low>  |  MOVE <id> <work|house>",
        "  LIST  |  HELP",
    ]
    return "\n".join(lines)


# ── Command Response ───────────────────────────────────────────────────────────

def build_response(results: list[dict]) -> tuple[str, str]:
    lines_html = ""
    lines_text = []

    for r in results:
        icon  = "✅" if r["ok"] else "❌"
        color = "#16a34a" if r["ok"] else "#dc2626"
        lines_html += f"""
        <div style="padding:8px 0;border-bottom:1px solid #f3f4f6">
          <span style="color:{color}">{icon}</span>
          <code style="margin:0 6px;background:#f3f4f6;padding:2px 6px;
                       border-radius:4px;font-size:13px">{r['cmd']}</code>
          <span style="color:#374151;font-size:14px">{r['message']}</span>
        </div>"""
        lines_text.append(f"{'✅' if r['ok'] else '❌'}  {r['cmd']} → {r['message']}")

    html = f"""
<!DOCTYPE html><html><body
  style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
         max-width:600px;margin:0 auto;padding:20px">
  <h3 style="margin:0 0 16px">Command Results</h3>
  {lines_html or '<p style="color:#6b7280">No commands found in your reply.</p>'}
  <p style="margin-top:20px;font-size:13px;color:#6b7280">
    Reply HELP to see all available commands.
  </p>
</body></html>"""

    text = "\n".join(lines_text) or "No commands found. Reply HELP for usage."
    return html, text


def build_help_email() -> tuple[str, str]:
    html = f"""
<!DOCTYPE html><html><body
  style="font-family:monospace;max-width:600px;margin:0 auto;padding:20px;
         white-space:pre-wrap;font-size:14px">{HELP_TEXT}</body></html>"""
    return html, HELP_TEXT
