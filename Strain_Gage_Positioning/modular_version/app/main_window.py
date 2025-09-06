# File: app/main_window.py

import os
import sys
import pandas as pd
import numpy as np
import pyvista as pv
from pathlib import Path

from PyQt5.QtWidgets import (QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QFileDialog,
                             QMessageBox, QDockWidget, QTableWidget, QTableWidgetItem,
                             QGroupBox, QAction, QLabel, QComboBox, QSpinBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QCoreApplication

# pyvistaqt is an optional dependency, so we handle the import gracefully
try:
    from pyvistaqt import QtInteractor, MainWindow as PyVistaMainWindow
except ImportError:
    print("Error: pyvistaqt is required. Please install it using 'pip install pyvistaqt'")
    sys.exit(1)

# Import our new components
from .ui_components import ControlPanel
from .analysis_engine import AnalysisEngine
from . import tooltips as tips


class MainWindow(QMainWindow):
    """
    The main application window. This class is the "Controller" in the MVC pattern.
    Its primary roles are:
    1. Assembling the UI from various components (ControlPanel, VisualizationPanel).
    2. Connecting signals from the UI (View) to trigger actions in the logic (Model).
    3. Receiving signals from the logic (Model) and updating the UI (View) with the results.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Strain Gage Positioning Tool v1.0 (MVC)")
        self.resize(1400, 900)

        # --- Application State ---
        self.project_dir = os.getcwd()
        self.input_file = None
        self.display_in_strain = False  # Default is microstrain
        self.engine_thread = None  # To hold a reference to the running engine
        self.last_results = {}  # Cache for visualization refreshes

        # --- UI Setup ---
        self._setup_ui()
        self._apply_tooltips()
        self._connect_signals()

    def _setup_ui(self):
        """Creates and arranges all UI components."""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Instantiate our custom UI components
        self.control_panel = ControlPanel()
        visualization_panel = self._create_visualization_panel()

        main_layout.addWidget(self.control_panel)
        main_layout.addWidget(visualization_panel)

        # Create other UI elements like menus and docks
        self._create_menu_bar()
        self._create_candidate_table_dock()

    def _create_visualization_panel(self):
        """Creates the right-side panel containing the PyVista plot and its controls."""
        right_side_widget = QWidget()
        layout = QVBoxLayout(right_side_widget)
        layout.setContentsMargins(5, 5, 5, 5)

        group_box_style = self.control_panel.styleSheet()

        # --- Graphical and Legend Controls ---
        graphical_group = QGroupBox("Graphical Controls")
        graphical_group.setStyleSheet(group_box_style)
        graphical_layout = QHBoxLayout(graphical_group)
        self.dspin_cloud_point_size = QDoubleSpinBox();
        self.dspin_cloud_point_size.setRange(1.0, 50.0);
        self.dspin_cloud_point_size.setValue(10.0)
        self.dspin_candidate_point_size = QDoubleSpinBox();
        self.dspin_candidate_point_size.setRange(1.0, 50.0);
        self.dspin_candidate_point_size.setValue(20.0)
        self.spin_label_font_size = QSpinBox();
        self.spin_label_font_size.setRange(8, 72);
        self.spin_label_font_size.setValue(20)
        graphical_layout.addWidget(QLabel("Cloud Size:"));
        graphical_layout.addWidget(self.dspin_cloud_point_size)
        graphical_layout.addWidget(QLabel("Candidate Size:"));
        graphical_layout.addWidget(self.dspin_candidate_point_size)
        graphical_layout.addWidget(QLabel("Label Size:"));
        graphical_layout.addWidget(self.spin_label_font_size)
        graphical_layout.addStretch(1)

        self.legend_group = QGroupBox("Legend Controls")
        self.legend_group.setStyleSheet(group_box_style)
        self.legend_layout = QHBoxLayout(self.legend_group)
        self.dspin_above_limit = QDoubleSpinBox();
        self.dspin_above_limit.setRange(-1e9, 1e9);
        self.dspin_above_limit.setValue(1.0)
        self.dspin_below_limit = QDoubleSpinBox();
        self.dspin_below_limit.setRange(-1e9, 1e9);
        self.dspin_below_limit.setValue(0.0)
        self.combo_above_color = QComboBox();
        self.combo_above_color.addItems(["Purple", "White"])
        self.combo_below_color = QComboBox();
        self.combo_below_color.addItems(["Gray", "White"])
        self.legend_layout.addWidget(QLabel("Upper Limit:"));
        self.legend_layout.addWidget(self.dspin_above_limit)
        self.legend_layout.addWidget(QLabel("Lower Limit:"));
        self.legend_layout.addWidget(self.dspin_below_limit)
        self.legend_layout.addWidget(QLabel("Above Color:"));
        self.legend_layout.addWidget(self.combo_above_color)
        self.legend_layout.addWidget(QLabel("Below Color:"));
        self.legend_layout.addWidget(self.combo_below_color)
        self.legend_layout.addStretch(1)

        # --- PyVista Interactor ---
        self.vtk_widget = QtInteractor(right_side_widget)
        self.global_axes = self.vtk_widget.add_axes(interactive=False)
        viewport = (0.0, 0.0, 0.25, 0.25)
        self.vtk_widget.add_axes(interactive=True, viewport=viewport)

        layout.addWidget(graphical_group)
        layout.addWidget(self.legend_group)
        layout.addWidget(self.vtk_widget.interactor)
        return right_side_widget

    def _create_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        self.action_set_proj = QAction("Set Project Directory", self)
        self.action_set_proj.triggered.connect(self.set_project_directory)
        file_menu.addAction(self.action_set_proj)

        view_menu = menubar.addMenu("Display")
        self.action_show_table = QAction("Table of Candidate Points", self, checkable=True)
        view_menu.addAction(self.action_show_table)

        self.action_display_strain = QAction("Results in Strain (mm/mm)", self, checkable=True)
        view_menu.addAction(self.action_display_strain)

    def _create_candidate_table_dock(self):
        self.candidate_table_dock = QDockWidget("Candidate Points", self)
        self.candidate_table = QTableWidget()
        self.candidate_table.setAlternatingRowColors(True)
        self.candidate_table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { background-color: lightgray; font-weight: bold; }")
        self.candidate_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.candidate_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.candidate_table_dock.setWidget(self.candidate_table)
        self.addDockWidget(Qt.RightDockWidgetArea, self.candidate_table_dock)
        self.candidate_table_dock.hide()

    def _apply_tooltips(self):
        """Applies all tooltips to the main window's widgets."""
        # Menu Actions
        self.action_set_proj.setToolTip(tips.SET_PROJECT_DIR)
        self.action_show_table.setToolTip(tips.SHOW_TABLE)
        self.action_display_strain.setToolTip(tips.DISPLAY_STRAIN)

        # Visualization Controls
        self.dspin_cloud_point_size.setToolTip(tips.CLOUD_POINT_SIZE)
        self.dspin_candidate_point_size.setToolTip(tips.CANDIDATE_POINT_SIZE)
        self.spin_label_font_size.setToolTip(tips.LABEL_FONT_SIZE)
        self.legend_group.setToolTip(tips.LEGEND_CONTROLS)

    def _connect_signals(self):
        """Connect the Model, View, and Controller components."""
        # --- Control Panel (View) -> MainWindow (Controller) ---
        self.control_panel.analysis_requested.connect(self.run_analysis)
        self.control_panel.file_load_requested.connect(self.load_strain_data)

        # --- Menu Actions (View) -> MainWindow (Controller) ---
        self.action_show_table.toggled.connect(self.toggle_candidate_table)
        self.action_display_strain.toggled.connect(self.toggle_display_mode)

        # --- Visualization Controls (View) -> MainWindow (Controller) ---
        for widget in [self.dspin_cloud_point_size, self.dspin_candidate_point_size,
                       self.spin_label_font_size, self.dspin_above_limit, self.dspin_below_limit,
                       self.combo_above_color, self.combo_below_color]:
            if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                widget.valueChanged.connect(self.refresh_visualization)
            else:
                widget.currentIndexChanged.connect(self.refresh_visualization)

    def set_project_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Project Directory", self.project_dir)
        if directory:
            self.project_dir = directory

    def load_strain_data(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select Strain Data File", self.project_dir,
                                               "Text Files (*.txt *.dat)")
        if fname:
            self.input_file = fname
            self.control_panel.set_file_label(Path(fname).name)
            self.last_results = {}  # Invalidate cache

    def toggle_display_mode(self, checked):
        self.display_in_strain = checked
        if self.input_file:
            self.run_analysis(is_continued_kmeans=False)

    def run_analysis(self, is_continued_kmeans=False):
        """Slot to create and start the analysis engine."""
        if not self.input_file:
            QMessageBox.warning(self, "Input Error", "Please load a strain data file first.")
            return

        params = self.control_panel.get_parameters()
        self.control_panel.set_button_state_running()

        self.engine_thread = AnalysisEngine(self.input_file, params, self.display_in_strain, is_continued_kmeans)
        self.engine_thread.analysis_complete.connect(self.on_analysis_complete)
        self.engine_thread.analysis_failed.connect(self.on_analysis_failed)
        self.engine_thread.kmeans_preview_ready.connect(self.on_kmeans_preview_ready)

        # NOTE: For a long-running analysis, you would move the engine to a QThread.
        # For simplicity here, we run it directly.
        QCoreApplication.processEvents()  # Allow UI to update
        self.engine_thread.run()

    def on_analysis_complete(self, coords, scalars, candidates_df):
        """Slot to receive results from the engine and update the view."""
        self.control_panel.set_button_state_ready()

        if candidates_df.empty and self.control_panel.get_parameters()["strategy"] == "Region of Interest (ROI) Search":
            QMessageBox.warning(self, "ROI Empty", "No data points found within the specified Region of Interest.")

        # Save results to a file
        output_path = os.path.join(self.project_dir, "strain_candidate_points.csv")
        candidates_df.to_csv(output_path, index=False, float_format="%.6e")

        # Cache results for refreshes
        self.last_results = {'coords': coords, 'scalars': scalars, 'candidates_df': candidates_df}

        # Update UI components
        if len(scalars) > 0:
            self.dspin_below_limit.setValue(np.min(scalars))
            self.dspin_above_limit.setValue(np.max(scalars))

        self.refresh_visualization()
        self.update_candidate_table(output_path)

    def on_kmeans_preview_ready(self, coords, cluster_labels):
        """Slot to handle the K-Means preview step."""
        self.control_panel.set_button_state_kmeans_continue()
        self.display_kmeans_preview(coords, cluster_labels)

    def on_analysis_failed(self, error_message):
        """Slot to handle errors reported by the engine."""
        QMessageBox.critical(self, "Analysis Failed", error_message)
        self.control_panel.set_button_state_ready()

    def clear_visualization(self, preserve_camera=False):
        camera = self.vtk_widget.camera.copy() if preserve_camera else None
        self.vtk_widget.clear()
        self.vtk_widget.renderer.AddActor(self.global_axes)
        self.camera_widget.EnabledOn()
        if camera:
            self.vtk_widget.camera = camera
        else:
            self.vtk_widget.reset_camera()

    def refresh_visualization(self):
        """Redraws the main plot using cached data and current graphical settings."""
        if not self.last_results:
            return

        self.display_strain_with_candidates(
            self.last_results['coords'],
            self.last_results['scalars'],
            self.last_results['candidates_df'],
            preserve_camera=True
        )

    def display_strain_with_candidates(self, coords, scalars, candidates_df, preserve_camera=False):
        self.clear_visualization(preserve_camera=preserve_camera)
        cloud = pv.PolyData(coords)
        cloud["Scalars"] = scalars

        scalar_title = "Strain (mm/mm)" if self.display_in_strain else "Microstrain (με)"

        self.vtk_widget.add_mesh(
            cloud, scalars="Scalars", cmap="jet",
            point_size=self.dspin_cloud_point_size.value(),
            render_points_as_spheres=True,
            clim=(self.dspin_below_limit.value(), self.dspin_above_limit.value()),
            below_color=self.combo_below_color.currentText().lower(),
            above_color=self.combo_above_color.currentText().lower(),
            scalar_bar_args={'title': scalar_title}
        )

        if not candidates_df.empty:
            candidate_points = pv.PolyData(candidates_df[['X', 'Y', 'Z']].values)
            self.vtk_widget.add_mesh(candidate_points, color="magenta",
                                     point_size=self.dspin_candidate_point_size.value(),
                                     render_points_as_spheres=True)

            strategy = self.control_panel.get_parameters()["strategy"]
            if "Gradient" in strategy:
                values = candidates_df['Local_Std'].values
                labels = [f"P{i + 1}\nStd: {v:.2e}" for i, v in enumerate(values)]
            else:
                values = candidates_df['Quality'].values
                max_val = values.max() if len(values) > 0 and values.max() > 0 else 1.0
                labels = [f"P{i + 1}\nQ: {v / max_val * 100:.1f}%" for i, v in enumerate(values)]

            self.vtk_widget.add_point_labels(candidate_points, labels,
                                             font_size=self.spin_label_font_size.value(),
                                             shape_color="#E9E1D4", always_visible=True, shadow=True)

        if not preserve_camera: self.vtk_widget.reset_camera()
        self.vtk_widget.render()

    def display_kmeans_preview(self, coords, cluster_labels):
        self.clear_visualization(preserve_camera=False)
        cloud = pv.PolyData(coords)
        cloud["Cluster"] = cluster_labels
        self.vtk_widget.add_mesh(cloud, scalars="Cluster", cmap="viridis",
                                 point_size=self.dspin_cloud_point_size.value(),
                                 render_points_as_spheres=True,
                                 scalar_bar_args={'title': "Cluster ID"})
        self.vtk_widget.add_text("K-Means Preview. Press 'Continue' to select points.",
                                 position='upper_left', font_size=14)
        self.vtk_widget.reset_camera()
        self.vtk_widget.render()

    def update_candidate_table(self, csv_filepath):
        if not os.path.exists(csv_filepath): return
        try:
            df = pd.read_csv(csv_filepath)
        except Exception as e:
            print(f"Error reading candidate CSV for table: {e}")
            return

        self.candidate_table.clear()
        self.candidate_table.setRowCount(len(df))
        self.candidate_table.setColumnCount(len(df.columns))
        self.candidate_table.setHorizontalHeaderLabels(df.columns.tolist())

        for row_idx, row_data in df.iterrows():
            for col_idx, col_name in enumerate(df.columns):
                cell_value = row_data[col_name]
                if pd.isna(cell_value):
                    item_text = "N/A"
                elif isinstance(cell_value, (int, np.integer)):
                    item_text = f"{cell_value}"
                elif isinstance(cell_value, (float, np.floating)):
                    item_text = f"{cell_value:.4g}"
                else:
                    item_text = str(cell_value)
                item = QTableWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignCenter)
                self.candidate_table.setItem(row_idx, col_idx, item)
        self.candidate_table.resizeColumnsToContents()

    def toggle_candidate_table(self, checked):
        if checked:
            self.candidate_table_dock.show()
            output_path = os.path.join(self.project_dir, "strain_candidate_points.csv")
            self.update_candidate_table(output_path)
        else:
            self.candidate_table_dock.hide()

    def closeEvent(self, event):
        """Ensure the application and any VTK elements close cleanly."""
        self.vtk_widget.close()
        event.accept()