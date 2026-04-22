"""GTD Dashboard CLI - Main entry point."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel

from gtd_dashboard.aggregator import TaskAggregator
from gtd_dashboard.config import DashboardConfig, create_default_config
from gtd_dashboard.models import TaskStatus
from gtd_dashboard.parser import TaskParser
from gtd_dashboard.reports import ReportRenderer
from gtd_dashboard.work_context import WorkContextMerger

app = typer.Typer(
    name="gtd-dashboard",
    help="GTD Dashboard CLI - Unified view of scattered GTD tasks",
    rich_markup_mode="rich",
)

console = Console()


def get_config(config_path: Optional[Path] = None) -> DashboardConfig:
    """Get configuration from file or auto-discover."""
    if config_path:
        return DashboardConfig.from_file(config_path)
    return DashboardConfig.auto_discover()


def parse_tasks(config: DashboardConfig, with_m365: bool = False) -> TaskAggregator:
    """Parse all tasks and return aggregator."""
    if not config.ensure_paths():
        console.print(f"[red]Error: Daily notes path not found: {config.daily_notes_path}[/]")
        console.print("[dim]Check your configuration or run 'gtd-dashboard init'[/]")
        raise typer.Exit(1)
    
    # Parse GTD tasks from daily notes
    parser = TaskParser(
        config.daily_notes_path,
        max_workers=config.max_workers
    )
    
    tasks = list(parser.parse_all(parallel=config.parallel_parsing))
    
    # Merge with M365 work-context if requested
    if with_m365 and config.work_context_path.exists():
        merger = WorkContextMerger(
            tasks,
            config.work_context_path,
            days=7
        )
        tasks = merger.merge()
    
    return TaskAggregator(tasks)


@app.command()
def now(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project"),
    person: Optional[str] = typer.Option(None, "--person", "-P", help="Filter by person"),
    with_m365: bool = typer.Option(False, "--with-m365", "-m", help="Include Microsoft 365 context"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Show NOW/DOING tasks - what you should be working on."""
    config = get_config(config_path)
    aggregator = parse_tasks(config, with_m365)
    
    # Apply filters
    if project:
        tasks = [t for t in aggregator.now() if t.project and project.lower() in t.project.lower()]
        aggregator = TaskAggregator(tasks)
    
    if person:
        tasks = [t for t in aggregator.now() if t.person and person.lower() in t.person.lower()]
        aggregator = TaskAggregator(tasks)
    
    renderer = ReportRenderer(console)
    renderer.render_now(aggregator)


@app.command()
def waiting(
    max_age: Optional[int] = typer.Option(None, "--max-age", "-a", help="Max age in days to show"),
    with_m365: bool = typer.Option(False, "--with-m365", "-m", help="Include Microsoft 365 context"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Show WAITING-FOR tasks with aging indicators."""
    config = get_config(config_path)
    aggregator = parse_tasks(config, with_m365)
    
    if max_age:
        tasks = aggregator.waiting_with_aging(max_age)
        aggregator = TaskAggregator(tasks)
    
    renderer = ReportRenderer(console)
    renderer.render_waiting(aggregator)


@app.command()
def later(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project"),
    with_m365: bool = typer.Option(False, "--with-m365", "-m", help="Include Microsoft 365 context"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Show LATER (scheduled) tasks."""
    config = get_config(config_path)
    aggregator = parse_tasks(config, with_m365)
    
    if project:
        tasks = [t for t in aggregator.later() if t.project and project.lower() in t.project.lower()]
        aggregator = TaskAggregator(tasks)
    
    renderer = ReportRenderer(console)
    renderer.render_later(aggregator)


@app.command()
def todo(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project"),
    person: Optional[str] = typer.Option(None, "--person", "-P", help="Filter by person"),
    with_m365: bool = typer.Option(False, "--with-m365", "-m", help="Include Microsoft 365 context"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Show TODO (next actions) tasks."""
    config = get_config(config_path)
    aggregator = parse_tasks(config, with_m365)
    
    tasks = aggregator.todo()
    
    if project:
        tasks = [t for t in tasks if t.project and project.lower() in t.project.lower()]
    
    if person:
        tasks = [t for t in tasks if t.person and person.lower() in t.person.lower()]
    
    renderer = ReportRenderer(console)
    renderer.render_todo(TaskAggregator(tasks))


@app.command()
def stale(
    days: int = typer.Option(30, "--days", "-d", help="Stale threshold in days"),
    with_m365: bool = typer.Option(False, "--with-m365", "-m", help="Include Microsoft 365 context"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Show stale tasks (30+ days old by default)."""
    config = get_config(config_path)
    aggregator = parse_tasks(config, with_m365)
    
    renderer = ReportRenderer(console)
    renderer.render_stale(aggregator, days)


@app.command()
def someday(
    with_m365: bool = typer.Option(False, "--with-m365", "-m", help="Include Microsoft 365 context"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Show SOMEDAY/MAYBE tasks."""
    config = get_config(config_path)
    aggregator = parse_tasks(config, with_m365)
    
    renderer = ReportRenderer(console)
    renderer.render_someday(aggregator)


@app.command()
def all(
    with_m365: bool = typer.Option(False, "--with-m365", "-m", help="Include Microsoft 365 context"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Show all active tasks (NOW, WAITING, TODO, LATER)."""
    config = get_config(config_path)
    aggregator = parse_tasks(config, with_m365)
    
    renderer = ReportRenderer(console)
    renderer.render_all(aggregator)


@app.command()
def stats(
    with_m365: bool = typer.Option(False, "--with-m365", "-m", help="Include Microsoft 365 context"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Show statistics dashboard."""
    config = get_config(config_path)
    aggregator = parse_tasks(config, with_m365)
    
    renderer = ReportRenderer(console)
    renderer.render_stats(aggregator)


@app.command()
def tree(
    with_m365: bool = typer.Option(False, "--with-m365", "-m", help="Include Microsoft 365 context"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Show tasks as tree view by project."""
    config = get_config(config_path)
    aggregator = parse_tasks(config, with_m365)
    
    renderer = ReportRenderer(console)
    renderer.render_tree(aggregator)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    with_m365: bool = typer.Option(False, "--with-m365", "-m", help="Include Microsoft 365 context"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Search tasks by content."""
    config = get_config(config_path)
    aggregator = parse_tasks(config, with_m365)
    
    results = aggregator.search(query)
    
    if not results:
        console.print(f"[dim]No tasks found matching '{query}'[/]")
        return
    
    console.print(f"[bold]Search results for '{query}':[/] {len(results)} tasks found\n")
    
    table = ReportRenderer(console)
    from rich.table import Table as RichTable
    
    t = RichTable(title=f"Search: '{query}'", box=box.ROUNDED)
    t.add_column("Status", width=10)
    t.add_column("Content", min_width=50)
    t.add_column("Project", width=20)
    t.add_column("Date", width=10)
    
    for task in results[:50]:  # Limit to 50 results
        status_str = task.status.value
        t.add_row(
            status_str,
            task.display_content[:60] + "..." if len(task.display_content) > 60 else task.display_content,
            task.project or "-",
            task.date.strftime('%Y-%m-%d')
        )
    
    console.print(t)


@app.command()
def export(
    format: str = typer.Option("json", "--format", "-f", help="Export format: json, csv, markdown"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file (default: stdout)"),
    with_m365: bool = typer.Option(False, "--with-m365", "-m", help="Include Microsoft 365 context"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
    status_filter: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
) -> None:
    """Export tasks to JSON, CSV, or Markdown."""
    config = get_config(config_path)
    aggregator = parse_tasks(config, with_m365)
    
    # Apply status filter if specified
    tasks = aggregator.tasks
    if status_filter:
        try:
            status = TaskStatus(status_filter.upper())
            tasks = [t for t in tasks if t.status == status]
        except ValueError:
            console.print(f"[red]Invalid status: {status_filter}[/]")
            raise typer.Exit(1)
    
    # Generate output
    if format == "json":
        data = [t.to_dict() for t in tasks]
        output_text = json.dumps(data, indent=2, default=str)
    elif format == "csv":
        if not tasks:
            output_text = ""
        else:
            import io
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["id", "content", "status", "project", "person", "date", "age_days"])
            for t in tasks:
                writer.writerow([
                    t.id, t.display_content, t.status.value, 
                    t.project or "", t.person or "",
                    t.date.strftime('%Y-%m-%d'), t.age_days or ""
                ])
            output_text = buf.getvalue()
    elif format == "markdown":
        lines = ["# GTD Tasks Export\n"]
        for t in tasks:
            status_emoji = {
                TaskStatus.NOW: "🔥",
                TaskStatus.LATER: "📅",
                TaskStatus.TODO: "⬜",
                TaskStatus.WAITING: "⏳",
                TaskStatus.SOMEDAY: "💭",
                TaskStatus.DONE: "✅",
            }.get(t.status, "•")
            lines.append(f"- {status_emoji} **{t.status.value}**: {t.display_content}")
            lines.append(f"  - Project: {t.project or 'N/A'} | Date: {t.date.strftime('%Y-%m-%d')}")
            lines.append("")
        output_text = "\n".join(lines)
    else:
        console.print(f"[red]Unsupported format: {format}[/]")
        raise typer.Exit(1)
    
    # Output
    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(output_text)
        console.print(f"[green]Exported {len(tasks)} tasks to {output}[/]")
    else:
        console.print(output_text)


@app.command()
def init(
    path: Optional[Path] = typer.Option(None, "--path", help="Knowledge graph path"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config"),
) -> None:
    """Initialize configuration file."""
    config_file = Path.cwd() / '.gtd-dashboard.yaml'
    
    if config_file.exists() and not force:
        console.print(f"[yellow]Config file already exists: {config_file}[/]")
        console.print("Use --force to overwrite")
        return
    
    # Create config with provided or default path
    if path:
        config = DashboardConfig(knowledge_graph_path=Path(path))
    else:
        config = DashboardConfig()
    
    create_default_config(config_file)
    console.print(f"[green]Created config file: {config_file}[/]")
    console.print(f"[dim]Knowledge graph path: {config.knowledge_graph_path}[/]")


@app.command()
def info(
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Show information about the knowledge graph and parsing stats."""
    config = get_config(config_path)
    
    console.print(Panel.fit("[bold]GTD Dashboard Information[/]", border_style="cyan"))
    
    console.print(f"[bold]Configuration:[/]")
    console.print(f"  Knowledge graph: {config.knowledge_graph_path}")
    console.print(f"  Daily notes: {config.daily_notes_path}")
    console.print(f"  Work context: {config.work_context_path}")
    console.print(f"  Stale threshold: {config.default_stale_days} days")
    console.print()
    
    # Check paths
    if config.daily_notes_path.exists():
        md_files = list(config.daily_notes_path.glob('*.md'))
        console.print(f"[green]Daily notes directory found: {len(md_files)} files[/]")
    else:
        console.print(f"[red]Daily notes directory not found![/]")
    
    if config.work_context_path.exists():
        ctx_files = list(config.work_context_path.glob('*.md'))
        console.print(f"[green]Work-context directory found: {len(ctx_files)} files[/]")
    else:
        console.print(f"[dim]Work-context directory not found (optional)[/]")
    
    # Parse stats
    if config.ensure_paths():
        console.print()
        console.print("[bold]Parsing statistics:[/]")
        parser = TaskParser(config.daily_notes_path)
        stats = parser.get_stats()
        
        console.print(f"  Total files: {stats['total_files']}")
        console.print(f"  Total tasks: {stats['total_tasks']}")
        console.print()
        console.print("  By status:")
        for status, count in sorted(stats['status_counts'].items(), key=lambda x: -x[1]):
            console.print(f"    {status}: {count}")


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
