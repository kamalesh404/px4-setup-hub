"""
Data models and telemetry representations for PX4 Setup Hub.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from .enums import HealthStatus, FlightMode, ArmingStatus, SensorType, CalibrationStep


@dataclass
class VehicleInfo:
    """Hardware and firmware identity of connected flight controller."""
    connected: bool = False
    board_name: str = "Unknown Board"
    board_vendor: str = "Unknown"
    board_id: int = 0
    firmware_version: str = "Unknown"
    firmware_vendor_version: str = ""
    os_version: str = ""
    target_name: str = ""
    uid: str = ""
    vehicle_type: str = "Multicopter (Quad X)"
    frame_class: str = "Generic Quadcopter"
    bootloader_version: str = ""
    connection_endpoint: str = ""
    last_heartbeat_time: float = 0.0

    @property
    def is_px4(self) -> bool:
        return "px4" in self.firmware_version.lower() or "px4" in self.board_name.lower() or self.connected


@dataclass
class TelemetryData:
    """Real-time flight controller state and sensory streams."""
    timestamp: float = 0.0
    
    # Attitude (degrees)
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    heading_deg: float = 0.0
    
    # Dynamics
    roll_rate_deg_s: float = 0.0
    pitch_rate_deg_s: float = 0.0
    yaw_rate_deg_s: float = 0.0
    ground_speed_m_s: float = 0.0
    climb_rate_m_s: float = 0.0
    altitude_relative_m: float = 0.0
    altitude_amsl_m: float = 0.0

    # Flight State
    flight_mode: FlightMode = FlightMode.UNKNOWN
    arming_status: ArmingStatus = ArmingStatus.DISARMED
    is_flying: bool = False
    mavlink_loss_pct: float = 0.0
    mavlink_message_rate: float = 0.0

    # GPS
    gps_fix_type: str = "No Fix"  # No Fix, 2D Fix, 3D Fix, 3D DGPS, RTK Float, RTK Fixed
    gps_satellites: int = 0
    gps_lat: float = 0.0
    gps_lon: float = 0.0
    gps_hdop: float = 99.9
    gps_vdop: float = 99.9

    # Power & Battery
    battery_voltage_v: float = 0.0
    battery_current_a: float = 0.0
    battery_remaining_pct: float = 0.0
    battery_cell_count: int = 4

    # System Health
    cpu_load_pct: float = 0.0
    ram_usage_pct: float = 0.0
    ekf_status_flags: int = 0
    sensors_healthy: bool = False


@dataclass
class SensorStatus:
    """Status verification for a single onboard sensor."""
    sensor_type: SensorType
    status: HealthStatus = HealthStatus.UNKNOWN
    detected: bool = False
    calibrated: bool = False
    detail: str = "Awaiting vehicle telemetry"
    evidence: str = ""
    last_updated: Optional[datetime] = None


@dataclass
class Parameter:
    """PX4 Configuration parameter model with validation metadata."""
    name: str
    value: Any
    default_value: Any = None
    type_name: str = "FLOAT"  # INT32 or FLOAT
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""
    group: str = "General"
    requires_reboot: bool = False
    is_modified: bool = False
    unit: str = ""

    def validate(self, candidate_value: Any) -> bool:
        try:
            val = float(candidate_value)
            if self.min_value is not None and val < self.min_value:
                return False
            if self.max_value is not None and val > self.max_value:
                return False
            return True
        except (ValueError, TypeError):
            return False


@dataclass
class PreflightCheckItem:
    """Individual preflight verification result."""
    id: str
    category: str
    title: str
    status: HealthStatus = HealthStatus.UNKNOWN
    evidence_value: str = "No data"
    explanation: str = "Vehicle telemetry not yet received"
    remediation_hint: str = ""


@dataclass
class CalibrationProgress:
    """Progress feedback during interactive sensor calibration."""
    calibration_type: str
    step: CalibrationStep = CalibrationStep.DETECTING
    progress_pct: int = 0
    instruction: str = "Prepare vehicle"
    completed_steps: List[CalibrationStep] = field(default_factory=list)
    is_done: bool = False
    is_error: bool = False
    error_message: str = ""
