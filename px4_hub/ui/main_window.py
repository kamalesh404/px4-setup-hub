"""
Main Application Shell for PX4 Setup Hub.
Features collapsible dark sidebar navigation, persistent top telemetry header, and view switching.
"""
from typing import Dict
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QToolButton, QLabel, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QObject
from .theme import DARK_THEME_QSS
from .components.widgets import StatusBadge
from .views.dashboard_view import DashboardView
from .views.connection_view import ConnectionView
from .views.calibration_view import CalibrationView
from .views.parameters_view import ParametersView
from .views.telemetry_view import TelemetryView
from .views.preflight_view import PreflightView
from ..core.enums import ConnectionState, HealthStatus
from ..core.models import TelemetryData, VehicleInfo, Parameter, CalibrationProgress
from ..modules.preflight.evaluator import PreflightEvaluator


class VehicleSignalBridge(QObject):
    """Bridges threaded vehicle events safely to Qt Main Thread GUI events."""
    state_changed = Signal(object, str)
    telemetry_updated = Signal(object)
    sensor_updated = Signal(object)
    param_received = Signal(object)
    calibration_progress = Signal(object)
    text_message = Signal(int, str)


class MainWindow(QMainWindow):
    """Root Application Window with Sidebar navigation and reactive views."""

    def __init__(self, connection_manager, db_manager):
        super().__init__()
        self.conn_mgr = connection_manager
        self.db_mgr = db_manager
        self.bridge = VehicleSignalBridge()

        self.setWindowTitle("PX4 Setup Hub — Ground Control & Calibration Platform")
        self.resize(1280, 840)
        self.setMinimumSize(1024, 680)
        self.setStyleSheet(DARK_THEME_QSS)

        self._init_ui()
        self._wire_signals()

    def _init_ui(self):
        root_widget = QWidget()
        self.setCentralWidget(root_widget)
        main_layout = QHBoxLayout(root_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(0, 16, 0, 16)
        s_layout.setSpacing(4)

        # Brand Title
        brand_frame = QFrame()
        b_layout = QVBoxLayout(brand_frame)
        b_layout.setContentsMargins(16, 0, 16, 16)
        b_layout.setSpacing(2)

        lbl_logo = QLabel("PX4 SETUP HUB")
        lbl_logo.setStyleSheet("font-size: 16px; font-weight: 800; color: #38bdf8; letter-spacing: 1px;")
        lbl_brand_sub = QLabel("GROUND CONTROL & CONFIG")
        lbl_brand_sub.setStyleSheet("font-size: 9px; font-weight: 600; color: #64748b; letter-spacing: 0.5px;")

        b_layout.addWidget(lbl_logo)
        b_layout.addWidget(lbl_brand_sub)
        s_layout.addWidget(brand_frame)

        # Navigation Buttons
        self.nav_buttons = []
        self.btn_dashboard = self._add_nav_btn(s_layout, "Dashboard", 0, True)
        self.btn_connection = self._add_nav_btn(s_layout, "Connection", 1)
        self.btn_calibration = self._add_nav_btn(s_layout, "Calibration Center", 2)
        self.btn_parameters = self._add_nav_btn(s_layout, "Parameters", 3)
        self.btn_telemetry = self._add_nav_btn(s_layout, "Live Telemetry", 4)
        self.btn_preflight = self._add_nav_btn(s_layout, "Preflight Verifier", 5)

        s_layout.addStretch()

        # Version footer
        lbl_ver = QLabel("v1.0.0-alpha • PX4 v1.15+")
        lbl_ver.setStyleSheet("color: #475569; font-size: 10px; padding: 0 16px;")
        s_layout.addWidget(lbl_ver)

        main_layout.addWidget(sidebar)

        # 2. Right Content Area (Top Bar + Stacked Views)
        content_frame = QFrame()
        c_layout = QVBoxLayout(content_frame)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(0)

        # Persistent Top Bar
        top_bar = QFrame()
        top_bar.setObjectName("TopHeader")
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(20, 10, 20, 10)
        tb_layout.setSpacing(16)

        self.lbl_hdr_vehicle = QLabel("No Vehicle")
        self.lbl_hdr_vehicle.setStyleSheet("font-size: 13px; font-weight: 700; color: #f8fafc;")

        self.hdr_conn_badge = StatusBadge(HealthStatus.FAIL)
        self.lbl_hdr_mode = QLabel("Mode: DISARMED")
        self.lbl_hdr_mode.setStyleSheet("font-size: 12px; font-weight: 600; color: #94a3b8;")

        self.lbl_hdr_battery = QLabel("Bat: --")
        self.lbl_hdr_battery.setStyleSheet("font-size: 12px; font-weight: 600; color: #38bdf8;")

        self.lbl_hdr_gps = QLabel("GPS: No Fix")
        self.lbl_hdr_gps.setStyleSheet("font-size: 12px; font-weight: 600; color: #94a3b8;")

        tb_layout.addWidget(self.lbl_hdr_vehicle)
        tb_layout.addWidget(self.hdr_conn_badge)
        tb_layout.addStretch()
        tb_layout.addWidget(self.lbl_hdr_mode)
        tb_layout.addWidget(self.lbl_hdr_battery)
        tb_layout.addWidget(self.lbl_hdr_gps)
        c_layout.addWidget(top_bar)

        # Views Stack
        self.stack = QStackedWidget()
        self.view_dashboard = DashboardView(self.conn_mgr)
        self.view_connection = ConnectionView(self.conn_mgr)
        self.view_calibration = CalibrationView(self.conn_mgr)
        self.view_parameters = ParametersView(self.conn_mgr, self.db_mgr)
        self.view_telemetry = TelemetryView()
        self.view_preflight = PreflightView(self.conn_mgr, self.db_mgr)

        self.stack.addWidget(self.view_dashboard)
        self.stack.addWidget(self.view_connection)
        self.stack.addWidget(self.view_calibration)
        self.stack.addWidget(self.view_parameters)
        self.stack.addWidget(self.view_telemetry)
        self.stack.addWidget(self.view_preflight)

        c_layout.addWidget(self.stack, 1)
        main_layout.addWidget(content_frame, 1)

    def _add_nav_btn(self, layout, text: str, index: int, checked: bool = False) -> QToolButton:
        btn = QToolButton()
        btn.setObjectName("NavButton")
        btn.setText(text)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.clicked.connect(lambda: self._switch_view(index))
        layout.addWidget(btn)
        self.nav_buttons.append(btn)
        return btn

    def _switch_view(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def _wire_signals(self):
        # Bridge events to main UI
        self.bridge.state_changed.connect(self._on_state_changed)
        self.bridge.telemetry_updated.connect(self._on_telemetry_updated)
        self.bridge.param_received.connect(self._on_param_received)
        self.bridge.calibration_progress.connect(self._on_calibration_progress)
        self.bridge.text_message.connect(self._on_text_message)

        # Hook into ConnectionManager whenever active_vehicle connects
        orig_connect = self.conn_mgr.connect

        def wrapped_connect(conn_type, endpoint, baud=115200):
            res = orig_connect(conn_type, endpoint, baud=baud)
            if res and self.conn_mgr.active_vehicle:
                v = self.conn_mgr.active_vehicle
                v.on_state_changed = lambda s, m: self.bridge.state_changed.emit(s, m)
                v.on_telemetry_updated = lambda t: self.bridge.telemetry_updated.emit(t)
                v.on_parameter_received = lambda p: self.bridge.param_received.emit(p)
                v.on_calibration_progress = lambda c: self.bridge.calibration_progress.emit(c)
                v.on_text_message = lambda sev, msg: self.bridge.text_message.emit(sev, msg)

                # Initialize parameter view with vehicle params if already cached
                if v.parameters:
                    self.view_parameters.set_parameters(v.parameters)
            return res

        self.conn_mgr.connect = wrapped_connect

    def _on_state_changed(self, state: ConnectionState, message: str):
        self.view_connection.update_state(state, message)
        v = self.conn_mgr.active_vehicle
        if state == ConnectionState.CONNECTED and v:
            self.lbl_hdr_vehicle.setText(v.vehicle_info.board_name)
            self.hdr_conn_badge.set_status(HealthStatus.PASS)
            self.view_dashboard.update_vehicle_info(v.vehicle_info)
            if v.parameters:
                self.view_parameters.set_parameters(v.parameters)
        else:
            self.lbl_hdr_vehicle.setText("No Vehicle")
            self.hdr_conn_badge.set_status(HealthStatus.FAIL)
            self.view_dashboard.update_vehicle_info(VehicleInfo(connected=False))

    def _on_telemetry_updated(self, t: TelemetryData):
        self.view_dashboard.update_telemetry(t)
        self.view_telemetry.update_telemetry(t)

        self.lbl_hdr_mode.setText(f"{t.arming_status.value} • {t.flight_mode.value}")
        self.lbl_hdr_battery.setText(f"{t.battery_voltage_v:.1f}V ({t.battery_remaining_pct:.0f}%)")
        self.lbl_hdr_gps.setText(f"GPS: {t.gps_fix_type} ({t.gps_satellites}s)")

        # Evaluate preflight continuously
        v = self.conn_mgr.active_vehicle
        if v:
            checks, score, overall = PreflightEvaluator.evaluate(
                v.vehicle_info, t, v.sensors, v.parameters
            )
            self.view_dashboard.update_evaluation(checks, score, overall)
            self.view_preflight.update_evaluation(checks, score, overall)

    def _on_param_received(self, p: Parameter):
        self.view_parameters.update_parameter(p)

    def _on_calibration_progress(self, prog: CalibrationProgress):
        self.view_calibration.update_progress(prog)

    def _on_text_message(self, severity: int, text: str):
        self.view_connection.log(f"[MAVLink Sev:{severity}] {text}")
