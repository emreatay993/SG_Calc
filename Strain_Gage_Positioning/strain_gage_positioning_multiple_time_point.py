import sys
import os
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
import pyvista as pv
from sklearn.cluster import KMeans

# PyQt5 and pyvistaqt imports
from PyQt5.QtWidgets import (QMainWindow, QApplication, QFileDialog, QVBoxLayout,
                             QHBoxLayout, QWidget, QPushButton, QLabel, QComboBox,
                             QSpinBox, QDoubleSpinBox, QMenuBar, QAction, QMessageBox,
                             QDockWidget, QTableWidget, QTableWidgetItem, QGroupBox)
from PyQt5.QtCore import Qt
from pyvistaqt import QtInteractor

# ================================
# STRAIN AND QUALITY COMPUTATION
# ================================
def compute_normal_strains(strain_data, angles):
    """Compute the normal strain for each node and angle."""
    angles_rad = np.radians(angles)
    cos_t = np.cos(angles_rad)
    sin_t = np.sin(angles_rad)
    exx = strain_data[:, 0][:, np.newaxis]
    eyy = strain_data[:, 1][:, np.newaxis]
    exy = strain_data[:, 2][:, np.newaxis]
    return exx * cos_t ** 2 + eyy * sin_t ** 2 + 1.0 * exy * sin_t * cos_t

def compute_quality_metrics(nodes, coords, strains, angles, quality_mode="Signal-Noise Ratio: |ε|/(σ+1e-12)",
                            uniformity_radius=1.0):
    """
    Computes the best strain, best angle, local standard deviation, and quality metric.
    Returns a DataFrame with the node information.
    """
    best_idx = np.argmax(np.abs(strains), axis=1)
    best_strains = strains[np.arange(len(strains)), best_idx]
    best_angles = np.array(angles)[best_idx]
    if len(angles) == 1:
        best_angles = np.full(len(nodes), np.nan)
    tree = cKDTree(coords)
    local_std = np.zeros(len(nodes))
    for i, point in enumerate(coords):
        indices = tree.query_ball_point(point, uniformity_radius)
        local_std[i] = np.std(best_strains[indices])
    abs_strain = np.abs(best_strains)
    if quality_mode == "Default: |ε|/(1+σ)":
        quality = abs_strain / (1.0 + local_std)
    elif quality_mode == "Squared: |ε|/(1+σ²)":
        quality = abs_strain / (1.0 + local_std ** 2)
    elif quality_mode == "Exponential: |ε|·exp(–1000σ)":
        quality = abs_strain * np.exp(-1000 * local_std)
    elif quality_mode == "Signal-Noise Ratio: |ε|/(σ+1e-12)":
        epsilon = 1e-12
        quality = abs_strain / (local_std + epsilon)
    else:
        raise ValueError(f"Unknown quality_mode: {quality_mode}")
    return pd.DataFrame({
        'Node': nodes,
        'X': coords[:, 0],
        'Y': coords[:, 1],
        'Z': coords[:, 2],
        'Best_Strain': best_strains,
        'Best_Angle': best_angles,
        'Local_Std': local_std,
        'Quality': quality
    })

# -------------------------------
# AGGREGATION FUNCTION (ADDED)
# -------------------------------
def aggregate_quality_metrics(quality_dfs, agg_method="max"):
    """Aggregate multiple quality metric DataFrames into a single DataFrame.
    Aggregation can be 'max' or 'average'.
    """
    if not quality_dfs:
        raise ValueError("No quality dataframes provided for aggregation.")
    agg_method = agg_method.lower()
    agg_quality = quality_dfs[0]["Quality"].values.copy()
    if agg_method == "max":
        for df in quality_dfs[1:]:
            agg_quality = np.maximum(agg_quality, df["Quality"].values)
    elif agg_method == "average":
        for df in quality_dfs[1:]:
            agg_quality += df["Quality"].values
        agg_quality /= len(quality_dfs)
    else:
        raise ValueError(f"Unknown aggregation method: {agg_method}")
    agg_df = quality_dfs[0].copy()
    agg_df["Quality"] = agg_quality
    return agg_df

# -------------------------------
# CANDIDATE SELECTION FUNCTIONS
# -------------------------------
def greedy_selection(df, min_distance, candidate_count):
    """Select candidate points by greedily enforcing a minimum spatial distance."""
    selected = []
    selected_coords = []
    for _, row in df.iterrows():
        point = np.array([row['X'], row['Y'], row['Z']])
        if not selected_coords or np.all(np.linalg.norm(np.array(selected_coords) - point, axis=1) >= min_distance):
            selected.append(row)
            selected_coords.append(point)
        if len(selected) >= candidate_count:
            break
    return pd.DataFrame(selected)

# MODIFIED: Added optional precomputed_df parameter.
def select_candidate_points(nodes, coords, strains, angles, candidate_count,
                            min_distance, uniformity_radius, quality_mode="original", precomputed_df=None):
    """Quality-based candidate selection using a greedy algorithm.
    If precomputed_df is provided, it will be used instead of computing quality metrics.
    """
    if precomputed_df is None:
        df = compute_quality_metrics(nodes, coords, strains, angles, quality_mode, uniformity_radius)
    else:
        df = precomputed_df
    df_sorted = df.sort_values(by='Quality', ascending=False)
    return greedy_selection(df_sorted, min_distance, candidate_count)

# MODIFIED: Added optional precomputed_df parameter.
def select_candidate_points_spatial_quality(nodes, coords, strains, angles, candidate_count,
                                            uniformity_radius, quality_mode="Signal-Noise Ratio: |ε|/(σ+1e-12)",
                                            precomputed_df=None):
    """
    Improved candidate selection that uses KMeans clustering to partition nodes.
    If precomputed_df is provided, it will be used instead of computing quality metrics.
    """
    if precomputed_df is None:
        df = compute_quality_metrics(nodes, coords, strains, angles, quality_mode, uniformity_radius)
    else:
        df = precomputed_df
    kmeans = KMeans(n_clusters=candidate_count, random_state=42).fit(coords)
    labels = kmeans.labels_
    candidate_rows = []
    for cluster in range(candidate_count):
        cluster_df = df[labels == cluster]
        if not cluster_df.empty:
            best_row = cluster_df.loc[cluster_df['Quality'].idxmax()]
            candidate_rows.append(best_row)
    candidate_df = pd.DataFrame(candidate_rows)
    return candidate_df.sort_values(by='Quality', ascending=False)

# ================================
# DATA INPUT/OUTPUT FUNCTIONS
# ================================
def load_data(input_filename):
    """Reads the input file and returns node, coordinate, and strain tensor information.
    Supports multiple strain tensor inputs if present.
    Assumes txt files to be in text export format of ANSYS Mechanical Result Objects.
    File format: first 4 columns: node, x, y, z; then groups of 4 columns for each strain measurement:
    exx, eyy, (dummy), exy.
    """
    df = pd.read_csv(input_filename, sep='\s+', skiprows=1, header=None)
    if df.shape[1] < 8:
        raise ValueError("Input file does not have the expected coordinate and strain columns.")
    nodes = df.iloc[:, 0].astype(int).values
    coords = df.iloc[:, 1:4].values
    conversion_factor = 1e6
    num_measurements = (df.shape[1] - 4) // 4   # ADDED: support for multiple measurements
    strain_tensors = {}
    for i in range(num_measurements):
        base = 4 + 4 * i
        exx = df.iloc[:, base].values * conversion_factor
        eyy = df.iloc[:, base + 1].values * conversion_factor
        exy = df.iloc[:, base + 3].values * conversion_factor
        strain_tensors[i] = np.column_stack((exx, eyy, exy))
    return nodes, coords, strain_tensors   # MODIFIED: return dictionary of strain tensors

def save_strain_results(output_filename, nodes, coords, strains, header_full):
    """Saves the computed strain results to a CSV file."""
    output_array = np.column_stack((nodes, coords, strains))
    np.savetxt(output_filename, output_array, delimiter=",", fmt="%.6e",
               header=header_full, comments="")

# ================================
# THE MAIN GUI APPLICATION CLASS
# ================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Strain Gage Positioning Tool v0.4")
        self.resize(1200, 800)
        self.project_dir = None
        self.input_file = None
        self.spatial_update_count = 0  # For spatial mode updates
        self.display_in_strain = False

        # Variables to store last visualization parameters.
        self.last_coords = None
        self.last_scalars = None
        self.last_candidates_df = None
        self.last_cloud_point_size = None
        self.last_candidate_point_size = None
        self.last_label_font_size = None

        # Create menu bar.
        self._createMenuBar()

        # Set common stylesheets
        group_box_style = """
        QGroupBox {
            /* Lightly bluish border */
            border: 1px solid #87CEFA;
            border-radius: 5px;
            /* This margin-top creates space for the title
               so it appears to break the border at the top */
            margin-top: 10px;
        }

        QGroupBox::title {
            /* Place the title within the group box margin so
               it looks like it's intersecting the border */
            subcontrol-origin: margin;
            subcontrol-position: top left;
            /* Indent the title a bit from the left edge */
            left: 10px;
            padding: 0 5px;
            /* You can give the title a background
               if you want an even more obvious 'break': */
            background-color: palette(window); 
            color: #3F94D1;  /* Slightly darker blue */
            font-weight: bold;
        }
        """

        # -------------------------------
        # Main Widget & Layout
        # -------------------------------
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # A horizontal layout splits the window into left and right sides.
        main_layout = QHBoxLayout(main_widget)

        # -------------------------------
        # 1) Left Panel: "Positioning Controls"
        # -------------------------------
        # Create a QGroupBox for the left panel.
        self.positioningGroup = QGroupBox("Positioning Controls")
        self.positioningGroup.setFixedWidth(251)
        self.positioningGroup.setStyleSheet(group_box_style)

        cp_layout = QVBoxLayout(self.positioningGroup)
        cp_layout.setAlignment(Qt.AlignTop)

        # Add controls to the Positioning Controls group.
        self.btn_load = QPushButton("Load Strain Data")
        self.btn_load.clicked.connect(self.loadStrainData)
        cp_layout.addWidget(self.btn_load)

        self.lbl_file = QLabel("No file loaded")
        cp_layout.addWidget(self.lbl_file)

        cp_layout.addWidget(QLabel("Measurement Mode:"))
        self.combo_measurement = QComboBox()
        self.combo_measurement.addItems(["Rosette", "Uniaxial"])
        cp_layout.addWidget(self.combo_measurement)

        cp_layout.addWidget(QLabel("Selection Strategy:"))
        self.combo_strategy = QComboBox()
        self.combo_strategy.addItems(["Quality-based (Greedy Search)", "Max Spatial Coverage (K-Means Clustering)"])
        cp_layout.addWidget(self.combo_strategy)

        cp_layout.addWidget(QLabel("Quality Metrics Mode:"))
        self.combo_quality = QComboBox()
        self.combo_quality.addItems([
            "Default: |ε|/(1+σ)",  # Original: Q = |ε|/(1+σ)
            "Squared: |ε|/(1+σ²)",  # Squared: Q = |ε|/(1+σ²)
            "Exponential: |ε|·exp(–1000σ)",  # Exponential: Q = |ε|·exp(–1000σ)
            "Signal-Noise Ratio: |ε|/(σ+1e-12)"  # SNR: Q = |ε|/(σ+1e-12)
        ])
        cp_layout.addWidget(self.combo_quality)

        cp_layout.addWidget(QLabel("Aggregation Method:"))
        self.combo_agg = QComboBox()
        self.combo_agg.addItems(["Max", "Average"])
        cp_layout.addWidget(self.combo_agg)

        cp_layout.addWidget(QLabel("Candidate Points Requested:"))
        self.spin_candidate_count = QSpinBox()
        self.spin_candidate_count.setRange(1, 1000)
        self.spin_candidate_count.setValue(10)
        cp_layout.addWidget(self.spin_candidate_count)

        cp_layout.addWidget(QLabel("Min Distance Between Candidate Points [mm]:"))
        self.dspin_min_distance = QDoubleSpinBox()
        self.dspin_min_distance.setRange(0, 10000)
        self.dspin_min_distance.setValue(10.0)
        cp_layout.addWidget(self.dspin_min_distance)

        cp_layout.addWidget(QLabel("Search Radius for Uniformity [mm]:"))
        self.dspin_uniformity_radius = QDoubleSpinBox()
        self.dspin_uniformity_radius.setRange(0, 1000)
        self.dspin_uniformity_radius.setValue(10.0)
        cp_layout.addWidget(self.dspin_uniformity_radius)

        self.btn_update = QPushButton("Update")
        self.btn_update.clicked.connect(self.updateSimulation)
        cp_layout.addWidget(self.btn_update)

        # Add the positioning group to the main layout (left side).
        main_layout.addWidget(self.positioningGroup)

        # -------------------------------
        # 2) Right Side: Graphical Controls (Top) and Main Screen (Below)
        # -------------------------------
        right_side_widget = QWidget()
        right_side_layout = QVBoxLayout(right_side_widget)
        right_side_layout.setContentsMargins(5, 5, 5, 5)
        right_side_layout.setSpacing(5)

        # a) Top: Graphical Controls Group
        self.graphicalGroup = QGroupBox("Graphical Controls")
        graphicalControlsLayout = QHBoxLayout(self.graphicalGroup)
        self.graphicalGroup.setStyleSheet(group_box_style)

        graphicalControlsLayout.setContentsMargins(5, 5, 5, 5)
        graphicalControlsLayout.setSpacing(10)

        graphicalControlsLayout.addWidget(QLabel("Cloud Point Size:"))
        self.dspin_cloud_point_size = QDoubleSpinBox()
        self.dspin_cloud_point_size.setRange(1.0, 50.0)
        self.dspin_cloud_point_size.setValue(10.0)
        graphicalControlsLayout.addWidget(self.dspin_cloud_point_size)

        graphicalControlsLayout.addWidget(QLabel("Candidate Point Size:"))
        self.dspin_candidate_point_size = QDoubleSpinBox()
        self.dspin_candidate_point_size.setRange(1.0, 50.0)
        self.dspin_candidate_point_size.setValue(20.0)
        graphicalControlsLayout.addWidget(self.dspin_candidate_point_size)

        graphicalControlsLayout.addWidget(QLabel("Label Font Size:"))
        self.spin_label_font_size = QSpinBox()
        self.spin_label_font_size.setRange(8, 72)
        self.spin_label_font_size.setValue(20)
        graphicalControlsLayout.addWidget(self.spin_label_font_size)

        graphicalControlsLayout.addStretch(1)

        # b) Legend Controls Group (for upper/lower limit and color)
        self.legendControlsGroup = QGroupBox("Legend Controls")
        self.legendControlsGroup.setStyleSheet(group_box_style)
        legendControlsLayout = QHBoxLayout(self.legendControlsGroup)
        legendControlsLayout.setContentsMargins(5, 5, 5, 5)
        legendControlsLayout.setSpacing(10)

        legendControlsLayout.addWidget(QLabel("Upper Limit Value:"))
        self.dspin_above_limit = QDoubleSpinBox()
        self.dspin_above_limit.setRange(-1e9, 1e9)
        self.dspin_above_limit.setValue(1.0)
        legendControlsLayout.addWidget(self.dspin_above_limit)

        legendControlsLayout.addWidget(QLabel("Lower Limit Value:"))
        self.dspin_below_limit = QDoubleSpinBox()
        self.dspin_below_limit.setRange(-1e9, 1e9)
        self.dspin_below_limit.setValue(0.0)
        legendControlsLayout.addWidget(self.dspin_below_limit)

        legendControlsLayout.addWidget(QLabel("Upper Limit Color:"))
        self.combo_above_color = QComboBox()
        self.combo_above_color.addItems(["Purple", "White"])
        legendControlsLayout.addWidget(self.combo_above_color)

        legendControlsLayout.addWidget(QLabel("Lower Limit Color:"))
        self.combo_below_color = QComboBox()
        self.combo_below_color.addItems(["Gray", "White"])
        legendControlsLayout.addWidget(self.combo_below_color)

        legendControlsLayout.addStretch(1)

        # Connect immediate update signals so that any change re-renders using the current camera view.
        self.dspin_cloud_point_size.valueChanged.connect(self.refreshVisualization)
        self.dspin_candidate_point_size.valueChanged.connect(self.refreshVisualization)
        self.spin_label_font_size.valueChanged.connect(self.refreshVisualization)
        self.dspin_above_limit.valueChanged.connect(self.refreshVisualization)
        self.dspin_below_limit.valueChanged.connect(self.refreshVisualization)
        self.combo_above_color.currentIndexChanged.connect(self.refreshVisualization)
        self.combo_below_color.currentIndexChanged.connect(self.refreshVisualization)

        # Add the graphical and legend controls group to the right side (top).
        right_side_layout.addWidget(self.graphicalGroup)
        right_side_layout.addWidget(self.legendControlsGroup)


        # c) Main Screen: PyVista Interactor.
        self.vtk_widget = QtInteractor(right_side_widget)
        right_side_layout.addWidget(self.vtk_widget.interactor)

        # Create persistent actors and widgets:
        self.global_axes = self.vtk_widget.add_axes(
            line_width=2,
            color='black',
            xlabel="", ylabel="", zlabel="",
            interactive=False
        )
        self.camera_widget = self.vtk_widget.add_camera_orientation_widget()
        self.camera_widget.EnabledOn()

        # Add the right side widget to the main layout.
        main_layout.addWidget(right_side_widget)

        # -------------------------------
        # 3) Candidate Table Dock Widget (Unchanged)
        # -------------------------------
        self.candidate_table_dock = QDockWidget("Candidate Points", self)
        self.candidate_table = QTableWidget()
        self.candidate_table.setAlternatingRowColors(True)
        self.candidate_table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { background-color: lightgray; font-weight: bold; }"
        )
        self.candidate_table.verticalHeader().setStyleSheet(
            "QHeaderView::section { background-color: lightgray; }"
        )
        self.candidate_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.candidate_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.candidate_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.candidate_table_dock.setWidget(self.candidate_table)
        self.addDockWidget(Qt.RightDockWidgetArea, self.candidate_table_dock)
        self.candidate_table_dock.hide()

    def _createMenuBar(self):
        menubar = self.menuBar()
        # File menu.
        fileMenu = menubar.addMenu("File")
        actionSetProj = QAction("Set Project Directory", self)
        actionSetProj.triggered.connect(self.setProjectDirectory)
        fileMenu.addAction(actionSetProj)
        # View menu.
        viewMenu = menubar.addMenu("Display")
        self.actionShowTable = QAction("Table of Candidate Points", self)
        self.actionShowTable.setCheckable(True)
        self.actionShowTable.toggled.connect(self.toggleCandidateTable)
        self.actionDisplayStrain = QAction("Results in Strain (mm/mm)", self)
        self.actionDisplayStrain.setCheckable(True)
        self.actionDisplayStrain.setChecked(False)  # Default is microstrain.
        self.actionDisplayStrain.triggered.connect(self.toggleDisplayMode)
        viewMenu.addAction(self.actionDisplayStrain)
        viewMenu.addAction(self.actionShowTable)

    def setProjectDirectory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Project Directory", os.getcwd())
        if directory:
            self.project_dir = directory

    def loadStrainData(self):
        start_dir = self.project_dir if self.project_dir else os.getcwd()
        fname, _ = QFileDialog.getOpenFileName(self, "Select Strain Data File", start_dir,
                                               "Text Files (*.txt *.dat);;All Files (*)")
        if fname:
            self.input_file = fname
            self.lbl_file.setText(os.path.basename(fname))
            QMessageBox.information(self, "File Loaded", f"Loaded file:\n{fname}")

    def clearVisualization(self, preserve_camera=False):
        # Clear dynamic actors
        self.vtk_widget.clear()

        # Re‑add the persistent axes
        if hasattr(self, 'global_axes') and self.global_axes is not None:
            self.vtk_widget.renderer.AddActor(self.global_axes)

        # Re‑enable the persistent camera widget (if needed)
        if hasattr(self, 'camera_widget') and self.camera_widget is not None:
            self.camera_widget.EnabledOn()

        if not preserve_camera:
            self.vtk_widget.reset_camera()

    def display_strain_with_candidates(self, coords, vm_strains, candidates_df, cloud_point_size,
                                       candidate_point_size, label_font_size, title="Visualization",
                                       preserve_camera=False):
        self.clearVisualization(preserve_camera)

        # Retrieve color choices from the user inputs
        above_color = self.combo_above_color.currentText().lower()  # "purple" or "white"
        below_color = self.combo_below_color.currentText().lower()  # "gray" or "white"

        # Retrieve clim values from the new spin boxes
        below_limit = self.dspin_below_limit.value()
        above_limit = self.dspin_above_limit.value()

        # Create full strain cloud.
        cloud = pv.PolyData(coords)
        cloud["Equivalent_Von_Mises_Strain"] = vm_strains
        self.vtk_widget.add_mesh(cloud, scalars="Equivalent_Von_Mises_Strain", cmap="jet",
                                 point_size=cloud_point_size, render_points_as_spheres=True,
                                 clim=(below_limit, above_limit),
                                 above_color=above_color,  # New argument for above limit color
                                 below_color=below_color,  # New argument for below limit color
                                 scalar_bar_args={'label_font_size': 10, 'title_font_size': 10})
        # Candidate points.
        candidate_coords = candidates_df[['X', 'Y', 'Z']].values
        candidate_points = pv.PolyData(candidate_coords)
        self.vtk_widget.add_mesh(candidate_points, color="purple", point_size=candidate_point_size,
                                 render_points_as_spheres=False, label="Candidate Points")
        # Quality labels.
        qualities = candidates_df['Quality'].values
        max_quality = qualities.max() if len(qualities) > 0 else 1
        normalized = (qualities / max_quality) * 100
        labels = [f"P{i + 1}: Q: {q:.1f}%" for i, q in enumerate(normalized)]
        self.vtk_widget.add_point_labels(candidate_points.points, labels,
                                         font_size=label_font_size, text_color="black",
                                         shape='rounded_rect', shape_color="#E9E1D4", margin=2,
                                         always_visible=True, shadow=True, name="Quality Labels")
        # Only reset the camera if not preserving it.
        if not preserve_camera:
            self.vtk_widget.reset_camera()
        self.vtk_widget.render()

    def display_kmeans(self, coords, candidate_count, cloud_point_size, title="K-Means Clustering"):
        self.clearVisualization()
        kmeans = KMeans(n_clusters=candidate_count, random_state=42).fit(coords)
        labels = kmeans.labels_
        cloud = pv.PolyData(coords)
        cloud["Cluster"] = labels
        self.vtk_widget.add_mesh(cloud, scalars="Cluster", cmap="jet",
                                 point_size=cloud_point_size, render_points_as_spheres=True)
        self.vtk_widget.add_text("Press Update to Continue...", position='upper_left', font_size=14, color='black')
        self.vtk_widget.reset_camera()
        self.vtk_widget.render()

    def updateCandidateTable(self, csv_filename):
        """Reads the candidate CSV file and updates the QTableWidget with improved formatting."""
        try:
            df = pd.read_csv(csv_filename)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load candidate CSV file:\n{str(e)}")
            return

        self.candidate_table.clear()
        self.candidate_table.setRowCount(len(df))
        self.candidate_table.setColumnCount(len(df.columns))
        self.candidate_table.setHorizontalHeaderLabels(df.columns.tolist())

        # Populate table with formatting for Best_Strain and Quality columns.
        for row in range(len(df)):
            for col in range(len(df.columns)):
                header = df.columns[col]
                cell_value = df.iat[row, col]
                if header == "Node":
                    try:
                        formatted_value = f"{int(cell_value)}"
                    except Exception:
                        formatted_value = str(cell_value)
                elif header in ["Best_Strain", "Quality"]:
                    try:
                        formatted_value = f"{float(cell_value):.3f}"
                    except Exception:
                        formatted_value = str(cell_value)
                elif header == "Local_Std":
                    try:
                        formatted_value = f"{float(cell_value):.32f}"
                    except Exception:
                        formatted_value = str(cell_value)
                else:
                    formatted_value = str(cell_value)
                item = QTableWidgetItem(formatted_value)
                item.setTextAlignment(Qt.AlignCenter)
                self.candidate_table.setItem(row, col, item)

        self.candidate_table.resizeColumnsToContents()
        self.candidate_table.horizontalHeader().setStretchLastSection(True)

    def toggleCandidateTable(self, checked):
        """Shows or hides the candidate table dock widget."""
        if checked:
            self.candidate_table_dock.show()
            csv_filename = "strain_candidate_points.csv"
            if os.path.exists(csv_filename):
                self.updateCandidateTable(csv_filename)
        else:
            self.candidate_table_dock.hide()

    def toggleDisplayMode(self, checked):
        self.display_in_strain = checked
        if self.input_file:
            self.updateSimulation()

    def refreshVisualization(self):
        # Re-display using the currently stored data and the updated control values.
        if self.last_coords is not None and self.last_scalars is not None and self.last_candidates_df is not None:
            self.display_strain_with_candidates(
                self.last_coords,
                self.last_scalars,
                self.last_candidates_df,
                self.dspin_cloud_point_size.value(),  # Use current value
                self.dspin_candidate_point_size.value(),  # Use current value
                self.spin_label_font_size.value(),  # Use current value
                preserve_camera=True
            )

    def updateSimulation(self):
        # Retrieve parameter values.
        measurement_mode = self.combo_measurement.currentText()
        selection_strategy = self.combo_strategy.currentText()
        quality_mode = self.combo_quality.currentText()
        candidate_count = self.spin_candidate_count.value()
        min_distance = self.dspin_min_distance.value()
        uniformity_radius = self.dspin_uniformity_radius.value()
        cloud_point_size = self.dspin_cloud_point_size.value()
        candidate_point_size = self.dspin_candidate_point_size.value()
        label_font_size = self.spin_label_font_size.value()

        if not self.input_file:
            QMessageBox.warning(self, "Error", "Please load a strain data file first.")
            return

        try:
            nodes, coords, strain_tensors = load_data(self.input_file)  # MODIFIED: now returns a dictionary of strain tensors
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        # Determine aggregation method from GUI.
        agg_method = self.combo_agg.currentText().lower()

        if measurement_mode == "Rosette":
            quality_dfs = []
            vm_strains_list = []
            for key in strain_tensors:
                tensor = strain_tensors[key]
                if self.display_in_strain:
                    vm_strains = np.sqrt(tensor[:, 0]**2 - tensor[:, 0]*tensor[:, 1] + tensor[:, 1]**2 + 3*(tensor[:, 2]**2)) / 1e6
                else:
                    vm_strains = np.sqrt(tensor[:, 0]**2 - tensor[:, 0]*tensor[:, 1] + tensor[:, 1]**2 + 3*(tensor[:, 2]**2))
                vm_strains_list.append(vm_strains)
                strains_i = vm_strains.reshape(-1, 1)
                angles_i = [0]
                quality_df = compute_quality_metrics(nodes, coords, strains_i, angles_i, quality_mode, uniformity_radius)
                quality_dfs.append(quality_df)
            # Aggregate quality metrics from multiple measurements.
            agg_quality_df = aggregate_quality_metrics(quality_dfs, agg_method)
            # Aggregate vm_strains for visualization.
            if agg_method == "max":
                vm_strains_agg = np.max(np.column_stack(vm_strains_list), axis=1)
            elif agg_method == "average":
                vm_strains_agg = np.mean(np.column_stack(vm_strains_list), axis=1)
            else:
                vm_strains_agg = np.max(np.column_stack(vm_strains_list), axis=1)
            if selection_strategy == "Quality-based (Greedy Search)":
                candidates_df = select_candidate_points(nodes, coords, None, angles_i, candidate_count,
                                                        min_distance, uniformity_radius, quality_mode,
                                                        precomputed_df=agg_quality_df)
            elif selection_strategy == "Max Spatial Coverage (K-Means Clustering)":
                if self.spatial_update_count == 0:
                    self.display_kmeans(coords, candidate_count, cloud_point_size)
                    self.spatial_update_count += 1
                    return
                else:
                    candidates_df = select_candidate_points_spatial_quality(nodes, coords, None, angles_i, candidate_count,
                                                                            uniformity_radius, quality_mode,
                                                                            precomputed_df=agg_quality_df)
                    self.spatial_update_count = 0
            current_scalars = vm_strains_agg
        else:  # Uniaxial (non-rosette)
            interval = 15
            angles = [0] + list(range(interval, 360, interval))
            quality_dfs = []
            strains_list = []
            for key in strain_tensors:
                tensor = strain_tensors[key]
                if self.display_in_strain:
                    strain_data = tensor / 1e6
                else:
                    strain_data = tensor
                strains_i = compute_normal_strains(strain_data, angles)
                strains_list.append(strains_i)
                quality_df = compute_quality_metrics(nodes, coords, strains_i, angles, quality_mode, uniformity_radius)
                quality_dfs.append(quality_df)
            agg_quality_df = aggregate_quality_metrics(quality_dfs, agg_method)
            # For visualization, aggregate strains (taking the maximum across measurements).
            strains_agg = np.max(np.stack(strains_list, axis=-1), axis=-1)
            if selection_strategy == "Quality-based (Greedy Search)":
                candidates_df = select_candidate_points(nodes, coords, None, angles, candidate_count,
                                                        min_distance, uniformity_radius, quality_mode,
                                                        precomputed_df=agg_quality_df)
            elif selection_strategy == "Max Spatial Coverage (K-Means Clustering)":
                if self.spatial_update_count == 0:
                    self.display_kmeans(coords, candidate_count, cloud_point_size)
                    self.spatial_update_count += 1
                    return
                else:
                    candidates_df = select_candidate_points_spatial_quality(nodes, coords, None, angles, candidate_count,
                                                                            uniformity_radius, quality_mode,
                                                                            precomputed_df=agg_quality_df)
                    self.spatial_update_count = 0
            current_scalars = strains_agg

        # Save candidate points to CSV.
        candidates_df.to_csv("strain_candidate_points.csv", index=False)

        # Update visualization limits.
        new_min = np.min(current_scalars)
        new_max = np.max(current_scalars)
        self.dspin_below_limit.setValue(new_min)
        self.dspin_above_limit.setValue(new_max)
        self.last_coords = coords
        self.last_scalars = current_scalars
        self.last_candidates_df = candidates_df
        self.last_cloud_point_size = cloud_point_size
        self.last_candidate_point_size = candidate_point_size
        self.last_label_font_size = label_font_size

        self.display_strain_with_candidates(coords,
                                            current_scalars,
                                            candidates_df, cloud_point_size,
                                            candidate_point_size, label_font_size,
                                            preserve_camera=True)
        if self.actionShowTable.isChecked():
            self.updateCandidateTable("strain_candidate_points.csv")

# ================================
# MAIN EXECUTION
# ================================
def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    win = MainWindow()
    win.showMaximized()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
