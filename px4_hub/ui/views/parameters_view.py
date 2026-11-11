"""
Parameter Manager View for PX4 Setup Hub.
Provides searchable parameter inspection, safe modification with range validation,
reboot warnings, and SQLite backup/restore.
"""
from typing import Dict, Optional, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QInputDialog, QFileDialog
)
from PySide6.QtCore import Qt
from ...core.models import Parameter


class ParametersView(QWidget):
    """Full PX4 Parameter Manager."""

    def __init__(self, connection_manager, db_manager, parent=None):
        super().__init__(parent)
        self.conn_mgr = connection_manager
        self.db_mgr = db_manager
        self._parameters: Dict[str, Parameter] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 1. Header Card
        header = QFrame()
        header.setProperty("class", "Card")
        h_layout = QVBoxLayout(header)
        lbl_title = QLabel("PX4 PARAMETER MANAGER")
        lbl_title.setObjectName("Title")
        lbl_sub = QLabel("Inspect, search, modify, backup, and restore flight controller parameters.")
        lbl_sub.setObjectName("Subtitle")
        h_layout.addWidget(lbl_title)
        h_layout.addWidget(lbl_sub)
        layout.addWidget(header)

        # 2. Controls Toolbar
        toolbar = QFrame()
        toolbar.setProperty("class", "Card")
        t_layout = QHBoxLayout(toolbar)
        t_layout.setContentsMargins(12, 10, 12, 10)
        t_layout.setSpacing(12)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search parameter name or description...")
        self.txt_search.textChanged.connect(self._filter_table)

        self.combo_group = QComboBox()
        self.combo_group.addItem("All Categories")
        self.combo_group.currentTextChanged.connect(self._filter_table)

        self.btn_refresh = QPushButton("Refresh from Vehicle")
        self.btn_refresh.clicked.connect(self._refresh_from_vehicle)

        self.btn_backup = QPushButton("Save Backup Snapshot")
        self.btn_backup.setObjectName("PrimaryButton")
        self.btn_backup.clicked.connect(self._create_backup)

        self.btn_export = QPushButton("Export .params")
        self.btn_export.clicked.connect(self._export_params)

        t_layout.addWidget(self.txt_search, 2)
        t_layout.addWidget(self.combo_group, 1)
        t_layout.addWidget(self.btn_refresh)
        t_layout.addWidget(self.btn_backup)
        t_layout.addWidget(self.btn_export)
        layout.addWidget(toolbar)

        # 3. Parameters Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Parameter Name", "Value", "Default", "Type", "Reboot?", "Description"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.doubleClicked.connect(self._handle_double_click)

        layout.addWidget(self.table, 1)

    def set_parameters(self, params: Dict[str, Parameter]):
        self._parameters = params
        groups = sorted(list(set(p.group for p in params.values() if p.group)))
        self.combo_group.blockSignals(True)
        self.combo_group.clear()
        self.combo_group.addItem("All Categories")
        self.combo_group.addItems(groups)
        self.combo_group.blockSignals(False)
        self._filter_table()

    def update_parameter(self, param: Parameter):
        self._parameters[param.name] = param
        self._filter_table()

    def _filter_table(self):
        query = self.txt_search.text().strip().lower()
        sel_group = self.combo_group.currentText()

        filtered = []
        for p in self._parameters.values():
            if sel_group != "All Categories" and p.group != sel_group:
                continue
            if query and query not in p.name.lower() and query not in p.description.lower():
                continue
            filtered.append(p)

        self.table.setRowCount(len(filtered))
        for row, p in enumerate(filtered):
            name_item = QTableWidgetItem(p.name)
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            name_item.setData(Qt.UserRole, p.name)

            val_str = f"{p.value:.4f}" if isinstance(p.value, float) else str(p.value)
            val_item = QTableWidgetItem(val_str)
            val_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if p.is_modified:
                val_item.setForeground(Qt.yellow)

            def_str = f"{p.default_value:.4f}" if isinstance(p.default_value, float) else str(p.default_value)
            def_item = QTableWidgetItem(def_str)
            def_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            type_item = QTableWidgetItem(p.type_name)
            reboot_item = QTableWidgetItem("YES" if p.requires_reboot else "No")
            desc_item = QTableWidgetItem(p.description)

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, val_item)
            self.table.setItem(row, 2, def_item)
            self.table.setItem(row, 3, type_item)
            self.table.setItem(row, 4, reboot_item)
            self.table.setItem(row, 5, desc_item)

    def _handle_double_click(self, index):
        row = index.row()
        name_item = self.table.item(row, 0)
        if not name_item:
            return
        param_name = name_item.data(Qt.UserRole)
        param = self._parameters.get(param_name)
        if not param:
            return

        hint = f"Range: [{param.min_value} .. {param.max_value}]" if param.min_value is not None else ""
        new_val_str, ok = QInputDialog.getText(
            self,
            f"Modify Parameter: {param.name}",
            f"{param.description}\n{hint}\nEnter new value:",
            text=str(param.value)
        )
        if not ok or not new_val_str.strip():
            return

        try:
            new_val = float(new_val_str) if param.type_name == "FLOAT" else int(new_val_str)
        except ValueError:
            QMessageBox.warning(self, "Invalid Value", f"Could not parse '{new_val_str}' as a number.")
            return

        if not param.validate(new_val):
            QMessageBox.warning(
                self, "Out of Range",
                f"Value {new_val} violates allowable bounds [{param.min_value} .. {param.max_value}]."
            )
            return

        if param.requires_reboot:
            QMessageBox.information(
                self, "Reboot Required",
                f"Changing {param.name} requires a flight controller reboot before taking effect."
            )

        if self.conn_mgr.active_vehicle:
            self.conn_mgr.active_vehicle.set_parameter(param.name, new_val)
            QMessageBox.information(self, "Parameter Sent", f"Updated {param.name} to {new_val}.")

    def _refresh_from_vehicle(self):
        if self.conn_mgr.active_vehicle:
            self.conn_mgr.active_vehicle.request_parameters()
        else:
            QMessageBox.warning(self, "No Connection", "Please connect a vehicle first.")

    def _create_backup(self):
        if not self._parameters:
            QMessageBox.warning(self, "Empty", "No parameters loaded to backup.")
            return

        vinfo = self.conn_mgr.active_vehicle.vehicle_info if self.conn_mgr.active_vehicle else None
        uid = vinfo.uid if vinfo else "OFFLINE"
        board = vinfo.board_name if vinfo else "Generic"
        fw = vinfo.firmware_version if vinfo else "PX4"

        data = {name: p.value for name, p in self._parameters.items()}
        backup_id = self.db_mgr.save_param_backup(uid, board, fw, data, "Manual User Snapshot")
        QMessageBox.information(self, "Backup Saved", f"Saved parameter snapshot #{backup_id} with {len(data)} parameters.")

    def _export_params(self):
        if not self._parameters:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Parameters", "px4_backup.params", "Params (*.params);;Text (*.txt)")
        if not path:
            return
        with open(path, "w") as f:
            f.write("# PX4 Setup Hub Parameter Export\n")
            f.write("# Vehicle Parameter Dump\n")
            for name, p in sorted(self._parameters.items()):
                f.write(f"1\t1\t{name}\t{p.value}\t6\n")
        QMessageBox.information(self, "Export Complete", f"Successfully exported parameters to:\n{path}")
