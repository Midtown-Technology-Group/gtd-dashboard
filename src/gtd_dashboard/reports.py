"""Report generation for GTD Dashboard using Rich."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from gtd_dashboard.models import Task, TaskStatus
from gtd_dashboard.aggregator import TaskAggregator


class ReportRenderer:
    """Renders GTD reports using Rich tables and formatting."""
    
    def __init__(self, console: Optional[Console] = None) -> None:
        """Initialize renderer.
        
        Args:
            console: Rich Console instance (creates default if None)
        """
        self.console = console or Console()
    
    def _task_to_row(self, task: Task, show_aging: bool = False) -> list[str]:
        """Convert task to table row."""
        status_emoji = {
            TaskStatus.NOW: "🔥",
            TaskStatus.DOING: "🔥",
            TaskStatus.LATER: "📅",
            TaskStatus.TODO: "⬜",
            TaskStatus.NEXT: "⬜",
            TaskStatus.WAITING: "⏳",
            TaskStatus.WAITING_FOR: "⏳",
            TaskStatus.SOMEDAY: "💭",
            TaskStatus.MAYBE: "💭",
            TaskStatus.DONE: "✅",
            TaskStatus.CANCELLED: "❌",
        }.get(task.status, "⬜")
        
        priority_style = {
            "A": "[bold red]A[/]",
            "B": "[bold yellow]B[/]",
            "C": "[bold blue]C[/]",
        }.get(task.priority or "", "")
        
        aging = ""
        if show_aging and task.age_days is not None:
            aging = f"{task.aging_indicator} {task.age_days}d"
        
        return [
            status_emoji,
            priority_style,
            task.display_content[:80] + ("..." if len(task.display_content) > 80 else ""),
            task.project or "-",
            task.person or "-",
            task.date.strftime('%Y-%m-%d'),
            aging,
        ]
    
    def render_now(self, aggregator: TaskAggregator) -> None:
        """Render NOW/DOING tasks."""
        tasks = aggregator.now()
        
        if not tasks:
            self.console.print(Panel("[green]No active NOW tasks! Time to pick something to do.[/]", 
                                     title="NOW", border_style="green"))
            return
        
        table = Table(
            title=f"🔥 NOW Tasks ({len(tasks)} active)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Status", width=3)
        table.add_column("Pri", width=4)
        table.add_column("Task", min_width=40, max_width=60)
        table.add_column("Project", min_width=15)
        table.add_column("Person", min_width=15)
        table.add_column("Date", width=10)
        
        for task in tasks:
            row = self._task_to_row(task)
            table.add_row(*row[:-1])  # Exclude aging column
        
        self.console.print(table)
    
    def render_waiting(self, aggregator: TaskAggregator) -> None:
        """Render WAITING-FOR tasks with aging."""
        tasks = aggregator.waiting_with_aging()
        
        if not tasks:
            self.console.print(Panel("[green]Nothing waiting! All clear.[/]", 
                                     title="WAITING-FOR", border_style="green"))
            return
        
        table = Table(
            title=f"⏳ WAITING-FOR Items ({len(tasks)} items)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold yellow"
        )
        table.add_column("Status", width=3)
        table.add_column("Pri", width=4)
        table.add_column("Task", min_width=40, max_width=60)
        table.add_column("Project", min_width=15)
        table.add_column("Person", min_width=15)
        table.add_column("Since", width=10)
        table.add_column("Aging", width=10)
        
        for task in tasks:
            row = self._task_to_row(task, show_aging=True)
            # Color aging indicators
            aging = row[6]
            if task.age_days:
                if task.age_days >= 14:
                    aging = f"[bold red]{aging}[/]"
                elif task.age_days >= 7:
                    aging = f"[bold orange]{aging}[/]"
                elif task.age_days >= 3:
                    aging = f"[bold yellow]{aging}[/]"
                else:
                    aging = f"[green]{aging}[/]"
            table.add_row(row[0], row[1], row[2], row[3], row[4], row[5], aging)
        
        self.console.print(table)
        
        # Summary of aged items
        aged = [t for t in tasks if t.age_days and t.age_days >= 7]
        if aged:
            self.console.print(f"\n[bold red]⚠️  {len(aged)} items waiting 7+ days - time to follow up![/]")
    
    def render_later(self, aggregator: TaskAggregator) -> None:
        """Render LATER (scheduled) tasks."""
        tasks = aggregator.later()
        
        if not tasks:
            self.console.print(Panel("[dim]No scheduled tasks.[/]", 
                                     title="LATER", border_style="dim"))
            return
        
        table = Table(
            title=f"📅 LATER Tasks ({len(tasks)} scheduled)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold blue"
        )
        table.add_column("Status", width=3)
        table.add_column("Pri", width=4)
        table.add_column("Task", min_width=40, max_width=60)
        table.add_column("Project", min_width=15)
        table.add_column("Person", min_width=15)
        table.add_column("Date", width=10)
        
        for task in tasks:
            row = self._task_to_row(task)
            table.add_row(*row[:-1])
        
        self.console.print(table)
    
    def render_todo(self, aggregator: TaskAggregator) -> None:
        """Render TODO (next actions) tasks."""
        tasks = aggregator.todo()
        
        if not tasks:
            self.console.print(Panel("[dim]No next actions defined.[/]", 
                                     title="TODO", border_style="dim"))
            return
        
        table = Table(
            title=f"⬜ Next Actions ({len(tasks)} items)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        table.add_column("Status", width=3)
        table.add_column("Pri", width=4)
        table.add_column("Task", min_width=40, max_width=60)
        table.add_column("Project", min_width=15)
        table.add_column("Person", min_width=15)
        table.add_column("Date", width=10)
        
        for task in tasks:
            row = self._task_to_row(task)
            table.add_row(*row[:-1])
        
        self.console.print(table)
    
    def render_stale(self, aggregator: TaskAggregator, days: int = 30) -> None:
        """Render stale tasks."""
        tasks = aggregator.stale(days)
        
        if not tasks:
            self.console.print(Panel(f"[green]No stale tasks (>{days} days old).[/]", 
                                     title="STALE", border_style="green"))
            return
        
        table = Table(
            title=f"🕸️ Stale Tasks ({len(tasks)} items >{days} days old)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold red"
        )
        table.add_column("Status", width=3)
        table.add_column("Pri", width=4)
        table.add_column("Task", min_width=40, max_width=60)
        table.add_column("Project", min_width=15)
        table.add_column("Person", min_width=15)
        table.add_column("Date", width=10)
        table.add_column("Age", width=8)
        
        for task in tasks:
            row = self._task_to_row(task)
            age_days = (datetime.now() - task.date).days
            age_str = f"{age_days}d"
            table.add_row(row[0], row[1], row[2], row[3], row[4], row[5], age_str)
        
        self.console.print(table)
    
    def render_someday(self, aggregator: TaskAggregator) -> None:
        """Render SOMEDAY/MAYBE tasks."""
        tasks = aggregator.someday()
        
        if not tasks:
            self.console.print(Panel("[dim]No someday/maybe items.[/]", 
                                     title="SOMEDAY", border_style="dim"))
            return
        
        table = Table(
            title=f"💭 Someday/Maybe ({len(tasks)} items)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold dim"
        )
        table.add_column("Status", width=3)
        table.add_column("Task", min_width=40, max_width=70)
        table.add_column("Project", min_width=15)
        table.add_column("Date", width=10)
        
        for task in tasks:
            row = self._task_to_row(task)
            table.add_row(row[0], row[2], row[3], row[5])
        
        self.console.print(table)
    
    def render_all(self, aggregator: TaskAggregator) -> None:
        """Render all active tasks grouped by status."""
        self.console.print(Panel.fit(
            "[bold]GTD Dashboard - Complete Overview[/]",
            border_style="cyan"
        ))
        
        self.render_now(aggregator)
        self.console.print()
        self.render_waiting(aggregator)
        self.console.print()
        self.render_todo(aggregator)
        self.console.print()
        self.render_later(aggregator)
    
    def render_stats(self, aggregator: TaskAggregator) -> None:
        """Render statistics dashboard."""
        stats = aggregator.get_stats()
        
        grid = Table.grid(expand=True)
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        
        # Summary cards
        summary = Table(
            title="Summary",
            box=box.ROUNDED,
            show_header=False
        )
        summary.add_column("Metric")
        summary.add_column("Value", justify="right")
        summary.add_row("Total Tasks", str(stats["total"]))
        summary.add_row("Active", f"[bold green]{stats['active']}[/]")
        summary.add_row("Completed", f"[dim]{stats['done']}[/]")
        summary.add_row("Stale", f"[bold red]{stats['stale']}[/]" if stats['stale'] else "0")
        summary.add_row("Projects", str(stats["projects"]))
        summary.add_row("People", str(stats["people"]))
        summary.add_row("Waiting Items", str(stats["waiting_count"]))
        summary.add_row("Avg Wait Time", f"{stats['avg_waiting_age_days']} days")
        
        # Status breakdown
        status_table = Table(
            title="By Status",
            box=box.ROUNDED,
            show_header=False
        )
        status_table.add_column("Status")
        status_table.add_column("Count", justify="right")
        
        for status, count in sorted(stats["by_status"].items(), key=lambda x: -x[1]):
            status_table.add_row(status, str(count))
        
        # Active projects
        projects = aggregator.group_by_project()
        project_table = Table(
            title="Top Projects",
            box=box.ROUNDED,
            show_header=False
        )
        project_table.add_column("Project")
        project_table.add_column("Tasks", justify="right")
        
        sorted_projects = sorted(
            [(p, len(t)) for p, t in projects.items() if p != "No Project"],
            key=lambda x: -x[1]
        )[:10]
        
        for project, count in sorted_projects:
            project_table.add_row(project[:30], str(count))
        
        self.console.print(summary)
        self.console.print()
        self.console.print(status_table)
        self.console.print()
        self.console.print(project_table)
    
    def render_tree(self, aggregator: TaskAggregator) -> None:
        """Render tasks as a tree by project."""
        projects = aggregator.group_by_project()
        
        root = Tree("[bold]GTD Tasks by Project[/]")
        
        for project, tasks in sorted(projects.items()):
            project_node = root.add(f"[cyan]{project}[/] ([dim]{len(tasks)}[/])")
            
            # Group by status
            by_status: dict[str, list[Task]] = {}
            for task in tasks:
                status = task.status.value
                by_status.setdefault(status, []).append(task)
            
            for status, status_tasks in by_status.items():
                status_node = project_node.add(f"[dim]{status} ({len(status_tasks)})[/]")
                for task in status_tasks[:5]:  # Limit to 5 per status
                    content = task.display_content[:50]
                    if len(task.display_content) > 50:
                        content += "..."
                    status_node.add(f"[dim]{content}[/]")
                
                if len(status_tasks) > 5:
                    status_node.add(f"[dim]... and {len(status_tasks) - 5} more[/]")
        
        self.console.print(root)
