"""
Live Telemetry Charts & Dynamics View for PX4 Setup Hub.
Displays real-time rolling strip charts for Attitude, Altitude, and Power.
"""
from collections import deque
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame
)
from PySide6.QtCore import Qt
from ...core.models import TelemetryData

try:
    import pyqtgraph as pg
    # Set dark theme for pyqtgraph
    pg.setConfigOption('background', '#0a0f1d')
    pg.setConfigOption('foreground', '#94a3b8')
    HAS_PG = True
except ImportError:
    HAS_PG = False


class TelemetryView(QWidget):
    """Real-time Telemetry Visualization View."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_points = 150
        self.timestamps = deque(maxlen=self.max_points)
        self.roll_data = deque(maxlen=self.max_points)
        self.pitch_data = deque(maxlen=self.max_points)
        self.yaw_data = deque(maxlen=self.max_points)
        self.alt_data = deque(maxlen=self.max_points)
        self.volt_data = deque(maxlen=self.max_points)
        self.curr_data = deque(maxlen=self.max_points)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header Card
        header = QFrame()
        header.setProperty("class", "Card")
        h_layout = QVBoxLayout(header)
        lbl_title = QLabel("LIVE TELEMETRY DYNAMICS & SENSORY PLOTS")
        lbl_title.setObjectName("Title")
        lbl_sub = QLabel("Real-time attitude rates, altitude tracking, and power consumption telemetry.")
        lbl_sub.setObjectName("Subtitle")
        h_layout.addWidget(lbl_title)
        h_layout.addWidget(lbl_sub)
        layout.addWidget(header)

        if not HAS_PG:
            lbl_err = QLabel("PyQtGraph is not loaded. Plots disabled.")
            layout.addWidget(lbl_err)
            return

        # Plots Grid
        grid = QGridLayout()
        grid.setSpacing(12)

        # 1. Attitude Plot (Roll & Pitch)
        self.plot_att = pg.PlotWidget(title="Attitude Angles (°)")
        self.plot_att.showGrid(x=True, y=True, alpha=0.2)
        self.curve_roll = self.plot_att.plot(pen=pg.mkPen('#38bdf8', width=2), name="Roll")
        self.curve_pitch = self.plot_att.plot(pen=pg.mkPen('#f43f5e', width=2), name="Pitch")
        grid.addWidget(self.plot_att, 0, 0)

        # 2. Heading Plot
        self.plot_yaw = pg.PlotWidget(title="Yaw / Compass Heading (°)")
        self.plot_yaw.showGrid(x=True, y=True, alpha=0.2)
        self.curve_yaw = self.plot_yaw.plot(pen=pg.mkPen('#eab308', width=2), name="Yaw")
        grid.addWidget(self.plot_yaw, 0, 1)

        # 3. Altitude Plot
        self.plot_alt = pg.PlotWidget(title="Altitude Relative (m)")
        self.plot_alt.showGrid(x=True, y=True, alpha=0.2)
        self.curve_alt = self.plot_alt.plot(pen=pg.mkPen('#22c55e', width=2), name="Alt")
        grid.addWidget(self.plot_alt, 1, 0)

        # 4. Battery Voltage & Current Plot
        self.plot_power = pg.PlotWidget(title="Battery Voltage (V) & Current (A)")
        self.plot_power.showGrid(x=True, y=True, alpha=0.2)
        self.curve_volt = self.plot_power.plot(pen=pg.mkPen('#a855f7', width=2), name="Volts")
        self.curve_curr = self.plot_power.plot(pen=pg.mkPen('#f97316', width=2), name="Amps")
        grid.addWidget(self.plot_power, 1, 1)

        layout.addLayout(grid, 1)

    def update_telemetry(self, t: TelemetryData):
        if not HAS_PG:
            return

        self.roll_data.append(t.roll_deg)
        self.pitch_data.append(t.pitch_deg)
        self.yaw_data.append(t.yaw_deg)
        self.alt_data.append(t.altitude_relative_m)
        self.volt_data.append(t.battery_voltage_v)
        self.curr_data.append(t.battery_current_a)

        x = list(range(len(self.roll_data)))

        self.curve_roll.setData(x, list(self.roll_data))
        self.curve_pitch.setData(x, list(self.pitch_data))
        self.curve_yaw.setData(x, list(self.yaw_data))
        self.curve_alt.setData(x, list(self.alt_data))
        self.curve_volt.setData(x, list(self.volt_data))
        self.curve_curr.setData(x, list(self.curr_data))
