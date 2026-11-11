"""
SQLite Storage Manager for PX4 Setup Hub.
Persists parameter backups, connection profiles, flight logs metadata, and preflight history.
"""
import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from contextlib import contextmanager


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            data_dir = os.path.expanduser("~/.px4_setup_hub")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "hub_data.db")
        self.db_path = db_path
        self._init_tables()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_tables(self):
        with self._connection() as conn:
            cursor = conn.cursor()
            
            # Parameter Backups table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS param_backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_uid TEXT,
                    board_name TEXT,
                    firmware_version TEXT,
                    timestamp TEXT,
                    tag TEXT,
                    params_json TEXT
                )
            """)

            # Preflight Reports table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preflight_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_uid TEXT,
                    timestamp TEXT,
                    overall_status TEXT,
                    readiness_score REAL,
                    report_json TEXT
                )
            """)

            # Calibration Log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calibration_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_uid TEXT,
                    sensor_name TEXT,
                    timestamp TEXT,
                    success INTEGER,
                    notes TEXT
                )
            """)

            # Connection Presets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connection_presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    conn_type TEXT,
                    endpoint TEXT,
                    baud_rate INTEGER,
                    last_used TEXT
                )
            """)
            conn.commit()

    def save_param_backup(self, vehicle_uid: str, board_name: str, firmware: str,
                          params: Dict[str, Any], tag: str = "Auto-Backup") -> int:
        """Create a full parameter snapshot before updates or modifications."""
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO param_backups 
                (vehicle_uid, board_name, firmware_version, timestamp, tag, params_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (vehicle_uid, board_name, firmware, timestamp, tag, json.dumps(params)))
            conn.commit()
            return cursor.lastrowid

    def list_param_backups(self, vehicle_uid: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            cursor = conn.cursor()
            if vehicle_uid:
                cursor.execute(
                    "SELECT id, vehicle_uid, board_name, firmware_version, timestamp, tag FROM param_backups WHERE vehicle_uid=? ORDER BY id DESC",
                    (vehicle_uid,)
                )
            else:
                cursor.execute(
                    "SELECT id, vehicle_uid, board_name, firmware_version, timestamp, tag FROM param_backups ORDER BY id DESC"
                )
            return [dict(row) for row in cursor.fetchall()]

    def get_param_backup(self, backup_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM param_backups WHERE id=?", (backup_id,))
            row = cursor.fetchone()
            if row:
                res = dict(row)
                res["params"] = json.loads(res["params_json"])
                return res
            return None

    def save_preflight_report(self, vehicle_uid: str, overall_status: str,
                              readiness_score: float, report_data: Dict[str, Any]) -> int:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO preflight_reports 
                (vehicle_uid, timestamp, overall_status, readiness_score, report_json)
                VALUES (?, ?, ?, ?, ?)
            """, (vehicle_uid, timestamp, overall_status, readiness_score, json.dumps(report_data)))
            conn.commit()
            return cursor.lastrowid

    def record_calibration(self, vehicle_uid: str, sensor: str, success: bool, notes: str = ""):
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO calibration_logs (vehicle_uid, sensor_name, timestamp, success, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (vehicle_uid, sensor, 1 if success else 0, notes))
            conn.commit()
