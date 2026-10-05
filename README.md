# Gmail-Actions

Synchronizes Gmail Promotions into the Advertisement label, removes them from Inbox, and moves labeled mail to Trash after a new completed Apple Reminder named `Check Advertisement folder` is detected. The LaunchAgent checks every 120 seconds while the Mac is awake and logged in. Each reminder completion is processed once. Bulk requests include retry/backoff.

## Public website

- [Homepage](https://aman-gautam007.github.io/amangautamportfolio.github.io/advertisement-cleaner/)
- [Privacy policy](https://aman-gautam007.github.io/amangautamportfolio.github.io/advertisement-cleaner/privacy/)
- [Terms of service](https://aman-gautam007.github.io/amangautamportfolio.github.io/advertisement-cleaner/terms/)

Website source is in [docs/](docs/). These URLs currently use the existing portfolio GitHub Pages deployment; copying the source here does not change the live URLs or OAuth settings.

## Installation

See [SETUP.md](SETUP.md). Use `--preview` to inspect the workflow without modifying Gmail or recording a reminder completion. Running without that flag performs the configured actions without another confirmation.

The installed runtime is `~/Library/Application Support/Gmail-Actions`, outside iCloud Desktop. Credentials, tokens and backups, logs, environments, and reminder state stay local and are excluded from Git.
