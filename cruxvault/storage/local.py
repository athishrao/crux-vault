import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from cruxvault.crypto.encryption import Encryptor
from cruxvault.models import Secret, SecretType, SecretVersion, AuditEntry
from cruxvault.storage.base import StorageBackend
from cruxvault.storage.models import Base, SecretModel, SecretVersionModel, AuditLogModel


class SQLiteStorage(StorageBackend):
    def __init__(self, db_path: str, encryptor: Encryptor) -> None:
        self.db_path = db_path
        self.encryptor = encryptor

        db_dir = os.path.dirname(db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{db_path}")
        self.SessionLocal = sessionmaker(bind=self.engine)

    def initialize(self) -> None:
        Base.metadata.create_all(bind=self.engine)

    def set_secret(
        self, path: str, value: str, secret_type: str = "secret", tags: Optional[list[str]] = None
    ) -> Secret:
        tags = tags or []

        with self.SessionLocal() as session:
            stmt = select(SecretModel).where(SecretModel.path == path)
            existing = session.execute(stmt).scalar_one_or_none()

            # Encrypt value
            encrypted_value = self.encryptor.encrypt(value)

            if existing:
                version_record = SecretVersionModel(
                    path=existing.path,
                    encrypted_value=existing.encrypted_value,
                    version=existing.version,
                    created_at=existing.updated_at,
                    created_by=os.getenv("USER", "unknown"),
                )
                session.add(version_record)

                existing.encrypted_value = encrypted_value
                existing.version += 1
                existing.updated_at = datetime.utcnow()
                existing.tags = json.dumps(tags)
                session.commit()

                return Secret(
                    path=existing.path,
                    value=value,
                    type=SecretType(existing.type),
                    version=existing.version,
                    created_at=existing.created_at,
                    updated_at=existing.updated_at,
                    tags=tags,
                )
            else:
                new_secret = SecretModel(
                    path=path,
                    encrypted_value=encrypted_value,
                    type=secret_type,
                    version=1,
                    tags=json.dumps(tags),
                )
                session.add(new_secret)
                session.commit()

                return Secret(
                    path=new_secret.path,
                    value=value,
                    type=SecretType(new_secret.type),
                    version=new_secret.version,
                    created_at=new_secret.created_at,
                    updated_at=new_secret.updated_at,
                    tags=tags,
                )

    def get_secret(self, path: str) -> Optional[Secret]:
        with self.SessionLocal() as session:
            stmt = select(SecretModel).where(SecretModel.path == path)
            secret_model = session.execute(stmt).scalar_one_or_none()

            if not secret_model:
                return None

            decrypted_value = self.encryptor.decrypt(secret_model.encrypted_value)

            return Secret(
                path=secret_model.path,
                value=decrypted_value,
                type=SecretType(secret_model.type),
                version=secret_model.version,
                created_at=secret_model.created_at,
                updated_at=secret_model.updated_at,
                tags=json.loads(secret_model.tags) if secret_model.tags else [],
                metadata=json.loads(secret_model.meta_data) if secret_model.meta_data else {},
            )

    def list_secrets(self, prefix: Optional[str] = None) -> list[Secret]:
        with self.SessionLocal() as session:
            stmt = select(SecretModel)
            if prefix:
                stmt = stmt.where(SecretModel.path.like(f"{prefix}%"))
            stmt = stmt.order_by(SecretModel.path)

            results = session.execute(stmt).scalars().all()

            secrets = []
            for secret_model in results:
                decrypted_value = self.encryptor.decrypt(secret_model.encrypted_value)

                secrets.append(
                    Secret(
                        path=secret_model.path,
                        value=decrypted_value,
                        type=SecretType(secret_model.type),
                        version=secret_model.version,
                        created_at=secret_model.created_at,
                        updated_at=secret_model.updated_at,
                        tags=json.loads(secret_model.tags) if secret_model.tags else [],
                        metadata=(
                            json.loads(secret_model.meta_data) if secret_model.meta_data else {}
                        ),
                    )
                )

            return secrets

    def delete_secret(self, path: str) -> bool:
        with self.SessionLocal() as session:
            stmt = select(SecretModel).where(SecretModel.path == path)
            secret = session.execute(stmt).scalar_one_or_none()

            if not secret:
                return False

            version_stmt = select(SecretVersionModel).where(SecretVersionModel.path == path)
            versions = session.execute(version_stmt).scalars().all()
            for version in versions:
                session.delete(version)

            session.delete(secret)
            session.commit()
            return True

    def get_history(self, path: str) -> list[SecretVersion]:
        with self.SessionLocal() as session:
            stmt = select(SecretModel).where(SecretModel.path == path)
            current = session.execute(stmt).scalar_one_or_none()

            if not current:
                return []

            stmt = (
                select(SecretVersionModel)
                .where(SecretVersionModel.path == path)
                .order_by(SecretVersionModel.version.desc())
            )
            history = session.execute(stmt).scalars().all()

            versions = []

            decrypted_value = self.encryptor.decrypt(current.encrypted_value)
            versions.append(
                SecretVersion(
                    path=current.path,
                    value=decrypted_value,
                    version=current.version,
                    created_at=current.updated_at,
                    created_by=os.getenv("USER", "unknown"),
                )
            )

            for version_model in history:
                decrypted_value = self.encryptor.decrypt(version_model.encrypted_value)
                versions.append(
                    SecretVersion(
                        path=version_model.path,
                        value=decrypted_value,
                        version=version_model.version,
                        created_at=version_model.created_at,
                        created_by=version_model.created_by,
                    )
                )

            return versions

    def rollback(self, path: str, version: int) -> Secret:
        with self.SessionLocal() as session:
            stmt = (
                select(SecretVersionModel)
                .where(SecretVersionModel.path == path)
                .where(SecretVersionModel.version == version)
            )
            version_model = session.execute(stmt).scalar_one_or_none()

            if not version_model:
                raise ValueError(f"Version {version} not found for {path}")

            stmt = select(SecretModel).where(SecretModel.path == path)
            current = session.execute(stmt).scalar_one_or_none()

            if not current:
                raise ValueError(f"Secret {path} not found")

            history_record = SecretVersionModel(
                path=current.path,
                encrypted_value=current.encrypted_value,
                version=current.version,
                created_at=current.updated_at,
                created_by=os.getenv("USER", "unknown"),
            )
            session.add(history_record)

            # Rollback to old version (but increment version number)
            current.encrypted_value = version_model.encrypted_value
            current.version += 1
            current.updated_at = datetime.utcnow()
            session.commit()

            decrypted_value = self.encryptor.decrypt(current.encrypted_value)
            return Secret(
                path=current.path,
                value=decrypted_value,
                type=SecretType(current.type),
                version=current.version,
                created_at=current.created_at,
                updated_at=current.updated_at,
                tags=json.loads(current.tags) if current.tags else [],
            )


    def log_audit(self, entry: AuditEntry) -> None:
        with self.SessionLocal() as session:
            audit = AuditLogModel(
                timestamp=entry.timestamp,
                user=entry.user,
                action=entry.action,
                path=entry.path,
                success=entry.success,
                error=entry.error,
                meta_data=json.dumps(entry.metadata),
            )
            session.add(audit)
            session.commit()


    def close(self) -> None:
        self.engine.dispose()

