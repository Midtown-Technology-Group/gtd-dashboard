# GTD Dashboard CLI

Unified view of scattered GTD tasks across your Logseq knowledge graph.

## Features

- ⚡ Parses 968+ daily notes in < 5 seconds with parallel processing
- 📊 Rich terminal tables with filtering and grouping
- ⏳ Aging calculation for WAITING-FOR items with visual indicators
- 🔗 Merge with work-context data for unified Microsoft 365 view
- 🕸️ Stale task detection (30+ days old)
- 📁 Export to JSON, CSV, or Markdown
- 🔍 Search across all tasks

## Installation

### Option 1: Install from source

```powershell
# Clone or navigate to the project
cd C:\Users\ThomasBray\OneDrive - Midtown Technology Group LLC\Knowledge\gtd-dashboard

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install in development mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

### Option 2: Use PowerShell wrapper (no install)

```powershell
# From the project directory
.\invoke.ps1 now
.\invoke.ps1 waiting --with-m365
```

## Quick Start

### 1. Initialize Configuration

```bash
gtd-dashboard init --path "C:\Users\ThomasBray\OneDrive - Midtown Technology Group LLC\Knowledge"
```

This creates `.gtd-dashboard.yaml` in the current directory.

### 2. View Your Tasks

```bash
# What you should be doing now
gtd-dashboard now

# What you're waiting for (with aging)
gtd-dashboard waiting

# Scheduled tasks
gtd-dashboard later

# Next actions
gtd-dashboard todo

# Stale tasks (30+ days old)
gtd-dashboard stale

# Everything
gtd-dashboard all
```

### 3. Merge with Microsoft 365

```bash
gtd-dashboard now --with-m365
gtd-dashboard all --with-m365
```

## Commands

| Command | Description |
|---------|-------------|
| `now` | Show NOW/DOING tasks |
| `waiting` | Show WAITING-FOR with aging indicators |
| `later` | Show LATER (scheduled) tasks |
| `todo` | Show TODO (next actions) |
| `stale` | Show stale tasks (30+ days) |
| `someday` | Show SOMEDAY/MAYBE tasks |
| `all` | Show all active tasks |
| `stats` | Show statistics dashboard |
| `tree` | Tree view by project |
| `search <query>` | Search task content |
| `export` | Export to JSON/CSV/Markdown |
| `info` | Show knowledge graph info |
| `init` | Create configuration file |

## Filtering

```bash
# Filter by project
gtd-dashboard now --project "bifrost"
gtd-dashboard later --project "ClientA"

# Filter by person
gtd-dashboard now --person "John"
gtd-dashboard todo --person "Mike"

# Combined filters
gtd-dashboard now --project "bifrost" --person "Thomas"
```

## Exporting

```bash
# Export all to JSON
gtd-dashboard all --format json --output tasks.json

# Export to CSV
gtd-dashboard export --format csv --output tasks.csv

# Export to Markdown
gtd-dashboard export --format markdown --output tasks.md

# Export only specific status
gtd-dashboard export --format json --status NOW --output now-tasks.json
```

## Configuration

Create `.gtd-dashboard.yaml` in your knowledge graph root:

```yaml
knowledge_graph_path: C:\Users\ThomasBray\OneDrive - Midtown Technology Group LLC\Knowledge
default_stale_days: 30
default_waiting_warning_days: 7
default_waiting_critical_days: 14
max_table_rows: 100
truncate_content_at: 80
show_aging_indicators: true
parallel_parsing: true
max_workers: null  # auto
default_export_format: json
```

The config is auto-discovered by looking for `.gtd-dashboard.yaml` in:
1. Current directory
2. Parent directories (up to 10 levels)
3. Home directory (`~/.gtd-dashboard.yaml`)

## Task Format

The parser recognizes these Logseq-style markers:

```markdown
- NOW Working on this right now
- DOING Alternative for NOW
- LATER Schedule this for later
- TODO Next action to take
- NEXT Alternative for TODO
- WAITING-FOR Waiting for someone's response
- WAITING Short form
- SOMEDAY Someday/maybe
- MAYBE Alternative
- DONE Completed
- CANCELLED Cancelled
```

Checkbox syntax is also supported:

```markdown
- [ ] TODO: Task with explicit marker
- [ ] Implicit TODO (no marker)
- [x] Completed task
- [X] Also completed
```

### Projects and People

Projects and people are automatically extracted from Logseq links:

```markdown
- TODO [[projects/bifrost]] Fix the API
- TODO [[people/John-Smith]] Review with John
```

## Aging Indicators

For WAITING-FOR items, visual indicators show age:

| Age | Indicator | Meaning |
|-----|-----------|---------|
| < 3 days | 🟢 | Fresh |
| 3-6 days | 🟡 | Getting old |
| 7-13 days | 🟠 | Needs follow-up |
| 14+ days | 🔴 | Stale - follow up now! |

## PowerShell Wrapper

Use `invoke.ps1` for convenience:

```powershell
# Quick commands via wrapper
.\invoke.ps1 now
.\invoke.ps1 waiting --with-m365
.\invoke.ps1 stats
.\invoke.ps1 search "API"
```

## Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=gtd_dashboard

# Format code
black src/
ruff check src/

# Type check
mypy src/gtd_dashboard
```

## Project Structure

```
gtd-dashboard/
├── src/
│   └── gtd_dashboard/
│       ├── __init__.py
│       ├── cli.py           # Typer CLI
│       ├── models.py        # Task dataclasses
│       ├── parser.py        # Daily notes parser
│       ├── aggregator.py    # Task grouping/filtering
│       ├── reports.py       # Rich table formatting
│       ├── work_context.py  # M365 integration
│       └── config.py        # Configuration
├── tests/
│   └── test_parser.py
├── pyproject.toml
├── README.md
└── invoke.ps1
```

## Performance

With parallel parsing enabled (default for 50+ files):
- 100 files: ~0.5 seconds
- 500 files: ~2 seconds
- 1000 files: ~4 seconds

Set `parallel_parsing: false` in config to disable.

## License

AGPL-3.0

## Author

Thomas Bray - MSP/IT Consultant at Midtown Technology Group

## Windows MSI

Tagged releases build a per-machine Windows MSI that installs `gtd-dashboard.exe` under `Program Files` and adds that install directory to the system PATH. Installing or uninstalling the MSI requires an elevated prompt.
