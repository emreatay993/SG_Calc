import sys
import csv
import os
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, \
    QComboBox, QLabel, QCheckBox, QMessageBox, QGroupBox, QSlider, QSpinBox, QDoubleSpinBox
from PyQt5.QtCore import Qt
from scipy.interpolate import griddata
import pyvista as pv
import vtk
from pyvistaqt import BackgroundPlotter

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("SG Plotter")
        self.showMaximized()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.vtk_widget = VTKWidget(self)
        self.tabs.addTab(self.vtk_widget, "3D Plot")

        self.settings_widget = QWidget()
        self.tabs.addTab(self.settings_widget, "Settings")
        self.initSettingsTab()

        self.show()
        self.openFolderNameDialog()

    def openFolderNameDialog(self):
        folderName = QFileDialog.getExistingDirectory(self, "Select Folder", "")
        if folderName:
            self.vtk_widget.processFolder(folderName)
        else:
            print("No folder selected.")
            sys.exit(1)

    def initSettingsTab(self):

        # Apply a stylesheet to widgets etc.
        self.setStyleSheet("""
            QGroupBox {
                font: bold;
                border: 1px solid gray;
                border-radius: 9px;
                margin-top: 10px;
                padding: 10px;
                background-color: #f0f0f0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
                border-radius: 5px;
            }
            QLabel {
                font-size: 12px;
            }
            QSlider {
                background: #dedede;
                border-radius: 5px;
                height: 10px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #c0c0c0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #5e5e5e;
                border: 1px solid #5e5e5e;
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QCheckBox {
                font-size: 12px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
            }
        """)

        layout = QVBoxLayout()

        self.checkbox_stl = QCheckBox("Show STL")
        self.checkbox_stl.stateChanged.connect(self.toggleSTLVisibility)
        layout.addWidget(self.checkbox_stl)

        self.stl_groupbox = QGroupBox("STL Settings")
        stl_layout = QVBoxLayout()

        h_layout_stl_file = QHBoxLayout()
        self.stl_comboBox = QComboBox()
        self.stl_comboBox.currentIndexChanged.connect(self.updateSTL)
        self.stl_file_label = QLabel("Select a file from the working folder:")
        h_layout_stl_file.addWidget(self.stl_file_label)
        h_layout_stl_file.addWidget(self.stl_comboBox)
        stl_layout.addLayout(h_layout_stl_file)

        h_layout_scale = QHBoxLayout()
        self.scale_label = QLabel("STL Scale Factor:")
        self.scale_factor_input = QComboBox()
        self.scale_factor_input.setEditable(True)
        self.scale_factor_input.addItems(["0.001", "0.01", "0.1", "1", "10","100","1000"])
        self.scale_factor_input.setCurrentText("999")
        self.scale_factor_input.editTextChanged.connect(self.validateScaleFactor)
        h_layout_scale.addWidget(self.scale_label)
        h_layout_scale.addWidget(self.scale_factor_input)
        stl_layout.addLayout(h_layout_scale)

        self.stl_groupbox.setLayout(stl_layout)
        self.stl_groupbox.hide()
        layout.addWidget(self.stl_groupbox)

        # Add Graphics Settings group box
        self.graphics_groupbox = QGroupBox("Graphics Settings")
        graphics_layout = QVBoxLayout()

        # Opacity slider for refined_mesh
        self.refined_mesh_opacity_slider = QSlider(Qt.Horizontal)
        self.refined_mesh_opacity_slider.setRange(0, 100)
        self.refined_mesh_opacity_slider.setValue(100)
        self.refined_mesh_opacity_slider.setToolTip("Set opacity for refined mesh")
        self.refined_mesh_opacity_slider.valueChanged.connect(self.updateRefinedMeshOpacity)
        graphics_layout.addWidget(QLabel("Refined Mesh Opacity"))
        graphics_layout.addWidget(self.refined_mesh_opacity_slider)

        # Opacity slider for stl_actor
        self.stl_opacity_slider = QSlider(Qt.Horizontal)
        self.stl_opacity_slider.setRange(0, 100)
        self.stl_opacity_slider.setValue(100)
        self.stl_opacity_slider.setToolTip("Set opacity for STL actor")
        self.stl_opacity_slider.valueChanged.connect(self.updateSTLOpacity)
        graphics_layout.addWidget(QLabel("STL Opacity"))
        graphics_layout.addWidget(self.stl_opacity_slider)

        # Opacity slider for selected_points
        self.selected_points_opacity_slider = QSlider(Qt.Horizontal)
        self.selected_points_opacity_slider.setRange(0, 100)
        self.selected_points_opacity_slider.setValue(100)
        self.selected_points_opacity_slider.setToolTip("Set opacity for selected points")
        self.selected_points_opacity_slider.valueChanged.connect(self.updateSelectedPointsOpacity)
        graphics_layout.addWidget(QLabel("Selected Points Opacity"))
        graphics_layout.addWidget(self.selected_points_opacity_slider)

        # Add a checkbox for centering the camera around the rotation center
        self.center_camera_checkbox = QCheckBox("Position the screen around the rotation center")
        self.center_camera_checkbox.setChecked(True)
        self.center_camera_checkbox.stateChanged.connect(self.vtk_widget.toggleCenterCamera)
        graphics_layout.addWidget(self.center_camera_checkbox)

        self.graphics_groupbox.setLayout(graphics_layout)
        layout.addWidget(self.graphics_groupbox)

        self.settings_widget.setLayout(layout)

    def validateScaleFactor(self, text):
        try:
            value = float(text)
            if value <= 0:
                raise ValueError("Scale factor must be positive.")

            adjusted_value = value
            self.scale_factor_input.blockSignals(True)
            self.scale_factor_input.setCurrentText(str(adjusted_value))
            self.scale_factor_input.blockSignals(False)
        except ValueError:
            self.scale_factor_input.setCurrentText("999")

    def toggleSTLVisibility(self, state):
        if state == Qt.Checked:
            self.stl_groupbox.show()
            self.updateSTL()
        else:
            self.stl_groupbox.hide()
            if self.vtk_widget.stl_actor is not None:
                self.vtk_widget.plotter.remove_actor(self.vtk_widget.stl_actor)
                self.vtk_widget.stl_actor = None

    def updateSTL(self):
        selected_stl = self.stl_comboBox.currentText()
        if selected_stl:
            self.vtk_widget.showSTL(selected_stl)

    def loadStlFiles(self, folder_path):
        self.stl_comboBox.clear()
        stl_files = [file_name for file_name in os.listdir(folder_path) if file_name.endswith(".stl")]
        if stl_files:
            self.stl_comboBox.addItems(stl_files)
            self.stl_comboBox.setCurrentIndex(0)
            self.checkbox_stl.setChecked(True)
            self.stl_comboBox.show()
        else:
            self.checkbox_stl.setChecked(False)
            self.checkbox_stl.setEnabled(False)

    def updateRefinedMeshOpacity(self, value):
        opacity = value / 100.0
        if self.vtk_widget.refined_mesh_actor:
            self.vtk_widget.refined_mesh_actor.GetProperty().SetOpacity(opacity)
            self.vtk_widget.plotter.render()

    def updateSTLOpacity(self, value):
        opacity = value / 100.0
        if self.vtk_widget.stl_actor:
            self.vtk_widget.stl_actor.GetProperty().SetOpacity(opacity)
            self.vtk_widget.plotter.render()

    def updateSelectedPointsOpacity(self, value):
        opacity = value / 100.0
        if self.vtk_widget.selected_points_actor:
            self.vtk_widget.selected_points_actor.GetProperty().SetOpacity(opacity)
            self.vtk_widget.plotter.render()

class VTKWidget(QWidget):

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        self.plotter = BackgroundPlotter(show=False)  # Initialize the PyVista plotter

        self.refined_mesh = None
        self.refined_mesh_actor = None
        self.selected_points_actor = None

        # Initialize the hover label using VTK
        self.hover_label = vtk.vtkTextActor()
        self.hover_label.GetTextProperty().SetFontSize(12)
        self.hover_label.GetTextProperty().SetColor(0, 0, 0)  # Black color

        # Add the hover label to the renderer but keep it invisible initially
        self.plotter.renderer.AddActor(self.hover_label)
        self.hover_label.VisibilityOff()

        # Set a distance threshold to determine when to hide the hover label
        self.distance_threshold = 1  # Adjust this value as needed

        # Initialize the directional vectors for the local coordinate system
        self.x_dir = None
        self.y_dir = None
        self.z_dir = None

        # Initialize bounding box offsets
        self.bounding_box_offset_x = 0.0
        self.bounding_box_offset_y = 0.0

        layout = QVBoxLayout()

        h_layout_1 = QHBoxLayout()
        self.label = QLabel("Select a channel:")
        self.comboBox = QComboBox()
        self.comboBox.currentIndexChanged.connect(self.updatePlot)
        h_layout_1.addWidget(self.label)
        h_layout_1.addWidget(self.comboBox)

        # Add non-editable QSpinBox for subdivide level
        self.subdivide_spinbox = QSpinBox()
        self.subdivide_spinbox.setRange(1, 8)
        self.subdivide_spinbox.setValue(4)  # Default value
        self.subdivide_spinbox.setFixedWidth(60)
        self.subdivide_spinbox.setFocusPolicy(Qt.NoFocus)
        self.subdivide_spinbox.valueChanged.connect(self.updatePlot)
        h_layout_1.addWidget(QLabel("Remesh Level (1 to 10):"))
        h_layout_1.addWidget(self.subdivide_spinbox)

        # Add the top horizontal layout to the main layout
        layout.addLayout(h_layout_1)

        # Create a horizontal layout for the checkboxes
        h_layout_2 = QHBoxLayout()

        self.checkbox_points = QCheckBox("Display Original Points")
        self.checkbox_points.stateChanged.connect(self.togglePointsVisibility)
        h_layout_2.addWidget(self.checkbox_points)

        self.checkbox_axes = QCheckBox("Display Local Axis")
        self.checkbox_axes.setChecked(True)
        self.checkbox_axes.stateChanged.connect(self.toggleAxesVisibility)
        h_layout_2.addWidget(self.checkbox_axes)

        # Checkbox for show_edges option
        self.checkbox_show_edges = QCheckBox("Show Mesh")
        self.checkbox_show_edges.setChecked(False)
        self.checkbox_show_edges.stateChanged.connect(self.toggleShowEdges)
        h_layout_2.addWidget(self.checkbox_show_edges)

        # Add the top horizontal layout to the main layout
        layout.addLayout(h_layout_2)

        h_layout_3 = QHBoxLayout()

        self.label_offset_x = QLabel("X Offset (Local Coord) :")
        self.offset_x_spinbox = QDoubleSpinBox()
        self.offset_x_spinbox.setRange(-50, 50)
        self.offset_x_spinbox.setValue(0)
        self.offset_x_spinbox.setSingleStep(0.2)
        self.offset_x_spinbox.valueChanged.connect(self.updateBoundingBoxPosition)
        h_layout_3.addWidget(self.label_offset_x)
        h_layout_3.addWidget(self.offset_x_spinbox)

        self.label_offset_y = QLabel("Y Offset (Local Coord) :")
        self.offset_y_spinbox = QDoubleSpinBox()
        self.offset_y_spinbox.setRange(-50, 50)
        self.offset_y_spinbox.setValue(0)
        self.offset_y_spinbox.setSingleStep(0.2)
        self.offset_y_spinbox.valueChanged.connect(self.updateBoundingBoxPosition)
        h_layout_3.addWidget(self.label_offset_y)
        h_layout_3.addWidget(self.offset_y_spinbox)

        layout.addLayout(h_layout_3)

        self.set_mouse_rotation_behavior()
        layout.addWidget(self.plotter.interactor)

        self.setLayout(layout)
        self.data_frames = {}
        self.file_mapping = {}
        self.polydata_actor = None
        self.sg_axes_actors = {}
        self.sg_data = None
        self.folder_path = None
        self.stl_actor = None
        self.plotter.show_axes()

        self.bounding_boxes = None
        self.rotation_sphere_actor = None
        self.center_camera = True

    def add_sphere_at_click(self, pick_position):
        """Adds a transparent sphere at the given pick position."""
        if pick_position:
            # Add a new sphere at the clicked position with a specified opacity
            sphere = pv.Sphere(radius=1, center=pick_position)
            self.rotation_sphere_actor = self.plotter.add_mesh(
                sphere, color="blue", opacity=0.3  # Set opacity to 50%
            )
            self.plotter.render()

    def remove_sphere(self):
        """Removes the sphere if it exists."""
        if self.rotation_sphere_actor is not None:
            self.plotter.remove_actor(self.rotation_sphere_actor)
            self.rotation_sphere_actor = None
            self.plotter.render()

    def toggleCenterCamera(self, state):
        """Enable or disable centering the screen around the rotation center."""
        self.center_camera = (state == Qt.Checked)

    def on_mouse_move(self, interactor, event):
        """Handles mouse movement to display strain values on hover."""
        # Get the mouse position in window coordinates
        click_pos = interactor.GetEventPosition()

        # Create a picker instance
        picker = vtk.vtkPointPicker()

        # Perform picking operation at the given mouse position
        picker.Pick(click_pos[0], click_pos[1], 0, self.plotter.renderer)
        pick_position = picker.GetPickPosition()

        if pick_position and self.refined_mesh is not None:
            # Find the closest point in the PolyData (refined mesh)
            closest_point_id = self.refined_mesh.find_closest_point(pick_position)
            if closest_point_id >= 0:  # Valid point found
                # Calculate the distance to the closest point
                closest_point = self.refined_mesh.points[closest_point_id]
                distance = np.linalg.norm(np.array(pick_position) - np.array(closest_point))

                # Check if the distance is within the threshold
                if distance <= self.distance_threshold:
                    strain_value = self.refined_mesh.point_data['Strain [µε]'][closest_point_id]

                    # Update the text and position of the hover label
                    self.hover_label.SetInput(f"Strain: {strain_value:.2f} µε")
                    self.hover_label.SetPosition(click_pos[0] + 10, click_pos[1] - 10)
                    self.hover_label.VisibilityOn()  # Make the label visible
                else:
                    self.hover_label.VisibilityOff()  # Hide the label if the mouse is far away
            else:
                self.hover_label.VisibilityOff()  # Hide the label if no valid point is found
        else:
            self.hover_label.VisibilityOff()  # Hide the label if not hovering over any point

        # Render the plotter after updating
        self.plotter.render()

    def set_mouse_rotation_behavior(self):
        """Customizes mouse rotation to use the clicked point as the center of rotation."""

        def on_left_button_down(interactor, event):
            # Get the click position
            click_pos = interactor.GetEventPosition()

            # Convert click position to 3D coordinates
            picker = interactor.GetPicker()
            picker.Pick(click_pos[0], click_pos[1], 0, self.plotter.renderer)
            pick_position = picker.GetPickPosition()

            if pick_position:
                # Call the method to add a sphere at the pick position
                self.add_sphere_at_click(pick_position)

            if self.center_camera:  # Only center the camera if the checkbox is checked
                # Set the focal point to the click position
                self.plotter.camera.focal_point = pick_position
                self.plotter.render()

            # Call the superclass method to handle the event normally
            interactor.GetInteractorStyle().OnLeftButtonDown()

        def on_left_button_up(interactor, event):
            # Call the method to remove the sphere
            self.remove_sphere()

            # Call the superclass method to handle the event normally
            interactor.GetInteractorStyle().OnLeftButtonUp()

        # Set the custom interaction behavior
        self.plotter.interactor.AddObserver("LeftButtonPressEvent", on_left_button_down)
        self.plotter.interactor.AddObserver("EndInteractionEvent", on_left_button_up)
        self.plotter.interactor.AddObserver("MouseMoveEvent", self.on_mouse_move)

        # Disable existing picking to avoid conflicts
        self.plotter.disable_picking()

        # Explicitly set interaction style back after observers
        self.plotter.interactor.SetInteractorStyle(self.plotter.interactor.GetInteractorStyle())

    def processFolder(self, folder_path):
        self.folder_path = folder_path
        # Load SG_coordinate_matrix.csv
        sg_file_path = os.path.join(folder_path, "SG_coordinate_matrix.csv")
        if os.path.exists(sg_file_path):
            self.sg_data = pd.read_csv(sg_file_path)

        # Load bounding boxes from SG_grid_body_vertices.csv
        vertices_file_path = os.path.join(folder_path, "SG_grid_body_vertices_in_local_CS.csv")
        if os.path.exists(vertices_file_path):
            grid_bodies = self._parse_sg_grid_body_vertices(vertices_file_path)
            global_bounding_boxes = self._calculate_global_bounding_boxes(grid_bodies)

        # Transform bounding boxes to local coordinates
        self.bounding_boxes = self._transform_to_local_coordinates(global_bounding_boxes)

        def sort_key(display_name):
            try:
                # Extract the base part (e.g., "SG_Ch_1_1") and ignore anything in parentheses
                base_name = display_name.split('(')[0]

                # Remove any non-numeric part at the end after the last underscore
                parts = base_name.split('_')

                # Convert the numeric parts to a tuple of integers
                numeric_parts = tuple(int(part) for part in parts if part.isdigit())

                return numeric_parts
            except ValueError as e:
                print(f"Error parsing '{display_name}': {e}. This item will be sorted at the end of the combobox.")
                return float('inf'), 0  # Move problematic entries to the end

        # Initialize dictionaries to store strain, preload, and zeroed files
        strain_items = []
        preload_items = {}
        zeroed_items = {}

        # Load each CSV file that starts with "StrainX_around_", "Preload_StrainX_around_", or ends with "_zeroed"
        for file_name in os.listdir(folder_path):
            if file_name.startswith("StrainX_around_") and file_name.endswith(".csv"):
                # Handle strain files
                file_path = os.path.join(folder_path, file_name)
                data = pd.read_csv(file_path, sep='\t')
                display_name = file_name.replace("StrainX_around_", "").replace(".csv", "")
                strain_items.append((display_name, data, file_name))

            elif file_name.startswith("Preload_StrainX_around_") and file_name.endswith(".csv"):
                # Handle preload files
                file_path = os.path.join(folder_path, file_name)
                data = pd.read_csv(file_path, sep='\t')
                display_name = file_name.replace("Preload_StrainX_around_", "").replace(".csv", "")
                preload_items[display_name] = data  # Store preload files

            elif file_name.endswith("_zeroed.csv"):
                # Handle zeroed files
                file_path = os.path.join(folder_path, file_name)
                data = pd.read_csv(file_path, sep='\t')
                display_name = file_name.replace("_zeroed.csv", "")
                zeroed_items[display_name] = data  # Store zeroed files

        # Sort items based on SG and channel numbers
        sorted_strain_items = sorted(strain_items, key=lambda x: sort_key(x[0]))

        # Add sorted items to the combobox and store data
        for display_name, data, file_name in sorted_strain_items:
            self.data_frames[display_name] = data
            self.file_mapping[display_name] = file_name
            self.comboBox.addItem(display_name)

            # Check if there is a corresponding preload file and store it
            if display_name in preload_items:
                preload_display_name = f"Preload_{display_name}"
                self.data_frames[preload_display_name] = preload_items[display_name]
                self.comboBox.addItem(preload_display_name)

            # Check if there is a corresponding zeroed file and store it
            if display_name in zeroed_items:
                zeroed_display_name = f"{display_name}_zeroed"
                self.data_frames[zeroed_display_name] = zeroed_items[display_name]
                self.comboBox.addItem(zeroed_display_name)

        # Notify settings tab to load STL files
        self.main_window.loadStlFiles(folder_path)

        if self.comboBox.count() > 0:
            self.comboBox.setCurrentIndex(0)

    def _parse_sg_grid_body_vertices(self, file_path):
        """Parses the SG_grid_body_vertices_in_local_CS.csv file to extract the vertices of each SG grid body."""
        grid_bodies = {}

        with open(file_path, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                body_name = row['Body_Name']
                vertex = (
                    float(row['X_local [mm]']),
                    float(row['Y_local [mm]']),
                    float(row['Z_local [mm]'])
                )
                if body_name not in grid_bodies:
                    grid_bodies[body_name] = []
                grid_bodies[body_name].append(vertex)

        return grid_bodies

    def _calculate_global_bounding_boxes(self, grid_bodies, extrusion_length=1.0):
        """Calculates the bounding box for each SG grid body in global coordinates, with extrusion if the body is 2D."""
        bounding_boxes = {}

        for body_name, vertices in grid_bodies.items():
            vertices = np.array(vertices)
            min_bounds = vertices.min(axis=0)
            max_bounds = vertices.max(axis=0)

            # Determine if the bounding box is 2D (one dimension is flat)
            if np.isclose(min_bounds[0], max_bounds[0]):  # Flat in X
                min_bounds[0] -= extrusion_length / 2
                max_bounds[0] += extrusion_length / 2
            elif np.isclose(min_bounds[1], max_bounds[1]):  # Flat in Y
                min_bounds[1] -= extrusion_length / 2
                max_bounds[1] += extrusion_length / 2
            elif np.isclose(min_bounds[2], max_bounds[2]):  # Flat in Z
                min_bounds[2] -= extrusion_length / 2
                max_bounds[2] += extrusion_length / 2

            bounding_boxes[body_name] = {
                'center': (min_bounds + max_bounds) / 2,
                'lengths': max_bounds - min_bounds
            }

        return bounding_boxes

    def _transform_to_local_coordinates(self, bounding_boxes):
        """Transforms the bounding boxes from global to local coordinates using the local CS of each SG."""
        transformed_bounding_boxes = {}

        for body_name, bbox in bounding_boxes.items():
            # Find the corresponding local coordinate system
            cs_name = body_name.replace("SG_Grid_Body_", "CS_SG_Ch_")
            if cs_name in self.sg_data['CS Name'].values:
                cs_row = self.sg_data[self.sg_data['CS Name'] == cs_name].iloc[0]
                origin = np.array([cs_row['Origin_X'], cs_row['Origin_Y'], cs_row['Origin_Z']])
                x_dir = np.array([cs_row['X_dir_i'], cs_row['X_dir_j'], cs_row['X_dir_k']])
                y_dir = np.array([cs_row['Y_dir_i'], cs_row['Y_dir_j'], cs_row['Y_dir_k']])
                z_dir = np.array([cs_row['Z_dir_i'], cs_row['Z_dir_j'], cs_row['Z_dir_k']])

                # Transformation matrix from global to local coordinates
                transformation_matrix = np.column_stack((x_dir, y_dir, z_dir))

                # Apply transformation: Rotation
                local_center = np.linalg.inv(transformation_matrix).dot(bbox['center'])
                local_lengths = bbox['lengths']  # Lengths remain unchanged since they are magnitudes

                transformed_bounding_boxes[body_name] = {
                    'center': local_center,
                    'lengths': local_lengths
                }

        return transformed_bounding_boxes

    def updatePlot(self):
        selected_display_name = self.comboBox.currentText()

        # Determine if this is a preload or zeroed file
        is_preload = selected_display_name.startswith("Preload_")
        is_zeroed = selected_display_name.endswith("_zeroed")

        # Determine the base display name
        if is_preload:
            base_display_name = selected_display_name.replace("Preload_", "")
        elif is_zeroed:
            base_display_name = selected_display_name.replace("_zeroed", "")
        else:
            base_display_name = selected_display_name

        # Use the same SG grid bodies and local coordinates for preload or zeroed data
        if base_display_name in self.data_frames:
            self.plotData(self.data_frames[selected_display_name], base_display_name)
        else:
            QMessageBox.warning(self, "Data Error", f"No data found for {selected_display_name}.")

    def plotData(self, data, display_name):
        try:
            camera_position = self.plotter.camera.position
            camera_focal_point = self.plotter.camera.focal_point
            camera_clipping_range = self.plotter.camera.clipping_range


            # Clear all plotter except the STL actor
            actors_to_remove = [actor for actor in self.plotter.renderer.actors.values() if actor != self.stl_actor]
            for actor in actors_to_remove:
                self.plotter.renderer.remove_actor(actor)

            # Extract X, Y, Z coordinates and strain values
            x = data['X Location (mm)'].values
            y = data['Y Location (mm)'].values
            z = data['Z Location (mm)'].values
            nodes = np.c_[x.ravel(), y.ravel(), z.ravel()]
            strain = (data['Normal Elastic Strain (mm/mm)'].values) * 1e6

            if display_name.startswith("Preload_") or display_name.endswith("_zeroed"):
                base_display_name = display_name.replace("Preload_", "").replace("_zeroed", "")
            else:
                base_display_name = display_name

            # Retrieve the local coordinate system and grid bodies data
            sg_row = self.sg_data[self.sg_data['CS Name'] == f"CS_{base_display_name}"]

            if not sg_row.empty:
                self.origin = sg_row[['Origin_X', 'Origin_Y', 'Origin_Z']].values.flatten()
                self.x_dir = sg_row[['X_dir_i', 'X_dir_j', 'X_dir_k']].values.flatten()
                self.y_dir = sg_row[['Y_dir_i', 'Y_dir_j', 'Y_dir_k']].values.flatten()
                self.z_dir = sg_row[['Z_dir_i', 'Z_dir_j', 'Z_dir_k']].values.flatten()

                # Normalize the directional vectors
                self.x_dir /= np.linalg.norm(self.x_dir)
                self.y_dir /= np.linalg.norm(self.y_dir)
                self.z_dir /= np.linalg.norm(self.z_dir)
            else:
                # Handle the case where SG data is not found
                raise ValueError(f"SG data for {display_name} not found.")

            # Create a PyVista PolyData for the original points
            points = np.vstack((x, y, z)).T
            polydata = pv.PolyData(points)
            polydata['Strain [µε]'] = strain

            # Calculate the max and min values of the strains in the existing data on the screen
            initial_clim = [strain.min(), strain.max()]

            # Add the original points to the plotter
            self.polydata_actor = self.plotter.add_mesh(polydata, scalars='Strain [µε]', cmap='turbo', point_size=15,
                                                        render_points_as_spheres=True, clim=initial_clim)

            # Remove the default scalar bar that PyVista adds
            #self.plotter.remove_scalar_bar()

            # Create the surface mesh of the strain data
            mesh = pv.PolyData(nodes)
            mesh = mesh.delaunay_2d()
            mesh.point_data['Strain [µε]'] = strain

            # Get the subdivide level from the spinbox
            subdivide_level = self.subdivide_spinbox.value()

            # Subdivide the mesh to increase resolution
            refined_mesh = mesh.subdivide(subdivide_level, subfilter='linear')
            refined_mesh = refined_mesh.sample(mesh)

            # Store the refined mesh for later use
            self.refined_mesh = refined_mesh

            # Apply bounding box filtering if the bounding box exists for this channel
            bounding_box_key = display_name.replace("SG_Ch_", "SG_Grid_Body_")
            if self.bounding_boxes and bounding_box_key in self.bounding_boxes:
                bounding_box = self.bounding_boxes[bounding_box_key]

                # Define bounding box bounds and center
                bbox_center = bounding_box['center']
                bbox_lengths = bounding_box['lengths']

                # Create the bounding box mesh (initially axis-aligned)
                bounding_box_mesh = pv.Cube(center=bbox_center, x_length=bbox_lengths[0], y_length=bbox_lengths[1],
                                            z_length=bbox_lengths[2])

                # Calculate the translation vector in the local coordinate system
                translation_vector = self.bounding_box_offset_x * np.array([1, 0, 0]) + self.bounding_box_offset_y * np.array([0, 1, 0])

                # Translate the entire bounding box along the local axes
                bounding_box_mesh.translate(translation_vector, inplace=True)

                # Create the 4x4 transformation matrix
                transformation_matrix = np.eye(4)
                transformation_matrix[:3, :3] = np.column_stack((self.x_dir, self.y_dir, self.z_dir))
                transformation_matrix[:3, 3] = self.origin - bbox_center

                # Apply the transformation to the bounding box
                bounding_box_mesh = bounding_box_mesh.transform(transformation_matrix)

                # Apply the inverse rotation to the refined mesh points
                inverse_transformation_matrix = np.linalg.inv(transformation_matrix)
                transformed_points = pv.PolyData(refined_mesh.points).transform(
                    inverse_transformation_matrix).points

                # Apply the inverse translation the refined mesh points
                transformed_points -= translation_vector

                # Define axis-aligned bounding box (AABB) in the transformed space
                transformed_bbox_min = bbox_center - bbox_lengths / 2
                transformed_bbox_max = bbox_center + bbox_lengths / 2

                # Filter points that lie within the AABB
                mask = (
                        (transformed_points[:, 0] >= transformed_bbox_min[0]) & (
                        transformed_points[:, 0] <= transformed_bbox_max[0]) &
                        (transformed_points[:, 1] >= transformed_bbox_min[1]) & (
                                transformed_points[:, 1] <= transformed_bbox_max[1]) &
                        (transformed_points[:, 2] >= transformed_bbox_min[2]) & (
                                transformed_points[:, 2] <= transformed_bbox_max[2])
                )

                # Calculate the average strain in the bounding box
                selected_points = refined_mesh.extract_points(mask)

                if selected_points.n_points > 0:
                    # Calculate the average strain in the bounding box
                    average_strain = selected_points['Strain [µε]'].mean()

                    # Visualize the bounding box as a wireframe
                    self.plotter.add_mesh(bounding_box_mesh, color='red', style='wireframe', line_width=5)

                    # Visualize the selected points inside the rotated bounding box
                    self.selected_points_actor = self.plotter.add_mesh(selected_points, color='yellow', point_size=10,
                                          render_points_as_spheres=True, opacity=1)

                    # Add a 3D label at the center of the bounding box
                    label_text = f"Strain (Avg.): {average_strain:.4f} µε"
                    bbox_center_rotated = bounding_box_mesh.center

                    self.plotter.add_point_labels(
                        [bbox_center_rotated], [label_text],
                        point_size=0, font_size=12, text_color='black', shape='rounded_rect', margin=5,
                        always_visible=True, shape_opacity=0.8, shape_color="#F5F5DC"
                    )
                else:
                    QMessageBox.warning(self, "Bounding Box Error",
                                        "No points found within the bounding box. Average strain cannot be calculated.")
                    return

            # Setting the properties of the scalar bar
            self.sargs = dict(title="Strain [µε]", height=0.7, width=0.05, vertical=True, position_x=0.03,
                                              position_y=0.2, n_labels=10,
                                              title_font_size=10, label_font_size=10)

            # Add the surface mesh to the plotter
            self.refined_mesh_actor = self.plotter.add_mesh(refined_mesh, scalars='Strain [µε]', cmap='turbo', opacity=1, clim=initial_clim,
                                  scalar_bar_args=self.sargs, show_edges=self.checkbox_show_edges.isChecked()) # TODO - Make this line work

            # Set the visibility of the original points based on the checkbox state
            if not self.checkbox_points.isChecked():
                self.polydata_actor.VisibilityOff()

            # Add the global origin
            self.plotter.add_axes_at_origin(labels_off=True, line_width=3)

            # Display local SG axes if the checkbox is checked
            if self.checkbox_axes.isChecked():
                self.show_axes(display_name)

            self.plotter.camera.position = camera_position
            self.plotter.camera.focal_point = camera_focal_point
            self.plotter.camera.clipping_range = camera_clipping_range

            # Render the plot
            self.plotter.show()

        except Exception as e:
            print(e)
            QMessageBox.critical(self, "Error", e)

    def updateBoundingBoxPosition(self):
        """Update the bounding box position based on user-defined offset values."""
        self.bounding_box_offset_x = self.offset_x_spinbox.value()
        self.bounding_box_offset_y = self.offset_y_spinbox.value()
        self.updatePlot()

    def togglePointsVisibility(self, state):
        if self.polydata_actor is not None:
            if state == Qt.Checked:
                self.polydata_actor.VisibilityOn()
            else:
                self.polydata_actor.VisibilityOff()
            self.plotter.render()

    def toggleAxesVisibility(self, state):
        selected_display_name = self.comboBox.currentText()
        if state == Qt.Checked:
            self.show_axes(selected_display_name)
        else:
            self.hide_axes(selected_display_name)

    def toggleShowEdges(self, state):
        show_edges = state == Qt.Checked
        if self.refined_mesh_actor:
            self.refined_mesh_actor.GetProperty().SetEdgeVisibility(show_edges)
            self.plotter.render()

    def show_axes(self, display_name):
        # Create and add the SG axes at the origin
        scale_factor_arrow = 4
        try:
            x_axis = pv.Arrow(start=self.origin, direction=self.x_dir, scale=scale_factor_arrow)
            y_axis = pv.Arrow(start=self.origin, direction=self.y_dir, scale=scale_factor_arrow)
            z_axis = pv.Arrow(start=self.origin, direction=self.z_dir, scale=scale_factor_arrow)

            x_actor = self.plotter.add_mesh(x_axis, color="red")
            y_actor = self.plotter.add_mesh(y_axis, color="green")
            z_actor = self.plotter.add_mesh(z_axis, color="blue")

            self.sg_axes_actors[display_name] = [x_actor, y_actor, z_actor]

        except Exception as e:
            print(e)

    def hide_axes(self, display_name):
        if display_name in self.sg_axes_actors:
            for actor in self.sg_axes_actors[display_name]:
                self.plotter.remove_actor(actor)
            del self.sg_axes_actors[display_name]

    def showSTL(self, selected_stl):
        stl_file_path = os.path.join(self.folder_path, selected_stl)
        #print(f"Loading STL file: {stl_file_path}")
        if os.path.exists(stl_file_path):
            stl_mesh = pv.read(stl_file_path)
            #print(f"STL mesh loaded: {stl_mesh}")

            # Apply scaling factor from settings
            scale_factor = float(
                self.main_window.scale_factor_input.currentText())  # Get the scale factor from settings
            stl_mesh.scale([scale_factor, scale_factor, scale_factor], inplace=True)
            #print(f"STL mesh scaled: {stl_mesh.bounds}")

            # Add the mesh to the plotter, ensuring the old actor is removed if it exists
            if self.stl_actor is not None:
                self.plotter.remove_actor(self.stl_actor)

            self.stl_actor = self.plotter.add_mesh(stl_mesh, color="white", opacity=0.99)  # Set opacity to 50%

            #print(f"STL actor added: {self.stl_actor}")
            self.plotter.render()
        else:
            print(f"STL file not found: {stl_file_path}")
            QMessageBox.critical(self, "Error", "STL file not found.")


if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    main_window = MainWindow()
    sys.exit(app.exec_())
