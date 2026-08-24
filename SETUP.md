# Advertisement cleanup for Apple Reminders + Gmail

This script checks whether an Apple Reminders item is completed. Only then can
it move every non-trashed Gmail message carrying the `Advertisement` label to
Trash. It never permanently deletes messages.

## 1. Install the Python packages

In Terminal, from this folder:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## 2. Create Google OAuth credentials

1. Open Google Cloud Console and create or choose a project.
2. Enable the Gmail API.
3. Configure the OAuth consent screen for your Google account.
4. Create an OAuth client of type **Desktop app**.
5. Download the JSON file as:
   `~/Library/Application Support/AdvertisementCleaner/credentials.json`

On first use, Google opens a browser so you can authorize `gmail.modify`.
The resulting token stays on this Mac in the same Application Support folder.

## 3. Create the recurring reminder

In Apple Reminders, create a weekly reminder named exactly:

`Check Advertisement folder`

Set it for Monday morning. A recurring reminder creates the next occurrence
after you complete the current one.

## 4. Test safely

Complete the reminder, then run a preview:

```sh
.venv/bin/python advertisement_cleanup.py
```

The preview reports the number of matching messages and changes nothing.

## 5. Create the Shortcut

In the macOS Shortcuts app, create a shortcut named `Clean Advertisement Mail`:

1. Add **Show Alert**: `Move all Advertisement emails to Gmail Trash?`
2. Add **Run Shell Script** (or **Run Script over SSH** only if you intentionally
   run this on another Mac).
3. Use this command, replacing `/FULL/PATH` with this folder's absolute path:

```sh
cd /FULL/PATH
.venv/bin/python advertisement_cleanup.py \
  --execute \
  --confirmation MOVE-ADVERTISEMENT-TO-TRASH
```

Run the shortcut after checking off the reminder. The script independently
verifies that the reminder is completed before accessing Gmail.

## Permissions and behavior

- macOS may ask whether Terminal, Shortcuts, or `osascript` may access Reminders.
  Approve this in **System Settings → Privacy & Security → Automation**.
- Google may show an unverified-app warning for a private OAuth app in testing;
  only authorize the OAuth client you created yourself.
- Gmail Trash is recoverable until Gmail permanently removes those messages.
- The script acts on the custom `Advertisement` label. It does not automatically
  add that label to new promotional messages; create a Gmail filter or update the
  script if you want new Promotions categorized automatically.
