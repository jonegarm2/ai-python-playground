"""
main.py — Weekly Task Manager entry point

Runs two jobs:
  1. Every Monday 07:00 MST → send weekly digest email
  2. Every 5 minutes        → poll for reply commands and process them
"""
import logging
import os
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from db import init_db
from gmail import send_email, get_unread_replies, mark_as_read
from formatter import build_weekly_digest, build_response, build_help_email
from executor import process_email_body

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Config (set via env vars or edit here) ─────────────────────────────────────
TO_EMAIL    = os.environ.get("TASK_EMAIL", "you@gmail.com")   # your email address
DIGEST_SUBJECT = "Weekly Tasks"
MST         = pytz.timezone("America/Denver")

# Shared state to track the last sent digest (for threading replies)
_last_digest: dict = {}  # {thread_id, message_id}


# ── Jobs ──────────────────────────────────────────────────────────────────────

def send_weekly_digest():
    log.info("Sending weekly digest...")
    html, text = build_weekly_digest()
    send_email(
        to=TO_EMAIL,
        subject=DIGEST_SUBJECT,
        html_body=html,
        text_body=text,
    )
    log.info("Weekly digest sent.")


def poll_replies():
    log.info("Polling for reply commands...")
    replies = get_unread_replies(subject_filter=DIGEST_SUBJECT)

    if not replies:
        log.info("No new replies.")
        return

    for msg in replies:
        log.info(f"Processing reply from {msg['from']} | subject: {msg['subject']}")
        results = process_email_body(msg["body"])

        if not results:
            log.info("No commands found in reply.")
            mark_as_read(msg["id"])
            continue

        # Check for special actions
        help_requested  = any(r.get("help_requested") for r in results)
        list_requested  = any(r.get("list_requested") for r in results)

        if help_requested:
            html, text = build_help_email()
            send_email(
                to=TO_EMAIL,
                subject=f"Re: {msg['subject']}",
                html_body=html,
                text_body=text,
                thread_id=msg["threadId"],
                message_id=msg["message_id"],
            )
        elif list_requested:
            html, text = build_weekly_digest()
            send_email(
                to=TO_EMAIL,
                subject=f"Re: {msg['subject']}",
                html_body=html,
                text_body=text,
                thread_id=msg["threadId"],
                message_id=msg["message_id"],
            )
        else:
            html, text = build_response(results)
            send_email(
                to=TO_EMAIL,
                subject=f"Re: {msg['subject']}",
                html_body=html,
                text_body=text,
                thread_id=msg["threadId"],
                message_id=msg["message_id"],
            )

        mark_as_read(msg["id"])
        log.info(f"Processed {len(results)} command(s) from reply.")


# ── CLI helpers ───────────────────────────────────────────────────────────────

def cmd_send_now():
    """Manually trigger a digest send (for testing)."""
    init_db()
    send_weekly_digest()
    print("Digest sent.")


def cmd_poll_now():
    """Manually trigger a reply poll (for testing)."""
    init_db()
    poll_replies()
    print("Poll complete.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    init_db()
    log.info("Weekly Task Manager starting...")
    log.info(f"Sending digests to: {TO_EMAIL}")

    scheduler = BlockingScheduler(timezone=MST)

    # Every Monday at 07:00 MST
    scheduler.add_job(
        send_weekly_digest,
        CronTrigger(day_of_week="mon", hour=7, minute=0, timezone=MST),
        id="weekly_digest",
        name="Monday 7am digest",
    )

    # Poll every 5 minutes
    scheduler.add_job(
        poll_replies,
        "interval",
        minutes=5,
        id="reply_poller",
        name="Reply poller",
    )

    log.info("Scheduler started. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "send":
            cmd_send_now()
        elif sys.argv[1] == "poll":
            cmd_poll_now()
        else:
            print(f"Unknown command: {sys.argv[1]}")
            print("Usage: python main.py [send|poll]")
    else:
        main()
