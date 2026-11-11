"""
Core enumerations for PX4 Setup Hub.
"""
from enum import Enum, auto


class HealthStatus(str, Enum):
    """
    Evidence-backed health status for sensors, subsystems, and preflight checks.
    Never assume PASS without telemetry confirmation.
    """
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"

    @property
    def color(self) -> str:
        if self == HealthStatus.PASS:
            return "#22c55e"  # Green
        elif self == HealthStatus.WARNING:
            return "#eab308"  # Yellow/Amber
        elif self == HealthStatus.FAIL:
            return "#ef4444"  # Red
        return "#94a3b8"      # Slate gray / Unknown

    @property
    def badge_bg(self) -> str:
        if self == HealthStatus.PASS:
            return "#14532d"
        elif self == HealthStatus.WARNING:
            return "#713f12"
        elif self == HealthStatus.FAIL:
            return "#7f1d1d"
        return "#1e293b"


class ConnectionState(str, Enum):
    """Connection states for vehicle communication manager."""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"


class ConnectionType(str, Enum):
    """Supported connection transport types."""
    SERIAL = "USB / Serial"
    UDP_SITL = "UDP (SITL / Network)"
    TCP = "TCP Client"
    MOCK = "Mock Vehicle (Simulation / Dev)"


class FlightMode(str, Enum):
    """PX4 standard flight modes."""
    UNKNOWN = "UNKNOWN"
    MANUAL = "MANUAL"
    STABILIZED = "STABILIZED"
    ALTCTL = "ALTITUDE"
    POSCTL = "POSITION"
    OFFBOARD = "OFFBOARD"
    AUTO_LOITER = "HOLD"
    AUTO_RTL = "RTL"
    AUTO_LAND = "LAND"
    AUTO_TAKEOFF = "TAKEOFF"
    AUTO_MISSION = "MISSION"
    ACRO = "ACRO"
    RATTITUDE = "RATTITUDE"


class ArmingStatus(str, Enum):
    """Vehicle arming state."""
    DISARMED = "DISARMED"
    ARMED = "ARMED"
    ARMING = "ARMING..."
    DISARMING = "DISARMING..."


class SensorType(str, Enum):
    """Standard onboard sensor subsystems."""
    GYRO = "Gyroscope"
    ACCEL = "Accelerometer"
    MAG = "Compass / Magnetometer"
    BARO = "Barometer"
    GPS = "GPS / GNSS"
    BATTERY = "Battery & Power"
    RC = "RC Receiver"
    AIRSPEED = "Airspeed Sensor"
    DISTANCE = "Distance Sensor / Lidar"


class CalibrationType(str, Enum):
    """Sensor calibration routines."""
    GYROSCOPE = "Gyroscope"
    ACCELEROMETER = "Accelerometer"
    COMPASS = "Compass (Magnetometer)"
    LEVEL_HORIZON = "Level Horizon"
    RC_RADIO = "RC Radio Transmitter"


class CalibrationStep(str, Enum):
    """6-point orientation calibration steps."""
    DETECTING = "Detecting..."
    NOSE_DOWN = "Nose Down"
    TAIL_DOWN = "Tail Down"
    LEFT_SIDE = "Left Side"
    RIGHT_SIDE = "Right Side"
    ROTATION_NORMAL = "Level (Top Up)"
    ROTATION_UPSIDE_DOWN = "Inverted (Upside Down)"
    ROTATING = "Rotate 360°"
    COMPLETE = "Calibration Complete"
    FAILED = "Calibration Failed"
