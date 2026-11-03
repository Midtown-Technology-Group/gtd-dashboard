# GTD Dashboard

This Python 3.10+ CLI presents tasks from Logseq graphs and can merge Microsoft 365 work context. Read [README.md](README.md) for statuses, filters, configuration, and exports. `src/gtd_dashboard` is the packaged code; `tests/` is the pytest target configured in `pyproject.toml`; `invoke.ps1` is the source-run Windows wrapper.

Use an isolated virtual environment and the documented editable development install, `pip install -e ".[dev]"`. Run `python -m pytest` for affected parsing and aggregation changes; the declared pytest configuration selects `tests/`. Preserve Python 3.10 compatibility and the existing 100-column Black/Ruff configuration. Confirm any additional lint/type commands against their tool configuration before claiming a complete gate.

Keep Logseq status semantics, scheduled dates, waiting-item age, parallel parsing, and project grouping stable. Prefer synthetic graph fixtures for parsing, Unicode, malformed frontmatter, dates, and duplicate/task identity behavior. Test Microsoft 365 merge behavior with fake context rather than reading the operator's actual mailbox or task records.

An operator's Knowledge graph, task exports, and `.gtd-dashboard.yaml` can contain private customer or personal information. Do not commit them, traverse unrelated OneDrive content, or initialize/rewrite a real graph as a development check. Configuration examples in README name a workstation path; derive the actual assigned graph from explicit configuration instead of treating that path as universal.

Windows MSI release automation lives in `.github/workflows/release-msi.yml`; source checks do not authorize publishing a release or installing over an operator's tool. Report inspected configuration, executed checks, and actual packaging/runtime evidence separately.

## Secret gate before publication

Before every push and PR creation/update, commit the complete candidate and run
`python3 scripts/secret_gate.py` (native Windows: `python`). Require exit 0;
missing tooling/authentication, scan errors and skipped scans block publication.
Then run the existing repository gates. Repeat after changing outgoing commits.
See [secret scanning](SECRET-SCANNING.md) for base selection, new branches,
pre-push input and prerequisites. Preserve GitGuardian App, CI and Gitleaks checks.
