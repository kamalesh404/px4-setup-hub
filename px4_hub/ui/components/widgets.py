"""
Reusable Custom UI Components for PX4 Setup Hub.
Includes StatusBadge, MetricCard, ChecklistRow, and HorizonWidget.
"""
import math
from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygonF
from ...core.enums import HealthStatus


class StatusBadge(QLabel):
    """Badge pill widget explicitly showing PASS, WARNING, FAIL, or UNKNOWN."""

    def __init__(self, status: HealthStatus = HealthStatus.UNKNOWN, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.set_status(status)

    def set_status(self, status: HealthStatus):
        self.status = status
        self.setText(f" {status.value} ")
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {status.badge_bg};
                color: {status.color};
                font-weight: 700;
                font-size: 11px;
                border: 1px solid {status.color};
                border-radius: 4px;
                padding: 2px 6px;
                min-width: 60px;
            }}
        """)


class MetricCard(QFrame):
    """Clean engineering metrics card displaying value, unit, and sub-label."""

    def __init__(self, label: str, value: str = "--", unit: str = "", parent=None):
        super().__init__(parent)
        self.setProperty("class", "Card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        self.lbl_title = QLabel(label.upper())
        self.lbl_title.setObjectName("MetricLabel")

        self.val_layout = QHBoxLayout()
        self.val_layout.setSpacing(4)

        self.lbl_val = QLabel(value)
        self.lbl_val.setObjectName("MetricValue")

        self.lbl_unit = QLabel(unit)
        self.lbl_unit.setStyleSheet("color: #64748b; font-size: 13px; font-weight: 500; padding-bottom: 3px;")
        self.lbl_unit.setAlignment(Qt.AlignBottom)

        self.val_layout.addWidget(self.lbl_val)
        self.val_layout.addWidget(self.lbl_unit)
        self.val_layout.addStretch()

        self.lbl_subtext = QLabel("")
        self.lbl_subtext.setStyleSheet("color: #94a3b8; font-size: 11px;")

        layout.addWidget(self.lbl_title)
        layout.addLayout(self.val_layout)
        layout.addWidget(self.lbl_subtext)

    def set_value(self, val: str, subtext: str = ""):
        self.lbl_val.setText(val)
        if subtext:
            self.lbl_subtext.setText(subtext)


class ChecklistRow(QFrame):
    """Row in the Preflight checklist displaying item name, status badge, and evidence text."""

    def __init__(self, title: str, category: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 6px;
                margin-bottom: 4px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-weight: 600; font-size: 13px; color: #f1f5f9;")

        self.lbl_evidence = QLabel("Awaiting telemetry evidence...")
        self.lbl_evidence.setStyleSheet("font-size: 11px; color: #94a3b8;")

        info_layout.addWidget(self.lbl_title)
        info_layout.addWidget(self.lbl_evidence)

        self.badge = StatusBadge(HealthStatus.UNKNOWN)

        layout.addLayout(info_layout, 1)
        layout.addWidget(self.badge)

    def update_check(self, status: HealthStatus, evidence: str, explanation: str = ""):
        self.badge.set_status(status)
        text = f"{evidence} — {explanation}" if explanation else evidence
        self.lbl_evidence.setText(text)


class ArtificialHorizon(QWidget):
    """Dynamic 2D Artificial Horizon showing roll angle and pitch ladder."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.roll = 0.0
        self.pitch = 0.0
        self.setMinimumSize(180, 180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_attitude(self, roll: float, pitch: float):
        self.roll = roll
        self.pitch = pitch
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        center_x = w / 2.0
        center_y = h / 2.0
        radius = min(w, h) / 2.0 - 8

        # Draw outer bezel
        painter.setPen(QPen(QColor("#334155"), 2))
        painter.setBrush(QBrush(QColor("#080c14")))
        painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

        # Clip to circle
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addEllipse(QPointF(center_x, center_y), radius - 2, radius - 2)
        painter.setClipPath(path)

        # Rotate according to roll angle
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(-self.roll)

        # Sky and Ground division
        pitch_offset = (self.pitch / 90.0) * (radius * 1.5)
        painter.translate(0, pitch_offset)

        # Sky (Deep slate blue)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#0369a1")))
        painter.drawRect(QRectF(-radius * 2, -radius * 2, radius * 4, radius * 2))

        # Ground (Earthy charcoal brown)
        painter.setBrush(QBrush(QColor("#3b2f2f")))
        painter.drawRect(QRectF(-radius * 2, 0, radius * 4, radius * 2))

        # Horizon line
        painter.setPen(QPen(QColor("#f8fafc"), 2))
        painter.drawLine(QPointF(-radius * 2, 0), QPointF(radius * 2, 0))

        # Pitch ladder ticks (±10°, ±20°)
        painter.setPen(QPen(QColor("#f8fafc"), 1))
        for deg in [-20, -10, 10, 20]:
            y_tick = -(deg / 90.0) * (radius * 1.5)
            tick_w = 20 if abs(deg) == 10 else 35
            painter.drawLine(QPointF(-tick_w, y_tick), QPointF(tick_w, y_tick))

        painter.restore()

        # Fixed Aircraft Crosshair Symbol
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#facc15"), 3))  # Yellow symbol
        painter.drawLine(QPointF(center_x - 30, center_y), QPointF(center_x - 10, center_y))
        painter.drawLine(QPointF(center_x + 10, center_y), QPointF(center_x + 30, center_y))
        painter.drawLine(QPointF(center_x - 10, center_y), QPointF(center_x - 10, center_y + 8))
        painter.drawLine(QPointF(center_x + 10, center_y), QPointF(center_x + 10, center_y + 8))
        painter.drawEllipse(QPointF(center_x, center_y), 3, 3)
