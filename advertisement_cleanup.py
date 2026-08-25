#!/usr/bin/env python3
"""Move Gmail messages with a label to Trash after a Reminders item is completed."""

from __future__ import annotations

import argparse
import fcntl
import json
import subprocess
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
DEFAULT_CONFIG_DIR = Path.home() / "Desktop" / "Programming" / "Gmail-Actions"
DEFAULT_STATE_PATH = DEFAULT_CONFIG_DIR / ".processed_reminders.json"
DEFAULT_LOCK_PATH = DEFAULT_CONFIG_DIR / ".cleanup.lock"


def latest_completed_reminder_id(title: str, list_name: str | None) -> str | None:
    script = r'''
on run argv
    set targetTitle to item 1 of argv
    set targetList to item 2 of argv
    set latestId to ""
    set latestDate to missing value
    tell application "Reminders"
        repeat with reminderList in lists
            if targetList is "" or name of reminderList is targetList then
                set matches to (every reminder of reminderList whose name is targetTitle)
                repeat with oneReminder in matches
                    if completed of oneReminder is true then
                        set completedAt to completion date of oneReminder
                        if completedAt is not missing value then
                            if latestDate is missing value or completedAt > latestDate then
                                set latestDate to completedAt
                                set latestId to id of oneReminder
                            end if
                        end if
                    end if
                end repeat
            end if
        end repeat
    end tell
    return latestId
end run
'''
    try:
        result = subprocess.run(
            ["osascript", "-e", script, title, list_name or ""],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Apple Reminders did not respond within 30 seconds") from exc
    if result.returncode != 0:
        raise RuntimeError(f"Could not read Apple Reminders: {result.stderr.strip()}")
    return result.stdout.strip() or None


def load_processed_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("processed_reminder_ids", []))
    except (OSError, ValueError, TypeError) as exc:
        raise RuntimeError(f"Could not read state file {path}: {exc}") from exc


def save_processed_ids(path: Path, reminder_ids: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps({"processed_reminder_ids": sorted(reminder_ids)}, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def gmail_service(credentials_path: Path, token_path: Path):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "Missing Google libraries. Install them with: "
            "python3 -m pip install -r requirements.txt"
        ) from exc

    credentials = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    elif not credentials or not credentials.valid:
        if not credentials_path.exists():
            raise RuntimeError(f"OAuth credentials file not found: {credentials_path}")
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        credentials = flow.run_local_server(port=0)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def find_label_id(service, label_name: str) -> str:
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label.get("name", "").casefold() == label_name.casefold():
            return label["id"]
    raise RuntimeError(f'Gmail label not found: "{label_name}"')


def list_message_ids(service, label_id: str) -> list[str]:
    message_ids: list[str] = []
    page_token = None
    while True:
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=[label_id],
                q="-in:trash",
                maxResults=500,
                pageToken=page_token,
            )
            .execute()
        )
        message_ids.extend(message["id"] for message in response.get("messages", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return message_ids


def trash_messages(service, message_ids: list[str]) -> None:
    failures: list[str] = []

    def callback(message_id, _response, exception):
        if exception:
            failures.append(f"{message_id}: {exception}")

    for start in range(0, len(message_ids), 100):
        batch = service.new_batch_http_request(callback=callback)
        for message_id in message_ids[start : start + 100]:
            batch.add(
                service.users().messages().trash(userId="me", id=message_id),
                request_id=message_id,
            )
        batch.execute()
        print(f"Moved {min(start + 100, len(message_ids))}/{len(message_ids)} to Trash")
    if failures:
        sample = "\n".join(failures[:10])
        raise RuntimeError(f"{len(failures)} messages failed. First failures:\n{sample}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reminder", default="Check Advertisement folder")
    parser.add_argument("--reminder-list", default=None)
    parser.add_argument("--gmail-label", default="Advertisement")
    parser.add_argument("--credentials", type=Path, default=DEFAULT_CONFIG_DIR / "credentials.json")
    parser.add_argument("--token", type=Path, default=DEFAULT_CONFIG_DIR / "token.json")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK_PATH)
    parser.add_argument("--preview", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lock_path = args.lock.expanduser()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Another cleanup run is already active. Skipping.")
            return 0

        print(f'Checking Apple reminder: "{args.reminder}"...', flush=True)
        reminder_id = latest_completed_reminder_id(args.reminder, args.reminder_list)
        if reminder_id is None:
            print("No completed matching reminder found. Nothing changed.")
            return 0

        state_path = args.state.expanduser()
        processed_ids = load_processed_ids(state_path)
        if reminder_id in processed_ids:
            print("This reminder completion was already processed. Nothing changed.")
            return 0

        print("New completed reminder found. Connecting to Gmail...", flush=True)
        service = gmail_service(args.credentials.expanduser(), args.token.expanduser())
        label_id = find_label_id(service, args.gmail_label)
        message_ids = list_message_ids(service, label_id)
        print(f'Found {len(message_ids)} non-trashed messages labeled "{args.gmail_label}".')

        if args.preview:
            print("Preview only. Nothing changed and the reminder remains unprocessed.")
            return 0

        if message_ids:
            trash_messages(service, message_ids)
        processed_ids.add(reminder_id)
        save_processed_ids(state_path, processed_ids)
        print(f"Finished: {len(message_ids)} messages moved to Gmail Trash.")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
