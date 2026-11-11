"""
Abstract Vehicle Interface for PX4 Setup Hub.
Defines required telemetry streams, parameter transactions, calibration triggers, and state signals.
"""
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Any
from ..core.enums import ConnectionState, HealthStatus, SensorType, CalibrationType
from ..core.models import VehicleInfo, TelemetryData, SensorStatus, Parameter, CalibrationProgress


class BaseVehicle(ABC):
    """Abstract base class for connected real or mock PX4 vehicles."""

    def __init__(self):
        self.state: ConnectionState = ConnectionState.DISCONNECTED
        self.vehicle_info: VehicleInfo = VehicleInfo()
        self.telemetry: TelemetryData = TelemetryData()
        self.sensors: Dict[SensorType, SensorStatus] = {}
        self.parameters: Dict[str, Parameter] = {}
        
        # Callbacks registered by managers/UI
        self.on_state_changed: Optional[Callable[[ConnectionState, str], None]] = None
        self.on_telemetry_updated: Optional[Callable[[TelemetryData], None]] = None
        self.on_sensor_status_updated: Optional[Callable[[SensorStatus], None]] = None
        self.on_parameter_received: Optional[Callable[[Parameter], None]] = None
        self.on_calibration_progress: Optional[Callable[[CalibrationProgress], None]] = None
        self.on_text_message: Optional[Callable[[int, str], None]] = None

    @abstractmethod
    def connect(self, endpoint: str, **kwargs) -> bool:
        """Connect to vehicle via serial port, UDP address, TCP or mock."""
        pass

    @abstractmethod
    def disconnect(self):
        """Cleanly close connection and background listener threads."""
        pass

    @abstractmethod
    def request_parameters(self):
        """Trigger parameter read from vehicle."""
        pass

    @abstractmethod
    def set_parameter(self, name: str, value: Any) -> bool:
        """Write parameter value to vehicle."""
        pass

    @abstractmethod
    def start_calibration(self, cal_type: CalibrationType):
        """Initiate sensor calibration sequence."""
        pass

    @abstractmethod
    def cancel_calibration(self):
        """Cancel ongoing calibration."""
        pass

    @abstractmethod
    def reboot_autopilot(self):
        """Send MAVLink reboot command to autopilot."""
        pass
