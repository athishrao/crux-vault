import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from cruxvault.models import AuditEntry


class AuditLogger:
    def __init__(self, log_path: str, enabled: bool = True, log_reads: bool = False) -> None:
        self.log_path = log_path
        self.enabled = enabled
        self.log_reads = log_reads

        log_dir = os.path.dirname(log_path)
        if log_dir:
            Path(log_dir).mkdir(parents=True, exist_ok=True)

    def log(
        self,
        action: str,
        path: str,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        if not self.enabled:
            return

        if not self.log_reads and action in ["get", "list"]:
            return

        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            user=os.getenv("USER", "unknown"),
            action=action,
            path=path,
            success=success,
            error=error,
            metadata=metadata or {},
        )

        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry.model_dump(), default=str) + "\n")
        except Exception:
            pass

    def get_recent_entries(self, limit: int = 100) -> list[AuditEntry]:
        if not os.path.exists(self.log_path):
            return []

        entries = []
        try:
            with open(self.log_path, "r") as f:
                lines = f.readlines()

            for line in reversed(lines[-limit:]):
                try:
                    data = json.loads(line)
                    entries.append(AuditEntry(**data))
                except Exception:
                    continue

            return entries
        except Exception:
            return []

    def get_entries_for_path(self, path: str, limit: int = 100) -> list[AuditEntry]:
        if not os.path.exists(self.log_path):
            return []

        entries = []
        try:
            with open(self.log_path, "r") as f:
                lines = f.readlines()

            # Parse JSON lines and filter by path
            for line in reversed(lines):
                try:
                    data = json.loads(line)
                    if data.get("path") == path:
                        entries.append(AuditEntry(**data))
                        if len(entries) >= limit:
                            break
                except Exception:
                    continue

            return entries
        except Exception:
            return []

