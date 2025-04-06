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
                             QDockWidget, QTableWidget, QTableWidgetItem)
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

def compute_quality_metrics(nodes, coords, strains, angles, quality_mode="snr", uniformity_radius=1.0):
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
    if quality_mode == "original":
        quality = abs_strain / (1.0 + local_std)
    elif quality_mode == "squared":
        quality = abs_strain / (1.0 + local_std ** 2)
    elif quality_mode == "exponential":
        quality = abs_strain * np.exp(-1000 * local_std)
    elif quality_mode == "snr":
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

# ================================
# CANDIDATE SELECTION FUNCTIONS
# ================================
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

def select_candidate_points(nodes, coords, strains, angles, candidate_count,
                            min_distance, uniformity_radius, quality_mode="original"):
    """Quality-based candidate selection using a greedy algorithm."""
    df = compute_quality_metrics(nodes, coords, strains, angles, quality_mode, uniformity_radius)
    df_sorted = df.sort_values(by='Quality', ascending=False)
    return greedy_selection(df_sorted, min_distance, candidate_count)

def select_candidate_points_spatial_quality(nodes, coords, strains, angles, candidate_count,
                                            uniformity_radius, quality_mode="snr"):
    """
    Improved candidate selection that uses KMeans clustering to partition nodes.
    The node with the highest quality in each cluster is selected.
    """
    df = compute_quality_metrics(nodes, coords, strains, angles, quality_mode, uniformity_radius)
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
    """Reads the input file and returns node, coordinate, and strain information."""
    df = pd.read_csv(input_filename, sep='\s+', skiprows=1, header=None)
    if df.shape[1] < 8:
        raise ValueError("Input file does not have the expected coordinate and strain columns.")
    nodes = df.iloc[:, 0].astype(int).values
    coords = df.iloc[:, 1:4].values

    conversion_factor = 1e6
    exx = df.iloc[:, 4].values * conversion_factor
    eyy = df.iloc[:, 5].values * conversion_factor
    exy = df.iloc[:, 7].values * conversion_factor
    return nodes, coords, exx, eyy, exy

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
        self.setWindowTitle("Strain Gage Positioning Tool v0.2")
        self.resize(1200, 800)
        self.project_dir = None
        self.input_file = None
        self.spatial_update_count = 0  # For spatial mode updates
        self.display_in_strain = False

        # Variables to store last visualization parameters
        self.last_coords = None
        self.last_scalars = None
        self.last_candidates_df = None
        self.last_cloud_point_size = None
        self.last_candidate_point_size = None
        self.last_label_font_size = None

        # Create menu bar.
        self._createMenuBar()

        # Main layout: control panel (left) and PyVista interactor (center)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Left side: control panel.
        self.control_panel = QWidget()
        self.control_panel.setFixedWidth(200)
        cp_layout = QVBoxLayout(self.control_panel)
        cp_layout.setAlignment(Qt.AlignTop)

        # Load strain data button.
        self.btn_load = QPushButton("Load Strain Data")
        self.btn_load.clicked.connect(self.loadStrainData)
        cp_layout.addWidget(self.btn_load)
        self.lbl_file = QLabel("No file loaded")
        cp_layout.addWidget(self.lbl_file)

        # Measurement mode.
        cp_layout.addWidget(QLabel("Measurement Mode:"))
        self.combo_measurement = QComboBox()
        self.combo_measurement.addItems(["rosette", "uniaxial"])
        cp_layout.addWidget(self.combo_measurement)

        # Candidate selection strategy.
        cp_layout.addWidget(QLabel("Selection Strategy:"))
        self.combo_strategy = QComboBox()
        self.combo_strategy.addItems(["quality", "spatial"])
        cp_layout.addWidget(self.combo_strategy)

        # Quality mode.
        cp_layout.addWidget(QLabel("Quality Metrics Mode:"))
        self.combo_quality = QComboBox()
        self.combo_quality.addItems(["original", "squared", "exponential", "snr"])
        cp_layout.addWidget(self.combo_quality)

        # Candidate count.
        cp_layout.addWidget(QLabel("Candidate Count:"))
        self.spin_candidate_count = QSpinBox()
        self.spin_candidate_count.setRange(1, 1000)
        self.spin_candidate_count.setValue(10)
        cp_layout.addWidget(self.spin_candidate_count)

        # Minimum distance.
        cp_layout.addWidget(QLabel("Min Distance [mm]:"))
        self.dspin_min_distance = QDoubleSpinBox()
        self.dspin_min_distance.setRange(0, 10000)
        self.dspin_min_distance.setValue(10.0)
        cp_layout.addWidget(self.dspin_min_distance)

        # Uniformity radius.
        cp_layout.addWidget(QLabel("Uniformity Radius [mm]:"))
        self.dspin_uniformity_radius = QDoubleSpinBox()
        self.dspin_uniformity_radius.setRange(0, 1000)
        self.dspin_uniformity_radius.setValue(10.0)
        cp_layout.addWidget(self.dspin_uniformity_radius)

        # Cloud point size.
        cp_layout.addWidget(QLabel("Cloud Point Size:"))
        self.dspin_cloud_point_size = QDoubleSpinBox()
        self.dspin_cloud_point_size.setRange(1.0, 50.0)
        self.dspin_cloud_point_size.setValue(10.0)
        cp_layout.addWidget(self.dspin_cloud_point_size)

        # Candidate point size.
        cp_layout.addWidget(QLabel("Candidate Point Size:"))
        self.dspin_candidate_point_size = QDoubleSpinBox()
        self.dspin_candidate_point_size.setRange(1.0, 50.0)
        self.dspin_candidate_point_size.setValue(20.0)
        cp_layout.addWidget(self.dspin_candidate_point_size)

        # Label font size.
        cp_layout.addWidget(QLabel("Label Font Size:"))
        self.spin_label_font_size = QSpinBox()
        self.spin_label_font_size.setRange(8, 72)
        self.spin_label_font_size.setValue(20)
        cp_layout.addWidget(self.spin_label_font_size)

        # Upper Limit Value.
        cp_layout.addWidget(QLabel("Upper Limit Value:"))
        self.dspin_above_limit = QDoubleSpinBox()
        self.dspin_above_limit.setRange(-1e9, 1e9)  # Set an appropriate range
        self.dspin_above_limit.setValue(1.0)  # Default value
        cp_layout.addWidget(self.dspin_above_limit)

        # Lower Limit Value.
        cp_layout.addWidget(QLabel("Lower Limit Value:"))
        self.dspin_below_limit = QDoubleSpinBox()
        self.dspin_below_limit.setRange(-1e9, 1e9)  # Set an appropriate range
        self.dspin_below_limit.setValue(0.0)  # Default value
        cp_layout.addWidget(self.dspin_below_limit)

        # Upper Limit Color.
        cp_layout.addWidget(QLabel("Upper Limit Color:"))
        self.combo_above_color = QComboBox()
        self.combo_above_color.addItems(["Purple", "White"])
        cp_layout.addWidget(self.combo_above_color)

        # Lower Limit Color.
        cp_layout.addWidget(QLabel("Lower Limit Color:"))
        self.combo_below_color = QComboBox()
        self.combo_below_color.addItems(["Gray", "White"])
        cp_layout.addWidget(self.combo_below_color)

        # Connect limit and color inputs to refresh visualization immediately.
        self.dspin_above_limit.valueChanged.connect(self.refreshVisualization)
        self.dspin_below_limit.valueChanged.connect(self.refreshVisualization)
        self.combo_above_color.currentIndexChanged.connect(self.refreshVisualization)
        self.combo_below_color.currentIndexChanged.connect(self.refreshVisualization)

        # Update button.
        self.btn_update = QPushButton("Update")
        self.btn_update.clicked.connect(self.updateSimulation)
        cp_layout.addWidget(self.btn_update)

        main_layout.addWidget(self.control_panel)

        # Center: PyVista interactor.
        self.vtk_widget = QtInteractor(main_widget)
        main_layout.addWidget(self.vtk_widget.interactor)

        # Create candidate table dock widget (initially hidden).
        self.candidate_table_dock = QDockWidget("Candidate Points", self)
        self.candidate_table = QTableWidget()
        self.candidate_table.setAlternatingRowColors(True)
        # Set header style.
        self.candidate_table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: lightgray; font-weight: bold; }")
        self.candidate_table.verticalHeader().setStyleSheet("QHeaderView::section { background-color: lightgray; }")
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

    def clearVisualization(self):
        self.vtk_widget.clear()
        self.vtk_widget.reset_camera()

    def display_strain_with_candidates(self, coords, vm_strains, candidates_df, cloud_point_size,
                                       candidate_point_size, label_font_size, title="Visualization"):
        self.clearVisualization()

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
                                 above_color = above_color,  # New argument for above limit color
                                 below_color = below_color,  # New argument for below limit color
                                 scalar_bar_args={'label_font_size': 10, 'title_font_size': 10})
        # Candidate points.
        candidate_coords = candidates_df[['X', 'Y', 'Z']].values
        candidate_points = pv.PolyData(candidate_coords)
        self.vtk_widget.add_mesh(candidate_points, color="red", point_size=candidate_point_size,
                                 render_points_as_spheres=True, label="Candidate Points")
        # Quality labels.
        qualities = candidates_df['Quality'].values
        max_quality = qualities.max() if len(qualities) > 0 else 1
        normalized = (qualities / max_quality) * 100
        labels = [f"P{i + 1}: Q: {q:.1f}%" for i, q in enumerate(normalized)]
        self.vtk_widget.add_point_labels(candidate_points.points, labels,
                                         font_size=label_font_size, text_color="black",
                                         shape='rounded_rect', shape_color="#E9E1D4", margin=2,
                                         always_visible=True, shadow=True, name="Quality Labels")
        self.vtk_widget.reset_camera()
        self.vtk_widget.render()

    def display_kmeans(self, coords, candidate_count, cloud_point_size, title="KMeans Clustering"):
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
                        # Format to 3 decimal places
                        formatted_value = f"{float(cell_value):.3f}"
                    except Exception:
                        formatted_value = str(cell_value)
                elif header == "Local_Std":
                    try:
                        # Format to 32 decimal places
                        formatted_value = f"{float(cell_value):.32f}"
                    except Exception:
                        formatted_value = str(cell_value)
                else:
                    formatted_value = str(cell_value)
                item = QTableWidgetItem(formatted_value)
                item.setTextAlignment(Qt.AlignCenter)
                self.candidate_table.setItem(row, col, item)

        # Resize columns to contents and stretch last column.
        self.candidate_table.resizeColumnsToContents()
        self.candidate_table.horizontalHeader().setStretchLastSection(True)

    def toggleCandidateTable(self, checked):
        """Shows or hides the candidate table dock widget."""
        if checked:
            self.candidate_table_dock.show()
            # Update table if CSV file exists.
            csv_filename = "strain_candidate_points.csv"
            if os.path.exists(csv_filename):
                self.updateCandidateTable(csv_filename)
        else:
            self.candidate_table_dock.hide()

    def toggleDisplayMode(self, checked):
        # If checked, show strain values (i.e., disable the microstrain conversion in visualization).
        self.display_in_strain = checked
        # Optionally trigger an update to refresh the visualization.
        if self.input_file:
            self.updateSimulation()

    def refreshVisualization(self):
        """Refresh the visualization using the stored point cloud and candidate data."""
        if self.last_coords is not None and self.last_scalars is not None and self.last_candidates_df is not None:
            self.display_strain_with_candidates(
                self.last_coords,
                self.last_scalars,
                self.last_candidates_df,
                self.last_cloud_point_size,
                self.last_candidate_point_size,
                self.last_label_font_size
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
            nodes, coords, exx, eyy, exy = load_data(self.input_file)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        if measurement_mode == "rosette":
            if self.display_in_strain:
                vm_strains = np.sqrt(exx ** 2 - exx * eyy + eyy ** 2 + 3 * (exy ** 2)) / 1e6
            else:
                vm_strains = np.sqrt(exx ** 2 - exx * eyy + eyy ** 2 + 3 * (exy ** 2))
            strains = vm_strains.reshape(-1, 1)
            angles = [0]
        else:
            interval = 15
            angles = [0] + list(range(interval, 360, interval))
            if self.display_in_strain:
                strain_data = np.column_stack((exx, eyy, exy)) / 1e6
            else:
                strain_data = np.column_stack((exx, eyy, exy))
            strains = compute_normal_strains(strain_data, angles)

        self.clearVisualization()

        # Process based on selection strategy.
        if selection_strategy == "quality":
            if measurement_mode == "rosette":
                candidates_df = select_candidate_points(nodes, coords, strains, [0],
                                                        candidate_count, min_distance,
                                                        uniformity_radius, quality_mode)
            else:
                candidates_df = select_candidate_points(nodes, coords, strains, angles,
                                                        candidate_count, min_distance,
                                                        uniformity_radius, quality_mode)
            # Save candidate points to CSV.
            candidates_df.to_csv("strain_candidate_points.csv", index=False)

            # Determine the new color limits based on the scalar field of the point cloud.
            current_scalars = vm_strains if measurement_mode == "rosette" else strains
            new_min = np.min(current_scalars)
            new_max = np.max(current_scalars)
            # Update the spin boxes with these values.
            self.dspin_below_limit.setValue(new_min)
            self.dspin_above_limit.setValue(new_max)
            # Store the current parameters for later refresh.
            self.last_coords = coords
            self.last_scalars = current_scalars
            self.last_candidates_df = candidates_df
            self.last_cloud_point_size = cloud_point_size
            self.last_candidate_point_size = candidate_point_size
            self.last_label_font_size = label_font_size

            self.display_strain_with_candidates(coords,
                                                vm_strains if measurement_mode == "rosette" else strains,
                                                candidates_df, cloud_point_size,
                                                candidate_point_size, label_font_size)
            self.spatial_update_count = 0
        elif selection_strategy == "spatial":
            if self.spatial_update_count == 0:
                self.display_kmeans(coords, candidate_count, cloud_point_size)
                self.spatial_update_count += 1
            else:
                if measurement_mode == "rosette":
                    candidates_df = select_candidate_points_spatial_quality(nodes, coords, strains, [0],
                                                                            candidate_count, uniformity_radius,
                                                                            quality_mode)
                else:
                    candidates_df = select_candidate_points_spatial_quality(nodes, coords, strains, angles,
                                                                            candidate_count, uniformity_radius,
                                                                            quality_mode)
                candidates_df.to_csv("strain_candidate_points.csv", index=False)

                current_scalars = vm_strains if measurement_mode == "rosette" else strains
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
                                                    vm_strains if measurement_mode == "rosette" else strains,
                                                    candidates_df, cloud_point_size,
                                                    candidate_point_size, label_font_size)
                self.spatial_update_count = 0

        # If the candidate table dock is visible, update its contents.
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
