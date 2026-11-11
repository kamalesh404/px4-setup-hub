"""
Unit tests for PX4 Setup Hub data models and enums.
"""
from px4_hub.core.enums import HealthStatus, FlightMode, ArmingStatus
from px4_hub.core.models import Parameter, VehicleInfo, TelemetryData


def test_health_status_properties():
    assert HealthStatus.PASS.color == "#22c55e"
    assert HealthStatus.WARNING.color == "#eab308"
    assert HealthStatus.FAIL.color == "#ef4444"
    assert HealthStatus.UNKNOWN.color == "#94a3b8"


def test_parameter_validation():
    p = Parameter(
        name="MPC_XY_VEL_MAX",
        value=12.0,
        default_value=12.0,
        type_name="FLOAT",
        min_value=1.0,
        max_value=30.0
    )
    assert p.validate(15.0) is True
    assert p.validate(0.5) is False
    assert p.validate(35.0) is False
    assert p.validate("invalid_str") is False


def test_vehicle_info_px4_detection():
    v = VehicleInfo(
        connected=True,
        board_name="MicroAir H7 AIO V4",
        firmware_version="PX4 Autopilot v1.15.0"
    )
    assert v.is_px4 is True
