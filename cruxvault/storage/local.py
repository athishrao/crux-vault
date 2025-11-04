import re
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from cruxvault.crypto.encryption import Encryptor
from cruxvault.storage.base import StorageBackend
from cruxvault.models import (
    AuditEntry,
    Branch,
    Commit,
    DiffEntry,
    MergeConflict,
    Secret,
    SecretType,
    SecretVersion
)
from cruxvault.storage.models import (
    AuditLogModel,
    Base,
    BranchModel,
    CommitModel,
    CommitSecretModel,
    SecretModel,
    SecretVersionModel,
)


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

    def _expand_variables(self, value: str, path: str, visited: set = None) -> str:
        if visited is None:
            visited = set()

        if path in visited:
            raise ValueError(f"Circular reference detected: {path}")

        visited.add(path)

        def replace_var(match):
            var_name = match.group(1)
            try:
                var_secret = self.get_secret(var_name)
                # Recursively expand the referenced value
                return self._expand_variables(var_secret.value, var_name, visited.copy())
            except:
                return match.group(0)  # Leave unchanged if not found

        return re.sub(r'\$\{([^}]+)\}', replace_var, value)

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

            expanded_value = self._expand_variables(decrypted_value, path)

            return Secret(
                path=secret_model.path,
                value=expanded_value,
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


    def create_branch(self, name: str, from_branch: Optional[str] = None) -> Branch:
        with self.SessionLocal() as session:
            stmt = select(BranchModel).where(BranchModel.name == name)
            existing = session.execute(stmt).scalar_one_or_none()
            if existing:
                raise ValueError(f"Branch '{name}' already exists")

            # Get head commit from source branch if specified
            head_commit_id = None
            if from_branch:
                stmt = select(BranchModel).where(BranchModel.name == from_branch)
                source_branch = session.execute(stmt).scalar_one_or_none()
                if not source_branch:
                    raise ValueError(f"Branch '{from_branch}' not found")
                head_commit_id = source_branch.head_commit_id

            branch = BranchModel(name=name, head_commit_id=head_commit_id)
            session.add(branch)
            session.commit()

            return Branch(
                name=branch.name, head_commit_id=branch.head_commit_id, created_at=branch.created_at
            )


    def list_branches(self) -> list[Branch]:
        with self.SessionLocal() as session:
            stmt = select(BranchModel)
            branches = session.execute(stmt).scalars().all()
            return [
                Branch(name=b.name, head_commit_id=b.head_commit_id, created_at=b.created_at)
                for b in branches
            ]


    def delete_branch(self, name: str) -> bool:
        with self.SessionLocal() as session:
            if name == "main":
                raise ValueError("Cannot delete main branch")

            stmt = select(BranchModel).where(BranchModel.name == name)
            branch = session.execute(stmt).scalar_one_or_none()
            if not branch:
                return False

            session.delete(branch)
            session.commit()
            return True


    def get_branch(self, name: str) -> Optional[Branch]:
        with self.SessionLocal() as session:
            stmt = select(BranchModel).where(BranchModel.name == name)
            branch = session.execute(stmt).scalar_one_or_none()
            if not branch:
                return None
            return Branch(
                name=branch.name, head_commit_id=branch.head_commit_id, created_at=branch.created_at
            )


    def commit(self, branch_name: str, message: str, author: Optional[str] = None) -> Commit:
        if not author:
            author = os.getenv("USER", "unknown")

        with self.SessionLocal() as session:
            stmt = select(BranchModel).where(BranchModel.name == branch_name)
            branch = session.execute(stmt).scalar_one_or_none()
            if not branch:
                raise ValueError(f"Branch '{branch_name}' not found")

            commit = CommitModel(
                parent_id=branch.head_commit_id,
                message=message,
                author=author,
                timestamp=datetime.utcnow(),
                branch=branch_name,
            )
            session.add(commit)
            session.flush()  # Get commit ID

            # Snapshot all current secrets
            stmt = select(SecretModel)
            secrets = session.execute(stmt).scalars().all()

            for secret in secrets:
                commit_secret = CommitSecretModel(
                    commit_id=commit.id,
                    path=secret.path,
                    encrypted_value=secret.encrypted_value,
                    type=secret.type,
                    tags=secret.tags,
                )
                session.add(commit_secret)

            branch.head_commit_id = commit.id
            session.commit()

            return Commit(
                id=commit.id,
                parent_id=commit.parent_id,
                message=commit.message,
                author=commit.author,
                timestamp=commit.timestamp,
                branch=commit.branch,
            )


    def get_commit_history(self, branch_name: str, limit: int = 10) -> list[Commit]:
        with self.SessionLocal() as session:
            stmt = select(BranchModel).where(BranchModel.name == branch_name)
            branch = session.execute(stmt).scalar_one_or_none()
            if not branch:
                raise ValueError(f"Branch '{branch_name}' not found")

            if not branch.head_commit_id:
                return []

            commits = []
            current_commit_id = branch.head_commit_id

            while current_commit_id and len(commits) < limit:
                stmt = select(CommitModel).where(CommitModel.id == current_commit_id)
                commit = session.execute(stmt).scalar_one_or_none()
                if not commit:
                    break

                commits.append(
                    Commit(
                        id=commit.id,
                        parent_id=commit.parent_id,
                        message=commit.message,
                        author=commit.author,
                        timestamp=commit.timestamp,
                        branch=commit.branch,
                    )
                )
                current_commit_id = commit.parent_id

            return commits


    def checkout_branch(self, branch_name: str) -> None:
        with self.SessionLocal() as session:
            stmt = select(BranchModel).where(BranchModel.name == branch_name)
            branch = session.execute(stmt).scalar_one_or_none()
            if not branch:
                raise ValueError(f"Branch '{branch_name}' not found")

            for secret in session.execute(select(SecretModel)).scalars().all():
                session.delete(secret)

            # Restore from commit if branch has commits
            if branch.head_commit_id:
                stmt = select(CommitSecretModel).where(
                    CommitSecretModel.commit_id == branch.head_commit_id
                )
                commit_secrets = session.execute(stmt).scalars().all()

                for cs in commit_secrets:
                    secret = SecretModel(
                        path=cs.path,
                        encrypted_value=cs.encrypted_value,
                        type=cs.type,
                        tags=cs.tags,
                        version=1,
                    )
                    session.add(secret)

            session.commit()


    def get_status(self, branch_name: str) -> dict:
        with self.SessionLocal() as session:
            stmt = select(BranchModel).where(BranchModel.name == branch_name)
            branch = session.execute(stmt).scalar_one_or_none()
            if not branch or not branch.head_commit_id:
                stmt = select(SecretModel)
                current_secrets = {s.path: s for s in session.execute(stmt).scalars().all()}
                return {
                    "added": list(current_secrets.keys()),
                    "modified": [],
                    "deleted": [],
                }

            stmt = select(CommitSecretModel).where(
                CommitSecretModel.commit_id == branch.head_commit_id
            )
            committed = {cs.path: cs for cs in session.execute(stmt).scalars().all()}

            stmt = select(SecretModel)
            current_secrets = {s.path: s for s in session.execute(stmt).scalars().all()}

            added = []
            modified = []
            deleted = []

            # Find added and modified
            for path, secret in current_secrets.items():
                if path not in committed:
                    added.append(path)
                elif secret.encrypted_value != committed[path].encrypted_value:
                    modified.append(path)

            # Find deleted
            for path in committed:
                if path not in current_secrets:
                    deleted.append(path)

            return {"added": added, "modified": modified, "deleted": deleted}


    def diff_commits(self, commit1_id: int, commit2_id: int) -> list[DiffEntry]:
        with self.SessionLocal() as session:
            stmt1 = select(CommitSecretModel).where(CommitSecretModel.commit_id == commit1_id)
            secrets1 = {cs.path: cs for cs in session.execute(stmt1).scalars().all()}

            stmt2 = select(CommitSecretModel).where(CommitSecretModel.commit_id == commit2_id)
            secrets2 = {cs.path: cs for cs in session.execute(stmt2).scalars().all()}

            diff = []

            # Find added and modified
            for path, cs2 in secrets2.items():
                if path not in secrets1:
                    diff.append(
                        DiffEntry(
                            path=path,
                            status="added",
                            old_value=None,
                            new_value=self.encryptor.decrypt(cs2.encrypted_value),
                        )
                    )
                elif cs2.encrypted_value != secrets1[path].encrypted_value:
                    diff.append(
                        DiffEntry(
                            path=path,
                            status="modified",
                            old_value=self.encryptor.decrypt(secrets1[path].encrypted_value),
                            new_value=self.encryptor.decrypt(cs2.encrypted_value),
                        )
                    )

            # Find deleted
            for path in secrets1:
                if path not in secrets2:
                    diff.append(
                        DiffEntry(
                            path=path,
                            status="deleted",
                            old_value=self.encryptor.decrypt(secrets1[path].encrypted_value),
                            new_value=None,
                        )
                    )

            return diff


    def rollback_to_commit(self, branch_name: str, commit_id: int) -> None:
        with self.SessionLocal() as session:
            stmt = select(CommitModel).where(CommitModel.id == commit_id)
            commit = session.execute(stmt).scalar_one_or_none()
            if not commit:
                raise ValueError(f"Commit {commit_id} not found")

            stmt = select(BranchModel).where(BranchModel.name == branch_name)
            branch = session.execute(stmt).scalar_one_or_none()
            if not branch:
                raise ValueError(f"Branch '{branch_name}' not found")

            branch.head_commit_id = commit_id
            
            # Restore secrets from commit
            for secret in session.execute(select(SecretModel)).scalars().all():
                session.delete(secret)

            stmt = select(CommitSecretModel).where(CommitSecretModel.commit_id == commit_id)
            commit_secrets = session.execute(stmt).scalars().all()

            for cs in commit_secrets:
                secret = SecretModel(
                    path=cs.path,
                    encrypted_value=cs.encrypted_value,
                    type=cs.type,
                    tags=cs.tags,
                    version=1,
                )
                session.add(secret)

            session.commit()


    def merge_branch(
        self, target_branch: str, source_branch: str
    ) -> tuple[bool, list[MergeConflict]]:
        with self.SessionLocal() as session:
            stmt = select(BranchModel).where(BranchModel.name == target_branch)
            target = session.execute(stmt).scalar_one_or_none()
            if not target:
                raise ValueError(f"Branch '{target_branch}' not found")

            stmt = select(BranchModel).where(BranchModel.name == source_branch)
            source = session.execute(stmt).scalar_one_or_none()
            if not source:
                raise ValueError(f"Branch '{source_branch}' not found")

            if not source.head_commit_id:
                return True, []  # Nothing to merge

            # Get secrets from both branches
            target_secrets = {}
            if target.head_commit_id:
                stmt = select(CommitSecretModel).where(
                    CommitSecretModel.commit_id == target.head_commit_id
                )
                target_secrets = {cs.path: cs for cs in session.execute(stmt).scalars().all()}

            stmt = select(CommitSecretModel).where(
                CommitSecretModel.commit_id == source.head_commit_id
            )
            source_secrets = {cs.path: cs for cs in session.execute(stmt).scalars().all()}

            # Detect conflicts
            conflicts = []
            for path, source_cs in source_secrets.items():
                if path in target_secrets:
                    if source_cs.encrypted_value != target_secrets[path].encrypted_value:
                        conflicts.append(
                            MergeConflict(
                                path=path,
                                current_value=self.encryptor.decrypt(
                                    target_secrets[path].encrypted_value
                                ),
                                incoming_value=self.encryptor.decrypt(source_cs.encrypted_value),
                            )
                        )

            if conflicts:
                return False, conflicts

            # No conflicts, perform merge
            # Update all secrets to source state
            for secret in session.execute(select(SecretModel)).scalars().all():
                session.delete(secret)

            for path, cs in source_secrets.items():
                secret = SecretModel(
                    path=cs.path,
                    encrypted_value=cs.encrypted_value,
                    type=cs.type,
                    tags=cs.tags,
                    version=1,
                )
                session.add(secret)

            session.commit()
            return True, []
