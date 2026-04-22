"""Configuration management for GTD Dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class DashboardConfig:
    """Configuration for GTD Dashboard."""
    
    # Paths
    knowledge_graph_path: Path = Path.home() / "Knowledge"
    daily_notes_path: Path = field(init=False)
    work_context_path: Path = field(init=False)
    
    # Filtering
    default_stale_days: int = 30
    default_waiting_warning_days: int = 7
    default_waiting_critical_days: int = 14
    
    # Display
    max_table_rows: int = 100
    truncate_content_at: int = 80
    show_aging_indicators: bool = True
    
    # Parallel processing
    parallel_parsing: bool = True
    max_workers: Optional[int] = None
    
    # Output
    default_export_format: str = "json"  # json, csv, markdown
    
    def __post_init__(self) -> None:
        """Set derived paths."""
        if not hasattr(self, 'daily_notes_path'):
            self.daily_notes_path = self.knowledge_graph_path / "daily"
        if not hasattr(self, 'work_context_path'):
            self.work_context_path = self.knowledge_graph_path / "work-context" / "daily"
    
    @classmethod
    def from_file(cls, path: Path) -> DashboardConfig:
        """Load configuration from YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Convert path strings to Path objects
        if 'knowledge_graph_path' in data:
            data['knowledge_graph_path'] = Path(data['knowledge_graph_path'])
        
        return cls(**data)
    
    @classmethod
    def auto_discover(cls, start_path: Optional[Path] = None) -> DashboardConfig:
        """Auto-discover configuration from .gtd-dashboard.yaml files."""
        config_names = [
            '.gtd-dashboard.yaml',
            '.gtd-dashboard.yml',
            'gtd-dashboard.yaml',
            'gtd-dashboard.yml',
        ]
        
        # Search from start_path upwards
        if start_path is None:
            start_path = Path.cwd()
        else:
            start_path = Path(start_path)
        
        current = start_path.resolve()
        
        # Check current and parent directories
        for _ in range(10):  # Limit search depth
            for config_name in config_names:
                config_path = current / config_name
                if config_path.exists():
                    return cls.from_file(config_path)
            
            parent = current.parent
            if parent == current:
                break
            current = parent
        
        # Check home directory
        home_config = Path.home() / '.gtd-dashboard.yaml'
        if home_config.exists():
            return cls.from_file(home_config)
        
        # Return defaults
        return cls()
    
    def to_file(self, path: Path) -> None:
        """Save configuration to YAML file."""
        data = {
            'knowledge_graph_path': str(self.knowledge_graph_path),
            'default_stale_days': self.default_stale_days,
            'default_waiting_warning_days': self.default_waiting_warning_days,
            'default_waiting_critical_days': self.default_waiting_critical_days,
            'max_table_rows': self.max_table_rows,
            'truncate_content_at': self.truncate_content_at,
            'show_aging_indicators': self.show_aging_indicators,
            'parallel_parsing': self.parallel_parsing,
            'max_workers': self.max_workers,
            'default_export_format': self.default_export_format,
        }
        
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
    
    def ensure_paths(self) -> bool:
        """Ensure configured paths exist."""
        return (
            self.daily_notes_path.exists() and 
            self.daily_notes_path.is_dir()
        )


def create_default_config(path: Path) -> None:
    """Create a default configuration file."""
    config = DashboardConfig()
    config.to_file(path)
