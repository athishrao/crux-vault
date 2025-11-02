import os
import yaml
from pathlib import Path
from typing import Optional

from cruxvault.models import AppConfig


class ConfigManager:

    DEFAULT_CONFIG_DIR = ".cruxvault"
    DEFAULT_CONFIG_FILE = "config.yaml"

    def __init__(self, config_dir: str = DEFAULT_CONFIG_DIR) -> None:
        self.config_dir = config_dir
        # self.config_path = os.path.join(config_dir, self.DEFAULT_CONFIG_FILE)

    def initialize(self) -> None:
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)

        # Create default config if it doesn't exist
        if self.config_path is None or not os.path.exists(self.config_path):
            default_config = AppConfig()
            self.save_config(default_config)

    @property
    def config_path(self) -> str:
        return self.get_config_path()

    def find_crux_root(self) -> Path:
        current = Path.cwd()
        while current != current.parent:
            unified_dir = current / self.config_dir
            if unified_dir.exists():
                return current
            current = current.parent
        return None
        # raise FileNotFoundError(f"Not in a cruxvault project (no {self.config_dir} found)")
    
    def get_config_path(self) -> Path:
        root = self.find_crux_root()
        if root is None:
            return None
        return root / self.config_dir / self.DEFAULT_CONFIG_FILE

    def load_config(self) -> AppConfig:
        if not os.path.exists(self.config_path):
            return AppConfig()

        try:
            with open(self.config_path, "r") as f:
                data = yaml.safe_load(f)
                return AppConfig(**data) if data else AppConfig()
        except Exception:
            return AppConfig()

    def save_config(self, config: AppConfig) -> None:
        # Path(self.config_dir).mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w") as f:
            yaml.dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)

    def get_storage_path(self) -> str:
        config = self.load_config()
        storage_path = config.storage.path

        if not os.path.isabs(storage_path):
            storage_path = os.path.join(self.find_crux_root(), self.config_dir, os.path.basename(storage_path))

        return storage_path

    def get_audit_path(self) -> str:
        config = self.load_config()
        audit_path = config.audit.path

        if not os.path.isabs(audit_path):
            audit_path = os.path.join(self.find_crux_root(), self.config_dir, os.path.basename(audit_path))

        return audit_path
