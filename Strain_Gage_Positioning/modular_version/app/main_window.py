# File: app/main_window.py

import os
import sys
import pandas as pd
import numpy as np
import pyvista as pv
from pathlib import Path

from PyQt5.QtWidgets import (QMainWindow, QHBoxLayout, QWidget, QFileDialog,
                             QMessageBox, QDockWidget, QTableWidget, QTableWidgetItem,
                             QAction, QVBoxLayout, QHeaderView)
from PyQt5.QtCore import Qt, QCoreApplication
from pyvistaqt import MainWindow as PyVistaMainWindow

from .ui_components import ControlPanel, VisualizationPanel, InputDataPanel
from .ui_tools import DistanceMeasureUI
from .analysis_engine import AnalysisEngine
from . import tooltips as tips


class MainWindow(QMainWindow):
    """
    The main application window. This class is the "Controller" in the MVC design pattern.
    Its primary roles are:
    1. Assembling the UI from various components (ControlPanel, VisualizationPanel).
    2. Connecting signals from the UI (View) to trigger actions in the logic (Model).
    3. Receiving signals from the logic (Model) and updating the UI (View) with the results.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Strain Gage Positioning Tool v0.4")
        self.resize(1400, 900)

        # --- Application State ---
        self.project_dir = os.getcwd()
        self.input_file = None
        self.display_in_strain = False
        self.engine_thread = None
        self.last_results = {}  # Cache for visualization refreshes

        # --- UI Setup ---
        self._setup_ui()
        self._apply_tooltips()
        self._connect_signals()

    def _setup_ui(self):
        """Creates and arranges all UI components."""
        main_widget = QWidget()
        main_widget.setObjectName("AppCentralWidget")
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Instantiate our custom UI components
        self.input_panel = InputDataPanel()
        self.control_panel = ControlPanel()
        self.visualization_panel = VisualizationPanel(self.control_panel)

        left_column = QVBoxLayout()
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.addWidget(self.input_panel)
        left_column.addWidget(self.control_panel)
        left_container = QWidget()
        left_container.setLayout(left_column)

        main_layout.addWidget(left_container)
        main_layout.addWidget(self.visualization_panel)

        # Attach the distance measurement UI tool to the plotter
        self.distance_tool = DistanceMeasureUI(self.visualization_panel.vtk_widget, units="mm")

        # Create other UI elements like menus and docks
        self._create_menu_bar()
        self._create_candidate_table_dock()

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
        header = self.candidate_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
        self.candidate_table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { background-color: lightgray; font-weight: bold; }")
        self.candidate_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.candidate_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.candidate_table_dock.setWidget(self.candidate_table)
        self.addDockWidget(Qt.RightDockWidgetArea, self.candidate_table_dock)
        self.candidate_table_dock.hide()

        # Camera fly-to on row click
        self.candidate_table.cellClicked.connect(self.on_candidate_table_cell_clicked)

    def _apply_tooltips(self):
        """Applies all tooltips to the main window's widgets."""
        # Tooltips for controls are now handled within their respective panel classes.
        self.action_set_proj.setToolTip(tips.SET_PROJECT_DIR)
        self.action_show_table.setToolTip(tips.SHOW_TABLE)
        self.action_display_strain.setToolTip(tips.DISPLAY_STRAIN)

    def _connect_signals(self):
        """Connect the Model, View, and Controller components."""
        # --- Control Panel (View) -> MainWindow (Controller) ---
        self.control_panel.analysis_requested.connect(self.run_analysis)
        self.input_panel.file_load_requested.connect(self.load_strain_data)

        # --- Menu Actions (View) -> MainWindow (Controller) ---
        self.action_show_table.toggled.connect(self.toggle_candidate_table)
        self.action_display_strain.toggled.connect(self.toggle_display_mode)

        # --- Visualization Panel (View) -> MainWindow (Controller) ---
        self.visualization_panel.visualization_settings_changed.connect(self.refresh_visualization)

    def set_project_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Project Directory", self.project_dir)
        if directory:
            self.project_dir = directory

    def load_strain_data(self):
        fnames, _ = QFileDialog.getOpenFileNames(self, "Select Strain Data File(s)", self.project_dir,
                                                 "Text Files (*.txt *.dat)")
        if fnames:
            # Store as list for multi-file support, or single path otherwise
            self.input_file = fnames if len(fnames) > 1 else fnames[0]
            # Label: show first file name (+ count if multiple)
            if isinstance(self.input_file, list):
                first = Path(self.input_file[0]).name
                count = len(self.input_file)
                label = f"{first} (+{count-1} more)" if count > 1 else first
            else:
                label = Path(self.input_file).name
            self.input_panel.set_file_label(label)
            self.last_results = {}  # Invalidate cache

    def toggle_display_mode(self, checked):
        self.display_in_strain = checked
        if self.input_file:
            # Rerun analysis with the new display unit setting
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

        QCoreApplication.processEvents()  # Allow UI to update before long computation
        self.engine_thread.run()

    def on_analysis_complete(self, coords, scalars, candidates_df):
        """Slot to receive results from the engine and update the view."""
        self.control_panel.set_button_state_ready()

        if candidates_df.empty and self.control_panel.get_parameters()["strategy"] == "Region of Interest (ROI) Search":
            QMessageBox.warning(self, "ROI Empty", "No data points found within the specified Region of Interest.")

        output_path = os.path.join(self.project_dir, "strain_candidate_points.csv")
        candidates_df.to_csv(output_path, index=False, float_format="%.6e")

        # Decide whether to preserve camera based on whether we have a prior scene
        preserve_camera = bool(self.last_results)
        self.last_results = {'coords': coords, 'scalars': scalars, 'candidates_df': candidates_df}

        # Update legend limits from current data so clim matches the dataset
        if len(scalars) > 0:
            self.visualization_panel.set_legend_limits(float(np.min(scalars)), float(np.max(scalars)))

        # Draw directly, resetting camera on the first render to fit the data bounds
        self.display_strain_with_candidates(coords, scalars, candidates_df, preserve_camera=preserve_camera)

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
        plotter = self.visualization_panel.vtk_widget
        camera = plotter.camera.copy() if preserve_camera else None
        plotter.clear()
        if camera:
            plotter.camera = camera
        else:
            plotter.reset_camera()

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
        plotter = self.visualization_panel.vtk_widget
        viz_settings = self.visualization_panel.get_settings()

        cloud = pv.PolyData(coords)
        cloud["Scalars"] = scalars
        scalar_title = "Strain (mm/mm)" if self.display_in_strain else "Microstrain (με)"

        plotter.add_mesh(
            cloud, scalars="Scalars", cmap="jet",
            point_size=viz_settings['cloud_point_size'],
            render_points_as_spheres=True,
            clim=(viz_settings['clim_min'], viz_settings['clim_max']),
            below_color=viz_settings['below_color'],
            above_color=viz_settings['above_color'],
            scalar_bar_args={'title': scalar_title}
        )

        if not candidates_df.empty:
            candidate_points = pv.PolyData(candidates_df[['X', 'Y', 'Z']].values)
            plotter.add_mesh(candidate_points, color="magenta",
                             point_size=viz_settings['candidate_point_size'],
                             render_points_as_spheres=True)

            strategy = self.control_panel.get_parameters()["strategy"]
            if "Gradient" in strategy:
                values = candidates_df['Local_Std'].values
                labels = [f"P{i + 1}\nStd: {v:.2e}" for i, v in enumerate(values)]
            else:
                values = candidates_df['Quality'].values
                max_val = values.max() if len(values) > 0 and values.max() > 0 else 1.0
                labels = [f"P{i + 1}\nQ: {v / max_val * 100:.1f}%" for i, v in enumerate(values)]

            plotter.add_point_labels(candidate_points, labels,
                                     font_size=viz_settings['label_font_size'],
                                     shape_color="#E9E1D4", always_visible=True, shadow=True)

        if not preserve_camera: plotter.reset_camera()
        plotter.render()

    def display_kmeans_preview(self, coords, cluster_labels):
        self.clear_visualization(preserve_camera=False)
        plotter = self.visualization_panel.vtk_widget
        viz_settings = self.visualization_panel.get_settings()

        cloud = pv.PolyData(coords)
        cloud["Cluster"] = cluster_labels
        plotter.add_mesh(cloud, scalars="Cluster", cmap="plasma",
                         point_size=viz_settings['cloud_point_size'],
                         render_points_as_spheres=True,
                         scalar_bar_args={'title': "Cluster ID"})
        plotter.add_text("K-Means Preview. Press 'Continue' to select points.",
                         position='upper_left', font_size=14)
        plotter.reset_camera()
        plotter.render()

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

        # Auto-size columns and adjust dock width so all columns are visible
        header = self.candidate_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.candidate_table.resizeColumnsToContents()
        total_width = int(header.length() + self.candidate_table.verticalHeader().width() + self.candidate_table.frameWidth() * 2 + 32)
        self.candidate_table_dock.setMinimumWidth(total_width)
        self.candidate_table_dock.resize(total_width, self.candidate_table_dock.height())

    def on_candidate_table_cell_clicked(self, row, column):
        """
        Fly the camera to the XYZ position of the clicked candidate row.

        Behavior:
        - Reads the table's column headers to locate the 'X', 'Y', 'Z' columns (robust to column order).
        - Parses the numeric values from the clicked row (ignores empty / N/A cells).
        - Uses PyVista's fly_to for a smooth camera transition; falls back to setting the
          camera focal point if fly_to is unavailable in the installed version.
        """
        try:
            # Determine indices of coordinate columns by header name, so this logic
            # remains valid even if the table column order changes in the future.
            headers = [self.candidate_table.horizontalHeaderItem(i).text() for i in range(self.candidate_table.columnCount())]
            x_idx = headers.index('X') if 'X' in headers else None
            y_idx = headers.index('Y') if 'Y' in headers else None
            z_idx = headers.index('Z') if 'Z' in headers else None
            if x_idx is None or y_idx is None or z_idx is None:
                return

            # Helper to get and safely convert a cell's text to float.
            def get_val(col_idx):
                item = self.candidate_table.item(row, col_idx)
                return float(item.text()) if item and item.text() not in (None, '', 'N/A') else None

            x = get_val(x_idx); y = get_val(y_idx); z = get_val(z_idx)
            if x is None or y is None or z is None:
                return

            plotter = self.visualization_panel.vtk_widget
            try:
                # Preferred smooth navigation when available (PyVista >= certain versions).
                plotter.fly_to((float(x), float(y), float(z)))
            except Exception:
                # Fallback for environments without fly_to: directly move camera focal point.
                cam = plotter.camera
                cam.focal_point = (float(x), float(y), float(z))
                plotter.render()
        except Exception:
            pass

    def toggle_candidate_table(self, checked):
        if checked:
            self.candidate_table_dock.show()
            output_path = os.path.join(self.project_dir, "strain_candidate_points.csv")
            self.update_candidate_table(output_path)
        else:
            self.candidate_table_dock.hide()

    def closeEvent(self, event):
        """Ensure the application and any VTK elements close cleanly."""
        self.visualization_panel.vtk_widget.close()
        event.accept()