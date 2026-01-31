"""
SQLite database for download history and state persistence
"""

import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Generator
import json

from macdl.core.models import DownloadJob, DownloadStatus


class Database:
    """
    SQLite database for storing download history and state.
    
    Stores:
    - Download history (completed, failed, cancelled)
    - Download state (for resume support)
    - Statistics
    """
    
    SCHEMA_VERSION = 1
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_dir = Path.home() / ".config" / "macdl"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / "downloads.db"
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema"""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                );
                
                CREATE TABLE IF NOT EXISTS downloads (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    output_path TEXT,
                    total_size INTEGER,
                    downloaded_size INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    error_message TEXT,
                    source_plugin TEXT,
                    original_url TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    metadata TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status);
                CREATE INDEX IF NOT EXISTS idx_downloads_created ON downloads(created_at);
                
                CREATE TABLE IF NOT EXISTS segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    download_id TEXT NOT NULL,
                    segment_id INTEGER NOT NULL,
                    start_byte INTEGER NOT NULL,
                    end_byte INTEGER NOT NULL,
                    downloaded INTEGER DEFAULT 0,
                    completed INTEGER DEFAULT 0,
                    temp_file TEXT,
                    FOREIGN KEY (download_id) REFERENCES downloads(id) ON DELETE CASCADE,
                    UNIQUE(download_id, segment_id)
                );
                
                CREATE TABLE IF NOT EXISTS statistics (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)
            
            # Set schema version if not exists
            cursor = conn.execute("SELECT version FROM schema_version LIMIT 1")
            if cursor.fetchone() is None:
                conn.execute("INSERT INTO schema_version (version) VALUES (?)", 
                           (self.SCHEMA_VERSION,))
    
    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with proper cleanup"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def save_download(self, job: DownloadJob) -> None:
        """Save or update a download job"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO downloads 
                (id, url, filename, output_path, total_size, downloaded_size, 
                 status, error_message, source_plugin, original_url,
                 created_at, started_at, completed_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id,
                job.url,
                job.filename,
                str(job.output_path) if job.output_path else None,
                job.total_size,
                job.downloaded_size,
                job.status.value,
                job.error_message,
                job.source_plugin,
                job.original_url,
                job.created_at.isoformat(),
                job.started_at.isoformat() if job.started_at else None,
                job.completed_at.isoformat() if job.completed_at else None,
                json.dumps({"num_threads": job.num_threads}),
            ))
            
            # Save segments
            for segment in job.segments:
                conn.execute("""
                    INSERT OR REPLACE INTO segments
                    (download_id, segment_id, start_byte, end_byte, downloaded, completed, temp_file)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.id,
                    segment.id,
                    segment.start,
                    segment.end,
                    segment.downloaded,
                    1 if segment.completed else 0,
                    str(segment.temp_file) if segment.temp_file else None,
                ))
    
    def get_download(self, download_id: str) -> Optional[DownloadJob]:
        """Get a download by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM downloads WHERE id = ?", (download_id,)
            ).fetchone()
            
            if row is None:
                return None
            
            return self._row_to_job(row)
    
    def get_downloads(
        self,
        status: Optional[DownloadStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DownloadJob]:
        """Get downloads with optional filtering"""
        with self._get_connection() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM downloads WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (status.value, limit, offset)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM downloads ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                ).fetchall()
            
            return [self._row_to_job(row) for row in rows]
    
    def get_pending_downloads(self) -> list[DownloadJob]:
        """Get downloads that are pending or in progress"""
        return self.get_downloads(status=DownloadStatus.PENDING) + \
               self.get_downloads(status=DownloadStatus.DOWNLOADING)
    
    def delete_download(self, download_id: str) -> bool:
        """Delete a download by ID"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM segments WHERE download_id = ?", (download_id,))
            cursor = conn.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
            return cursor.rowcount > 0
    
    def clear_history(self, keep_days: int = 0) -> int:
        """Clear download history, optionally keeping recent entries"""
        with self._get_connection() as conn:
            if keep_days > 0:
                cutoff = datetime.now().isoformat()
                cursor = conn.execute(
                    "DELETE FROM downloads WHERE created_at < date(?, ?)",
                    (cutoff, f"-{keep_days} days")
                )
            else:
                cursor = conn.execute("DELETE FROM downloads")
            
            conn.execute("DELETE FROM segments WHERE download_id NOT IN (SELECT id FROM downloads)")
            
            return cursor.rowcount
    
    def get_statistics(self) -> dict:
        """Get download statistics"""
        with self._get_connection() as conn:
            stats = {}
            
            # Total downloads
            row = conn.execute("SELECT COUNT(*) as count FROM downloads").fetchone()
            stats["total_downloads"] = row["count"]
            
            # By status
            rows = conn.execute(
                "SELECT status, COUNT(*) as count FROM downloads GROUP BY status"
            ).fetchall()
            stats["by_status"] = {row["status"]: row["count"] for row in rows}
            
            # Total bytes downloaded
            row = conn.execute(
                "SELECT SUM(downloaded_size) as total FROM downloads WHERE status = 'completed'"
            ).fetchone()
            stats["total_bytes"] = row["total"] or 0
            
            return stats
    
    def _row_to_job(self, row: sqlite3.Row) -> DownloadJob:
        """Convert database row to DownloadJob"""
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        
        job = DownloadJob(
            id=row["id"],
            url=row["url"],
            filename=row["filename"],
            output_path=Path(row["output_path"]) if row["output_path"] else None,
            total_size=row["total_size"],
            downloaded_size=row["downloaded_size"],
            status=DownloadStatus(row["status"]),
            error_message=row["error_message"],
            source_plugin=row["source_plugin"],
            original_url=row["original_url"],
            num_threads=metadata.get("num_threads", 8),
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )
        
        return job


# Global database instance
_db: Optional[Database] = None


def get_db() -> Database:
    """Get the global database instance"""
    global _db
    if _db is None:
        _db = Database()
    return _db
