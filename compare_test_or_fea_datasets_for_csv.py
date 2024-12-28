import sys
import os
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QFileDialog, QTabWidget, QListWidget, QSplitter, QSizePolicy,
    QDoubleSpinBox, QMessageBox, QComboBox, QDialog, QTextBrowser,
    QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QGuiApplication
import markdown
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
        self.final_names = []       # store results after user picks

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

        # Reference dataset selector
        ref_layout = QHBoxLayout()
        self.reference_selector = QComboBox()
        self.reference_selector.addItems(["Dataset 1", "Dataset 2"])
        self.reference_selector.currentIndexChanged.connect(self.update_tab2_plot)
        ref_layout.addWidget(QLabel("Select Reference Dataset:"))
        ref_layout.addWidget(self.reference_selector)
        tab2_layout.addLayout(ref_layout)

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

        # Reference dataset selector for Tab3
        ref_layout_tab3 = QHBoxLayout()
        self.reference_selector_tab3 = QComboBox()
        self.reference_selector_tab3.addItems(["Dataset 1 (Reference)", "Dataset 2 (Reference)"])
        self.reference_selector_tab3.currentIndexChanged.connect(self.update_tab3_plot)
        ref_layout_tab3.addWidget(QLabel("Select Reference Dataset:"))
        ref_layout_tab3.addWidget(self.reference_selector_tab3)
        tab3_layout.addLayout(ref_layout_tab3)

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

        # Finally add Tab3 to tab widget
        self.tab_widget.addTab(self.tab3, "Comparison with Scaled/Offset")

        #
        # Add the tab widget to main layout
        #
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)
        self.setWindowTitle("Test Comparison Tool v0.4")

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

            # Interpolate and align
            self.df1_aligned, self.df2_aligned = self.interpolate_and_align(df1, df2)

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

            # time range
            st = self.start_time_spinbox_tab1.value()
            et = self.end_time_spinbox_tab1.value()

            df1_f = self.df1_aligned[(self.df1_aligned["Time"] >= st) & (self.df1_aligned["Time"] <= et)]
            df2_f = self.df2_aligned[(self.df2_aligned["Time"] >= st) & (self.df2_aligned["Time"] <= et)]

            df1_f = df1_f[["Time"] + selected_columns]
            df2_f = df2_f[["Time"] + selected_columns]

            # Calculate old metrics
            metrics = self.compare_datasets_statistical(df1_f, df2_f)
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
        help_dialog = HelpDialog(self)
        help_dialog.exec_()

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

            # Choose reference
            if self.reference_selector.currentIndex() == 0:
                reference_df = self.df1_aligned
                target_df = self.df2_aligned
            else:
                reference_df = self.df2_aligned
                target_df = self.df1_aligned

            ref_f = reference_df[(reference_df["Time"] >= st) & (reference_df["Time"] <= et)]
            tgt_f = target_df[(target_df["Time"] >= st) & (target_df["Time"] <= et)]

            ref_f = ref_f[["Time"] + selected_columns]
            tgt_f = tgt_f[["Time"] + selected_columns]

            scale_offset_metrics = self.calculate_scale_offset(ref_f, tgt_f)
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
          - Scaled-only data (slope * target)
          - Offset-only data (intercept + target)
          - Scaled+offset (slope * target + intercept)
        """
        try:
            selected_items = self.column_list_widget_tab3.selectedItems()
            selected_columns = [item.text() for item in selected_items]
            if not selected_columns:
                return

            st = self.start_time_spinbox_tab3.value()
            et = self.end_time_spinbox_tab3.value()

            # Choose reference
            if self.reference_selector_tab3.currentIndex() == 0:
                reference_df = self.df1_aligned
                target_df = self.df2_aligned
                ref_name = self.dataset1_name.text() if self.dataset1_name.text() else "Dataset1"
                tgt_name = self.dataset2_name.text() if self.dataset2_name.text() else "Dataset2"
            else:
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

                # scaled-only: slope * (original)
                scaled_only_df[col] = slope * tgt_f[col]
                # offset-only: intercept + (original)
                offset_only_df[col] = intercept + tgt_f[col]
                # scaled+offset
                scaled_offset_df[col] = slope * tgt_f[col] + intercept

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
            plot_title = (f"Comparison:\n"
                          f"{ref_name} (Reference), {tgt_name} (Original), "
                          f"{tgt_name} (Scaled-Only), {tgt_name} (Offset-Only), "
                          f"{tgt_name} (Scaled+Offset)")

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
                fig.add_trace(go.Scatter(
                    x=tgt_df["Time"], y=tgt_df[col],
                    mode="lines",
                    name=f"{tgt_name} (Original) - {col}",
                    line=dict(dash='dot')
                ))
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

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Statistical Metrics Help")
        self.setMinimumSize(800, 600)

        # Layout
        layout = QVBoxLayout()

        # MarkdownView for displaying Markdown content
        self.markdown_view = MarkdownView(self)

        # Load the Markdown content
        markdown_content = """
        # Statistical Metrics Help Document

        ## 1. Mean Squared Error (MSE)
        **Formula:**
        $$ \\text{MSE} = \\frac{1}{n} \\sum_{i=1}^{n} (x_i - y_i)^2 $$

        **Meaning:**  
        MSE measures the average squared difference between actual values \(x\) and predicted values \(y\). Smaller MSE values indicate better model accuracy.

        **Practical Use Case:**  
        - Evaluating the accuracy of stress-strain predictions in finite element analysis.  
        - Quantifying the error in temperature sensor measurements compared to a standard reference.

        ---

        ## 2. Root Mean Squared Error (RMSE)
        **Formula:**
        $$ \\text{RMSE} = \\sqrt{\\text{MSE}} $$

        **Meaning:**  
        RMSE is the square root of MSE. It provides the error magnitude in the same units as the data.

        **Practical Use Case:**  
        - Comparing vibration amplitude predictions against measured data.  
        - Assessing the accuracy of dynamic pressure models in fluid mechanics.

        ---

        ## 3. Absolute Error (\(\Delta\))
        **Formula:**
        $$ \\text{Absolute Error} = |x - y| $$

        **Meaning:**  
        Measures the absolute difference between actual and predicted values without considering the direction of the error.

        **Practical Use Case:**  
        - Evaluating alignment errors in rotating machinery measurements.  
        - Comparing load cell readings during tensile testing.

        ---

        ## 4. Percentage Error
        **Formula:**
        $$ \\text{Percentage Error} = \\frac{|x - y|}{x} \\times 100\\% $$

        **Meaning:**  
        Quantifies errors as a percentage of the actual values. Helps normalize error measurement.

        **Practical Use Case:**  
        - Analyzing deviation in power output between simulated and experimental results for turbines.  
        - Evaluating error percentages in fatigue life predictions.

        ---

        ## 5. Symmetric Mean Absolute Percentage Error (SMAPE)
        **Formula:**
        $$ \\text{SMAPE} = \\frac{1}{n} \\sum_{i=1}^{n} \\frac{|x_i - y_i|}{\\frac{|x_i| + |y_i|}{2}} \\times 100\\% $$

        **Meaning:**  
        Normalizes percentage errors and avoids large values caused by near-zero actual values.

        **Practical Use Case:**  
        - Comparing strain gauge measurements across different time periods.  
        - Evaluating thermal expansion model predictions versus experimental data.

        ---

        ## 6. Pearson Correlation Coefficient (PCC or R)
        **Formula:**
        $$ \\text{PCC} = \\frac{\\text{Cov}(x, y)}{\\sigma_x \\cdot \\sigma_y} $$

        Where:
        - \(\\text{Cov}(x, y)\\): Covariance of \(x\) and \(y\).  
        - \(\\sigma_x, \\sigma_y\\): Standard deviations of \(x\\) and \(y\\).

        **Meaning:**  
        Measures the linear relationship between two datasets. Values range from -1 (perfect negative correlation) to 1 (perfect positive correlation).

        **Practical Use Case:**  
        - Identifying relationships between torque and rotational speed in engines.  
        - Analyzing time lag correlations between hydraulic system pressure and flow rates.

        ---

        ## 7. Coefficient of Determination (\(R^2\))
        **Formula:**
        $$ R^2 = 1 - \\frac{\\text{SS}_{\\text{residual}}}{\\text{SS}_{\\text{total}}} $$

        Where:
        - \(\\text{SS}_{\\text{residual}} = \\sum (x - y)^2\\): Residual sum of squares.  
        - \(\\text{SS}_{\\text{total}} = \\sum (x - \\bar{x})^2\\): Total sum of squares.

        **Meaning:**  
        Indicates the proportion of variance in the dependent variable explained by the independent variable.

        **Values:**  
        - \(R^2 = 1\): Perfect fit.  
        - \(R^2 = 0\): Model explains no variance.  
        - \(R^2 < 0\): Model performs worse than a horizontal line at the mean of the data.

        **Practical Use Case:**  
        - Evaluating the goodness-of-fit for force-displacement models in structural analysis.  
        - Comparing predicted and measured stress-strain curves.

        ---

        ## 8. Maximum Correlation Coefficient
        **Formula:**
        $$ \\text{Max Correlation} = \\max(\\text{Cross Correlation Coefficients}) $$

        **Meaning:**  
        Identifies the strongest linear correlation between two datasets across all lags.

        **Practical Use Case:**  
        - Synchronizing signal measurements from two sensors placed at different locations.  
        - Determining the phase relationship in oscillatory systems.

        ---

        ## 9. Lag at Maximum Correlation
        **Meaning:**  
        The time shift (lag) at which the maximum correlation occurs.

        **Practical Use Case:**  
        - Identifying time delays in the response of a system to an applied load.  
        - Analyzing phase shifts in vibration or acoustic signals.

        ---

        ## Practical Notes
        - **Data Scaling:** Ensure data is normalized or standardized where necessary.  
        - **Outlier Handling:** Remove or analyze outliers separately as they can significantly affect metrics.  
        - **Choose Metrics Wisely:** The choice of metric depends on the specific use case and dataset characteristics.
        """
        self.markdown_view.setValue(markdown_content)
        layout.addWidget(self.markdown_view)

        # Close Button
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)

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
