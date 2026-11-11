"""
Unit tests for MockVehicle communication, telemetry streaming, and calibration.
"""
import time
from px4_hub.comms.mock_vehicle import MockVehicle
from px4_hub.core.enums import ConnectionState, HealthStatus, CalibrationType, SensorType


def test_mock_vehicle_connection():
    vehicle = MockVehicle()
    assert vehicle.state == ConnectionState.DISCONNECTED

    state_log = []
    vehicle.on_state_changed = lambda s, m: state_log.append(s)

    ok = vehicle.connect("mock://test-drone")
    assert ok is True
    assert vehicle.state == ConnectionState.CONNECTED
    assert vehicle.vehicle_info.connected is True
    assert "MicroAir H7" in vehicle.vehicle_info.board_name

    # Give telemetry loop a brief moment to run
    time.sleep(0.25)
    assert vehicle.telemetry.battery_voltage_v > 14.0
    assert vehicle.telemetry.gps_satellites > 0

    vehicle.disconnect()
    assert vehicle.state == ConnectionState.DISCONNECTED


def test_mock_parameter_transactions():
    vehicle = MockVehicle()
    vehicle.connect()

    # Read parameter
    assert "SYS_AUTOSTART" in vehicle.parameters
    param = vehicle.parameters["SYS_AUTOSTART"]
    assert param.value == 4001

    # Modify valid value
    ok = vehicle.set_parameter("SYS_AUTOSTART", 4002)
    assert ok is True
    assert vehicle.parameters["SYS_AUTOSTART"].value == 4002
    assert vehicle.parameters["SYS_AUTOSTART"].is_modified is True

    # Reject out of bounds value
    ok = vehicle.set_parameter("SYS_AUTOSTART", -50)
    assert ok is False

    vehicle.disconnect()


def test_mock_gyro_calibration_workflow():
    vehicle = MockVehicle()
    vehicle.connect()

    progress_events = []
    vehicle.on_calibration_progress = lambda p: progress_events.append(p)

    vehicle.start_calibration(CalibrationType.GYROSCOPE)

    # Wait for mock calibration to progress and finish
    timeout = 6.0
    start = time.time()
    while time.time() - start < timeout:
        if any(p.is_done for p in progress_events):
            break
        time.sleep(0.1)

    assert any(p.is_done for p in progress_events)
    assert vehicle.sensors[SensorType.GYRO].status == HealthStatus.PASS
    assert vehicle.sensors[SensorType.GYRO].calibrated is True

    vehicle.disconnect()
