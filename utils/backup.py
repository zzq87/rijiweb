import os
import gzip
import shutil
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def backup_database(db_path: str, backup_dir: str, keep_count: int = 30):
    if not os.path.exists(db_path):
        logger.warning("Database file not found: %s", db_path)
        return

    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_name = f"riji_backup_{timestamp}.db.gz"
    backup_path = os.path.join(backup_dir, backup_name)

    try:
        with open(db_path, "rb") as src:
            with gzip.open(backup_path, "wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
        logger.info("Backup created: %s", backup_path)
    except Exception as e:
        logger.error("Backup failed: %s", e)
        return

    backups = sorted(
        [f for f in os.listdir(backup_dir) if f.startswith("riji_backup_")],
        reverse=True,
    )
    for old in backups[keep_count:]:
        old_path = os.path.join(backup_dir, old)
        try:
            os.remove(old_path)
            logger.info("Removed old backup: %s", old_path)
        except OSError as e:
            logger.warning("Failed to remove old backup %s: %s", old_path, e)
