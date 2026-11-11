"""
Low-level MAVLink connection layer using pymavlink.
Supports USB Serial (with auto-detection), UDP (PX4 SITL / network), and TCP.
Runs inside a dedicated background worker to guarantee zero UI lockups.
"""
import time
import threading
from typing import Dict, Any, Optional
from .base import BaseVehicle
from ..core.enums import (
    ConnectionState, HealthStatus, FlightMode, ArmingStatus,
    SensorType, CalibrationType, CalibrationStep
)
from ..core.models import (
    VehicleInfo, TelemetryData, SensorStatus, Parameter, CalibrationProgress
)

try:
    from pymavlink import mavutil
    HAS_PYMAVLINK = True
except ImportError:
    mavutil = None
    HAS_PYMAVLINK = False


class MavlinkVehicle(BaseVehicle):
    """
    Communicates with PX4 Autopilot over Serial, UDP, or TCP via MAVLink 2.
    Decodes telemetry, handles parameter transactions, and listens for STATUSTEXT.
    """

    def __init__(self):
        super().__init__()
        self._master = None
        self._rx_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_heartbeat_time = 0.0

    def connect(self, endpoint: str, baud: int = 115200, **kwargs) -> bool:
        if not HAS_PYMAVLINK:
            err_msg = "pymavlink is not installed in the active environment"
            if self.on_state_changed:
                self.on_state_changed(ConnectionState.ERROR, err_msg)
            return False

        self.state = ConnectionState.CONNECTING
        if self.on_state_changed:
            self.on_state_changed(self.state, f"Connecting to {endpoint} (Baud: {baud})...")

        try:
            self._master = mavutil.mavlink_connection(
                endpoint,
                baud=baud,
                autoreconnect=True,
                source_system=255,   # Standard GCS system ID
                source_component=190 # Standard GCS component ID
            )
            self._stop_event.clear()
            self._rx_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._rx_thread.start()
            return True
        except Exception as e:
            self.state = ConnectionState.ERROR
            if self.on_state_changed:
                self.on_state_changed(self.state, f"Connection failed: {str(e)}")
            return False

    def disconnect(self):
        self._stop_event.set()
        if self._master:
            try:
                self._master.close()
            except Exception:
                pass
            self._master = None
        self.state = ConnectionState.DISCONNECTED
        self.vehicle_info.connected = False
        if self.on_state_changed:
            self.on_state_changed(self.state, "Disconnected")

    def _read_loop(self):
        """Dedicated thread reading incoming MAVLink packets."""
        while not self._stop_event.is_set():
            if not self._master:
                break
            try:
                msg = self._master.recv_match(blocking=True, timeout=0.1)
                if msg is None:
                    # Check for heartbeat loss (> 3.5s timeout)
                    if self.state == ConnectionState.CONNECTED and time.time() - self._last_heartbeat_time > 3.5:
                        self.state = ConnectionState.RECONNECTING
                        if self.on_state_changed:
                            self.on_state_changed(self.state, "Heartbeat lost. Waiting for vehicle...")
                    continue

                msg_type = msg.get_type()

                if msg_type == 'HEARTBEAT':
                    self._handle_heartbeat(msg)
                elif msg_type == 'ATTITUDE':
                    self._handle_attitude(msg)
                elif msg_type == 'GLOBAL_POSITION_INT':
                    self._handle_global_pos(msg)
                elif msg_type == 'GPS_RAW_INT':
                    self._handle_gps_raw(msg)
                elif msg_type == 'SYS_STATUS':
                    self._handle_sys_status(msg)
                elif msg_type == 'PARAM_VALUE':
                    self._handle_param_value(msg)
                elif msg_type == 'STATUSTEXT':
                    self._handle_statustext(msg)
                elif msg_type == 'AUTOPILOT_VERSION':
                    self._handle_autopilot_version(msg)

            except Exception as e:
                # Catch read timeouts or port breaks gracefully
                time.sleep(0.05)

    def _handle_heartbeat(self, msg):
        self._last_heartbeat_time = time.time()
        was_disconnected = (self.state != ConnectionState.CONNECTED)
        self.state = ConnectionState.CONNECTED

        # Armed / Disarmed
        base_mode = getattr(msg, 'base_mode', 0)
        is_armed = bool(base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        self.telemetry.arming_status = ArmingStatus.ARMED if is_armed else ArmingStatus.DISARMED

        # Autopilot and Type identification
        autopilot_type = getattr(msg, 'autopilot', 0)
        is_px4 = (autopilot_type == mavutil.mavlink.MAV_AUTOPILOT_PX4)
        if is_px4:
            self.vehicle_info.board_name = "PX4 Autopilot Device"
            self.vehicle_info.firmware_version = "PX4 Autopilot"

        self.vehicle_info.connected = True
        self.vehicle_info.last_heartbeat_time = self._last_heartbeat_time

        if was_disconnected and self.on_state_changed:
            self.on_state_changed(self.state, "MAVLink Heartbeat detected!")
            # Request autopilot version & data streams
            self._request_stream_rates()
            self._request_autopilot_version()

    def _request_stream_rates(self):
        if not self._master:
            return
        # Request standard telemetry rates: 10Hz attitude, 5Hz position, 2Hz sys_status
        for stream_id, rate in [(mavutil.mavlink.MAV_DATA_STREAM_EXTRA1, 10),
                                (mavutil.mavlink.MAV_DATA_STREAM_POSITION, 5),
                                (mavutil.mavlink.MAV_DATA_STREAM_EXTENDED_STATUS, 2)]:
            self._master.mav.request_data_stream_send(
                self._master.target_system,
                self._master.target_component,
                stream_id,
                rate,
                1
            )

    def _request_autopilot_version(self):
        if not self._master:
            return
        self._master.mav.command_long_send(
            self._master.target_system,
            self._master.target_component,
            mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,
            0,
            mavutil.mavlink.MAVLINK_MSG_ID_AUTOPILOT_VERSION,
            0, 0, 0, 0, 0, 0
        )

    def _handle_attitude(self, msg):
        import math
        self.telemetry.roll_deg = round(math.degrees(msg.roll), 2)
        self.telemetry.pitch_deg = round(math.degrees(msg.pitch), 2)
        yaw_deg = math.degrees(msg.yaw)
        if yaw_deg < 0:
            yaw_deg += 360.0
        self.telemetry.yaw_deg = round(yaw_deg, 2)
        self.telemetry.heading_deg = round(yaw_deg, 1)
        self.telemetry.roll_rate_deg_s = round(math.degrees(msg.rollspeed), 2)
        self.telemetry.pitch_rate_deg_s = round(math.degrees(msg.pitchspeed), 2)
        self.telemetry.yaw_rate_deg_s = round(math.degrees(msg.yawspeed), 2)
        self.telemetry.timestamp = time.time()
        if self.on_telemetry_updated:
            self.on_telemetry_updated(self.telemetry)

    def _handle_global_pos(self, msg):
        self.telemetry.altitude_relative_m = round(msg.relative_alt / 1000.0, 2)
        self.telemetry.altitude_amsl_m = round(msg.alt / 1000.0, 2)
        self.telemetry.climb_rate_m_s = round(-msg.vz / 100.0, 2)
        if self.on_telemetry_updated:
            self.on_telemetry_updated(self.telemetry)

    def _handle_gps_raw(self, msg):
        fix_types = {0: "No GPS", 1: "No Fix", 2: "2D Fix", 3: "3D Fix", 4: "DGPS", 5: "RTK Float", 6: "RTK Fixed"}
        self.telemetry.gps_fix_type = fix_types.get(msg.fix_type, "Unknown")
        self.telemetry.gps_satellites = msg.satellites_visible
        self.telemetry.gps_lat = msg.lat / 1e7
        self.telemetry.gps_lon = msg.lon / 1e7
        self.telemetry.gps_hdop = msg.eph / 100.0 if hasattr(msg, 'eph') else 99.9
        self.telemetry.gps_vdop = msg.epv / 100.0 if hasattr(msg, 'epv') else 99.9
        if self.on_telemetry_updated:
            self.on_telemetry_updated(self.telemetry)

    def _handle_sys_status(self, msg):
        self.telemetry.battery_voltage_v = round(msg.voltage_battery / 1000.0, 2)
        self.telemetry.battery_current_a = round(msg.current_battery / 100.0, 2) if msg.current_battery >= 0 else 0.0
        self.telemetry.battery_remaining_pct = float(msg.battery_remaining) if msg.battery_remaining >= 0 else 0.0
        self.telemetry.cpu_load_pct = round(msg.load / 10.0, 1)
        if self.on_telemetry_updated:
            self.on_telemetry_updated(self.telemetry)

    def _handle_param_value(self, msg):
        param_id = msg.param_id
        if isinstance(param_id, bytes):
            param_id = param_id.decode('utf-8', errors='ignore').rstrip('\x00')
        param_val = msg.param_value

        p = Parameter(
            name=param_id,
            value=param_val,
            default_value=param_val,
            type_name="FLOAT"
        )
        self.parameters[param_id] = p
        if self.on_parameter_received:
            self.on_parameter_received(p)

    def _handle_statustext(self, msg):
        text = msg.text
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='ignore').rstrip('\x00')
        severity = getattr(msg, 'severity', 6)
        if self.on_text_message:
            self.on_text_message(severity, text)

    def _handle_autopilot_version(self, msg):
        flight_sw_version = msg.flight_sw_version
        major = (flight_sw_version >> 24) & 0xFF
        minor = (flight_sw_version >> 16) & 0xFF
        patch = (flight_sw_version >> 8) & 0xFF
        self.vehicle_info.firmware_version = f"PX4 v{major}.{minor}.{patch}"
        if hasattr(msg, 'uid'):
            self.vehicle_info.uid = str(msg.uid)

    def request_parameters(self):
        if not self._master:
            return
        self._master.mav.param_request_list_send(
            self._master.target_system,
            self._master.target_component
        )

    def set_parameter(self, name: str, value: Any) -> bool:
        if not self._master:
            return False
        param_id_bytes = name.encode('utf-8')[:16]
        self._master.mav.param_set_send(
            self._master.target_system,
            self._master.target_component,
            param_id_bytes,
            float(value),
            mavutil.mavlink.MAV_PARAM_TYPE_REAL32
        )
        return True

    def start_calibration(self, cal_type: CalibrationType):
        if not self._master:
            return
        # MAV_CMD_PREFLIGHT_CALIBRATION (241)
        # param1: gyro, param2: mag, param3: ground pressure, param4: radio, param5: accel, param6: comp motor
        p1 = 1 if cal_type == CalibrationType.GYROSCOPE else 0
        p2 = 1 if cal_type == CalibrationType.COMPASS else 0
        p4 = 1 if cal_type == CalibrationType.RC_RADIO else 0
        p5 = 1 if cal_type == CalibrationType.ACCELEROMETER else 0

        self._master.mav.command_long_send(
            self._master.target_system,
            self._master.target_component,
            mavutil.mavlink.MAV_CMD_PREFLIGHT_CALIBRATION,
            0,
            p1, p2, 0, p4, p5, 0, 0
        )

    def cancel_calibration(self):
        if not self._master:
            return
        # Sending 0 to all params aborts active calibration
        self._master.mav.command_long_send(
            self._master.target_system,
            self._master.target_component,
            mavutil.mavlink.MAV_CMD_PREFLIGHT_CALIBRATION,
            0,
            0, 0, 0, 0, 0, 0, 0
        )

    def reboot_autopilot(self):
        if not self._master:
            return
        self._master.mav.command_long_send(
            self._master.target_system,
            self._master.target_component,
            mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN,
            0,
            1, 0, 0, 0, 0, 0, 0
        )
