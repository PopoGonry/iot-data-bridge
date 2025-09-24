"""
Log Management Utilities
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict


class LogManager:
    """Log file management utilities"""
    
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def get_log_files(self, pattern: str = "*") -> List[Path]:
        """Get all log files matching pattern"""
        return list(self.logs_dir.glob(f"{pattern}*.log"))
    
    def get_log_files_by_date(self, date_str: str) -> List[Path]:
        """Get log files for specific date (YYYYMMDD)"""
        return list(self.logs_dir.glob(f"*{date_str}*.log"))
    
    def get_log_files_by_device(self, device_id: str) -> List[Path]:
        """Get log files for specific device"""
        return list(self.logs_dir.glob(f"device_{device_id}_*.log"))
    
    def get_log_files_by_middleware(self) -> List[Path]:
        """Get middleware log files"""
        return list(self.logs_dir.glob("iot_data_bridge_*.log"))
    
    def cleanup_old_logs(self, days: int = 7) -> int:
        """Clean up log files older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        for log_file in self.get_log_files():
            if log_file.stat().st_mtime < cutoff_date.timestamp():
                try:
                    log_file.unlink()
                    cleaned_count += 1
                except Exception:
                    pass
        
        return cleaned_count
    
    def get_log_summary(self) -> Dict:
        """Get summary of log files"""
        all_logs = self.get_log_files()
        
        summary = {
            "total_files": len(all_logs),
            "total_size_mb": sum(f.stat().st_size for f in all_logs) / (1024 * 1024),
            "device_logs": len(self.get_log_files_by_device("*")),
            "middleware_logs": len(self.get_log_files_by_middleware()),
            "oldest_log": min((f.stat().st_mtime for f in all_logs), default=0),
            "newest_log": max((f.stat().st_mtime for f in all_logs), default=0)
        }
        
        return summary
    
    def archive_logs(self, archive_dir: str = "logs/archive") -> int:
        """Archive old log files"""
        archive_path = Path(archive_dir)
        archive_path.mkdir(parents=True, exist_ok=True)
        
        archived_count = 0
        cutoff_date = datetime.now() - timedelta(days=3)
        
        for log_file in self.get_log_files():
            if log_file.stat().st_mtime < cutoff_date.timestamp():
                try:
                    archive_file = archive_path / log_file.name
                    shutil.move(str(log_file), str(archive_file))
                    archived_count += 1
                except Exception:
                    pass
        
        return archived_count


def get_log_files_info():
    """Get information about all log files"""
    manager = LogManager()
    return manager.get_log_summary()


if __name__ == "__main__":
    # Test log management
    manager = LogManager()
    
    print("=== Log Files Summary ===")
    summary = manager.get_log_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    print("\n=== All Log Files ===")
    for log_file in manager.get_log_files():
        print(f"{log_file.name} - {log_file.stat().st_size} bytes")
