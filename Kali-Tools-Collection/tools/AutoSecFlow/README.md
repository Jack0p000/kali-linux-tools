# AutoSecFlow

AutoSecFlow is a local-first visual workflow builder and scheduler for repeatable defensive checks on a Linux workstation.

## Features

- Original visual sequential workflow editor, with up to 20 nodes.
- Save and reload the workflow in the user's local data directory.
- Schedule saved workflows at fixed intervals: 15 or 30 minutes, hourly, every 3, 6 or 12 hours, daily, or weekly.
- Pause, resume, and delete scheduled jobs from the GUI.
- Background scheduler checks due jobs every 10 seconds while AutoSecFlow is running.
- System snapshot (hostname, OS, Python version and free disk space).
- Read-only directory inventory hash (up to 500 files, skipping files larger than 20 MiB).
- HTTPS/TLS certificate expiry check for a hostname supplied by the operator.
- Local activity journal and optional ToolShareHub event publication.
- Shared ToolAuth login integration.

Scheduled workflows are selected from saved workflows and execute only the predefined allowlisted actions. Scheduling does not support arbitrary shell commands, scripts, remote execution, or system modifications. The scheduler runs only while the AutoSecFlow process is open; it is not installed as a system service. The web server binds to `127.0.0.1` only.

## Requirements

- Python 3.10 or newer.
- The collection's `apps/ToolAuth` module for the shared login flow.
- `apps/ToolShareHub` is optional; when present, startup and workflow events are published to it.

All runtime state is stored under `~/.local/share/autosecflow/`:
- `workflows.json`
- `schedules.json`
- `activity.jsonl`

No workflow database, activity log, credentials or machine-specific paths are committed.

## Start

From this directory run:

```bash
bash run_tool.sh
```

The interface opens at `http://127.0.0.1:8796`. If the browser does not open automatically, enter that address manually.

## Scheduling a workflow

1. Open **Workflow Builder**, configure the nodes, and select **SAVE FLOW**.
2. Open **Scheduled runs**.
3. Select the saved workflow and choose an interval.
4. Select **SAVE SCHEDULE**. The first run occurs after the selected interval.
5. Use **PAUSE/ENABLE** to suspend or resume a job, or **DELETE** to remove it.

AutoSecFlow must remain running for scheduled jobs to execute. Closing the app pauses automation; it resumes when the app is started again and the stored schedule becomes due.

## Available node types

| Node | Purpose |
|---|---|
| `system_snapshot` | Read basic host and disk information |
| `hash_directory` | Build a SHA-256 inventory fingerprint for a directory |
| `tls_check` | Inspect the TLS protocol and certificate expiry of a hostname |
| `log` | Add a note to the local activity journal |

Only use TLS checks against systems you own or are authorized to assess.
