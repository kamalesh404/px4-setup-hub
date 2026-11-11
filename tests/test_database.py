"""
Unit tests for SQLite database manager and parameter snapshot backups.
"""
import os
import tempfile
from px4_hub.core.database import DatabaseManager


def test_param_backup_save_and_retrieve():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        db = DatabaseManager(db_path=db_path)

        mock_params = {
            "SYS_AUTOSTART": 4001,
            "MC_ROLL_P": 6.5,
            "CAL_MAG0_ID": 196608
        }

        backup_id = db.save_param_backup(
            vehicle_uid="TEST_UID_123",
            board_name="MicroAir H7 AIO V4",
            firmware="PX4 v1.15.0",
            params=mock_params,
            tag="Pre-update Test Backup"
        )
        assert backup_id > 0

        # Retrieve backup
        loaded = db.get_param_backup(backup_id)
        assert loaded is not None
        assert loaded["vehicle_uid"] == "TEST_UID_123"
        assert loaded["params"]["SYS_AUTOSTART"] == 4001
        assert loaded["params"]["MC_ROLL_P"] == 6.5

        # List backups
        backups = db.list_param_backups()
        assert len(backups) == 1
        assert backups[0]["tag"] == "Pre-update Test Backup"
