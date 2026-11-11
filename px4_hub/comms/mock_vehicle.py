"""
High-fidelity Mock PX4 Vehicle.
Simulates a MicroAir H7 AIO V4 flight controller with HGLRC M10 GPS running PX4 Autopilot v1.15.0.
Provides realistic asynchronous telemetry streams, parameter reads/writes, and calibration simulation.
"""
import time
import math
import random
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


class MockVehicle(BaseVehicle):
    """
    Offline simulator providing evidence-backed telemetry, realistic calibration loops,
    and actual parameter databases without requiring physical hardware or PX4 SITL.
    """

    def __init__(self):
        super().__init__()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cal_thread: Optional[threading.Thread] = None
        self._cal_active = False
        self._cal_type: Optional[CalibrationType] = None
        self._ticks = 0
        self._init_mock_data()

    def _init_mock_data(self):
        # 1. Hardware & Board Info (Targeting user's MicroAir H7 AIO V4 profile)
        self.vehicle_info = VehicleInfo(
            connected=True,
            board_name="MicroAir H7 AIO V4 (STM32H743)",
            board_vendor="MicroAir",
            board_id=1024,
            firmware_version="PX4 Autopilot v1.15.0-rc2 (Custom Built)",
            firmware_vendor_version="v1.15.0",
            os_version="NuttX 11.0.0",
            target_name="px4_fmu-v7",
            uid="33003B000C51393037383632",
            vehicle_type="Multicopter (Quad X)",
            frame_class="Generic 5-inch Freestyle Quad",
            bootloader_version="v5.0.1",
            connection_endpoint="Mock USB Serial /dev/ttyACM0 (Virtual)",
            last_heartbeat_time=time.time()
        )

        # 2. Onboard Sensors Initial State
        self.sensors = {
            SensorType.GYRO: SensorStatus(
                sensor_type=SensorType.GYRO,
                status=HealthStatus.PASS,
                detected=True,
                calibrated=True,
                detail="ICM-42688-P Primary IMU active, noise floor: 0.003 rad/s",
                evidence="Rate std-dev < 0.05 rad/s, temp: 38.4°C"
            ),
            SensorType.ACCEL: SensorStatus(
                sensor_type=SensorType.ACCEL,
                status=HealthStatus.PASS,
                detected=True,
                calibrated=True,
                detail="Dual redundant accelerometers online (ICM-42688 + BMI088)",
                evidence="Gravity magnitude: 9.806 m/s² (0.1% error)"
            ),
            SensorType.MAG: SensorStatus(
                sensor_type=SensorType.MAG,
                status=HealthStatus.WARNING,
                detected=True,
                calibrated=False,
                detail="QMC5883L external compass uncalibrated or magnetic interference detected",
                evidence="MAG0 ID detected, CAL_MAG0_ID=0 (Needs 6-axis calibration)"
            ),
            SensorType.BARO: SensorStatus(
                sensor_type=SensorType.BARO,
                status=HealthStatus.PASS,
                detected=True,
                calibrated=True,
                detail="DPS310 high-precision barometric pressure sensor",
                evidence="Pressure: 1013.25 hPa, temp: 34.2°C"
            ),
            SensorType.GPS: SensorStatus(
                sensor_type=SensorType.GPS,
                status=HealthStatus.PASS,
                detected=True,
                calibrated=True,
                detail="HGLRC M10 GNSS (14 Satellites, 3D Fix, HDOP 0.82)",
                evidence="UBX-NAV-PVT lock OK, fix_type=3D"
            ),
            SensorType.BATTERY: SensorStatus(
                sensor_type=SensorType.BATTERY,
                status=HealthStatus.PASS,
                detected=True,
                calibrated=True,
                detail="4S LiPo Power Monitor: 16.24V (4.06V/cell), 88% capacity",
                evidence="ADC sense pin calibrated, current draw: 1.18A idle"
            ),
            SensorType.RC: SensorStatus(
                sensor_type=SensorType.RC,
                status=HealthStatus.WARNING,
                detected=False,
                calibrated=True,
                detail="CRSF / ELRS Receiver: No active transmitter signal",
                evidence="RC RSSI: 0%, Failsafe active (USB bench mode)"
            )
        }

        # 3. Rich PX4 Parameter Catalog
        mock_param_specs = [
            ("SYS_AUTOSTART", 4001, "INT32", 0, 10000, "Airframe autostart ID (4001 = Generic Quadcopter X)", "Airframe", True),
            ("SYS_MC_EST_GROUP", 2, "INT32", 1, 3, "State estimator group (2 = EKF2)", "Estimator", True),
            ("CAL_MAG0_ID", 0, "INT32", 0, 9999999, "Magnetometer 0 Calibration ID", "Sensors", False),
            ("CAL_ACC0_ID", 131072, "INT32", 0, 9999999, "Accelerometer 0 Calibration ID", "Sensors", False),
            ("CAL_GYRO0_ID", 131072, "INT32", 0, 9999999, "Gyroscope 0 Calibration ID", "Sensors", False),
            ("SENS_BOARD_ROT", 0, "INT32", 0, 36, "Flight controller board orientation rotation", "Sensors", True),
            ("COM_ARM_WO_GPS", 1, "INT32", 0, 1, "Allow arming without GPS lock in altitude/stabilized", "Commander", False),
            ("COM_RC_IN_MODE", 0, "INT32", 0, 2, "RC input mode: 0=normal, 1=joystick, 2=virtual", "Commander", False),
            ("COM_DISARM_PRFLT", 10.0, "FLOAT", 0.0, 60.0, "Timeout for disarm after auto-disarm (seconds)", "Commander", False),
            ("BAT1_N_CELLS", 4, "INT32", 1, 14, "Number of cells in Battery 1", "Battery", False),
            ("BAT1_V_EMPTY", 3.5, "FLOAT", 2.0, 4.5, "Empty cell voltage limit (V)", "Battery", False),
            ("BAT1_V_CHARGED", 4.2, "FLOAT", 3.0, 4.5, "Full charged cell voltage limit (V)", "Battery", False),
            ("BAT1_CAPACITY", 1500.0, "FLOAT", 100.0, 50000.0, "Battery capacity (mAh)", "Battery", False),
            ("EKF2_AID_MASK", 1, "INT32", 0, 255, "EKF2 sensor fusion aid mask (1=GPS)", "EKF2", True),
            ("EKF2_HGT_REF", 0, "INT32", 0, 3, "Primary height source: 0=Baro, 1=GNSS, 2=Range", "EKF2", False),
            ("MC_ROLL_P", 6.5, "FLOAT", 0.0, 20.0, "Roll axis proportional attitude gain", "Attitude Control", False),
            ("MC_PITCH_P", 6.5, "FLOAT", 0.0, 20.0, "Pitch axis proportional attitude gain", "Attitude Control", False),
            ("MC_YAW_P", 2.8, "FLOAT", 0.0, 10.0, "Yaw axis proportional attitude gain", "Attitude Control", False),
            ("MC_ROLLRATE_P", 0.15, "FLOAT", 0.0, 1.0, "Roll rate proportional gain", "Rate Control", False),
            ("MC_PITCHRATE_P", 0.15, "FLOAT", 0.0, 1.0, "Pitch rate proportional gain", "Rate Control", False),
            ("MC_YAWRATE_P", 0.20, "FLOAT", 0.0, 1.0, "Yaw rate proportional gain", "Rate Control", False),
            ("MPC_XY_VEL_MAX", 12.0, "FLOAT", 1.0, 30.0, "Maximum horizontal velocity in Auto/PosCtl (m/s)", "Position Control", False),
            ("MPC_Z_VEL_MAX_UP", 3.0, "FLOAT", 0.5, 10.0, "Maximum ascent rate (m/s)", "Position Control", False),
            ("MPC_Z_VEL_MAX_DN", 1.5, "FLOAT", 0.5, 5.0, "Maximum descent rate (m/s)", "Position Control", False),
            ("NAV_RCL_ACT", 2, "INT32", 0, 5, "Failsafe action on RC loss: 0=Disabled, 2=RTL, 3=Land", "Safety", False),
            ("NAV_DLL_ACT", 0, "INT32", 0, 3, "Failsafe action on DataLink loss", "Safety", False),
            ("CBRK_SUPPLY_CHK", 0, "INT32", 0, 894281, "Circuit breaker for power supply check (0 = enforced)", "Safety", False),
            ("CBRK_USB_CHK", 0, "INT32", 0, 197848, "Circuit breaker to allow arming over USB", "Safety", False),
            ("MOT_POLE_COUNT", 14, "INT32", 2, 60, "Number of magnetic poles in brushless motor", "Actuators", False),
            ("PWM_MAIN_DISARM", 900, "INT32", 800, 1200, "PWM pulse during disarmed state (us)", "Actuators", False),
            ("PWM_MAIN_MIN", 1075, "INT32", 900, 1500, "PWM minimum motor spin threshold (us)", "Actuators", False),
            ("PWM_MAIN_MAX", 2000, "INT32", 1500, 2200, "PWM full throttle pulse width (us)", "Actuators", False),
        ]

        self.parameters = {}
        for name, val, tname, min_v, max_v, desc, group, reboot in mock_param_specs:
            self.parameters[name] = Parameter(
                name=name,
                value=val,
                default_value=val,
                type_name=tname,
                min_value=min_v,
                max_value=max_v,
                description=desc,
                group=group,
                requires_reboot=reboot,
                is_modified=False
            )

    def connect(self, endpoint: str = "mock://px4-microair-h7", **kwargs) -> bool:
        self.state = ConnectionState.CONNECTING
        if self.on_state_changed:
            self.on_state_changed(self.state, f"Connecting to {endpoint}...")

        time.sleep(0.3)  # Brief simulated handshake
        self.state = ConnectionState.CONNECTED
        self.vehicle_info.connection_endpoint = endpoint
        self.vehicle_info.connected = True
        self.vehicle_info.last_heartbeat_time = time.time()

        if self.on_state_changed:
            self.on_state_changed(self.state, f"Connected to {self.vehicle_info.board_name}")

        self._running = True
        self._thread = threading.Thread(target=self._telemetry_loop, daemon=True)
        self._thread.start()

        # Emit initial sensor states
        for sensor in self.sensors.values():
            if self.on_sensor_status_updated:
                self.on_sensor_status_updated(sensor)

        return True

    def disconnect(self):
        self._running = False
        self._cal_active = False
        self.state = ConnectionState.DISCONNECTED
        self.vehicle_info.connected = False
        if self.on_state_changed:
            self.on_state_changed(self.state, "Disconnected from vehicle")

    def _telemetry_loop(self):
        """Asynchronous stream running at ~10Hz generating realistic telemetry noise."""
        while self._running:
            self._ticks += 1
            t = self._ticks * 0.1

            # Micro bench-top vibration / orientation drifts
            roll = math.sin(t * 0.4) * 0.8 + (random.random() - 0.5) * 0.1
            pitch = math.cos(t * 0.3) * 0.6 + (random.random() - 0.5) * 0.1
            yaw = (t * 1.5) % 360.0

            # Battery gradual discharge simulation
            volts = 16.24 - (self._ticks * 0.0001)
            pct = max(0.0, min(100.0, (volts - 14.0) / (16.8 - 14.0) * 100))

            self.telemetry = TelemetryData(
                timestamp=time.time(),
                roll_deg=round(roll, 2),
                pitch_deg=round(pitch, 2),
                yaw_deg=round(yaw, 2),
                heading_deg=round(yaw, 1),
                roll_rate_deg_s=round(math.cos(t * 0.4) * 0.3, 3),
                pitch_rate_deg_s=round(-math.sin(t * 0.3) * 0.2, 3),
                yaw_rate_deg_s=0.01,
                ground_speed_m_s=0.0,
                climb_rate_m_s=round(math.sin(t * 0.2) * 0.04, 2),
                altitude_relative_m=round(0.08 + math.sin(t * 0.1) * 0.02, 2),
                altitude_amsl_m=142.5,
                flight_mode=FlightMode.MANUAL,
                arming_status=ArmingStatus.DISARMED,
                is_flying=False,
                mavlink_loss_pct=0.0,
                mavlink_message_rate=14.5,
                gps_fix_type="3D Fix",
                gps_satellites=14,
                gps_lat=37.774929 + math.sin(t * 0.01) * 0.00001,
                gps_lon=-122.419416 + math.cos(t * 0.01) * 0.00001,
                gps_hdop=0.82,
                gps_vdop=1.14,
                battery_voltage_v=round(volts, 2),
                battery_current_a=1.18,
                battery_remaining_pct=round(pct, 1),
                battery_cell_count=4,
                cpu_load_pct=round(24.5 + math.sin(t * 0.5) * 3.0, 1),
                ram_usage_pct=42.1,
                ekf_status_flags=1,
                sensors_healthy=True
            )

            if self.on_telemetry_updated:
                self.on_telemetry_updated(self.telemetry)

            time.sleep(0.1)

    def request_parameters(self):
        """Simulate reading all parameters from vehicle."""
        for param in self.parameters.values():
            if self.on_parameter_received:
                self.on_parameter_received(param)

    def set_parameter(self, name: str, value: Any) -> bool:
        if name in self.parameters:
            param = self.parameters[name]
            if param.validate(value):
                param.value = value
                param.is_modified = (param.value != param.default_value)
                if self.on_parameter_received:
                    self.on_parameter_received(param)
                return True
        return False

    def start_calibration(self, cal_type: CalibrationType):
        if self._cal_active:
            return
        self._cal_active = True
        self._cal_type = cal_type
        self._cal_thread = threading.Thread(target=self._run_mock_calibration, daemon=True)
        self._cal_thread.start()

    def cancel_calibration(self):
        self._cal_active = False
        if self.on_calibration_progress and self._cal_type:
            self.on_calibration_progress(CalibrationProgress(
                calibration_type=self._cal_type.value,
                step=CalibrationStep.FAILED,
                progress_pct=0,
                instruction="Calibration cancelled by operator.",
                is_done=True,
                is_error=True,
                error_message="User requested abort"
            ))

    def _run_mock_calibration(self):
        """Simulate interactive 6-axis calibration steps with realistic delays."""
        cal_name = self._cal_type.value if self._cal_type else "Calibration"

        if self._cal_type == CalibrationType.GYROSCOPE:
            # Gyro calibration requires resting stationary
            steps = [
                ("Hold vehicle still on level surface...", 25),
                ("Sampling angular rates...", 60),
                ("Calculating drift offsets...", 90),
                ("Gyro calibrated successfully!", 100),
            ]
            for msg, pct in steps:
                if not self._cal_active:
                    return
                time.sleep(0.8)
                if self.on_calibration_progress:
                    self.on_calibration_progress(CalibrationProgress(
                        calibration_type=cal_name,
                        step=CalibrationStep.ROTATION_NORMAL,
                        progress_pct=pct,
                        instruction=msg,
                        is_done=(pct == 100)
                    ))
            # Update sensor state
            self.sensors[SensorType.GYRO].status = HealthStatus.PASS
            self.sensors[SensorType.GYRO].calibrated = True

        elif self._cal_type == CalibrationType.COMPASS or self._cal_type == CalibrationType.ACCELEROMETER:
            # 6-orientation calibration sequence
            orientations = [
                (CalibrationStep.ROTATION_NORMAL, "Place vehicle level with top facing UP", 16),
                (CalibrationStep.ROTATION_UPSIDE_DOWN, "Flip vehicle UPSIDE DOWN", 33),
                (CalibrationStep.NOSE_DOWN, "Hold vehicle vertical with NOSE DOWN", 50),
                (CalibrationStep.TAIL_DOWN, "Hold vehicle vertical with TAIL DOWN", 66),
                (CalibrationStep.LEFT_SIDE, "Rest vehicle on its LEFT SIDE", 83),
                (CalibrationStep.RIGHT_SIDE, "Rest vehicle on its RIGHT SIDE", 100),
            ]
            completed = []
            for step, instruction, pct in orientations:
                if not self._cal_active:
                    return
                # Show instruction
                if self.on_calibration_progress:
                    self.on_calibration_progress(CalibrationProgress(
                        calibration_type=cal_name,
                        step=step,
                        progress_pct=pct - 10,
                        instruction=instruction,
                        completed_steps=list(completed),
                        is_done=False
                    ))
                time.sleep(1.2)  # Wait for user orientation
                if not self._cal_active:
                    return
                completed.append(step)
                if self.on_calibration_progress:
                    self.on_calibration_progress(CalibrationProgress(
                        calibration_type=cal_name,
                        step=step,
                        progress_pct=pct,
                        instruction=f"{step.value} recorded. Hold still...",
                        completed_steps=list(completed),
                        is_done=(pct == 100)
                    ))
                time.sleep(0.4)

            # Mark Compass as calibrated
            if self._cal_type == CalibrationType.COMPASS:
                self.sensors[SensorType.MAG].status = HealthStatus.PASS
                self.sensors[SensorType.MAG].calibrated = True
                self.sensors[SensorType.MAG].detail = "QMC5883L external compass calibrated (Mag offsets: -12, +45, +8)"
                self.sensors[SensorType.MAG].evidence = "Sphere fit error: 0.8% (PASS)"
                self.parameters["CAL_MAG0_ID"].value = 196608
                self.parameters["CAL_MAG0_ID"].is_modified = True

        self._cal_active = False

    def reboot_autopilot(self):
        if self.on_text_message:
            self.on_text_message(0, "[COMMAND] MAVLink MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN sent.")
        # Briefly drop and restore heartbeat
        self.vehicle_info.connected = False
        time.sleep(1.0)
        self.vehicle_info.connected = True
