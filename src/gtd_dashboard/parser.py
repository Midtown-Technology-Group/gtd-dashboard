"""Task parser for extracting GTD tasks from Logseq daily notes."""

from __future__ import annotations

import hashlib
import re
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from gtd_dashboard.models import Task, TaskStatus


class TaskParser:
    """Parser for extracting GTD tasks from Logseq markdown files."""
    
    # Regex patterns for task markers (Logseq style)
    TASK_PATTERNS = [
        # NOW/DOING - currently doing
        (r'(?:^|\n)\s*-?\s*(NOW|DOING|IN-PROGRESS)\s+(.*)$', TaskStatus.NOW),
        # LATER - scheduled
        (r'(?:^|\n)\s*-?\s*LATER\s+(.*)$', TaskStatus.LATER),
        # TODO/TODO - next action
        (r'(?:^|\n)\s*-?\s*(?:TODO|NEXT)\s+(.*)$', TaskStatus.TODO),
        # WAITING-FOR - waiting
        (r'(?:^|\n)\s*-?\s*WAITING(?:-FOR)?\s+(.*)$', TaskStatus.WAITING),
        # SOMEDAY/MAYBE
        (r'(?:^|\n)\s*-?\s*(SOMEDAY|MAYBE)\s+(.*)$', TaskStatus.SOMEDAY),
        # DONE - completed
        (r'(?:^|\n)\s*-?\s*DONE\s+(.*)$', TaskStatus.DONE),
        # CANCELLED
        (r'(?:^|\n)\s*-?\s*CANCELLED\s+(.*)$', TaskStatus.CANCELLED),
        # Checkbox style with markers: - [ ] TODO: task or - [ ] NOW task
        (r'(?:^|\n)\s*- \[.]\s*(NOW|DOING|LATER|TODO|NEXT|WAITING|WAITING-FOR|SOMEDAY|MAYBE|DONE|CANCELLED)[:\s]+(.*)$', None),
        # Checkbox without explicit marker (infer TODO)
        (r'(?:^|\n)\s*- \[ ]\s+(.*)$', TaskStatus.TODO),
        # Completed checkbox (infer DONE)
        (r'(?:^|\n)\s*- \[[xX]]\s+(.*)$', TaskStatus.DONE),
    ]
    
    def __init__(self, daily_notes_path: Path, max_workers: Optional[int] = None) -> None:
        """Initialize parser.
        
        Args:
            daily_notes_path: Path to daily/ directory containing YYYY-MM-DD.md files
            max_workers: Maximum number of parallel workers (None = auto)
        """
        self.daily_notes_path = Path(daily_notes_path)
        self.max_workers = max_workers
    
    def _extract_date_from_filename(self, filename: str) -> Optional[datetime]:
        """Extract date from filename like YYYY-MM-DD.md."""
        match = re.match(r'(\d{4})-(\d{2})-(\d{2})\.md$', filename)
        if match:
            year, month, day = map(int, match.groups())
            try:
                return datetime(year, month, day)
            except ValueError:
                return None
        return None
    
    def _generate_task_id(self, content: str, date: datetime, line_num: int) -> str:
        """Generate unique task ID from content hash."""
        hash_input = f"{date.isoformat()}:{line_num}:{content}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _parse_file(self, file_path: Path) -> list[Task]:
        """Parse a single daily note file and extract tasks."""
        tasks = []
        
        date = self._extract_date_from_filename(file_path.name)
        if not date:
            return tasks
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except (IOError, OSError) as e:
            return tasks
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.rstrip()
            if not line:
                continue
            
            for pattern, default_status in self.TASK_PATTERNS:
                match = re.match(pattern, line)
                if match:
                    # Extract status and content
                    if default_status is None:
                        # Status is in the first capture group
                        status_str = match.group(1).upper()
                        task_content = match.group(2).strip()
                        
                        # Map various forms to standard statuses
                        status_map = {
                            'NOW': TaskStatus.NOW,
                            'DOING': TaskStatus.NOW,
                            'IN-PROGRESS': TaskStatus.NOW,
                            'LATER': TaskStatus.LATER,
                            'TODO': TaskStatus.TODO,
                            'NEXT': TaskStatus.TODO,
                            'WAITING': TaskStatus.WAITING,
                            'WAITING-FOR': TaskStatus.WAITING,
                            'SOMEDAY': TaskStatus.SOMEDAY,
                            'MAYBE': TaskStatus.SOMEDAY,
                            'DONE': TaskStatus.DONE,
                            'CANCELLED': TaskStatus.CANCELLED,
                        }
                        status = status_map.get(status_str, TaskStatus.TODO)
                    else:
                        # Status is predetermined
                        status = default_status
                        if len(match.groups()) >= 1:
                            task_content = match.group(1 if default_status in (TaskStatus.DONE, TaskStatus.TODO) else len(match.groups())).strip()
                        else:
                            task_content = line.strip()
                    
                    # Skip empty content
                    if not task_content:
                        continue
                    
                    # Generate task ID
                    task_id = self._generate_task_id(task_content, date, line_num)
                    
                    # Determine waiting_since for WAITING tasks
                    waiting_since = None
                    if status in (TaskStatus.WAITING, TaskStatus.WAITING_FOR):
                        waiting_since = date
                    
                    task = Task(
                        id=task_id,
                        content=task_content,
                        status=status,
                        source_file=file_path,
                        date=date,
                        line_number=line_num,
                        raw_line=line,
                        waiting_since=waiting_since,
                    )
                    
                    tasks.append(task)
                    break  # Only match first pattern per line
        
        return tasks
    
    def parse_all(self, parallel: bool = True) -> Iterator[Task]:
        """Parse all daily notes and yield tasks.
        
        Args:
            parallel: Use parallel processing for large numbers of files
            
        Yields:
            Task objects
        """
        files = list(self.daily_notes_path.glob('*.md'))
        
        if not files:
            return
        
        # Use parallel processing for many files
        if parallel and len(files) > 50:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                results = executor.map(self._parse_file, files)
                for tasks in results:
                    yield from tasks
        elif parallel and len(files) > 10:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                results = executor.map(self._parse_file, files)
                for tasks in results:
                    yield from tasks
        else:
            for file_path in files:
                yield from self._parse_file(file_path)
    
    def parse_single(self, file_path: Path) -> list[Task]:
        """Parse a single file and return tasks."""
        return self._parse_file(file_path)
    
    def get_stats(self) -> dict:
        """Return parsing statistics."""
        files = list(self.daily_notes_path.glob('*.md'))
        
        total_tasks = 0
        status_counts: dict[str, int] = {}
        
        for task in self.parse_all(parallel=False):
            total_tasks += 1
            status_counts[task.status.value] = status_counts.get(task.status.value, 0) + 1
        
        return {
            "total_files": len(files),
            "total_tasks": total_tasks,
            "status_counts": status_counts,
        }
