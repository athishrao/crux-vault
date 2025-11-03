"""CruxVault CLI - Secrets, configs, and feature flags management."""

__version__ = "0.1.0"

from pathlib import Path
from dataclasses import asdict
from rich.console import Console
from rich.table import Table

from cruxvault.storage.local import SQLiteStorage
from cruxvault.crypto.encryption import Encryptor
from cruxvault.utils.utils import get_storage_and_audit

class CruxVault:
    def __init__(self, root: Path = None):
        storage, _ = get_storage_and_audit()
        self._storage = storage

    def get(self, path: str) -> str:
        return self._storage.get_secret(path).value

    def set(self, path: str, value: str, tags: list = None) -> None:
        self._storage.set_secret(path, value, tags=tags)

    def delete(self, path: str) -> bool:
        return self._storage.delete_secret(path)

    def list(self, prefix: str = None, print_: bool = False) -> list:
        secrets = self._storage.list_secrets(prefix)
        
        data = [
            {
                "path": s.path,
                "type": s.type.value,
                "version": s.version,
                "tags": s.tags,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in secrets
        ]
        
        if print_:
            console = Console()
            table = Table(show_header=True)
            table.add_column("Path")
            table.add_column("Type")
            table.add_column("Version")
            table.add_column("Tags")
            table.add_column("Updated")
            
            for item in data:
                table.add_row(
                    item["path"],
                    item["type"],
                    str(item["version"]),
                    ", ".join(item["tags"]),
                    item["updated_at"][:10]
                )
            
            console.print(table)
            return None
        
        return data

    def history(self, path: str, print_: bool = False) -> dict:
        versions = self._storage.get_history(path)
        
        data = [
            {
                "version": v.version,
                "value": v.value,
                "created_at": v.created_at.isoformat(),
                "created_by": v.created_by or "unknown",
            }
            for v in versions
        ]
        
        if print_:
            console = Console()
            table = Table(title=f"History for {path}")
            table.add_column("Version")
            table.add_column("Created")
            table.add_column("Created By")
            table.add_column("Value Preview")
            
            for v in data:
                table.add_row(
                    str(v["version"]),
                    v["created_at"][:19],
                    v["created_by"],
                    v["value"][:20] + "..." if len(v["value"]) > 20 else v["value"]
                )
            
            console.print(table)
            return None
        
        return data
    
    def rollback(self, path: str, version: int) -> None:
        self._storage.rollback(path, version)

_instance = None

def _get_instance():
    global _instance
    if _instance is None:
        _instance = CruxVault()
    return _instance

def get(path: str) -> str:
    return _get_instance().get(path)

def set(path: str, value: str, tags: list = None):
    return _get_instance().set(path, value, tags)

def delete(path: str):
    return _get_instance().delete(path)

def list(prefix: str = None, print_: bool = False):
    return _get_instance().list(prefix, print_)

def history(path: str, print_: bool = False):
    return _get_instance().history(path, print_)

def rollback(path: str, version: int):
    return _get_instance().rollback(path, version)


__all__ = ['CruxVault', 'get', 'set', 'delete', 'list', 'history', 'rollback']

