"""
Unit tests for evidence-backed Preflight Evaluator.
"""
from px4_hub.core.enums import HealthStatus, SensorType, FlightMode, ArmingStatus
from px4_hub.core.models import VehicleInfo, TelemetryData, SensorStatus, Parameter
from px4_hub.modules.preflight.evaluator import PreflightEvaluator


def test_preflight_disconnected():
    info = VehicleInfo(connected=False)
    telem = TelemetryData()
    checks, score, overall = PreflightEvaluator.evaluate(info, telem, {}, {})

    assert overall == HealthStatus.FAIL
    assert score == 0.0
    assert len(checks) == 1
    assert checks[0].status == HealthStatus.FAIL


def test_preflight_connected_with_warnings():
    info = VehicleInfo(
        connected=True,
        board_name="MicroAir H7 AIO V4",
        firmware_version="PX4 Autopilot v1.15.0"
    )
    telem = TelemetryData(
        gps_fix_type="3D Fix",
        gps_satellites=12,
        gps_hdop=0.9,
        battery_voltage_v=16.2,
        battery_remaining_pct=85.0
    )
    sensors = {
        SensorType.GYRO: SensorStatus(SensorType.GYRO, HealthStatus.PASS, True, True),
        SensorType.ACCEL: SensorStatus(SensorType.ACCEL, HealthStatus.PASS, True, True),
        SensorType.MAG: SensorStatus(SensorType.MAG, HealthStatus.WARNING, True, False),
    }
    params = {
        "SYS_AUTOSTART": Parameter("SYS_AUTOSTART", 4001),
        "CAL_GYRO0_ID": Parameter("CAL_GYRO0_ID", 131072),
        "CAL_ACC0_ID": Parameter("CAL_ACC0_ID", 131072),
        "CAL_MAG0_ID": Parameter("CAL_MAG0_ID", 0),  # 0 indicates uncalibrated
    }

    checks, score, overall = PreflightEvaluator.evaluate(info, telem, sensors, params)

    assert overall == HealthStatus.WARNING
    assert score > 75.0
    # Compass should be flagged as WARNING
    mag_check = next(c for c in checks if c.id == "CHECK_MAG")
    assert mag_check.status == HealthStatus.WARNING
    assert "CAL_MAG0_ID=0" in mag_check.evidence_value


def test_preflight_critical_battery_fail():
    info = VehicleInfo(connected=True, firmware_version="PX4 Autopilot v1.15.0")
    telem = TelemetryData(
        gps_fix_type="3D Fix",
        gps_satellites=14,
        gps_hdop=0.8,
        battery_voltage_v=13.2,  # Critically low for 4S
        battery_remaining_pct=5.0
    )
    params = {
        "SYS_AUTOSTART": Parameter("SYS_AUTOSTART", 4001),
        "CAL_GYRO0_ID": Parameter("CAL_GYRO0_ID", 131072),
        "CAL_ACC0_ID": Parameter("CAL_ACC0_ID", 131072),
        "CAL_MAG0_ID": Parameter("CAL_MAG0_ID", 196608),
    }
    checks, score, overall = PreflightEvaluator.evaluate(info, telem, {}, params)

    assert overall == HealthStatus.FAIL
    bat_check = next(c for c in checks if c.id == "CHECK_BATTERY")
    assert bat_check.status == HealthStatus.FAIL
