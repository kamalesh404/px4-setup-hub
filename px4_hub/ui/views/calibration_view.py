"""
Calibration Center View for PX4 Setup Hub.
Provides interactive step-by-step guidance for Gyroscope, Accelerometer, Compass, and Level Horizon.
"""
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt
from ..components.widgets import StatusBadge
from ...core.enums import CalibrationType, CalibrationStep, HealthStatus
from ...core.models import CalibrationProgress


class CalibrationView(QWidget):
    """Interactive Sensor Calibration Wizard."""

    def __init__(self, connection_manager, parent=None):
        super().__init__(parent)
        self.conn_mgr = connection_manager
        self.current_cal_type: Optional[CalibrationType] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 1. Header Card
        header = QFrame()
        header.setProperty("class", "Card")
        h_layout = QVBoxLayout(header)
        lbl_title = QLabel("SENSOR CALIBRATION CENTER")
        lbl_title.setObjectName("Title")
        lbl_sub = QLabel("Calibrate onboard inertial and magnetic sensors according to official PX4 procedures.")
        lbl_sub.setObjectName("Subtitle")
        h_layout.addWidget(lbl_title)
        h_layout.addWidget(lbl_sub)
        layout.addWidget(header)

        # 2. Calibration Selection Cards Grid
        grid = QGridLayout()
        grid.setSpacing(12)

        self.btn_gyro = self._create_cal_card(
            "Gyroscope", "Hold vehicle completely still on a stable flat surface.", CalibrationType.GYROSCOPE, 0, 0, grid
        )
        self.btn_accel = self._create_cal_card(
            "Accelerometer", "Position vehicle across all 6 primary orientations.", CalibrationType.ACCELEROMETER, 0, 1, grid
        )
        self.btn_compass = self._create_cal_card(
            "Compass (Magnetometer)", "Rotate vehicle 360° across multiple axes away from metal.", CalibrationType.COMPASS, 1, 0, grid
        )
        self.btn_level = self._create_cal_card(
            "Level Horizon", "Level vehicle perfectly to set zero pitch and roll reference.", CalibrationType.LEVEL_HORIZON, 1, 1, grid
        )
        layout.addLayout(grid)

        # 3. Active Calibration Wizard Box
        self.wizard_card = QFrame()
        self.wizard_card.setProperty("class", "Card")
        w_layout = QVBoxLayout(self.wizard_card)
        w_layout.setSpacing(12)

        w_header = QHBoxLayout()
        self.lbl_cal_title = QLabel("NO ACTIVE CALIBRATION")
        self.lbl_cal_title.setObjectName("SectionHeading")
        self.cal_badge = StatusBadge(HealthStatus.UNKNOWN)
        w_header.addWidget(self.lbl_cal_title)
        w_header.addStretch()
        w_header.addWidget(self.cal_badge)
        w_layout.addLayout(w_header)

        self.lbl_instruction = QLabel("Select a sensor above to begin calibration.")
        self.lbl_instruction.setStyleSheet("font-size: 15px; font-weight: 600; color: #38bdf8; padding: 12px 0;")
        w_layout.addWidget(self.lbl_instruction)

        # Orientation Checklist Pills for 6-axis calibrations
        self.orientation_frame = QFrame()
        o_layout = QHBoxLayout(self.orientation_frame)
        o_layout.setSpacing(8)
        self.orient_badges = {}
        for step in [CalibrationStep.ROTATION_NORMAL, CalibrationStep.ROTATION_UPSIDE_DOWN,
                     CalibrationStep.NOSE_DOWN, CalibrationStep.TAIL_DOWN,
                     CalibrationStep.LEFT_SIDE, CalibrationStep.RIGHT_SIDE]:
            b = QLabel(step.value)
            b.setStyleSheet("""
                QLabel {
                    background-color: #1e293b;
                    color: #94a3b8;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)
            self.orient_badges[step] = b
            o_layout.addWidget(b)
        w_layout.addWidget(self.orientation_frame)

        # Progress bar
        self.pbar = QProgressBar()
        self.pbar.setRange(0, 100)
        self.pbar.setValue(0)
        self.pbar.setFixedHeight(14)
        w_layout.addWidget(self.pbar)

        # Cancel Button
        btn_bar = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel Calibration")
        self.btn_cancel.setObjectName("DangerButton")
        self.btn_cancel.clicked.connect(self._cancel_active)
        self.btn_cancel.setEnabled(False)
        btn_bar.addStretch()
        btn_bar.addWidget(self.btn_cancel)
        w_layout.addLayout(btn_bar)

        layout.addWidget(self.wizard_card)
        layout.addStretch()

    def _create_cal_card(self, title: str, desc: str, cal_type: CalibrationType, row: int, col: int, grid: QGridLayout) -> QPushButton:
        card = QFrame()
        card.setProperty("class", "Card")
        c_layout = QVBoxLayout(card)

        lbl = QLabel(title)
        lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #f8fafc;")
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        desc_lbl.setWordWrap(True)

        btn = QPushButton(f"Calibrate {title}")
        btn.setObjectName("PrimaryButton")
        btn.clicked.connect(lambda: self._start_cal(cal_type))

        c_layout.addWidget(lbl)
        c_layout.addWidget(desc_lbl)
        c_layout.addStretch()
        c_layout.addWidget(btn)

        grid.addWidget(card, row, col)
        return btn

    def _start_cal(self, cal_type: CalibrationType):
        if not self.conn_mgr.is_connected:
            QMessageBox.warning(self, "No Connection", "Please connect a vehicle before starting calibration.")
            return

        self.current_cal_type = cal_type
        self.lbl_cal_title.setText(f"CALIBRATING {cal_type.value.upper()}")
        self.lbl_instruction.setText("Initializing sensor calibration sequence...")
        self.cal_badge.set_status(HealthStatus.WARNING)
        self.pbar.setValue(0)
        self.btn_cancel.setEnabled(True)

        # Reset orientation pills
        for b in self.orient_badges.values():
            b.setStyleSheet("background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 4px; padding: 4px 8px; font-size: 11px;")

        self.conn_mgr.active_vehicle.start_calibration(cal_type)

    def _cancel_active(self):
        if self.conn_mgr.active_vehicle:
            self.conn_mgr.active_vehicle.cancel_calibration()
        self.btn_cancel.setEnabled(False)

    def update_progress(self, p: CalibrationProgress):
        self.lbl_instruction.setText(p.instruction)
        self.pbar.setValue(p.progress_pct)

        # Update step pills
        for step in p.completed_steps:
            if step in self.orient_badges:
                self.orient_badges[step].setStyleSheet("""
                    background-color: #14532d;
                    color: #22c55e;
                    border: 1px solid #22c55e;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: 700;
                """)

        if p.is_done:
            self.btn_cancel.setEnabled(False)
            if p.is_error:
                self.cal_badge.set_status(HealthStatus.FAIL)
                self.lbl_instruction.setText(f"Failed: {p.error_message}")
            else:
                self.cal_badge.set_status(HealthStatus.PASS)
                self.lbl_instruction.setText(f"✓ {p.calibration_type} Calibrated Successfully!")
