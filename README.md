# GTD Dashboard CLI

Unified view of scattered GTD tasks across your Logseq knowledge graph.

## Installation

```bash
pip install gtd-dashboard
```

## Usage

```bash
# View all NOW actions
gtd-dashboard now

# View WAITING-FOR items with aging
gtd-dashboard waiting

# View stale tasks (30+ days old)
gtd-dashboard stale

# Filter by project or person
gtd-dashboard now --project "ClientA" --person "John"

# Include Microsoft 365 context
gtd-dashboard now --with-m365

# Export to JSON
gtd-dashboard all --format json
```

## Features

- Parses 968+ daily notes in < 5 seconds
- Rich terminal tables with filtering
- Aging calculation for WAITING-FOR items
- Merge with work-context data for unified view
- Stale task detection

## License

AGPL-3.0
