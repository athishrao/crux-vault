from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SecretType(str, Enum):
    SECRET = "secret"
    CONFIG = "config"
    FLAG = "flag"


class Secret(BaseModel):
    path: str = Field(..., description="Path to the secret (e.g., database/password)")
    value: str = Field(..., description="Secret value")
    type: SecretType = Field(default=SecretType.SECRET, description="Type of secret")
    version: int = Field(default=1, description="Version number")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tags: list[str] = Field(default_factory=list, description="Tags for organization")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SecretVersion(BaseModel):
    path: str
    value: str
    version: int
    created_at: datetime
    created_by: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class StorageConfig(BaseModel):
    backend: str = Field(default="sqlite", description="Storage backend")
    path: str = Field(default=".unified/store.db", description="Path to storage file")
    encryption_enabled: bool = Field(default=True, description="Whether encryption is enabled")


class AppConfig(BaseModel):
    storage: StorageConfig = Field(default_factory=StorageConfig)
    default_tags: list[str] = Field(default_factory=list, description="Default tags for secrets")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

