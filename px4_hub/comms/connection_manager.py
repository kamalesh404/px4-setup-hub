"""
Connection Manager for PX4 Setup Hub.
Orchestrates port scanning, hardware detection, vehicle connection lifecycle, and bridge signals.
"""
from typing import Dict, List, Optional, Tuple, Any
import serial.tools.list_ports
from .base import BaseVehicle
from .mock_vehicle import MockVehicle
from .mavlink_comm import MavlinkVehicle
from ..core.enums import ConnectionState, ConnectionType


class ConnectionManager:
    """Manages active connection, port discovery, and vehicle interface dispatch."""

    def __init__(self):
        self.active_vehicle: Optional[BaseVehicle] = None
        self.connection_type: ConnectionType = ConnectionType.MOCK
        self.active_endpoint: str = ""
        self.active_baud: int = 115200

    @staticmethod
    def list_serial_ports() -> List[Dict[str, str]]:
        """Scan system COM ports and flag known flight controller vendor/product IDs."""
        ports = []
        for port in serial.tools.list_ports.comports():
            # Check for STM32, Pixhawk, PX4, FTDI, CP210x, CH340
            desc = port.description or ""
            hwid = port.hwid or ""
            is_fc = any(kw in (desc + hwid).lower() for kw in [
                "stm32", "px4", "pixhawk", "microair", "holybro", "cuav", "fmu", "virtual com"
            ])
            ports.append({
                "device": port.device,
                "description": desc,
                "hwid": hwid,
                "is_likely_fc": is_fc
            })
        return ports

    def connect(self, conn_type: ConnectionType, endpoint: str, baud: int = 115200) -> bool:
        """Disconnect current session and connect to chosen vehicle endpoint."""
        self.disconnect()

        self.connection_type = conn_type
        self.active_endpoint = endpoint
        self.active_baud = baud

        if conn_type == ConnectionType.MOCK:
            vehicle = MockVehicle()
            success = vehicle.connect(endpoint)
        else:
            vehicle = MavlinkVehicle()
            success = vehicle.connect(endpoint, baud=baud)

        if success:
            self.active_vehicle = vehicle
            return True
        return False

    def disconnect(self):
        if self.active_vehicle:
            self.active_vehicle.disconnect()
            self.active_vehicle = None

    @property
    def is_connected(self) -> bool:
        return self.active_vehicle is not None and self.active_vehicle.state == ConnectionState.CONNECTED

    @property
    def current_state(self) -> ConnectionState:
        if not self.active_vehicle:
            return ConnectionState.DISCONNECTED
        return self.active_vehicle.state
