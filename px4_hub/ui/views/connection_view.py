"""
Connection View for PX4 Setup Hub.
Manages USB serial ports, PX4 SITL UDP, TCP, and Mock Vehicle simulations.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QComboBox, QLineEdit, QTextEdit, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt
from ..components.widgets import StatusBadge
from ...core.enums import ConnectionState, ConnectionType, HealthStatus


class ConnectionView(QWidget):
    """Configuration pane for vehicle connectivity."""

    def __init__(self, connection_manager, parent=None):
        super().__init__(parent)
        self.conn_mgr = connection_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 1. Header Card
        header = QFrame()
        header.setProperty("class", "Card")
        h_layout = QVBoxLayout(header)
        lbl_title = QLabel("VEHICLE CONNECTION MANAGER")
        lbl_title.setObjectName("Title")
        lbl_sub = QLabel("Select communication link to connect your flight controller or simulation environment.")
        lbl_sub.setObjectName("Subtitle")
        h_layout.addWidget(lbl_title)
        h_layout.addWidget(lbl_sub)
        layout.addWidget(header)

        # 2. Connection Settings Card
        settings_card = QFrame()
        settings_card.setProperty("class", "Card")
        s_layout = QVBoxLayout(settings_card)
        s_layout.setSpacing(16)

        # Mode Selection Radios
        radio_layout = QHBoxLayout()
        self.btn_group = QButtonGroup(self)

        self.rb_serial = QRadioButton("USB / Serial")
        self.rb_udp = QRadioButton("UDP (PX4 SITL / Network)")
        self.rb_tcp = QRadioButton("TCP Client")
        self.rb_mock = QRadioButton("Mock Vehicle (Development Simulator)")
        self.rb_mock.setChecked(True)

        self.btn_group.addButton(self.rb_serial, 0)
        self.btn_group.addButton(self.rb_udp, 1)
        self.btn_group.addButton(self.rb_tcp, 2)
        self.btn_group.addButton(self.rb_mock, 3)

        radio_layout.addWidget(self.rb_serial)
        radio_layout.addWidget(self.rb_udp)
        radio_layout.addWidget(self.rb_tcp)
        radio_layout.addWidget(self.rb_mock)
        radio_layout.addStretch()
        s_layout.addLayout(radio_layout)

        # Controls Grid
        grid = QGridLayout()
        grid.setSpacing(12)

        # Serial Controls
        self.lbl_port = QLabel("Serial Port:")
        self.combo_ports = QComboBox()
        self.btn_refresh_ports = QPushButton("Refresh Ports")
        self.btn_refresh_ports.clicked.connect(self.scan_ports)

        self.lbl_baud = QLabel("Baud Rate:")
        self.combo_baud = QComboBox()
        self.combo_baud.addItems(["115200", "57600", "921600", "460800", "230400", "38400"])

        grid.addWidget(self.lbl_port, 0, 0)
        grid.addWidget(self.combo_ports, 0, 1)
        grid.addWidget(self.btn_refresh_ports, 0, 2)
        grid.addWidget(self.lbl_baud, 1, 0)
        grid.addWidget(self.combo_baud, 1, 1)

        # Network Controls (UDP/TCP)
        self.lbl_endpoint = QLabel("Network Target:")
        self.txt_endpoint = QLineEdit("udp:127.0.0.1:14540")
        grid.addWidget(self.lbl_endpoint, 2, 0)
        grid.addWidget(self.txt_endpoint, 2, 1, 1, 2)

        s_layout.addLayout(grid)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_connect = QPushButton("Connect Vehicle")
        self.btn_connect.setObjectName("PrimaryButton")
        self.btn_connect.clicked.connect(self._handle_connect_toggle)

        self.status_badge = StatusBadge(HealthStatus.FAIL)
        self.lbl_status = QLabel("DISCONNECTED")
        self.lbl_status.setStyleSheet("font-weight: 600; color: #94a3b8;")

        btn_layout.addWidget(self.btn_connect)
        btn_layout.addSpacing(16)
        btn_layout.addWidget(self.status_badge)
        btn_layout.addWidget(self.lbl_status)
        btn_layout.addStretch()
        s_layout.addLayout(btn_layout)

        layout.addWidget(settings_card)

        # 3. Connection Logs Terminal Card
        log_card = QFrame()
        log_card.setProperty("class", "Card")
        l_layout = QVBoxLayout(log_card)
        lbl_log = QLabel("CONNECTION & MAVLINK ACTIVITY LOG")
        lbl_log.setObjectName("SectionHeading")

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("""
            QTextEdit {
                background-color: #080c14;
                color: #38bdf8;
                font-family: Consolas, monospace;
                font-size: 11px;
                border: 1px solid #1e293b;
                border-radius: 4px;
            }
        """)

        l_layout.addWidget(lbl_log)
        l_layout.addWidget(self.txt_log)
        layout.addWidget(log_card, 1)

        # Hook toggles
        self.rb_serial.toggled.connect(self._update_fields)
        self.rb_udp.toggled.connect(self._update_fields)
        self.rb_tcp.toggled.connect(self._update_fields)
        self.rb_mock.toggled.connect(self._update_fields)

        self.scan_ports()
        self._update_fields()

    def scan_ports(self):
        self.combo_ports.clear()
        ports = self.conn_mgr.list_serial_ports()
        if not ports:
            self.combo_ports.addItem("No COM ports detected", "")
        else:
            for p in ports:
                tag = " (Likely Flight Controller)" if p["is_likely_fc"] else ""
                label = f"{p['device']} - {p['description']}{tag}"
                self.combo_ports.addItem(label, p["device"])
        self.log("[SYSTEM] Port scan complete.")

    def _update_fields(self):
        is_serial = self.rb_serial.isChecked()
        is_net = self.rb_udp.isChecked() or self.rb_tcp.isChecked()

        self.combo_ports.setEnabled(is_serial)
        self.combo_baud.setEnabled(is_serial)
        self.btn_refresh_ports.setEnabled(is_serial)
        self.txt_endpoint.setEnabled(is_net)

        if self.rb_udp.isChecked():
            self.txt_endpoint.setText("udp:127.0.0.1:14540")
        elif self.rb_tcp.isChecked():
            self.txt_endpoint.setText("tcp:127.0.0.1:5760")
        elif self.rb_mock.isChecked():
            self.txt_endpoint.setText("mock://px4-microair-h7")

    def _handle_connect_toggle(self):
        if self.conn_mgr.is_connected:
            self.conn_mgr.disconnect()
            self.log("[SYSTEM] Connection closed by user.")
            self._update_status_display(ConnectionState.DISCONNECTED, "Disconnected")
            return

        # Determine target
        if self.rb_mock.isChecked():
            target_type = ConnectionType.MOCK
            endpoint = "mock://px4-microair-h7"
            baud = 115200
        elif self.rb_serial.isChecked():
            target_type = ConnectionType.SERIAL
            endpoint = self.combo_ports.currentData()
            if not endpoint:
                self.log("[ERROR] No valid serial COM port selected.")
                return
            baud = int(self.combo_baud.currentText())
        elif self.rb_udp.isChecked():
            target_type = ConnectionType.UDP_SITL
            endpoint = self.txt_endpoint.text().strip()
            baud = 115200
        else:
            target_type = ConnectionType.TCP
            endpoint = self.txt_endpoint.text().strip()
            baud = 115200

        self.log(f"[CONNECTING] Target: {endpoint} ({target_type.value})...")
        success = self.conn_mgr.connect(target_type, endpoint, baud)
        if not success:
            self.log(f"[ERROR] Failed to initiate connection to {endpoint}")

    def update_state(self, state: ConnectionState, message: str):
        self._update_status_display(state, message)
        self.log(f"[{state.value}] {message}")

    def _update_status_display(self, state: ConnectionState, msg: str):
        if state == ConnectionState.CONNECTED:
            self.status_badge.set_status(HealthStatus.PASS)
            self.lbl_status.setText("CONNECTED")
            self.lbl_status.setStyleSheet("font-weight: 700; color: #22c55e;")
            self.btn_connect.setText("Disconnect Vehicle")
            self.btn_connect.setObjectName("DangerButton")
        elif state == ConnectionState.CONNECTING:
            self.status_badge.set_status(HealthStatus.WARNING)
            self.lbl_status.setText("CONNECTING...")
            self.lbl_status.setStyleSheet("font-weight: 700; color: #eab308;")
        else:
            self.status_badge.set_status(HealthStatus.FAIL)
            self.lbl_status.setText("DISCONNECTED")
            self.lbl_status.setStyleSheet("font-weight: 600; color: #94a3b8;")
            self.btn_connect.setText("Connect Vehicle")
            self.btn_connect.setObjectName("PrimaryButton")

        # Refresh styling
        self.btn_connect.style().unpolish(self.btn_connect)
        self.btn_connect.style().polish(self.btn_connect)

    def log(self, text: str):
        import datetime
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.txt_log.append(f"[{now}] {text}")
