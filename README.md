## tab-sync

Tool used to automatically rotate all necessary database passwords and update all embedded database credentials on Tableau Server.

## Overview
- Can sign in to multiple sites on Tableau Server using a personal access token.
- Finds objects (datasources, workbooks, flows) that have connections matching the configured server name and username under `configs.yml` file.
- Updates those connections with newly rotated password.
- Optionally, runs in dry-run mode to preview changes without making any updates.

## Prerequisites
- Access to Tableau Server with permissions to update data source connections.
- Python 3.11 or later (see `pyproject.toml`).
- Dependencies: `ruamel.yaml` and `snowflake-connector-python` (installed via `pyproject.toml`).

## Setup
1. Clone this repository
2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows
```

3. Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # Linux/macOS
# or
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"    # Windows
```

4. Install dependencies:
```bash
uv pip install -r pyproject.toml
```

5. Rename and configure settings:
```bash
cp -r configs-example configs
# Edit configs.yml with required connection details
```

Config file location: `configs/{environment}/config.yml` (where `{environment}` is `dev`, `tst`, `stg`, or `prd`). The config must include `objects`, and `tableau_servers` entries. Example structure:

- `objects`: list of object types to process (e.g., `["workbooks", "datasources", "flows"]`)
- `tableau_servers`:
	- `<server_name>`:
		- `tableau_server_info`:
			- `tableau_server`: base URL (e.g., `https://tableau.example.com`)
			- `api_version`
			- `token_name`
			- `token_secret`
			- `sites`: list of site names to process
			- `database_connections`: map of db keys to connection info.

## Usage
Run the tool from the repository root. Required flags:
- `-e`, `--environment` : `dev|tst|stg|prd`
- `-s`, `--server` : `serialized|standard`

Optional:
- `-d`, `--dry_run` : if set, the tool will sign in and discover what would be updated but will not perform any updates; it logs `DRY-RUN` entries instead.

Examples:

Preview (dry-run):
```bash
python main.py -e dev -s standard --dry_run
# or using short flag
python main.py -e dev -s standard -d
```

Perform updates:
```bash
python main.py -e dev -s standard
```

## Behavior and Failure Policy
- The tool signs in per site, enumerates objects, and updates matching connections.
- Current failure policy: if a critical error occurs (authentication failure, API error, malformed config), the process will stop and raise an error. This behavior ensures you notice failures immediately. Failed runs can be retried after fixing the underlying issue.
- Dry-run: the tool still signs in and performs read operations (`get_objects`, `get_connections`) so the preview reflects actual discovery; only `update_connection()` calls are skipped.

## Logging
- The path for the log file is taken from the config (`log_file`).
- Log entries include an ISO timestamp and short messages. In dry-run mode entries are prefixed with `[DRY-RUN]` when appropriate.

## Notes / Troubleshooting
- Ensure the config YAML is valid; malformed YAML will prevent execution.
- `pyproject.toml` lists required runtime packages; use a virtual environment.
- If you want a more resilient mode (log and continue on individual failures), that can be added as an option in a future change.