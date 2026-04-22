"""Tests for GTD Dashboard parser."""

from datetime import datetime
from pathlib import Path

import pytest

from gtd_dashboard.models import Task, TaskStatus
from gtd_dashboard.parser import TaskParser


class TestTaskParser:
    """Tests for the TaskParser class."""
    
    def test_extract_date_from_filename_valid(self, tmp_path: Path) -> None:
        """Test extracting date from valid filename."""
        parser = TaskParser(tmp_path)
        
        date = parser._extract_date_from_filename("2024-03-15.md")
        
        assert date is not None
        assert date.year == 2024
        assert date.month == 3
        assert date.day == 15
    
    def test_extract_date_from_filename_invalid(self, tmp_path: Path) -> None:
        """Test extracting date from invalid filename."""
        parser = TaskParser(tmp_path)
        
        date = parser._extract_date_from_filename("invalid.md")
        
        assert date is None
    
    def test_parse_file_with_now_task(self, tmp_path: Path) -> None:
        """Test parsing a file with NOW task."""
        # Create test file
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        
        test_file = daily_dir / "2024-03-15.md"
        test_file.write_text("""
# 2024-03-15

- NOW Working on the important feature
- LATER Schedule the meeting
- TODO Buy groceries
""")
        
        parser = TaskParser(daily_dir)
        tasks = parser.parse_single(test_file)
        
        assert len(tasks) == 3
        
        now_tasks = [t for t in tasks if t.status == TaskStatus.NOW]
        assert len(now_tasks) == 1
        assert "important feature" in now_tasks[0].content
    
    def test_parse_file_with_checkbox_tasks(self, tmp_path: Path) -> None:
        """Test parsing checkbox style tasks."""
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        
        test_file = daily_dir / "2024-03-15.md"
        test_file.write_text("""
# Test Day

- [ ] Unchecked task becomes TODO
- [x] Completed task becomes DONE
- [ ] NOW: Task with marker
""")
        
        parser = TaskParser(daily_dir)
        tasks = parser.parse_single(test_file)
        
        todo_tasks = [t for t in tasks if t.status == TaskStatus.TODO]
        done_tasks = [t for t in tasks if t.status == TaskStatus.DONE]
        now_tasks = [t for t in tasks if t.status == TaskStatus.NOW]
        
        assert len(todo_tasks) >= 1
        assert len(done_tasks) >= 1
    
    def test_parse_file_with_waiting_task(self, tmp_path: Path) -> None:
        """Test parsing WAITING-FOR task with aging."""
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        
        test_file = daily_dir / "2024-03-15.md"
        test_file.write_text("""
- WAITING-FOR Response from John about the proposal
""")
        
        parser = TaskParser(daily_dir)
        tasks = parser.parse_single(test_file)
        
        waiting_tasks = [t for t in tasks if t.status == TaskStatus.WAITING]
        assert len(waiting_tasks) == 1
        assert waiting_tasks[0].waiting_since is not None
    
    def test_parse_file_with_project_link(self, tmp_path: Path) -> None:
        """Test extracting project from [[project/name]] link."""
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        
        test_file = daily_dir / "2024-03-15.md"
        test_file.write_text("""
- TODO [[projects/bifrost]] Fix the API endpoint
""")
        
        parser = TaskParser(daily_dir)
        tasks = parser.parse_single(test_file)
        
        assert len(tasks) == 1
        assert tasks[0].project == "bifrost"
    
    def test_parse_file_with_person_link(self, tmp_path: Path) -> None:
        """Test extracting person from [[people/name]] link."""
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        
        test_file = daily_dir / "2024-03-15.md"
        test_file.write_text("""
- TODO Discuss with [[people/John-Smith]] about requirements
""")
        
        parser = TaskParser(daily_dir)
        tasks = parser.parse_single(test_file)
        
        assert len(tasks) == 1
        assert tasks[0].person == "John Smith"
    
    def test_task_id_generation(self, tmp_path: Path) -> None:
        """Test that task IDs are unique and deterministic."""
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        
        test_file = daily_dir / "2024-03-15.md"
        test_file.write_text("- TODO Test task")
        
        parser = TaskParser(daily_dir)
        tasks = parser.parse_single(test_file)
        
        assert len(tasks) == 1
        assert len(tasks[0].id) == 16  # SHA256 hex truncated
        assert all(c in '0123456789abcdef' for c in tasks[0].id)
    
    def test_parse_all_multiple_files(self, tmp_path: Path) -> None:
        """Test parsing multiple files."""
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        
        # Create multiple files
        for day in range(1, 4):
            test_file = daily_dir / f"2024-03-{day:02d}.md"
            test_file.write_text(f"- TODO Task for day {day}")
        
        parser = TaskParser(daily_dir)
        tasks = list(parser.parse_all(parallel=False))
        
        assert len(tasks) == 3


class TestTaskModel:
    """Tests for the Task data model."""
    
    def test_task_aging_calculation(self, tmp_path: Path) -> None:
        """Test age calculation for waiting tasks."""
        old_date = datetime(2024, 1, 1)
        
        task = Task(
            id="test123",
            content="WAITING-FOR Something",
            status=TaskStatus.WAITING,
            source_file=tmp_path / "test.md",
            date=old_date,
            line_number=1,
            raw_line="- WAITING-FOR Something",
            waiting_since=old_date,
        )
        
        assert task.age_days is not None
        assert task.age_days > 0
    
    def test_task_stale_detection(self, tmp_path: Path) -> None:
        """Test stale task detection."""
        very_old = datetime(2020, 1, 1)
        
        task = Task(
            id="test123",
            content="TODO Old task",
            status=TaskStatus.TODO,
            source_file=tmp_path / "test.md",
            date=very_old,
            line_number=1,
            raw_line="- TODO Old task",
        )
        
        assert task.is_stale
    
    def test_task_aging_indicator(self, tmp_path: Path) -> None:
        """Test aging indicator emoji."""
        task = Task(
            id="test123",
            content="WAITING-FOR Something",
            status=TaskStatus.WAITING,
            source_file=tmp_path / "test.md",
            date=datetime.now(),
            line_number=1,
            raw_line="- WAITING-FOR Something",
            waiting_since=datetime.now(),
        )
        
        # New task should have green indicator
        assert "🟢" in task.aging_indicator
    
    def test_display_content_cleaning(self, tmp_path: Path) -> None:
        """Test content cleaning for display."""
        task = Task(
            id="test123",
            content="TODO [[projects/test]] Fix the #bug",
            status=TaskStatus.TODO,
            source_file=tmp_path / "test.md",
            date=datetime.now(),
            line_number=1,
            raw_line="- TODO [[projects/test]] Fix the #bug",
        )
        
        display = task.display_content
        assert "[[" not in display
        assert "TODO" not in display
        assert "projects/test" in display


class TestAggregator:
    """Tests for TaskAggregator."""
    
    def test_filter_by_status(self, tmp_path: Path) -> None:
        """Test filtering tasks by status."""
        from gtd_dashboard.aggregator import TaskAggregator
        
        tasks = [
            Task(id="1", content="NOW Task 1", status=TaskStatus.NOW, 
                 source_file=tmp_path / "a.md", date=datetime.now(), line_number=1, raw_line=""),
            Task(id="2", content="NOW Task 2", status=TaskStatus.NOW, 
                 source_file=tmp_path / "a.md", date=datetime.now(), line_number=2, raw_line=""),
            Task(id="3", content="TODO Task", status=TaskStatus.TODO, 
                 source_file=tmp_path / "a.md", date=datetime.now(), line_number=3, raw_line=""),
        ]
        
        agg = TaskAggregator(tasks)
        now_tasks = agg.now()
        
        assert len(now_tasks) == 2
    
    def test_filter_by_project(self, tmp_path: Path) -> None:
        """Test filtering tasks by project."""
        from gtd_dashboard.aggregator import TaskAggregator
        
        t1 = Task(id="1", content="Task", status=TaskStatus.TODO, 
                  source_file=tmp_path / "a.md", date=datetime.now(), line_number=1, raw_line="",
                  project="ProjectA")
        t2 = Task(id="2", content="Task", status=TaskStatus.TODO, 
                  source_file=tmp_path / "a.md", date=datetime.now(), line_number=2, raw_line="",
                  project="ProjectB")
        
        agg = TaskAggregator([t1, t2])
        project_a_tasks = agg.by_project("ProjectA")
        
        assert len(project_a_tasks) == 1
        assert project_a_tasks[0].project == "ProjectA"
    
    def test_group_by_status(self, tmp_path: Path) -> None:
        """Test grouping tasks by status."""
        from gtd_dashboard.aggregator import TaskAggregator
        
        tasks = [
            Task(id="1", content="NOW Task", status=TaskStatus.NOW, 
                 source_file=tmp_path / "a.md", date=datetime.now(), line_number=1, raw_line=""),
            Task(id="2", content="TODO Task", status=TaskStatus.TODO, 
                 source_file=tmp_path / "a.md", date=datetime.now(), line_number=2, raw_line=""),
            Task(id="3", content="LATER Task", status=TaskStatus.LATER, 
                 source_file=tmp_path / "a.md", date=datetime.now(), line_number=3, raw_line=""),
        ]
        
        agg = TaskAggregator(tasks)
        groups = agg.group_by_status()
        
        assert "NOW" in groups
        assert "TODO" in groups
        assert "LATER" in groups
        assert len(groups["NOW"]) == 1


class TestConfig:
    """Tests for configuration."""
    
    def test_default_config(self) -> None:
        """Test default configuration values."""
        from gtd_dashboard.config import DashboardConfig
        
        config = DashboardConfig()
        
        assert config.default_stale_days == 30
        assert config.parallel_parsing is True
        assert config.show_aging_indicators is True
    
    def test_config_save_and_load(self, tmp_path: Path) -> None:
        """Test saving and loading configuration."""
        from gtd_dashboard.config import DashboardConfig
        
        config_path = tmp_path / "test-config.yaml"
        config = DashboardConfig(knowledge_graph_path=tmp_path / "custom")
        
        config.to_file(config_path)
        
        loaded = DashboardConfig.from_file(config_path)
        
        assert loaded.knowledge_graph_path == config.knowledge_graph_path
        assert loaded.default_stale_days == config.default_stale_days
