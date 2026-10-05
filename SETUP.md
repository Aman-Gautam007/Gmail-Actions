# Advertisement Cleaner setup

## Local runtime

Keep the installed script, requirements, virtual environment, credentials, token, logs, and state in `~/Library/Application Support/Gmail-Actions` to avoid iCloud Desktop offloading. Update the script from this repository without overwriting credentials or `.processed_reminders.json`.

```sh
cd "$HOME/Library/Application Support/Gmail-Actions"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## OAuth and safe preview

Enable Gmail API in Google Cloud, create a Desktop app OAuth client, and save the downloaded configuration as `credentials.json` in the runtime directory. The script requests `https://www.googleapis.com/auth/gmail.modify`. Use the README's public URLs for Branding.

Audience publishing status and verification status are separate. Testing-mode Gmail authorizations expire after seven days. After moving to Production, obtain a new token to remove that particular expiry rule; other revocation conditions still apply.

```sh
"$HOME/Library/Application Support/Gmail-Actions/.venv/bin/python" \
  "$HOME/Library/Application Support/Gmail-Actions/advertisement_cleanup.py" --preview
```

Complete browser authorization when prompted. Preview does not change Gmail or mark the reminder processed. If an existing token is revoked, stop the job, move `token.json` to a uniquely named local backup, and rerun preview to authorize again. Preserve reminder state.

## Reminder and cleanup

Create a recurring Monday morning Apple Reminder named exactly `Check Advertisement folder`. Grant Reminders automation access when macOS asks.

The script first labels Promotions and archives Advertisement messages from Inbox. A newly completed reminder then triggers moving all non-trashed Advertisement messages to Trash. The LaunchAgent polls every 120 seconds while the Mac is awake and logged in; checking the reminder does not directly launch a Shortcut.

Running without `--preview` performs actions without prompting. The old `--execute` and `--confirmation` flags are unsupported. The script does not permanently delete messages; Gmail Trash retention rules apply.

## Background job

Install the repository plist as a regular file at `~/Library/LaunchAgents/com.amangautam.gmail-advertisement-cleanup.plist`, not a symlink to Desktop. The template uses the developer's absolute runtime paths; adjust them on another Mac.

Stop a loaded job before updates or reauthorization:

```sh
launchctl bootout "gui/$(id -u)/com.amangautam.gmail-advertisement-cleanup"
```

After installation or authorization, load it:

```sh
launchctl bootstrap "gui/$(id -u)" \
  "$HOME/Library/LaunchAgents/com.amangautam.gmail-advertisement-cleanup.plist"
```

Loading starts a run immediately and may clean mail if a completed reminder is pending. Diagnose failures using `cleanup.log` and `cleanup-error.log` in the runtime directory.
