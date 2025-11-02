import os
import yaml
from pathlib import Path
from typing import Optional

from unified.models import AppConfig


class ConfigManager:

    DEFAULT_CONFIG_DIR = ".unified"
    DEFAULT_CONFIG_FILE = "config.yaml"

    def __init__(self, config_dir: str = DEFAULT_CONFIG_DIR) -> None:
        self.config_dir = config_dir
        self.config_path = os.path.join(config_dir, self.DEFAULT_CONFIG_FILE)

    def initialize(self) -> None:
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)

        # Create default config if it doesn't exist
        if not os.path.exists(self.config_path):
            default_config = AppConfig()
            self.save_config(default_config)

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
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w") as f:
            yaml.dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)

    def get_storage_path(self) -> str:
        config = self.load_config()
        storage_path = config.storage.path

        if not os.path.isabs(storage_path):
            storage_path = os.path.join(self.config_dir, os.path.basename(storage_path))

        return storage_path
