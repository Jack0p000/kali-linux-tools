# AutoSecFlow

AutoSecFlow is a local-first visual workflow builder for repeatable defensive checks on a Linux workstation.

## Features

- Visual sequential workflow editor with up to 20 nodes.
- Save and reload a workflow in the user's local data directory.
- System snapshot (hostname, OS, Python version and free disk space).
- Read-only directory inventory hash (up to 500 files, skipping files larger than 20 MiB).
- HTTPS/TLS certificate expiry check for a hostname supplied by the operator.
- Local activity journal and optional ToolShareHub event publication.
- Shared ToolAuth login integration.

The engine only exposes an allowlist of predefined actions. It does not execute arbitrary shell commands. The web server binds to `127.0.0.1` only.

## Requirements

- Python 3.10 or newer.
- The collection's `apps/ToolAuth` module for the shared login flow.
- `apps/ToolShareHub` is optional; when present, startup and workflow events are published to it.

All runtime state is stored under `~/.local/share/autosecflow/`. No workflow database, activity log, credentials or machine-specific paths are committed.

## Start

From this directory run:

```bash
bash run_tool.sh
```

The interface opens at `http://127.0.0.1:8796`. If the browser does not open automatically, enter that address manually.

## Available node types

| Node | Purpose |
|---|---|
| `system_snapshot` | Read basic host and disk information |
| `hash_directory` | Build a SHA-256 inventory fingerprint for a directory |
| `tls_check` | Inspect the TLS protocol and certificate expiry of an HTTPS host |
| `log` | Add a note to the local activity journal |

Only use TLS checks against systems you own or are authorized to assess.
