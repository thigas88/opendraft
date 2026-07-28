import time
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from engine.ui.database import get_db, init_db

logger = logging.getLogger(__name__)

class SQLiteTracker:
    """Tracks draft generation progress locally using SQLite for the Web UI."""
    
    MAX_ACTIVITY_LOG_SIZE = 50

    def __init__(self, job_id: str):
        self.job_id = job_id
        self._activity_log: List[Dict[str, Any]] = []
        self._progress_details: Dict[str, Any] = {}
        init_db()

    def _get_phase_emoji(self, phase: str) -> str:
        emojis = {
            "research": "🔍",
            "structure": "📋",
            "writing": "✍️",
            "compiling": "🔧",
            "exporting": "📄",
            "completed": "✅",
            "error": "❌",
        }
        return emojis.get(phase, "📌")

    def _add_activity_entry(self, phase: str, message: str, event_type: str = "info"):
        entry = {
            "id": f"{phase}_{event_type}_{int(time.time() * 1000)}",
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message,
            "icon": self._get_phase_emoji(phase or "research"),
        }
        self._activity_log.append(entry)
        if len(self._activity_log) > self.MAX_ACTIVITY_LOG_SIZE:
            self._activity_log = self._activity_log[-self.MAX_ACTIVITY_LOG_SIZE:]

    def log_activity(self, message: str, event_type: str = "info", phase: str = "research"):
        self._add_activity_entry(phase, message, event_type)
        self._update_db()

    def update_phase(
        self,
        phase: str,
        progress_percent: int = 0,
        sources_count: Optional[int] = None,
        chapters_count: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if details:
            self._progress_details.update(details)
            
        # Extract stage or use phase name for log message
        stage = details.get("stage", phase) if details else phase
        
        # Add a brief log entry if a stage changes
        if progress_percent > 0:
            self._add_activity_entry(phase, f"Started {stage}", "info")
            
        self._update_db(phase=phase, progress_percent=progress_percent)
        logger.info(f"Progress [{self.job_id}]: {phase} ({progress_percent}%)")

    def _update_db(self, phase: Optional[str] = None, progress_percent: Optional[int] = None):
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            updates = ["updated_at = ?"]
            params = [datetime.now().isoformat()]
            
            if phase:
                updates.append("current_phase = ?")
                params.append(phase)
            if progress_percent is not None:
                updates.append("progress_percent = ?")
                params.append(progress_percent)
                
            details_json = json.dumps({
                "activity_log": self._activity_log,
                **self._progress_details
            })
            updates.append("progress_details = ?")
            params.append(details_json)
            
            params.append(self.job_id)
            
            cursor.execute(f'''
                UPDATE jobs SET {", ".join(updates)} WHERE id = ?
            ''', params)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to update SQLiteTracker: {e}")

    def check_cancellation(self):
        pass
        
    def send_heartbeat(self):
        self._update_db()
        
    def log_source_found(self, title: str, authors: List[str] = None, year: int = None, source_type: str = "paper", doi: str = None, url: str = None, verified: bool = True):
        self.log_activity(f"📄 Encontrado: {title}", event_type="found", phase="research")
        
    def update_research(self, sources_count: int, phase_detail: str = ""):
        self.update_phase("research", details={"sources_count": sources_count, "stage": phase_detail})
        
    def update_exporting(self, export_type: str = ""):
        self.update_phase("exporting", details={"stage": f"exporting_{export_type}"})

    def mark_completed(self):
        try:
            self._add_activity_entry("completed", "Generation completed successfully", "success")
            self._update_db(phase="completed", progress_percent=100)
            
            conn = get_db()
            conn.execute(
                "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
                ("completed", datetime.now().isoformat(), self.job_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to mark completed in SQLiteTracker: {e}")

    def mark_failed(self, error_message: str = None):
        try:
            self._add_activity_entry("error", f"Failed: {error_message}", "error")
            self._update_db(phase="error")
            
            conn = get_db()
            conn.execute(
                "UPDATE jobs SET status = ?, error_message = ?, updated_at = ? WHERE id = ?",
                ("error", error_message, datetime.now().isoformat(), self.job_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to mark failed in SQLiteTracker: {e}")
