"""
Main Dashboard View for PX4 Setup Hub.
Displays evidence-backed flight status, readiness score, setup checklist, and live attitude.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QProgressBar, QPushButton, QMessageBox, QScrollArea
)
from PySide6.QtCore import Qt
from ..components.widgets import StatusBadge, MetricCard, ChecklistRow, ArtificialHorizon
from ...core.enums import HealthStatus, FlightMode, ArmingStatus
from ...core.models import TelemetryData, VehicleInfo
from ...modules.preflight.evaluator import PreflightEvaluator


class DashboardView(QWidget):
    """Unified Dashboard showing live status, system readiness, checklist, and attitude."""

    def __init__(self, connection_manager, parent=None):
        super().__init__(parent)
        self.conn_mgr = connection_manager

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Scrollable container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(16)

        # 1. Header & Live Connection Summary Banner
        self.banner = QFrame()
        self.banner.setObjectName("Banner")
        self.banner.setStyleSheet("""
            QFrame#Banner {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        banner_layout = QHBoxLayout(self.banner)

        title_col = QVBoxLayout()
        self.lbl_board_name = QLabel("NO VEHICLE CONNECTED")
        self.lbl_board_name.setObjectName("Title")
        self.lbl_fw_info = QLabel("Connect flight controller via USB or select SITL / Mock in Connection tab")
        self.lbl_fw_info.setObjectName("Subtitle")
        title_col.addWidget(self.lbl_board_name)
        title_col.addWidget(self.lbl_fw_info)

        self.conn_badge = StatusBadge(HealthStatus.FAIL)
        self.btn_reboot = QPushButton("Reboot Autopilot")
        self.btn_reboot.clicked.connect(self._confirm_reboot)
        self.btn_reboot.setEnabled(False)

        banner_layout.addLayout(title_col, 1)
        banner_layout.addWidget(self.conn_badge)
        banner_layout.addWidget(self.btn_reboot)
        container_layout.addWidget(self.banner)

        # 2. Key Metrics Row
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(12)

        self.card_mode = MetricCard("Flight Mode", "UNKNOWN")
        self.card_arming = MetricCard("Armed Status", "DISARMED")
        self.card_gps = MetricCard("GPS Fix", "No Fix", "0 Sats")
        self.card_battery = MetricCard("Battery", "0.0", "V")
        self.card_alt = MetricCard("Altitude", "0.0", "m")
        self.card_speed = MetricCard("Ground Speed", "0.0", "m/s")

        metrics_grid.addWidget(self.card_mode, 0, 0)
        metrics_grid.addWidget(self.card_arming, 0, 1)
        metrics_grid.addWidget(self.card_gps, 0, 2)
        metrics_grid.addWidget(self.card_battery, 1, 0)
        metrics_grid.addWidget(self.card_alt, 1, 1)
        metrics_grid.addWidget(self.card_speed, 1, 2)
        container_layout.addLayout(metrics_grid)

        # 3. Middle Section: Readiness Score & Artificial Horizon side-by-side
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(16)

        # Readiness Box
        self.readiness_card = QFrame()
        self.readiness_card.setProperty("class", "Card")
        r_layout = QVBoxLayout(self.readiness_card)
        r_layout.setContentsMargins(16, 16, 16, 16)
        r_layout.setSpacing(8)

        lbl_r_title = QLabel("PREFLIGHT SYSTEM READINESS")
        lbl_r_title.setObjectName("SectionHeading")

        self.lbl_score = QLabel("0%")
        self.lbl_score.setStyleSheet("font-size: 38px; font-weight: 800; color: #f8fafc;")

        self.pbar_readiness = QProgressBar()
        self.pbar_readiness.setRange(0, 100)
        self.pbar_readiness.setValue(0)
        self.pbar_readiness.setFixedHeight(12)

        self.lbl_readiness_msg = QLabel("Connect flight controller to evaluate hardware readiness.")
        self.lbl_readiness_msg.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.lbl_readiness_msg.setWordWrap(True)

        r_layout.addWidget(lbl_r_title)
        r_layout.addWidget(self.lbl_score)
        r_layout.addWidget(self.pbar_readiness)
        r_layout.addWidget(self.lbl_readiness_msg)
        r_layout.addStretch()

        # Artificial Horizon Box
        self.horizon_card = QFrame()
        self.horizon_card.setProperty("class", "Card")
        h_layout = QVBoxLayout(self.horizon_card)
        h_layout.setContentsMargins(16, 16, 16, 16)
        h_layout.setSpacing(8)

        lbl_h_title = QLabel("ATTITUDE & ARTIFICIAL HORIZON")
        lbl_h_title.setObjectName("SectionHeading")
        self.horizon_widget = ArtificialHorizon()

        self.lbl_angles = QLabel("Roll: 0.0°  Pitch: 0.0°  Yaw: 0.0°")
        self.lbl_angles.setAlignment(Qt.AlignCenter)
        self.lbl_angles.setStyleSheet("font-size: 12px; font-weight: 600; color: #38bdf8;")

        h_layout.addWidget(lbl_h_title)
        h_layout.addWidget(self.horizon_widget, 1)
        h_layout.addWidget(self.lbl_angles)

        middle_layout.addWidget(self.readiness_card, 1)
        middle_layout.addWidget(self.horizon_card, 1)
        container_layout.addLayout(middle_layout)

        # 4. Setup Checklist
        chk_card = QFrame()
        chk_card.setProperty("class", "Card")
        chk_layout = QVBoxLayout(chk_card)
        chk_layout.setContentsMargins(16, 16, 16, 16)
        chk_layout.setSpacing(8)

        lbl_chk_title = QLabel("FLIGHT CONTROLLER SETUP CHECKLIST")
        lbl_chk_title.setObjectName("SectionHeading")
        chk_layout.addWidget(lbl_chk_title)

        self.checklist_rows = {}
        for chk_id, title, cat in [
            ("CHECK_FW", "Firmware Verification", "System"),
            ("CHECK_FRAME", "Frame Configuration", "Configuration"),
            ("CHECK_GYRO", "Gyroscope Calibration", "Sensors"),
            ("CHECK_ACCEL", "Accelerometer Calibration", "Sensors"),
            ("CHECK_MAG", "Compass Calibration", "Sensors"),
            ("CHECK_GPS", "GPS Readiness", "Navigation"),
            ("CHECK_BATTERY", "Battery & Safety Limits", "Power"),
        ]:
            row = ChecklistRow(title, cat)
            self.checklist_rows[chk_id] = row
            chk_layout.addWidget(row)

        container_layout.addWidget(chk_card)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def update_telemetry(self, t: TelemetryData):
        self.card_mode.set_value(t.flight_mode.value)
        self.card_arming.set_value(t.arming_status.value)
        self.card_gps.set_value(t.gps_fix_type, f"{t.gps_satellites} Sats (HDOP {t.gps_hdop:.2f})")
        self.card_battery.set_value(f"{t.battery_voltage_v:.2f}", f"{t.battery_remaining_pct:.0f}% ({t.battery_current_a:.1f}A)")
        self.card_alt.set_value(f"{t.altitude_relative_m:.2f}", f"AMSL {t.altitude_amsl_m:.1f}m")
        self.card_speed.set_value(f"{t.ground_speed_m_s:.1f}", f"Climb {t.climb_rate_m_s:.2f}m/s")

        self.horizon_widget.set_attitude(t.roll_deg, t.pitch_deg)
        self.lbl_angles.setText(f"Roll: {t.roll_deg:+.1f}°  Pitch: {t.pitch_deg:+.1f}°  Yaw: {t.yaw_deg:.1f}°")

    def update_vehicle_info(self, info: VehicleInfo):
        if info.connected:
            self.lbl_board_name.setText(info.board_name.upper())
            self.lbl_fw_info.setText(f"{info.firmware_version} • Endpoint: {info.connection_endpoint}")
            self.conn_badge.set_status(HealthStatus.PASS)
            self.btn_reboot.setEnabled(True)
        else:
            self.lbl_board_name.setText("NO VEHICLE CONNECTED")
            self.lbl_fw_info.setText("Connect flight controller via USB or select SITL / Mock in Connection tab")
            self.conn_badge.set_status(HealthStatus.FAIL)
            self.btn_reboot.setEnabled(False)

    def update_evaluation(self, checks, score: float, overall: HealthStatus):
        self.lbl_score.setText(f"{score:.0f}%")
        self.pbar_readiness.setValue(int(score))
        
        # Color bar according to status
        color = overall.color
        self.pbar_readiness.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)

        if overall == HealthStatus.PASS:
            self.lbl_readiness_msg.setText("All preflight criteria satisfied. Vehicle is READY FOR FLIGHT.")
            self.lbl_readiness_msg.setStyleSheet("color: #22c55e; font-weight: 600;")
        elif overall == HealthStatus.WARNING:
            self.lbl_readiness_msg.setText("Warnings detected. Safe for bench testing, but caution required before flying.")
            self.lbl_readiness_msg.setStyleSheet("color: #eab308; font-weight: 600;")
        else:
            self.lbl_readiness_msg.setText("Critical checks failing. Takeoff disallowed by PX4 safety rules.")
            self.lbl_readiness_msg.setStyleSheet("color: #ef4444; font-weight: 600;")

        for c in checks:
            if c.id in self.checklist_rows:
                self.checklist_rows[c.id].update_check(c.status, c.evidence_value, c.explanation)

    def _confirm_reboot(self):
        reply = QMessageBox.question(
            self,
            "Confirm Autopilot Reboot",
            "Are you sure you want to send a reboot command to the flight controller?\n"
            "All sensors and estimator state will restart.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes and self.conn_mgr.active_vehicle:
            self.conn_mgr.active_vehicle.reboot_autopilot()
