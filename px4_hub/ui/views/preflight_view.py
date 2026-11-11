"""
Preflight Verification View for PX4 Setup Hub.
Displays comprehensive verification checks, failure diagnosis, and report generation.
"""
from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QScrollArea, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from ..components.widgets import StatusBadge
from ...core.enums import HealthStatus
from ...core.models import PreflightCheckItem


class PreflightView(QWidget):
    """Detailed Preflight Verification & Health Diagnostics Screen."""

    def __init__(self, connection_manager, db_manager, parent=None):
        super().__init__(parent)
        self.conn_mgr = connection_manager
        self.db_mgr = db_manager
        self.last_checks: List[PreflightCheckItem] = []
        self.last_score = 0.0
        self.last_overall = HealthStatus.UNKNOWN

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header Card
        header = QFrame()
        header.setProperty("class", "Card")
        h_layout = QVBoxLayout(header)
        lbl_title = QLabel("PREFLIGHT HEALTH & SAFETY VERIFIER")
        lbl_title.setObjectName("Title")
        lbl_sub = QLabel("Evaluates live flight controller telemetry against strict PX4 arming and flight readiness rules.")
        lbl_sub.setObjectName("Subtitle")
        h_layout.addWidget(lbl_title)
        h_layout.addWidget(lbl_sub)
        layout.addWidget(header)

        # Action Bar
        action_bar = QFrame()
        action_bar.setProperty("class", "Card")
        ab_layout = QHBoxLayout(action_bar)
        ab_layout.setContentsMargins(12, 10, 12, 10)

        self.lbl_score_summary = QLabel("System Readiness: 0% [UNKNOWN]")
        self.lbl_score_summary.setStyleSheet("font-size: 15px; font-weight: 700; color: #f8fafc;")

        self.btn_export = QPushButton("Export Diagnostic Report")
        self.btn_export.setObjectName("PrimaryButton")
        self.btn_export.clicked.connect(self._export_report)

        ab_layout.addWidget(self.lbl_score_summary)
        ab_layout.addStretch()
        ab_layout.addWidget(self.btn_export)
        layout.addWidget(action_bar)

        # Scrollable Checks List
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self.container = QWidget()
        self.chk_list_layout = QVBoxLayout(self.container)
        self.chk_list_layout.setContentsMargins(0, 0, 0, 0)
        self.chk_list_layout.setSpacing(10)

        scroll.setWidget(self.container)
        layout.addWidget(scroll, 1)

    def update_evaluation(self, checks: List[PreflightCheckItem], score: float, overall: HealthStatus):
        self.last_checks = checks
        self.last_score = score
        self.last_overall = overall

        self.lbl_score_summary.setText(f"System Readiness: {score:.0f}% [{overall.value}]")
        self.lbl_score_summary.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {overall.color};")

        # Clear existing rows
        while self.chk_list_layout.count():
            item = self.chk_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Build card for each check
        for c in checks:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: #0f172a;
                    border: 1px solid {c.status.color};
                    border-radius: 6px;
                    padding: 12px;
                }}
            """)
            c_layout = QVBoxLayout(card)
            c_layout.setSpacing(4)

            top_row = QHBoxLayout()
            title = QLabel(f"[{c.category}] {c.title}")
            title.setStyleSheet("font-weight: 700; font-size: 14px; color: #f8fafc;")
            badge = StatusBadge(c.status)

            top_row.addWidget(title)
            top_row.addStretch()
            top_row.addWidget(badge)
            c_layout.addLayout(top_row)

            ev_lbl = QLabel(f"Evidence: {c.evidence_value}")
            ev_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #38bdf8;")
            c_layout.addWidget(ev_lbl)

            expl_lbl = QLabel(c.explanation)
            expl_lbl.setStyleSheet("font-size: 12px; color: #cbd5e1;")
            expl_lbl.setWordWrap(True)
            c_layout.addWidget(expl_lbl)

            if c.remediation_hint:
                hint_lbl = QLabel(f"Remediation: {c.remediation_hint}")
                hint_lbl.setStyleSheet("font-size: 11px; color: #facc15; font-style: italic;")
                hint_lbl.setWordWrap(True)
                c_layout.addWidget(hint_lbl)

            self.chk_list_layout.addWidget(card)

        self.chk_list_layout.addStretch()

    def _export_report(self):
        if not self.last_checks:
            QMessageBox.warning(self, "No Report", "No preflight evaluation data available yet.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Export Report", "px4_preflight_report.md", "Markdown (*.md);;Text (*.txt)")
        if not path:
            return

        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report_lines = [
            "# PX4 Setup Hub - Preflight Diagnostic & Verification Report",
            f"Generated: {now}",
            f"Overall Status: **{self.last_overall.value}**",
            f"Readiness Score: **{self.last_score:.1f}%**",
            "",
            "## Verification Checks",
            "| Category | Check | Status | Evidence | Explanation |",
            "|---|---|---|---|---|"
        ]

        for c in self.last_checks:
            report_lines.append(f"| {c.category} | {c.title} | {c.status.value} | {c.evidence_value} | {c.explanation} |")

        report_lines.extend(["", "## Remediation Guidelines"])
        for c in self.last_checks:
            if c.remediation_hint:
                report_lines.append(f"- **{c.title}**: {c.remediation_hint}")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        # Also store to SQLite
        vinfo = self.conn_mgr.active_vehicle.vehicle_info if self.conn_mgr.active_vehicle else None
        uid = vinfo.uid if vinfo else "UNKNOWN"
        self.db_mgr.save_preflight_report(
            uid,
            self.last_overall.value,
            self.last_score,
            {"checks": [c.__dict__ for c in self.last_checks]}
        )

        QMessageBox.information(self, "Report Saved", f"Preflight report exported to:\n{path}")
