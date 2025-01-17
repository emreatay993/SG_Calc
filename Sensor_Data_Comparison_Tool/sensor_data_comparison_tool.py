import sys
import os
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QFileDialog, QTabWidget, QListWidget, QSplitter, QSizePolicy,
    QDoubleSpinBox, QMessageBox, QComboBox, QDialog, QTextBrowser, QCheckBox,
    QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QGuiApplication, QDesktopServices
import plotly.graph_objects as go
from scipy.interpolate import interp1d
from scipy.stats import linregress
from tempfile import NamedTemporaryFile
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Enable High DPI scaling
QGuiApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


class ColumnMatchingDialog(QDialog):
    """
    Lets the user reorder or remove columns from Dataset1 and Dataset2
    so that the final lists line up one-to-one in the correct order.
    """

    def __init__(self, dataset1_cols, dataset2_cols, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Match Columns Between Dataset1 & Dataset2")

        # Copy in case we want to manipulate them
        self.dataset1_cols = dataset1_cols[:]
        self.dataset2_cols = dataset2_cols[:]

        # Final results stored here
        self.final_dataset1_cols = []
        self.final_dataset2_cols = []

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        instructions = QLabel(
            "Reorder/remove columns so they match 1-to-1.\n"
            "The i-th column in Dataset1 will align with the i-th column in Dataset2.\n"
            "Click OK when finished."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        lists_layout = QHBoxLayout()

        # Left list (Dataset1 columns)
        self.left_list = QListWidget()
        self.left_list.addItems(self.dataset1_cols)
        self.left_list.setSelectionMode(QListWidget.ExtendedSelection)

        # Right list (Dataset2 columns)
        self.right_list = QListWidget()
        self.right_list.addItems(self.dataset2_cols)
        self.right_list.setSelectionMode(QListWidget.ExtendedSelection)

        lists_layout.addWidget(self.left_list)
        lists_layout.addWidget(self.right_list)
        layout.addLayout(lists_layout)

        # Buttons to move up/down or remove items
        buttons_layout = QGridLayout()

        self.btn_left_up = QPushButton("Move Up (Left)")
        self.btn_left_down = QPushButton("Move Down (Left)")
        self.btn_left_remove = QPushButton("Remove (Left)")

        self.btn_right_up = QPushButton("Move Up (Right)")
        self.btn_right_down = QPushButton("Move Down (Right)")
        self.btn_right_remove = QPushButton("Remove (Right)")

        matching_dialog_button_style = """
        QPushButton {
            background-color: lightgrey;
            color: black;
            border: 1px solid #cccccc;
            padding: 4px 8px;
        }
        QPushButton:hover {
            background-color: #a9a9a9; /* Darker grey for better visibility */
            color: black; /* Keep text black on hover */
        }
        QPushButton:pressed {
            background-color: #808080; /* Even darker grey when pressed */
        }
        """

        self.btn_left_up.setStyleSheet(matching_dialog_button_style)
        self.btn_left_down.setStyleSheet(matching_dialog_button_style)
        self.btn_left_remove.setStyleSheet(matching_dialog_button_style)
        self.btn_right_up.setStyleSheet(matching_dialog_button_style)
        self.btn_right_down.setStyleSheet(matching_dialog_button_style)
        self.btn_right_remove.setStyleSheet(matching_dialog_button_style)

        buttons_layout.addWidget(self.btn_left_up, 0, 0)
        buttons_layout.addWidget(self.btn_left_down, 1, 0)
        buttons_layout.addWidget(self.btn_left_remove, 2, 0)

        buttons_layout.addWidget(self.btn_right_up, 0, 1)
        buttons_layout.addWidget(self.btn_right_down, 1, 1)
        buttons_layout.addWidget(self.btn_right_remove, 2, 1)

        # Connect signals
        self.btn_left_up.clicked.connect(lambda: self.move_up(self.left_list))
        self.btn_left_down.clicked.connect(lambda: self.move_down(self.left_list))
        self.btn_left_remove.clicked.connect(lambda: self.remove_selected(self.left_list))

        self.btn_right_up.clicked.connect(lambda: self.move_up(self.right_list))
        self.btn_right_down.clicked.connect(lambda: self.move_down(self.right_list))
        self.btn_right_remove.clicked.connect(lambda: self.remove_selected(self.right_list))

        layout.addLayout(buttons_layout)

        # OK / Cancel
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Cancel")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def move_up(self, list_widget):
        """
        Moves the selected items up in the list while maintaining their relative order.
        """
        selected_items = list_widget.selectedItems()
        if not selected_items:
            return

        # Get indices of the selected items
        selected_indices = [list_widget.row(item) for item in selected_items]

        # Check if any item is at the top (cannot move further up)
        if min(selected_indices) == 0:
            return

        # Move items up while maintaining relative order
        for index in selected_indices:
            item = list_widget.takeItem(index)
            list_widget.insertItem(index - 1, item)

        # Reselect the moved items
        for i, index in enumerate(selected_indices):
            list_widget.item(index - 1).setSelected(True)

    def move_down(self, list_widget):
        """
        Moves the selected items down in the list while maintaining their relative order.
        """
        selected_items = list_widget.selectedItems()
        if not selected_items:
            return

        # Get indices of the selected items
        selected_indices = [list_widget.row(item) for item in selected_items]

        # Check if any item is at the bottom (cannot move further down)
        if max(selected_indices) == list_widget.count() - 1:
            return

        # Move items down while maintaining relative order (process reversed)
        for index in reversed(selected_indices):
            item = list_widget.takeItem(index)
            list_widget.insertItem(index + 1, item)

        # Reselect the moved items
        for i, index in enumerate(selected_indices):
            list_widget.item(index + 1).setSelected(True)

    def remove_selected(self, list_widget):
        for item in list_widget.selectedItems():
            row = list_widget.row(item)
            list_widget.takeItem(row)

    def accept(self):
        """
        Build final lists from each list widget, then accept.
        """
        self.final_dataset1_cols = [self.left_list.item(i).text()
                                    for i in range(self.left_list.count())]
        self.final_dataset2_cols = [self.right_list.item(i).text()
                                    for i in range(self.right_list.count())]
        super().accept()

    def get_results(self):
        """
        :return: (list_of_cols_for_dataset1, list_of_cols_for_dataset2)
        """
        return self.final_dataset1_cols, self.final_dataset2_cols


class ColumnNameDialog(QDialog):
    """
    Lets the user pick the final name for each pair of columns, e.g.:
     (SG_001_1, SG1_1) --> user can choose "SG_001_1", "SG1_1", or custom.
    """

    def __init__(self, col_pairs, parent=None):
        """
        :param col_pairs: list of (df1_col, df2_col)
        """
        super().__init__(parent)
        self.setWindowTitle("Choose Final Column Names")

        self.col_pairs = col_pairs  # list of tuples
        self.final_names = []  # store results after user picks

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        instructions = QLabel(
            "For each pair of columns, choose the final name to use.\n"
            "You can manually edit the cell in 'Final Name' column, or\n"
            "use the 'Use Left Names'/'Use Right Names' buttons.\n"
            "Click OK when done."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # We'll build a small table with 3 columns:
        #   - col0: Dataset1 column
        #   - col1: Dataset2 column
        #   - col2: Final Name (editable)
        self.table = QTableWidget(len(self.col_pairs), 3)
        self.table.setHorizontalHeaderLabels(["Dataset1", "Dataset2", "Final Name"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.AllEditTriggers)

        for row, (left_name, right_name) in enumerate(self.col_pairs):
            # col 0: left_name (read-only)
            item0 = QTableWidgetItem(left_name)
            item0.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 0, item0)

            # col 1: right_name (read-only)
            item1 = QTableWidgetItem(right_name)
            item1.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 1, item1)

            # col 2: final name (editable)
            # by default, pick left_name (you can pick right_name or blank if you prefer)
            item2 = QTableWidgetItem(left_name)
            self.table.setItem(row, 2, item2)

        layout.addWidget(self.table)

        # Buttons at bottom
        btn_layout = QHBoxLayout()
        self.btn_use_left = QPushButton("Use Column Names from Dataset1")
        self.btn_use_right = QPushButton("Use Column Names from Dataset2")
        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Cancel")

        # Set background color, black text, and hover effect only for the specified buttons
        name_dialog_button_style = """
    QPushButton {
        background-color: lightgrey;
        color: black;
        border: 1px solid #cccccc;
        padding: 4px 8px;
    }
    QPushButton:hover {
        background-color: #a9a9a9; /* Darker grey for better visibility */
        color: black; /* Keep text black on hover */
    }
    QPushButton:pressed {
        background-color: #808080; /* Even darker grey when pressed */
    }
"""

        self.btn_use_left.setStyleSheet(name_dialog_button_style)
        self.btn_use_right.setStyleSheet(name_dialog_button_style)

        self.btn_use_left.clicked.connect(self.use_left_names)
        self.btn_use_right.clicked.connect(self.use_right_names)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_use_left)
        btn_layout.addWidget(self.btn_use_right)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def use_left_names(self):
        """
        Overwrite the 'Final Name' column with the left (Dataset1) name for each row
        """
        for row in range(self.table.rowCount()):
            left_name = self.table.item(row, 0).text()
            self.table.setItem(row, 2, QTableWidgetItem(left_name))

    def use_right_names(self):
        """
        Overwrite the 'Final Name' column with the right (Dataset2) name for each row
        """
        for row in range(self.table.rowCount()):
            right_name = self.table.item(row, 1).text()
            self.table.setItem(row, 2, QTableWidgetItem(right_name))

    def accept(self):
        """
        Gather final names from the third column
        """
        self.final_names = []
        for row in range(self.table.rowCount()):
            final_name = self.table.item(row, 2).text()
            self.final_names.append(final_name)
        super().accept()

    def get_final_names(self):
        return self.final_names


class MetricsCalculator(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # ---- Dataset Selection for 1st dataset
        dataset1_layout = QHBoxLayout()
        self.dataset1_path = QLineEdit()
        self.dataset1_path.setReadOnly(True)
        self.dataset1_name = QLineEdit()
        browse1_button = QPushButton("...")
        browse1_button.clicked.connect(lambda: self.select_file(self.dataset1_path))

        dataset1_layout.addWidget(QLabel("Select 1st dataset:"))
        dataset1_layout.addWidget(browse1_button)
        dataset1_layout.addWidget(self.dataset1_path)
        dataset1_layout.addWidget(QLabel("Enter Dataset Name 1"))
        dataset1_layout.addWidget(self.dataset1_name)
        main_layout.addLayout(dataset1_layout)

        # ---- Dataset Selection for 2nd dataset
        dataset2_layout = QHBoxLayout()
        self.dataset2_path = QLineEdit()
        self.dataset2_path.setReadOnly(True)
        self.dataset2_name = QLineEdit()
        browse2_button = QPushButton("...")
        browse2_button.clicked.connect(lambda: self.select_file(self.dataset2_path))

        dataset2_layout.addWidget(QLabel("Select 2nd dataset:"))
        dataset2_layout.addWidget(browse2_button)
        dataset2_layout.addWidget(self.dataset2_path)
        dataset2_layout.addWidget(QLabel("Enter Dataset Name 2"))
        dataset2_layout.addWidget(self.dataset2_name)
        main_layout.addLayout(dataset2_layout)

        # ---- Calculate Button
        calculate_button = QPushButton("Click to Calculate")
        calculate_button.clicked.connect(self.calculate_metrics)
        main_layout.addWidget(calculate_button)

        # ---- Reference Dataset Selector UI ----
        reference_selector_layout = QHBoxLayout()

        reference_label = QLabel("Select Reference Dataset:")
        self.reference_selector = QComboBox()
        self.reference_selector.addItems(["Dataset 1", "Dataset 2"])  # Default to Dataset 1
        self.reference_selector.setCurrentIndex(0)

        reference_selector_layout.addWidget(reference_label)
        reference_selector_layout.addWidget(self.reference_selector)

        # Connect reference selection to plot updates
        self.reference_selector.currentIndexChanged.connect(self.update_all_plots)

        main_layout.addLayout(reference_selector_layout)

        # ---- Synchronization UI ----
        sync_layout = QHBoxLayout()

        sync_label = QLabel("Select Reference Time Points to Synchronize the Datasets:")
        self.sync_checkbox = QCheckBox()
        self.sync_checkbox.setChecked(False)  # default unchecked
        self.sync_checkbox.stateChanged.connect(self.toggle_sync_widgets)  # Connect to the toggle function

        self.sync_time1 = QDoubleSpinBox()
        self.sync_time1.setPrefix("Ref Time1: ")
        self.sync_time1.setDecimals(3)
        self.sync_time1.setRange(0, 999999)
        self.sync_time1.setVisible(False)  # Hidden by default

        self.sync_time2 = QDoubleSpinBox()
        self.sync_time2.setPrefix("Ref Time2: ")
        self.sync_time2.setDecimals(3)
        self.sync_time2.setRange(0, 999999)
        self.sync_time2.setVisible(False)  # Hidden by default

        # Combobox to choose which dataset to shift
        self.dataset_shift_label = QLabel("Select Which Dataset to Shift:")
        self.dataset_shift_label.setVisible(False)  # Hidden by default

        self.sync_dataset_combo = QComboBox()
        self.sync_dataset_combo.addItems(["Dataset 1", "Dataset 2"])
        self.sync_dataset_combo.setVisible(False)  # Hidden by default

        # Synchronize and Revert buttons
        self.sync_button = QPushButton("Synchronize")
        self.sync_button.clicked.connect(self.synchronize_datasets)
        self.sync_button.setVisible(False)  # Hidden by default

        self.revert_button = QPushButton("Revert")
        self.revert_button.clicked.connect(self.revert_datasets)
        self.revert_button.setVisible(False)  # Hidden by default

        sync_layout.addWidget(sync_label)
        sync_layout.addWidget(self.sync_checkbox)
        sync_layout.addWidget(self.sync_time1)
        sync_layout.addWidget(self.sync_time2)
        sync_layout.addWidget(self.dataset_shift_label)
        sync_layout.addWidget(self.sync_dataset_combo)
        sync_layout.addWidget(self.sync_button)
        sync_layout.addWidget(self.revert_button)

        main_layout.addLayout(sync_layout)
        # ---- End of global sync UI ----

        # ---- Tab Widget
        self.tab_widget = QTabWidget()

        # =========================
        #       TAB1: Old Metrics
        # =========================
        self.tab1 = QWidget()
        tab1_layout = QVBoxLayout()

        # Time range for Tab1
        tab1_time_layout = QHBoxLayout()
        self.start_time_spinbox_tab1 = QDoubleSpinBox()
        self.start_time_spinbox_tab1.setPrefix("Start Time: ")
        self.start_time_spinbox_tab1.setDecimals(3)
        self.start_time_spinbox_tab1.setRange(0, 999999)
        self.start_time_spinbox_tab1.valueChanged.connect(self.update_tab1_plot)

        self.end_time_spinbox_tab1 = QDoubleSpinBox()
        self.end_time_spinbox_tab1.setPrefix("End Time: ")
        self.end_time_spinbox_tab1.setDecimals(3)
        self.end_time_spinbox_tab1.setRange(0, 999999)
        self.end_time_spinbox_tab1.valueChanged.connect(self.update_tab1_plot)

        # Add Help Button in Statistical Metrics Tab
        help_button_tab1 = QPushButton("?")
        help_button_tab1.setFixedSize(48, 24)
        help_button_tab1.setToolTip("Click to open a help document about the metrics.")
        help_button_tab1.clicked.connect(self.open_help_document)

        tab1_time_layout.addWidget(self.start_time_spinbox_tab1)
        tab1_time_layout.addWidget(self.end_time_spinbox_tab1)
        tab1_layout.addLayout(tab1_time_layout)
        tab1_time_layout.addWidget(help_button_tab1)

        # List widget for Tab1
        self.column_list_widget_tab1 = QListWidget()
        self.column_list_widget_tab1.setSelectionMode(QListWidget.ExtendedSelection)
        self.column_list_widget_tab1.itemSelectionChanged.connect(self.update_tab1_plot)

        # Splitter for Tab1
        splitter_tab1 = QSplitter(Qt.Horizontal)
        splitter_tab1.addWidget(self.column_list_widget_tab1)

        self.plot_view_tab1 = QWebEngineView()
        self.plot_view_tab1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter_tab1.addWidget(self.plot_view_tab1)

        splitter_tab1.setSizes([200, 800])  # initial widths
        tab1_layout.addWidget(splitter_tab1)

        self.tab1.setLayout(tab1_layout)
        self.tab_widget.addTab(self.tab1, "Statistical Metrics")

        # =========================
        #      TAB2: Scale & Offset
        # =========================
        self.tab2 = QWidget()
        tab2_layout = QVBoxLayout()

        # Time range for Tab2
        tab2_time_layout = QHBoxLayout()
        self.start_time_spinbox_tab2 = QDoubleSpinBox()
        self.start_time_spinbox_tab2.setPrefix("Start Time: ")
        self.start_time_spinbox_tab2.setDecimals(3)
        self.start_time_spinbox_tab2.setRange(0, 999999)
        self.start_time_spinbox_tab2.valueChanged.connect(self.update_tab2_plot)

        self.end_time_spinbox_tab2 = QDoubleSpinBox()
        self.end_time_spinbox_tab2.setPrefix("End Time: ")
        self.end_time_spinbox_tab2.setDecimals(3)
        self.end_time_spinbox_tab2.setRange(0, 999999)
        self.end_time_spinbox_tab2.valueChanged.connect(self.update_tab2_plot)

        tab2_time_layout.addWidget(self.start_time_spinbox_tab2)
        tab2_time_layout.addWidget(self.end_time_spinbox_tab2)
        tab2_layout.addLayout(tab2_time_layout)

        # List widget for Tab2
        self.column_list_widget_tab2 = QListWidget()
        self.column_list_widget_tab2.setSelectionMode(QListWidget.ExtendedSelection)
        self.column_list_widget_tab2.itemSelectionChanged.connect(self.update_tab2_plot)

        # Splitter for Tab2
        splitter_tab2 = QSplitter(Qt.Horizontal)
        splitter_tab2.addWidget(self.column_list_widget_tab2)

        self.plot_view_tab2 = QWebEngineView()
        self.plot_view_tab2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter_tab2.addWidget(self.plot_view_tab2)

        splitter_tab2.setSizes([200, 800])  # initial widths
        tab2_layout.addWidget(splitter_tab2)

        self.tab2.setLayout(tab2_layout)
        self.tab_widget.addTab(self.tab2, "Scale and Offset Coefficients")

        #
        # ============= NEW: TAB3: Plot both datasets + scaled/offset dataset
        #
        self.tab3 = QWidget()
        tab3_layout = QVBoxLayout()

        # Time range for Tab3
        tab3_time_layout = QHBoxLayout()
        self.start_time_spinbox_tab3 = QDoubleSpinBox()
        self.start_time_spinbox_tab3.setPrefix("Start Time: ")
        self.start_time_spinbox_tab3.setDecimals(3)
        self.start_time_spinbox_tab3.setRange(0, 999999)
        self.start_time_spinbox_tab3.valueChanged.connect(self.update_tab3_plot)

        self.end_time_spinbox_tab3 = QDoubleSpinBox()
        self.end_time_spinbox_tab3.setPrefix("End Time: ")
        self.end_time_spinbox_tab3.setDecimals(3)
        self.end_time_spinbox_tab3.setRange(0, 999999)
        self.end_time_spinbox_tab3.valueChanged.connect(self.update_tab3_plot)

        tab3_time_layout.addWidget(self.start_time_spinbox_tab3)
        tab3_time_layout.addWidget(self.end_time_spinbox_tab3)
        tab3_layout.addLayout(tab3_time_layout)

        self.hide_scaled_checkbox_tab3 = QCheckBox("Hide Scaled/Offset")
        self.hide_scaled_checkbox_tab3.setToolTip(
            "When checked, hides scaled-only, offset-only, and scaled+offset plots.")
        # Connect it so that toggling re-plots
        self.hide_scaled_checkbox_tab3.stateChanged.connect(self.update_tab3_plot)

        tab3_time_layout.addWidget(self.hide_scaled_checkbox_tab3)

        tab3_layout.addLayout(tab3_time_layout)

        # List widget for Tab3
        self.column_list_widget_tab3 = QListWidget()
        self.column_list_widget_tab3.setSelectionMode(QListWidget.ExtendedSelection)
        self.column_list_widget_tab3.itemSelectionChanged.connect(self.update_tab3_plot)

        splitter_tab3 = QSplitter(Qt.Horizontal)
        splitter_tab3.addWidget(self.column_list_widget_tab3)

        # QWebEngineView for Tab3
        self.plot_view_tab3 = QWebEngineView()
        self.plot_view_tab3.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter_tab3.addWidget(self.plot_view_tab3)
        splitter_tab3.setSizes([200, 800])  # initial widths

        tab3_layout.addWidget(splitter_tab3)
        self.tab3.setLayout(tab3_layout)

        # Add Tab3 to tab widget
        self.tab_widget.addTab(self.tab3, "Overlay Plot")

        #
        # Add the tab widget to main layout
        #
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)
        self.setWindowTitle("Sensor Data Comparison Tool v0.5")

    def select_file(self, line_edit):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv)")
        if file_path:
            line_edit.setText(file_path)

    def calculate_metrics(self):
        """
        Loads the two datasets, ensures 'Time' columns are correct,
        aligns the data, and populates the list widgets in all tabs.
        """
        try:
            path1 = self.dataset1_path.text()
            path2 = self.dataset2_path.text()

            if not path1 or not path2:
                QMessageBox.warning(self, "Missing Data", "Both dataset file paths must be selected.")
                return

            df1 = pd.read_csv(path1)
            df2 = pd.read_csv(path2)

            # Validate 'Time' col
            if df1.columns[0] != "Time" or df2.columns[0] != "Time":
                QMessageBox.critical(self, "Error", "The first column of both datasets must be named 'Time'.")
                return

            # Separate out 'Time'
            df1_cols = [c for c in df1.columns if c != "Time"]
            df2_cols = [c for c in df2.columns if c != "Time"]

            # Open the ColumnMatchingDialog
            dlg_match = ColumnMatchingDialog(df1_cols, df2_cols, parent=self)
            if dlg_match.exec_() != QDialog.Accepted:
                return  # user canceled
            matched_cols1, matched_cols2 = dlg_match.get_results()

            # Check if we have same length
            if len(matched_cols1) != len(matched_cols2):
                QMessageBox.critical(self, "Error",
                                     "After matching, the two column lists differ in length. Cannot proceed.")
                return

            # Next, let user finalize column names
            col_pairs = list(zip(matched_cols1, matched_cols2))
            dlg_names = ColumnNameDialog(col_pairs, parent=self)
            if dlg_names.exec_() != QDialog.Accepted:
                return  # user canceled

            final_names = dlg_names.get_final_names()
            if len(final_names) != len(col_pairs):
                QMessageBox.critical(self, "Error", "No final names found. Cannot proceed.")
                return

            # Reorder df1, df2 in the new order, then rename
            df1 = df1[["Time"] + matched_cols1]
            df2 = df2[["Time"] + matched_cols2]

            # Create final columns list: first is "Time", then the user-chosen final names
            new_cols = ["Time"] + final_names
            df1.columns = new_cols
            df2.columns = new_cols

            # Validate the presence of "Time" column
            if df1.columns[0] != "Time" or df2.columns[0] != "Time":
                QMessageBox.critical(self, "Error", "The first column of both datasets must be named 'Time'.")
                return

            # Validate number of columns
            if df1.shape[1] != df2.shape[1]:
                QMessageBox.critical(self, "Error", "The number of columns in the two datasets is different!")
                return

            # Validate column names
            if not all(df1.columns == df2.columns):
                user_choice = QMessageBox.question(
                    self,
                    "Column Name Mismatch",
                    "The column names in the two datasets are different.\n"
                    "Would you like to use column names from the first dataset?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if user_choice == QMessageBox.Yes:
                    col_names = df1.columns
                else:
                    col_names = df2.columns
                df1.columns = col_names
                df2.columns = col_names

            # For safety, store raw copies (if you want raw reversion):
            self.df1_original = df1.copy()
            self.df2_original = df2.copy()

            # Interpolate and align
            self.df1_aligned, self.df2_aligned = self.interpolate_and_align(df1, df2)

            # Store "aligned" backups, so we can revert to them:
            self.df1_aligned_original = self.df1_aligned.copy()
            self.df2_aligned_original = self.df2_aligned.copy()

            # Clear old items in tabs
            self.column_list_widget_tab1.clear()
            self.column_list_widget_tab2.clear()
            self.column_list_widget_tab3.clear()

            # Populate columns in each tab
            for col in df1.columns:
                if col != "Time":
                    self.column_list_widget_tab1.addItem(col)
                    self.column_list_widget_tab2.addItem(col)
                    self.column_list_widget_tab3.addItem(col)

            # Set time ranges in all tabs
            min_t = float(self.df1_aligned["Time"].min())
            max_t = float(self.df1_aligned["Time"].max())

            # Tab1 spinboxes
            self.start_time_spinbox_tab1.setRange(min_t, max_t)
            self.start_time_spinbox_tab1.setValue(min_t)
            self.end_time_spinbox_tab1.setRange(min_t, max_t)
            self.end_time_spinbox_tab1.setValue(max_t)

            # Tab2 spinboxes
            self.start_time_spinbox_tab2.setRange(min_t, max_t)
            self.start_time_spinbox_tab2.setValue(min_t)
            self.end_time_spinbox_tab2.setRange(min_t, max_t)
            self.end_time_spinbox_tab2.setValue(max_t)

            # Tab3 spinboxes
            self.start_time_spinbox_tab3.setRange(min_t, max_t)
            self.start_time_spinbox_tab3.setValue(min_t)
            self.end_time_spinbox_tab3.setRange(min_t, max_t)
            self.end_time_spinbox_tab3.setValue(max_t)

            QMessageBox.information(self, "Data Loaded", "Datasets loaded successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            import traceback
            traceback.print_exc()

    def synchronize_datasets(self):
        """
        Shift the chosen dataset's time so that 'sync_time2' aligns with 'sync_time1'.
        Zero-pad on the newly exposed side with 1e-8, crop the opposite side
        to retain the same length. Then re-plot.
        """
        if not self.sync_checkbox.isChecked():
            QMessageBox.information(self, "Sync not active",
                                    "Synchronization checkbox is not checked. No shift applied.")
            return

        try:
            ref_t1 = self.sync_time1.value()
            ref_t2 = self.sync_time2.value()
            shift_seconds = ref_t1 - ref_t2

            # Decide which aligned DataFrame to shift
            if self.sync_dataset_combo.currentIndex() == 0:
                df_to_shift = self.df1_aligned
                dataset_str = "Dataset1"
            else:
                df_to_shift = self.df2_aligned
                dataset_str = "Dataset2"

            if df_to_shift.empty:
                QMessageBox.warning(self, "No Data", f"{dataset_str} is empty!")
                return

            # 1) Figure out approximate dt
            if len(df_to_shift) < 2:
                QMessageBox.warning(self, "Insufficient Data", "Not enough points to shift.")
                return
            dt = df_to_shift["Time"].iloc[1] - df_to_shift["Time"].iloc[0]

            # 2) Convert shift in seconds to integer shift in samples
            shift_samples = int(round(shift_seconds / dt))
            n = len(df_to_shift)

            if shift_samples == 0:
                QMessageBox.information(self, "No Shift", "Shift is effectively zero samples.")
                return

            # Save old data columns
            data_cols = [c for c in df_to_shift.columns if c != "Time"]
            data_array = df_to_shift[data_cols].values  # shape (n, #columns)

            if shift_samples > 0:
                # SHIFT RIGHT: we pad the left with 1e-8, drop some on the right
                pad_block = np.full((shift_samples, data_array.shape[1]), 1e-8)

                # Example: new_data = [pad_block, data_array[:-shift_samples]]
                # Because we remove the last 'shift_samples' rows to keep length the same
                if shift_samples >= n:
                    QMessageBox.warning(self, "Large Shift", "Shift is too large, bigger than dataset length.")
                    return

                new_data = np.vstack([pad_block, data_array[:-shift_samples]])
                df_to_shift[data_cols] = new_data

            else:
                # SHIFT LEFT: shift_samples < 0
                shift_samples_abs = abs(shift_samples)

                if shift_samples_abs >= n:
                    QMessageBox.warning(self, "Large Shift", "Shift is too large, bigger than dataset length.")
                    return

                pad_block = np.full((shift_samples_abs, data_array.shape[1]), 1e-8)
                # new_data = [data_array[shift_samples_abs:], pad_block]
                new_data = np.vstack([data_array[shift_samples_abs:], pad_block])
                df_to_shift[data_cols] = new_data

            # QMessageBox.information(
            #     self, "Datasets Synchronized",
            #     f"{dataset_str} was shifted by {shift_samples} samples (~{shift_seconds:.3f} sec)."
            # )

            # Re-plot all tabs to show effect
            self.update_tab1_plot()
            self.update_tab2_plot()
            self.update_tab3_plot()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during synchronization: {str(e)}")

    def revert_datasets(self):
        """
        Restore df1_aligned, df2_aligned to their original aligned state
        (i.e., undo any time shifts or zero-padding).
        """
        if not hasattr(self, 'df1_aligned_original') or not hasattr(self, 'df2_aligned_original'):
            QMessageBox.warning(self, "Not Available", "No original alignment data to revert to.")
            return

        self.df1_aligned = self.df1_aligned_original.copy()
        self.df2_aligned = self.df2_aligned_original.copy()

        # QMessageBox.information(self, "Reverted", "Datasets have been reverted to the original alignment.")

        # Re-plot each tab
        self.update_tab1_plot()
        self.update_tab2_plot()
        self.update_tab3_plot()

    def interpolate_and_align(self, df1, df2):
        """
        Uses interp1d to align df1 & df2 along a common 'Time' axis.
        """
        max_time = min(df1["Time"].max(), df2["Time"].max())
        df1 = df1[df1["Time"] <= max_time]
        df2 = df2[df2["Time"] <= max_time]

        # We'll pick whichever dataset has more time points
        time_dense = df1["Time"].values if len(df1) > len(df2) else df2["Time"].values

        df1_interp = pd.DataFrame({"Time": time_dense})
        df2_interp = pd.DataFrame({"Time": time_dense})

        for col in df1.columns:
            if col != "Time":
                f1 = interp1d(df1["Time"], df1[col], kind="linear", fill_value="extrapolate")
                f2 = interp1d(df2["Time"], df2[col], kind="linear", fill_value="extrapolate")

                df1_interp[col] = f1(time_dense)
                df2_interp[col] = f2(time_dense)

        return df1_interp, df2_interp

    # --------------------------------------------------------------------------------
    #                           TAB1 LOGIC: Statistical Metrics
    # --------------------------------------------------------------------------------
    def update_tab1_plot(self):
        try:
            selected_items = self.column_list_widget_tab1.selectedItems()
            selected_columns = [item.text() for item in selected_items]
            if not selected_columns:
                return

            if self.reference_selector.currentIndex() == 0:
                reference_df = self.df1_aligned
                target_df = self.df2_aligned
                ref_name = self.dataset1_name.text() if self.dataset1_name.text() else "Dataset1"
                tgt_name = self.dataset2_name.text() if self.dataset2_name.text() else "Dataset2"
            elif self.reference_selector.currentIndex() == 1:
                reference_df = self.df2_aligned
                target_df = self.df1_aligned
                ref_name = self.dataset2_name.text() if self.dataset2_name.text() else "Dataset2"
                tgt_name = self.dataset1_name.text() if self.dataset1_name.text() else "Dataset1"

            # Time range
            st = self.start_time_spinbox_tab1.value()
            et = self.end_time_spinbox_tab1.value()

            # Choose reference dataset
            if self.reference_selector.currentIndex() == 0:
                reference_df = self.df1_aligned
                target_df = self.df2_aligned
            elif self.reference_selector.currentIndex() == 1:
                reference_df = self.df2_aligned
                target_df = self.df1_aligned

            ref_f = reference_df[(reference_df["Time"] >= st) & (reference_df["Time"] <= et)]
            tgt_f = target_df[(target_df["Time"] >= st) & (target_df["Time"] <= et)]

            ref_f = ref_f[["Time"] + selected_columns]
            tgt_f = tgt_f[["Time"] + selected_columns]

            # Calculate metrics
            metrics = self.compare_datasets_statistical(ref_f, tgt_f)
            self.plot_metrics_tab1(metrics)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error updating Tab1 plot: {str(e)}")
            import traceback
            traceback.print_exc()

    def compare_datasets_statistical(self, df1, df2):
        metrics_list = []
        columns = [col for col in df1.columns if col != "Time"]

        # -- Compute approximate dt (assuming df1 is aligned & fairly uniform)
        if len(df1) > 1:
            dt = df1["Time"].iloc[1] - df1["Time"].iloc[0]
        else:
            dt = 0.0

        for col in columns:
            x = df1[col].values
            y = df2[col].values

            # Cross correlation
            x_norm = (x - np.mean(x)) / np.std(x)
            y_norm = (y - np.mean(y)) / np.std(y)
            cross_corr = np.correlate(x_norm, y_norm, mode="full") / len(x)
            max_corr = np.max(cross_corr)
            lag_at_max_corr = np.argmax(cross_corr) - (len(x) - 1)

            # Time shift in seconds
            time_shift_sec = lag_at_max_corr * dt

            # MSE + RMSE
            mse = np.mean((x - y) ** 2)
            rmse = np.sqrt(mse)

            # R^2 (Coefficient of Determination)
            ss_total = np.sum((x - np.mean(x)) ** 2)
            ss_residual = np.sum((x - y) ** 2)
            r_squared = 1 - (ss_residual / ss_total) if ss_total != 0 else np.nan

            # Pearson Correlation Coefficient (PCC or R)
            pearson_corr = np.corrcoef(x, y)[0, 1]

            # Absolute Error
            abs_error = np.abs(x - y)

            # Percentage Error
            with np.errstate(divide='ignore', invalid='ignore'):  # Handle division by zero
                perc_error = np.where(x != 0, np.abs((x - y) / x) * 100, np.nan)

            # SMAPE
            with np.errstate(divide='ignore', invalid='ignore'):  # Handle division by zero
                smape = np.nanmean(2 * np.abs(x - y) / (np.abs(x) + np.abs(y)) * 100)

            # WMAPE
            with np.errstate(divide='ignore', invalid='ignore'):
                wmape = np.sum(abs_error) / np.sum(np.abs(x)) * 100 if np.sum(np.abs(x)) != 0 else np.nan

            metrics_list.append({
                "Channel": col,
                "Max Correlation": max_corr,
                "Lag at Max Correlation (samples)": lag_at_max_corr,  # Store sample-based lag
                "Time Shift (s)": time_shift_sec,  # Store time-based shift in seconds
                "MSE": mse,  # Mean Square Error
                "RMSE": rmse,  # Root Mean Square Error
                "R^2": r_squared,  # Coefficient of Determination
                "Pearson Correlation": pearson_corr,
                "Absolute Error": abs_error.mean(),  # Average absolute error
                "Percentage Error": np.nanmean(perc_error),  # Average percentage error
                "SMAPE": smape,  # Symmetric Mean Absolute Percentage Error
                "WMAPE": wmape  # Weighted Mean Absolute Percentage Error
            })

        return metrics_list

    def plot_metrics_tab1(self, metrics):
        try:
            # Grab dataset names for the title
            d1_name = self.dataset1_name.text() if self.dataset1_name.text() else "Dataset1"
            d2_name = self.dataset2_name.text() if self.dataset2_name.text() else "Dataset2"
            plot_title = f"Statistical Metrics - {d1_name} vs {d2_name}"

            screen = QGuiApplication.primaryScreen()
            dpi = screen.logicalDotsPerInch()
            scale_factor = dpi / 96.0

            base_font_size = 10
            title_font_size = int(base_font_size * 1.2 * scale_factor)
            axis_label_font_size = int(base_font_size * scale_factor)
            tick_font_size = int(base_font_size * 0.9 * scale_factor)
            legend_font_size = int(base_font_size * scale_factor)

            channels = [m["Channel"] for m in metrics]
            max_corr = [m["Max Correlation"] for m in metrics]

            # Instead of 'lag_corr', let's store both:
            sample_lags = [m["Lag at Max Correlation (samples)"] for m in metrics]
            time_shifts = [m["Time Shift (s)"] for m in metrics]

            mse_vals = [m["MSE"] for m in metrics]
            rmse_vals = [m["RMSE"] for m in metrics]
            r_squared_vals = [m["R^2"] for m in metrics]
            pearson_vals = [m["Pearson Correlation"] for m in metrics]
            abs_error_vals = [m["Absolute Error"] for m in metrics]
            perc_error_vals = [m["Percentage Error"] for m in metrics]
            smape_vals = [m["SMAPE"] for m in metrics]
            wmape_vals = [m["WMAPE"] for m in metrics]

            fig = go.Figure()

            # Bar: Max Correlation
            fig.add_trace(go.Bar(
                x=channels, y=max_corr,
                name="Max Correlation",
                marker_color="#3498db"
            ))

            # Bar: Sample Lag
            fig.add_trace(go.Bar(
                x=channels, y=sample_lags,
                name="Lag at Max Corr (Samples)",
                marker_color="red"
            ))

            # Bar: Time Shift
            #   NEW -> show how many seconds correspond to that lag
            fig.add_trace(go.Bar(
                x=channels, y=time_shifts,
                name="Time Shift (s)",
                marker_color="orange"
            ))

            # Bar: R^2
            fig.add_trace(go.Bar(
                x=channels, y=r_squared_vals,
                name="R^2 (Coeff. of Determination)",
                marker_color="magenta"
            ))

            # Bar: PCC or R
            fig.add_trace(go.Bar(
                x=channels, y=pearson_vals,
                name="R (Pearson Corr.)",
                marker_color="purple"
            ))

            # Line: MSE
            fig.add_trace(go.Scatter(
                x=channels, y=mse_vals,
                name="MSE",
                mode="lines+markers"
            ))

            # Line: RMSE
            fig.add_trace(go.Scatter(
                x=channels, y=rmse_vals,
                name="RMSE",
                mode="lines+markers"
            ))

            # Line: Absolute Error
            fig.add_trace(go.Scatter(
                x=channels, y=abs_error_vals,
                name="Absolute Error",
                mode="lines+markers",
                line=dict(color='orange', dash='dot')
            ))

            # Line: Percentage Error
            fig.add_trace(go.Scatter(
                x=channels, y=perc_error_vals,
                name="Percentage Error (%)",
                mode="lines+markers",
                line=dict(color='green', dash='dash')
            ))

            # Line: SMAPE
            fig.add_trace(go.Scatter(
                x=channels, y=smape_vals,
                name="SMAPE",
                mode="lines+markers",
                line=dict(color='blue', dash='dash')
            ))

            # Line: WMAPE
            fig.add_trace(go.Scatter(
                x=channels, y=wmape_vals,
                name="WMAPE",
                mode="lines+markers",
                line=dict(color='red', dash='dot')
            ))

            fig.update_layout(
                title=dict(
                    text=plot_title,
                    font=dict(size=title_font_size),
                    x=0.5,
                    xanchor='center',
                    yanchor='top'
                ),
                xaxis=dict(
                    title=dict(text="Channel", font=dict(size=axis_label_font_size)),
                    tickfont=dict(size=tick_font_size)
                ),
                yaxis=dict(
                    title=dict(text="Metric Value", font=dict(size=axis_label_font_size)),
                    tickfont=dict(size=tick_font_size),
                    nticks=11
                ),
                legend=dict(font=dict(size=legend_font_size)),
                barmode="group",
                template="plotly_white",
                autosize=True
            )

            with NamedTemporaryFile(delete=False, suffix=".html") as temp_file:
                fig.write_html(temp_file.name)
                temp_html_path = temp_file.name

            self.plot_view_tab1.setUrl(QUrl.fromLocalFile(temp_html_path))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in plotting Tab1 metrics: {str(e)}")
            import traceback
            traceback.print_exc()

    def open_help_document(self):
        pdf_path = "Help_Doc_Statistical_Metrics.pdf"
        if os.path.exists(pdf_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
        else:
            print("File not found.")

    # --------------------------------------------------------------------------------
    #                       TAB2 LOGIC: Scale & Offset
    # --------------------------------------------------------------------------------
    def update_tab2_plot(self):
        try:
            selected_items = self.column_list_widget_tab2.selectedItems()
            selected_columns = [item.text() for item in selected_items]
            if not selected_columns:
                return

            st = self.start_time_spinbox_tab2.value()
            et = self.end_time_spinbox_tab2.value()

            # Choose reference dataset
            if self.reference_selector.currentIndex() == 0:
                reference_df = self.df1_aligned
                target_df = self.df2_aligned
            elif self.reference_selector.currentIndex() == 1:
                reference_df = self.df2_aligned
                target_df = self.df1_aligned

            ref_f = reference_df[(reference_df["Time"] >= st) & (reference_df["Time"] <= et)]
            tgt_f = target_df[(target_df["Time"] >= st) & (target_df["Time"] <= et)]

            ref_f = ref_f[["Time"] + selected_columns]
            tgt_f = tgt_f[["Time"] + selected_columns]

            scale_offset_metrics = self.calculate_scale_offset(tgt_f, ref_f)
            self.plot_scale_offset_tab2(scale_offset_metrics)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error updating Tab2 plot: {str(e)}")
            import traceback
            traceback.print_exc()

    def calculate_scale_offset(self, ref_df, tgt_df):
        results = []
        columns = [c for c in ref_df.columns if c != "Time"]
        for col in columns:
            r = ref_df[col].values
            t = tgt_df[col].values
            slope, intercept, _, _, _ = linregress(r, t)
            results.append({
                "Channel": col,
                "Scale": slope,
                "Offset": intercept
            })
        return results

    def plot_scale_offset_tab2(self, metrics):
        try:
            d1_name = self.dataset1_name.text() if self.dataset1_name.text() else "Dataset1"
            d2_name = self.dataset2_name.text() if self.dataset2_name.text() else "Dataset2"
            if self.reference_selector.currentIndex() == 0:
                plot_title = f"Scale & Offset Coefficients: {d1_name} as Reference"
            else:
                plot_title = f"Scale & Offset Coefficients: {d2_name} as Reference"

            screen = QGuiApplication.primaryScreen()
            dpi = screen.logicalDotsPerInch()
            scale_factor = dpi / 96.0

            base_font_size = 10
            title_font_size = int(base_font_size * 1.2 * scale_factor)
            axis_label_font_size = int(base_font_size * scale_factor)
            tick_font_size = int(base_font_size * 0.9 * scale_factor)
            legend_font_size = int(base_font_size * scale_factor)

            channels = [m["Channel"] for m in metrics]
            scales = [m["Scale"] for m in metrics]
            offsets = [m["Offset"] for m in metrics]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=channels, y=scales,
                name="Scale",
                marker_color="blue"
            ))
            fig.add_trace(go.Bar(
                x=channels, y=offsets,
                name="Offset",
                marker_color="purple"
            ))

            fig.update_layout(
                title=dict(
                    text=plot_title,
                    font=dict(size=title_font_size),
                    x=0.5,
                    xanchor='center',
                    yanchor='top'
                ),
                xaxis=dict(
                    title=dict(text="Channel", font=dict(size=axis_label_font_size)),
                    tickfont=dict(size=tick_font_size)
                ),
                yaxis=dict(
                    title=dict(text="Coefficient Value", font=dict(size=axis_label_font_size)),
                    tickfont=dict(size=tick_font_size),
                    nticks=11
                ),
                legend=dict(font=dict(size=legend_font_size)),
                barmode="group",
                template="plotly_white",
                autosize=True
            )

            with NamedTemporaryFile(delete=False, suffix=".html") as temp_file:
                fig.write_html(temp_file.name)
                temp_html_path = temp_file.name

            self.plot_view_tab2.setUrl(QUrl.fromLocalFile(temp_html_path))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error plotting Tab2 scale/offset: {str(e)}")
            import traceback
            traceback.print_exc()

    # --------------------------------------------------------------------------------
    #               TAB3 LOGIC: Combined Plot with Scale & Offset
    # --------------------------------------------------------------------------------
    def update_tab3_plot(self):
        """
        Plots:
          - Reference data (no transform)
          - Original target data
          - Scaled-only data (target / slope)
          - Offset-only data (target - intercept)
          - Scaled+offset (target / slope - intercept)
        """
        try:
            selected_items = self.column_list_widget_tab3.selectedItems()
            selected_columns = [item.text() for item in selected_items]
            if not selected_columns:
                return

            st = self.start_time_spinbox_tab3.value()
            et = self.end_time_spinbox_tab3.value()

            # Choose which dataset to shift
            if self.reference_selector.currentIndex() == 0:
                reference_df = self.df1_aligned
                target_df = self.df2_aligned
                ref_name = self.dataset1_name.text() if self.dataset1_name.text() else "Dataset1"
                tgt_name = self.dataset2_name.text() if self.dataset2_name.text() else "Dataset2"
            elif self.reference_selector.currentIndex() == 1:
                reference_df = self.df2_aligned
                target_df = self.df1_aligned
                ref_name = self.dataset2_name.text() if self.dataset2_name.text() else "Dataset1"
                tgt_name = self.dataset1_name.text() if self.dataset1_name.text() else "Dataset2"

            ref_f = reference_df[(reference_df["Time"] >= st) & (reference_df["Time"] <= et)]
            tgt_f = target_df[(target_df["Time"] >= st) & (target_df["Time"] <= et)]

            ref_f = ref_f[["Time"] + selected_columns]
            tgt_f = tgt_f[["Time"] + selected_columns]

            # Compute scale & offset for each selected column (like Tab2)
            scale_offset_metrics = self.calculate_scale_offset(ref_f, tgt_f)

            # Build new DataFrames for scaled-only, offset-only, and scaled+offset
            scaled_only_df = pd.DataFrame()
            offset_only_df = pd.DataFrame()
            scaled_offset_df = pd.DataFrame()

            scaled_only_df["Time"] = tgt_f["Time"]
            offset_only_df["Time"] = tgt_f["Time"]
            scaled_offset_df["Time"] = tgt_f["Time"]

            for m in scale_offset_metrics:
                col = m["Channel"]
                slope = m["Scale"]
                intercept = m["Offset"]

                # scaled-only: target / slope
                scaled_only_df[col] = tgt_f[col] / slope if slope != 0 else np.nan
                # offset-only: target - intercept
                offset_only_df[col] = tgt_f[col] - intercept
                # scaled+offset: (target - intercept) / slope
                scaled_offset_df[col] = tgt_f[col] / slope - intercept if slope != 0 else np.nan

            # Now plot everything in a single figure
            self.plot_tab3(ref_f, tgt_f, scaled_only_df, offset_only_df, scaled_offset_df, ref_name, tgt_name)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error updating Tab3 plot: {str(e)}")
            import traceback
            traceback.print_exc()

    def plot_tab3(self, ref_df, tgt_df, scaled_only_df, offset_only_df, scaled_offset_df, ref_name, tgt_name):
        """
        Makes an interactive line plot with:
          - the reference data
          - the original target data
          - the scaled-only data
          - the offset-only data
          - the scaled+offset data
        for each selected channel.
        """
        try:
            # Update plot title to include the current reference dataset
            plot_title = (f"Overlay Plot:\n"
                          f"Reference: {ref_name}, Checked: {tgt_name}")

            screen = QGuiApplication.primaryScreen()
            dpi = screen.logicalDotsPerInch()
            scale_factor = dpi / 96.0

            base_font_size = 10
            title_font_size = int(base_font_size * 1.2 * scale_factor)
            axis_label_font_size = int(base_font_size * scale_factor)
            tick_font_size = int(base_font_size * 0.9 * scale_factor)
            legend_font_size = int(base_font_size * scale_factor)

            columns = [c for c in ref_df.columns if c != "Time"]
            fig = go.Figure()

            for col in columns:
                # 1) Plot reference (no transform)
                fig.add_trace(go.Scatter(
                    x=ref_df["Time"], y=ref_df[col],
                    mode="lines",
                    name=f"{ref_name} - {col}"
                ))

                # 2) Plot original target
                if self.hide_scaled_checkbox_tab3.isChecked():
                    original_trace_name = f"{tgt_name} - {col}"
                else:
                    original_trace_name = f"{tgt_name} (Original) - {col}"

                fig.add_trace(go.Scatter(
                    x=tgt_df["Time"], y=tgt_df[col],
                    mode="lines",
                    name=original_trace_name,  # Updated here
                ))

                # If "Hide Scaled/Offset" is checked, skip the next three lines
                if not self.hide_scaled_checkbox_tab3.isChecked():
                    # 3) Plot scaled-only
                    fig.add_trace(go.Scatter(
                        x=scaled_only_df["Time"], y=scaled_only_df[col],
                        mode="lines",
                        name=f"{tgt_name} (Scaled only) - {col}",
                        line=dict(dash='dash')
                    ))
                    # 4) Plot offset-only
                    fig.add_trace(go.Scatter(
                        x=offset_only_df["Time"], y=offset_only_df[col],
                        mode="lines",
                        name=f"{tgt_name} (Offset only) - {col}",
                        line=dict(dash='dashdot')
                    ))
                    # 5) Plot scaled+offset
                    fig.add_trace(go.Scatter(
                        x=scaled_offset_df["Time"], y=scaled_offset_df[col],
                        mode="lines",
                        name=f"{tgt_name} (Scaled+Offset) - {col}",
                        line=dict(dash='longdash')
                    ))

            fig.update_layout(
                title=dict(
                    text=plot_title,
                    font=dict(size=title_font_size),
                    x=0.5,
                    xanchor='center',
                    yanchor='top'
                ),
                xaxis=dict(
                    title=dict(text="Time", font=dict(size=axis_label_font_size)),
                    tickfont=dict(size=tick_font_size)
                ),
                yaxis=dict(
                    title=dict(text="Coefficient Value", font=dict(size=axis_label_font_size)),
                    tickfont=dict(size=tick_font_size),
                    nticks=11
                ),
                legend=dict(font=dict(size=legend_font_size)),
                template="plotly_white",
                autosize=True
            )

            # Write to temporary HTML file so QWebEngineView can load it
            with NamedTemporaryFile(delete=False, suffix=".html") as temp_file:
                fig.write_html(temp_file.name)
                temp_html_path = temp_file.name

            self.plot_view_tab3.setUrl(QUrl.fromLocalFile(temp_html_path))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error plotting Tab3: {str(e)}")
            import traceback
            traceback.print_exc()

    def update_all_plots(self):
        """
        Update all plots when invoked.
        """
        try:
            self.update_tab1_plot()
            self.update_tab2_plot()
            self.update_tab3_plot()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error updating plots: {str(e)}")
            import traceback
            traceback.print_exc()

    def toggle_sync_widgets(self, state):
        """
        Toggles the visibility of synchronization widgets based on the checkbox state.
        """
        widgets = [self.sync_time1, self.sync_time2, self.sync_dataset_combo,
                   self.sync_button, self.revert_button, self.dataset_shift_label]

        for widget in widgets:
            widget.setVisible(state == Qt.Checked)


# --------------------------------------------------------------------------
#                                  MAIN
# --------------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    style_sheet = """
    QWidget {
        background-color: #fafafa;
        font-size: 10pt;
        color: #2c3e50;
    }

    /* PushButtons */
    QPushButton {
        background-color: #3498db; /* bluish button */
        color: #ffffff;
        border: none;
        padding: 6px 12px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #2980b9; /* darker bluish */
    }

    QLineEdit[readOnly="true"] {
        color: #a0a0a0;  /* Light gray text color */
    }

    /* ComboBoxes */
    QComboBox {
        background-color: #ffffff; /* white background */
        border: 1px solid #cccccc; /* light grey border */
        padding: 2px 8px; /* padding inside the box */
        border-radius: 4px; /* rounded corners */
        color: #2c3e50; /* text color */
    }
    QComboBox:hover {
        border: 1px solid #2980b9; /* blue border on hover */
    }

    /* ComboBox Popup Menu */
    QComboBox QAbstractItemView {
        background-color: #ffffff; /* white background */
        color: #2c3e50; /* text color */
        selection-background-color: #2980b9; /* blue highlight */
        selection-color: #ffffff; /* white text on highlight */
    }

    /* Tabs (QTabBar) */
    QTabBar::tab {
        background: #3498db;
        color: #ffffff;
        padding: 6px 12px;
        margin: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected, QTabBar::tab:hover {
        background: #2980b9; /* highlight the selected tab or hover */
    }

    /* The actual tab-page area (QTabWidget::pane) */
    QTabWidget::pane {
        background-color: #ffffff;
        border: 2px solid #3498db;
        border-radius: 4px;
    }
    """

    app.setStyleSheet(style_sheet)

    window = MetricsCalculator()
    window.showMaximized()
    sys.exit(app.exec_())
