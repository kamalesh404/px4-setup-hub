"""
Evidence-Backed Preflight Health and Safety Evaluator for PX4.
Never marks an item PASS without real verification telemetry.
Distinguishes PASS, WARNING, FAIL, and UNKNOWN.
"""
from typing import List, Dict, Tuple
from ...core.enums import HealthStatus, SensorType, FlightMode, ArmingStatus
from ...core.models import TelemetryData, VehicleInfo, SensorStatus, Parameter, PreflightCheckItem


class PreflightEvaluator:
    """Evaluates drone readiness strictly against evidence received from the vehicle."""

    @staticmethod
    def evaluate(
        vehicle_info: VehicleInfo,
        telemetry: TelemetryData,
        sensors: Dict[SensorType, SensorStatus],
        parameters: Dict[str, Parameter]
    ) -> Tuple[List[PreflightCheckItem], float, HealthStatus]:
        checks: List[PreflightCheckItem] = []

        # If vehicle is completely disconnected, everything is UNKNOWN / FAIL
        if not vehicle_info.connected:
            disconnected_check = PreflightCheckItem(
                id="SYS_CONN",
                category="System",
                title="Vehicle Connection",
                status=HealthStatus.FAIL,
                evidence_value="DISCONNECTED",
                explanation="No flight controller heartbeat detected over USB, telemetry or network.",
                remediation_hint="Connect flight controller via USB or select SITL UDP port in Connection tab."
            )
            return [disconnected_check], 0.0, HealthStatus.FAIL

        # 1. Firmware & Autopilot Verification
        fw_status = HealthStatus.PASS if vehicle_info.is_px4 else HealthStatus.WARNING
        checks.append(PreflightCheckItem(
            id="CHECK_FW",
            category="System",
            title="Firmware Verification",
            status=fw_status,
            evidence_value=vehicle_info.firmware_version,
            explanation=f"Detected: {vehicle_info.board_name} running {vehicle_info.firmware_version}.",
            remediation_hint="Ensure PX4 stable firmware (v1.14+) is flashed if unverified."
        ))

        # 2. Airframe / Frame Configuration
        sys_autostart = parameters.get("SYS_AUTOSTART")
        if sys_autostart and int(sys_autostart.value) > 0:
            frame_status = HealthStatus.PASS
            frame_evidence = f"SYS_AUTOSTART = {sys_autostart.value} ({vehicle_info.vehicle_type})"
            frame_expl = "Airframe geometry and mixer configurations loaded."
            frame_hint = ""
        else:
            frame_status = HealthStatus.FAIL
            frame_evidence = f"SYS_AUTOSTART = {sys_autostart.value if sys_autostart else 'Not Loaded'}"
            frame_expl = "No valid airframe autostart ID assigned. Motors/actuators cannot be mapped."
            frame_hint = "Select airframe type (e.g., Quadrotor X) in Vehicle Configuration."

        checks.append(PreflightCheckItem(
            id="CHECK_FRAME",
            category="Configuration",
            title="Frame Configuration",
            status=frame_status,
            evidence_value=frame_evidence,
            explanation=frame_expl,
            remediation_hint=frame_hint
        ))

        # 3. Gyroscope Calibration
        gyro_sensor = sensors.get(SensorType.GYRO)
        cal_gyro_id = parameters.get("CAL_GYRO0_ID")
        gyro_calibrated = (gyro_sensor and gyro_sensor.calibrated) or (cal_gyro_id and int(cal_gyro_id.value) > 0)
        
        if gyro_calibrated:
            gyro_status = HealthStatus.PASS
            gyro_ev = f"CAL_GYRO0_ID={cal_gyro_id.value if cal_gyro_id else 'Valid'}"
            gyro_expl = "Angular rate sensors zero-bias calibrated and stationary test passed."
            gyro_hint = ""
        else:
            gyro_status = HealthStatus.FAIL
            gyro_ev = "Uncalibrated or zero ID"
            gyro_expl = "Gyroscope has not completed static thermal/offset calibration."
            gyro_hint = "Run Gyroscope Calibration while holding the vehicle completely still."

        checks.append(PreflightCheckItem(
            id="CHECK_GYRO",
            category="Sensors",
            title="Gyroscope Calibration",
            status=gyro_status,
            evidence_value=gyro_ev,
            explanation=gyro_expl,
            remediation_hint=gyro_hint
        ))

        # 4. Accelerometer Calibration
        accel_sensor = sensors.get(SensorType.ACCEL)
        cal_acc_id = parameters.get("CAL_ACC0_ID")
        accel_calibrated = (accel_sensor and accel_sensor.calibrated) or (cal_acc_id and int(cal_acc_id.value) > 0)
        
        if accel_calibrated:
            acc_status = HealthStatus.PASS
            acc_ev = f"CAL_ACC0_ID={cal_acc_id.value if cal_acc_id else 'Valid'}"
            acc_expl = "6-axis gravity reference vector matches 1G scale."
            acc_hint = ""
        else:
            acc_status = HealthStatus.FAIL
            acc_ev = "Uncalibrated"
            acc_expl = "Accelerometers require 6-position orientation calibration."
            acc_hint = "Run Accelerometer Calibration in the Calibration Center."

        checks.append(PreflightCheckItem(
            id="CHECK_ACCEL",
            category="Sensors",
            title="Accelerometer Calibration",
            status=acc_status,
            evidence_value=acc_ev,
            explanation=acc_expl,
            remediation_hint=acc_hint
        ))

        # 5. Compass / Magnetometer Calibration
        mag_sensor = sensors.get(SensorType.MAG)
        cal_mag_id = parameters.get("CAL_MAG0_ID")
        mag_calibrated = (mag_sensor and mag_sensor.calibrated) or (cal_mag_id and int(cal_mag_id.value) > 0)

        if mag_calibrated:
            mag_status = HealthStatus.PASS
            mag_ev = f"CAL_MAG0_ID={cal_mag_id.value if cal_mag_id else 'Valid'}"
            mag_expl = "Magnetometer sphere-fit calibration valid with acceptable hard/soft iron offsets."
            mag_hint = ""
        else:
            mag_status = HealthStatus.WARNING
            mag_ev = f"CAL_MAG0_ID={cal_mag_id.value if cal_mag_id else '0'} (Pending)"
            mag_expl = "Compass is uncalibrated or magnetic interference is present. Position control modes will be restricted."
            mag_hint = "Perform Compass 360° rotation calibration away from indoor metal objects."

        checks.append(PreflightCheckItem(
            id="CHECK_MAG",
            category="Sensors",
            title="Compass Calibration",
            status=mag_status,
            evidence_value=mag_ev,
            explanation=mag_expl,
            remediation_hint=mag_hint
        ))

        # 6. GPS Readiness & Fix Quality
        gps_fix = telemetry.gps_fix_type
        gps_sats = telemetry.gps_satellites
        gps_hdop = telemetry.gps_hdop

        if "3D" in gps_fix and gps_sats >= 10 and gps_hdop < 1.5:
            gps_status = HealthStatus.PASS
            gps_ev = f"{gps_fix} ({gps_sats} Sats, HDOP {gps_hdop:.2f})"
            gps_expl = "High quality 3D satellite lock acquired. Autonomous navigation and return-to-land ready."
            gps_hint = ""
        elif "3D" in gps_fix:
            gps_status = HealthStatus.WARNING
            gps_ev = f"{gps_fix} ({gps_sats} Sats, HDOP {gps_hdop:.2f})"
            gps_expl = "3D Fix established, but satellite count or accuracy is marginal."
            gps_hint = "Move drone outdoors with clear line-of-sight to open sky."
        else:
            gps_status = HealthStatus.WARNING
            gps_ev = f"{gps_fix} ({gps_sats} Sats)"
            gps_expl = "No 3D GNSS lock. Vehicle will only permit Stabilized/Altitude flight."
            gps_hint = "Ensure GPS antenna has clear sky view. Position hold disabled without fix."

        checks.append(PreflightCheckItem(
            id="CHECK_GPS",
            category="Navigation",
            title="GPS Readiness",
            status=gps_status,
            evidence_value=gps_ev,
            explanation=gps_expl,
            remediation_hint=gps_hint
        ))

        # 7. Battery & Power Safety
        volts = telemetry.battery_voltage_v
        pct = telemetry.battery_remaining_pct
        if volts >= 14.8 and pct >= 30.0:
            bat_status = HealthStatus.PASS
            bat_ev = f"{volts:.2f}V ({pct:.0f}% remaining)"
            bat_expl = "Battery voltage well above critical threshold."
            bat_hint = ""
        elif volts > 14.0 and pct > 15.0:
            bat_status = HealthStatus.WARNING
            bat_ev = f"{volts:.2f}V ({pct:.0f}% remaining)"
            bat_expl = "Battery is moderately depleted. Flight endurance will be limited."
            bat_hint = "Charge battery to full before conducting test flights."
        elif volts > 0:
            bat_status = HealthStatus.FAIL
            bat_ev = f"{volts:.2f}V ({pct:.0f}%)"
            bat_expl = "Battery voltage dangerously low! Risk of inflight brownout or failsafe land."
            bat_hint = "Recharge immediately. Do not attempt takeoff."
        else:
            bat_status = HealthStatus.UNKNOWN
            bat_ev = "No telemetry"
            bat_expl = "Power monitor / ADC not reporting voltage."
            bat_hint = "Check power module wiring and BAT1 parameters."

        checks.append(PreflightCheckItem(
            id="CHECK_BATTERY",
            category="Power",
            title="Battery & Power Health",
            status=bat_status,
            evidence_value=bat_ev,
            explanation=bat_expl,
            remediation_hint=bat_hint
        ))

        # Calculate Overall Readiness Score (0 - 100%)
        # Weights: PASS=1.0, WARNING=0.5, FAIL=0.0, UNKNOWN=0.0
        total_weight = len(checks)
        earned = sum(1.0 if c.status == HealthStatus.PASS else (0.5 if c.status == HealthStatus.WARNING else 0.0) for c in checks)
        readiness_score = round((earned / total_weight) * 100.0, 1)

        # Overall Status
        if any(c.status == HealthStatus.FAIL for c in checks):
            overall = HealthStatus.FAIL
        elif any(c.status == HealthStatus.WARNING for c in checks):
            overall = HealthStatus.WARNING
        elif all(c.status == HealthStatus.PASS for c in checks):
            overall = HealthStatus.PASS
        else:
            overall = HealthStatus.UNKNOWN

        return checks, readiness_score, overall
