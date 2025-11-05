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

    def import_env(self, file_path: str, prefix: str = None) -> None:
        storage, _ = get_storage_and_audit()
        imported = 0
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                   continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if not value:
                    continue
                path = key.lower().replace("_", "/")
                if prefix:
                    path = f"{prefix}/{path}"
                try:
                    storage.set_secret(path, value, "config", ["imported"])
                    imported += 1
                except Exception:
                    continue
        return imported

    def export_env(self) -> dict:
        storage, _ = get_storage_and_audit()
        exported = 0
        secrets_list = storage.list_secrets()
        if not secrets_list:
            return ""

        lines = []
        for secret in secrets_list:
            # Convert path to env var name (database/password -> DATABASE_PASSWORD)
            env_name = secret.path.replace("/", "_").replace("-", "_").upper()
            lines.append(f'{env_name}="{secret.value}"')

        env_content = "\n".join(lines)
        return env_content


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

def import_env(path: str, prefix: str = None):
    return _get_instance().import_env(path, prefix)

def export_env():
    return _get_instance().export_env()

__all__ = ['CruxVault', 'get', 'set', 'delete', 'list', 'history', 'rollback', 'import_env', 'export_env']

