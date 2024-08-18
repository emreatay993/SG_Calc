import sys
import os
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, \
    QComboBox, QLabel, QCheckBox, QMessageBox, QGroupBox
from PyQt5.QtCore import Qt
from scipy.interpolate import griddata
import pyvista as pv
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
        h_layout_stl_file.addWidget(self.stl_comboBox)
        h_layout_stl_file.addWidget(self.stl_file_label)
        stl_layout.addLayout(h_layout_stl_file)

        h_layout_scale = QHBoxLayout()
        self.scale_label = QLabel("STL Scale Factor:")
        self.scale_factor_input = QComboBox()
        self.scale_factor_input.setEditable(True)  # Make the combobox editable
        self.scale_factor_input.addItems(["0.001", "0.01", "0.1", "1", "10","100","1000"])
        self.scale_factor_input.setCurrentText("999")
        self.scale_factor_input.editTextChanged.connect(self.validateScaleFactor)
        h_layout_scale.addWidget(self.scale_label)
        h_layout_scale.addWidget(self.scale_factor_input)
        stl_layout.addLayout(h_layout_scale)

        self.stl_groupbox.setLayout(stl_layout)
        self.stl_groupbox.hide()  # Initially hide the STL settings groupbox
        layout.addWidget(self.stl_groupbox)

        self.settings_widget.setLayout(layout)

    def validateScaleFactor(self, text):
        try:
            value = float(text)
            if value <= 0:
                raise ValueError("Scale factor must be positive.")

            adjusted_value = value
            self.scale_factor_input.blockSignals(True)  # Temporarily block signals to avoid recursive updates
            self.scale_factor_input.setCurrentText(str(adjusted_value))
            self.scale_factor_input.blockSignals(False)  # Re-enable signals
        except ValueError:
            self.scale_factor_input.setCurrentText("999")  # Revert to 1000 if the input is not valid

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
            self.checkbox_stl.setChecked(True)  # Check the checkbox if STL files are found
            self.stl_comboBox.show()  # Show the combobox if STL files are found
        else:
            self.checkbox_stl.setChecked(False)
            self.checkbox_stl.setEnabled(False)


class VTKWidget(QWidget):

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.first_channel_plot = True

        layout = QVBoxLayout()

        h_layout = QHBoxLayout()
        self.label = QLabel("Select a channel:")
        self.comboBox = QComboBox()
        self.comboBox.currentIndexChanged.connect(self.updatePlot)
        h_layout.addWidget(self.label)
        h_layout.addWidget(self.comboBox)

        self.checkbox_points = QCheckBox("Show original points")
        self.checkbox_points.stateChanged.connect(self.togglePointsVisibility)
        h_layout.addWidget(self.checkbox_points)

        self.checkbox_axes = QCheckBox("Show Axes")
        self.checkbox_axes.setChecked(True)
        self.checkbox_axes.stateChanged.connect(self.toggleAxesVisibility)
        h_layout.addWidget(self.checkbox_axes)

        layout.addLayout(h_layout)

        self.plotter = BackgroundPlotter(show=False)  # Initialize the PyVista plotter

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
                # Set the focal point to the click position
                self.plotter.camera.focal_point = pick_position
                self.plotter.render()

            # Call the superclass method to handle the event normally
            interactor.GetInteractorStyle().OnLeftButtonDown()

        # Set the custom interaction behavior
        self.plotter.interactor.AddObserver("LeftButtonPressEvent", on_left_button_down)

    def processFolder(self, folder_path):
        self.folder_path = folder_path
        # Load SG_coordinate_matrix.csv
        sg_file_path = os.path.join(folder_path, "SG_coordinate_matrix.csv")
        if os.path.exists(sg_file_path):
            self.sg_data = pd.read_csv(sg_file_path)

        # Load each CSV file that starts with "StrainX_around_"
        items = []
        for file_name in os.listdir(folder_path):
            if file_name.startswith("StrainX_around_") and file_name.endswith(".csv"):
                file_path = os.path.join(folder_path, file_name)
                data = pd.read_csv(file_path, sep='\t')
                display_name = file_name.replace("StrainX_around_", "").replace(".csv", "")
                items.append((display_name, data, file_name))

        def sort_key(display_name):
            try:
                return tuple(map(int, display_name.replace("SG_Ch_", "").split('_')))
            except ValueError as e:
                print(f"Error parsing '{display_name}': {e}. This item will be sorted at the end of the combobox.")
                return float('inf'), 0  # Move problematic entries to the end

        # Sort items based on SG and channel numbers
        sorted_items = sorted(items, key=lambda x: sort_key(x[0]))

        # Add sorted items to the combobox and store data
        for display_name, data, file_name in sorted_items:
            self.data_frames[display_name] = data
            self.file_mapping[display_name] = file_name
            self.comboBox.addItem(display_name)

        # Notify settings tab to load STL files
        self.main_window.loadStlFiles(folder_path)

        if self.comboBox.count() > 0:
            self.comboBox.setCurrentIndex(0)

    def updatePlot(self):
        selected_display_name = self.comboBox.currentText()
        if selected_display_name in self.data_frames:
            self.plotData(self.data_frames[selected_display_name], selected_display_name)

    def plotData(self, data, display_name):
        try:
            # Store the current camera settings if not the first actual channel plot
            if not self.first_channel_plot:
                camera_position = self.plotter.camera.position
                camera_focal_point = self.plotter.camera.focal_point
                camera_clipping_range = self.plotter.camera.clipping_range
            else:
                camera_position = None

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

            # Create a PyVista PolyData for the original points
            points = np.vstack((x, y, z)).T
            polydata = pv.PolyData(points)
            polydata['Strain [µε]'] = strain

            # Calculate the max and min values of the strains in the existing data on the screen
            initial_clim = [strain.min(), strain.max()]

            # Add the original points to the plotter
            self.polydata_actor = self.plotter.add_mesh(polydata, scalars='Strain [µε]', cmap='turbo', point_size=15,
                                                        render_points_as_spheres=True, clim=initial_clim)

            # Create the surface mesh of the strain data
            mesh = pv.PolyData(nodes)
            mesh = mesh.delaunay_2d()
            mesh.point_data['Strain [µε]'] = strain

            # Subdivide the mesh to increase resolution
            refined_mesh = mesh.subdivide(3, subfilter='linear')
            refined_mesh = refined_mesh.sample(mesh)

            # Setting the properties of the scalar bar
            sargs = dict(title="Strain [µε]", height=0.7, width=0.05, vertical=True, position_x=0.03,
                                              position_y=0.2, n_labels=10,
                                              title_font_size=10, label_font_size=10)

            # Add the surface mesh to the plotter
            self.plotter.add_mesh(refined_mesh, scalars='Strain [µε]', cmap='turbo', opacity=0.99, clim=initial_clim,
                                  scalar_bar_args=sargs)

            # Set the visibility of the original points based on the checkbox state
            if not self.checkbox_points.isChecked():
                self.polydata_actor.VisibilityOff()

            # Add the global origin
            self.plotter.add_axes_at_origin(labels_off=True, line_width=3)

            # Define the origin and directional vectors for the SG axes based on SG_coordinate_matrix.csv
            if self.sg_data is not None:
                sg_row = self.sg_data[self.sg_data['CS Name'] == f"CS_{display_name}"]
                if not sg_row.empty:
                    self.origin = sg_row[['Origin_X', 'Origin_Y', 'Origin_Z']].values.flatten()
                    self.x_dir = sg_row[['X_dir_i', 'X_dir_j', 'X_dir_k']].values.flatten()
                    self.y_dir = sg_row[['Y_dir_i', 'Y_dir_j', 'Y_dir_k']].values.flatten()
                    self.z_dir = sg_row[['Z_dir_i', 'Z_dir_j', 'Z_dir_k']].values.flatten()

                    # Add SG axes if the checkbox is checked
                    if self.checkbox_axes.isChecked():
                        self.show_axes(display_name)

            # Restore the camera settings if they were set previously and this is not the first channel plot
            if camera_position is not None:
                self.plotter.camera.position = camera_position
                self.plotter.camera.focal_point = camera_focal_point
                self.plotter.camera.clipping_range = camera_clipping_range

                # Render the plot
                self.plotter.show()

            # Mark the first channel plot as complete
            self.first_channel_plot = False

        except Exception as e:
            QMessageBox.critical(self, "Error", e)

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

            self.stl_actor = self.plotter.add_mesh(stl_mesh, color="white", opacity=1)  # Set opacity to 50%

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
