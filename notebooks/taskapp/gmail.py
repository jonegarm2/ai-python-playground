"""
gmail.py — Send emails and poll for replies via Gmail API
"""
import base64
import email as email_lib
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

CREDS_PATH  = Path(__file__).parent / "credentials.json"
TOKEN_PATH  = Path(__file__).parent / "token.json"

# ── Auth ──────────────────────────────────────────────────────────────────────

def get_service():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


# ── Send ──────────────────────────────────────────────────────────────────────

def send_email(to: str, subject: str, html_body: str, text_body: str,
               thread_id: str = None, message_id: str = None):
    """Send an email, optionally threading it as a reply."""
    service = get_service()

    msg = MIMEMultipart("alternative")
    msg["To"]      = to
    msg["Subject"] = subject
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    if message_id:
        msg["In-Reply-To"] = message_id
        msg["References"]  = message_id

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    body = {"raw": raw}
    if thread_id:
        body["threadId"] = thread_id

    service.users().messages().send(userId="me", body=body).execute()


# ── Poll for replies ───────────────────────────────────────────────────────────

def get_unread_replies(subject_filter: str = "Weekly Tasks") -> list[dict]:
    """
    Return list of unread messages whose subject contains subject_filter.
    Each dict has: id, threadId, subject, from, body, message_id_header
    """
    service = get_service()
    query = f'is:unread subject:"{subject_filter}"'
    results = service.users().messages().list(userId="me", q=query).execute()
    messages = results.get("messages", [])

    parsed = []
    for m in messages:
        msg = service.users().messages().get(
            userId="me", id=m["id"], format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        body = _extract_body(msg["payload"])

        parsed.append({
            "id":               m["id"],
            "threadId":         m["threadId"],
            "subject":          headers.get("Subject", ""),
            "from":             headers.get("From", ""),
            "message_id":       headers.get("Message-ID", ""),
            "body":             body,
        })

    return parsed


def mark_as_read(message_id: str):
    service = get_service()
    service.users().messages().modify(
        userId="me", id=message_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def _extract_body(payload) -> str:
    """Recursively extract plain text body from a Gmail message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        result = _extract_body(part)
        if result:
            return result
    return ""
