from cruxvault.config import ConfigManager
from cruxvault.audit.logger import AuditLogger
from cruxvault.storage.local import SQLiteStorage
from cruxvault.crypto.encryption import Encryptor
from cruxvault.crypto.utils import get_or_create_master_key


def get_audit_logger() -> AuditLogger:
    config_manager = ConfigManager()
    config = config_manager.load_config()

    audit_path = config_manager.get_audit_path()
    audit_logger = AuditLogger(
        audit_path,
        enabled=config.audit.enabled,
        log_reads=config.audit.log_reads,
    )
    return audit_logger

def get_storage_and_audit() -> tuple[SQLiteStorage, AuditLogger]:
    config_manager = ConfigManager()
    config = config_manager.load_config()

    master_key = get_or_create_master_key()
    encryptor = Encryptor(master_key)

    storage_path = config_manager.get_storage_path()
    storage = SQLiteStorage(storage_path, encryptor)

    audit_path = config_manager.get_audit_path()
    audit_logger = AuditLogger(
        audit_path,
        enabled=config.audit.enabled,
        log_reads=config.audit.log_reads,
    )

    return storage, audit_logger


