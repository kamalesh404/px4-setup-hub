# PX4 Setup Hub

An all-in-one, unified desktop ground control and vehicle configuration platform for PX4 Autopilot flight controllers.

Built with **Python 3.11+**, **PySide6**, **pymavlink**, and **PyQtGraph**. Designed with an aerospace engineering dark aesthetic and an **evidence-backed** preflight verification system.

---

## Key Features

1. **Evidence-Backed Preflight Verifier**:
   - Every status check is derived directly from vehicle telemetry and parameters.
   - Strictly distinguishes `PASS`, `WARNING`, `FAIL`, and `UNKNOWN`.
   - Never assumes health without telemetry confirmation.
   - Evaluates firmware verification, airframe configuration (`SYS_AUTOSTART`), gyroscope bias, 6-axis accelerometer calibration, 360° magnetometer/compass sphere-fit, GPS satellite density and HDOP, and battery cell health.

2. **Vehicle Connection Manager**:
   - **USB / Serial**: Automatic flight controller detection (STM32, Pixhawk, MicroAir H7, Holybro, CUAV).
   - **UDP (PX4 SITL / Network)**: Connects to Gazebo, jMAVSim, or local network telemetry (`udp:127.0.0.1:14540` or `udp:0.0.0.0:14550`).
   - **TCP Client**: Direct TCP streaming (`tcp:127.0.0.1:5760`).
   - **Mock Vehicle Simulator**: Full offline development vehicle simulating a MicroAir H7 AIO V4 with HGLRC M10 GPS for development and testing without hardware.

3. **Sensor Calibration Center**:
   - Step-by-step interactive wizards for:
     * Gyroscope (static zero-bias calibration)
     * Accelerometer (6-point orientation calibration)
     * Magnetometer / Compass (360° spherical rotation)
     * Level Horizon (zero pitch and roll reference)
   - Orientation pills showing completed and pending steps.

4. **PX4 Parameter Manager**:
   - Fast, searchable table with group filtering (Commander, Sensors, Battery, Estimator, Rate Control, Safety, Actuators).
   - Safe modification dialog with allowable min/max range enforcement.
   - Reboot warnings for parameters requiring autopilot restart.
   - Local SQLite snapshot backup and restore.
   - `.params` file import and export.

5. **Live Telemetry & Strip Charts**:
   - Real-time 2D artificial horizon indicator with roll bank and pitch ladder.
   - Multi-axis strip charts for attitude rates, yaw heading, altitude, and battery voltage/current.

---

## Hardware Compatibility Profile

- **Primary Target**: MicroAir H7 AIO V4 (STM32H743) + HGLRC M10 GPS (QMC5883L compass)
- **Standard Boards**: Pixhawk 6C, Pixhawk 6X, Holybro Kakute, CUAV V5+, PX4 FMU-v5 / FMU-v6X
- **SITL Autopilots**: PX4 Autopilot v1.14+, v1.15+

---

## Directory Structure

```
px4-setup-hub/
├── px4_hub/
│   ├── app.py                     # Application entry point & Qt lifecycle
│   ├── core/
│   │   ├── enums.py               # HealthStatus, ConnectionState, FlightMode
│   │   ├── models.py              # TelemetryData, VehicleInfo, Parameter
│   │   └── database.py            # SQLite database & backup manager
│   ├── comms/
│   │   ├── base.py                # Abstract Base Vehicle interface
│   │   ├── mavlink_comm.py        # pymavlink Serial/UDP/TCP async worker
│   │   ├── mock_vehicle.py        # MicroAir H7 / SITL simulator
│   │   └── connection_manager.py  # Port scanning and connection coordinator
│   ├── modules/
│   │   └── preflight/
│   │       └── evaluator.py       # Evidence-backed preflight evaluator
│   └── ui/
│       ├── theme.py               # Dark engineering QSS stylesheet
│       ├── main_window.py         # Root window shell & navigation sidebar
│       ├── components/
│       │   └── widgets.py         # StatusBadge, MetricCard, ChecklistRow, Horizon
│       └── views/
│           ├── dashboard_view.py  # Main Dashboard & setup checklist
│           ├── connection_view.py # USB/UDP/TCP connection controls
│           ├── calibration_view.py# Sensor calibration wizard
│           ├── parameters_view.py # Searchable parameter table & backup
│           ├── telemetry_view.py  # Live PyQtGraph charts
│           └── preflight_view.py  # Detailed preflight diagnostic report
├── tests/
│   ├── test_models.py             # Enums & model validation tests
│   ├── test_mock_vehicle.py       # Simulated telemetry & calibration tests
│   ├── test_preflight_evaluator.py# Preflight evidence & scoring tests
│   └── test_database.py           # SQLite parameter snapshot tests
├── requirements.txt
└── run.py                         # Startup script
```

---

## Quick Start

### 1. Activate Environment & Install Dependencies

```powershell
cd C:\Users\kamal\.gemini\antigravity\scratch\px4-setup-hub
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Run the Application

```powershell
python run.py
```

### 3. Run Automated Tests

```powershell
python -m pytest tests -v
```

### 4. Connect to Vehicle or SITL

- **For Mock Simulation**: Select **Mock Vehicle** in the Connection tab and click **Connect Vehicle**.
- **For PX4 SITL**: Launch PX4 SITL (`make px4_sitl jmavsim` or `gazebo-classic`), select **UDP (PX4 SITL / Network)** at `udp:127.0.0.1:14540`, and click **Connect Vehicle**.
- **For Physical Flight Controller**: Plug your flight controller into USB, click **Refresh Ports**, select the detected COM port, and click **Connect Vehicle**.
