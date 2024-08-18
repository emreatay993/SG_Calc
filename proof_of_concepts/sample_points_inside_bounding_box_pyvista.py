import sys
import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QFrame
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initial bounding box dimensions
        self.x_min, self.x_max = -2, 2
        self.y_min, self.y_max = -2, 2
        self.z_min, self.z_max = -0.5, 0.5

        # Set up the main window
        self.setWindowTitle("Bounding Box Translation")
        self.setGeometry(100, 100, 900, 700)

        # Create the central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Create a frame for the visualization area
        self.visualization_frame = QFrame()
        self.visualization_layout = QVBoxLayout(self.visualization_frame)
        self.visualization_frame.setFrameShape(QFrame.StyledPanel)
        self.main_layout.addWidget(self.visualization_frame)

        # Add the PyVista plotter to the PyQt5 layout
        self.plotter = QtInteractor(self.visualization_frame)
        self.visualization_layout.addWidget(self.plotter.interactor)

        # Add the control panel
        self.create_control_panel()

        # Generate initial visualization
        self.create_visualization()

    def create_control_panel(self):
        # Create a horizontal layout for the control panel
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        self.main_layout.addWidget(control_panel)

        # Add buttons with icons and tooltips
        button_size = QSize(40, 40)  # Set a good size for buttons

        x_plus_button = QPushButton(QIcon("icons/x_plus.png"), "")
        x_plus_button.setToolTip("Translate bounding box in +X direction")
        x_plus_button.setIconSize(button_size)
        x_plus_button.setMinimumSize(button_size)
        x_plus_button.clicked.connect(lambda: self.update_bounding_box(dx=0.1))
        control_layout.addWidget(x_plus_button)

        x_minus_button = QPushButton(QIcon("icons/x_minus.png"), "")
        x_minus_button.setToolTip("Translate bounding box in -X direction")
        x_minus_button.setIconSize(button_size)
        x_minus_button.setMinimumSize(button_size)
        x_minus_button.clicked.connect(lambda: self.update_bounding_box(dx=-0.1))
        control_layout.addWidget(x_minus_button)

        y_plus_button = QPushButton(QIcon("icons/y_plus.png"), "")
        y_plus_button.setToolTip("Translate bounding box in +Y direction")
        y_plus_button.setIconSize(button_size)
        y_plus_button.setMinimumSize(button_size)
        y_plus_button.clicked.connect(lambda: self.update_bounding_box(dy=0.1))
        control_layout.addWidget(y_plus_button)

        y_minus_button = QPushButton(QIcon("icons/y_minus.png"), "")
        y_minus_button.setToolTip("Translate bounding box in -Y direction")
        y_minus_button.setIconSize(button_size)
        y_minus_button.setMinimumSize(button_size)
        y_minus_button.clicked.connect(lambda: self.update_bounding_box(dy=-0.1))
        control_layout.addWidget(y_minus_button)

        z_plus_button = QPushButton(QIcon("icons/z_plus.png"), "")
        z_plus_button.setToolTip("Translate bounding box in +Z direction")
        z_plus_button.setIconSize(button_size)
        z_plus_button.setMinimumSize(button_size)
        z_plus_button.clicked.connect(lambda: self.update_bounding_box(dz=0.1))
        control_layout.addWidget(z_plus_button)

        z_minus_button = QPushButton(QIcon("icons/z_minus.png"), "")
        z_minus_button.setToolTip("Translate bounding box in -Z direction")
        z_minus_button.setIconSize(button_size)
        z_minus_button.setMinimumSize(button_size)
        z_minus_button.clicked.connect(lambda: self.update_bounding_box(dz=-0.1))
        control_layout.addWidget(z_minus_button)

        # Apply modern button styling
        for button in control_layout.children():
            if isinstance(button, QPushButton):
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #2c3e50;
                        color: white;
                        border-radius: 5px;
                        padding: 5px;
                    }
                    QPushButton:hover {
                        background-color: #34495e;
                    }
                """)

    def create_visualization(self):
        # Generate node locations for a curved surface
        n_points = 100
        x = np.linspace(-5, 5, n_points)
        y = np.linspace(-5, 5, n_points)
        x, y = np.meshgrid(x, y)
        z = np.sin(np.sqrt(x**2 + y**2))
        nodes = np.c_[x.ravel(), y.ravel(), z.ravel()]

        # Simulate strain values
        strain_values = np.exp(-0.1 * (x**2 + y**2)).ravel()

        # Create the mesh and assign strain values
        mesh = pv.PolyData(nodes)
        mesh = mesh.delaunay_2d()
        mesh.point_data['strain'] = strain_values

        # Subdivide the mesh to increase resolution
        self.refined_mesh = mesh.subdivide(2, subfilter='linear')
        self.refined_mesh = self.refined_mesh.sample(mesh)

        # Initial visualization
        self.update_bounding_box()

    def update_bounding_box(self, dx=0, dy=0, dz=0):
        # Update bounding box position
        self.x_min += dx
        self.x_max += dx
        self.y_min += dy
        self.y_max += dy
        self.z_min += dz
        self.z_max += dz

        # Clear the previous meshes
        self.plotter.clear()

        # Define bounding box bounds and center
        bbox_center = np.array([
            (self.x_min + self.x_max) / 2,
            (self.y_min + self.y_max) / 2,
            (self.z_min + self.z_max) / 2,
        ])

        bbox_lengths = np.array([
            self.x_max - self.x_min,
            self.y_max - self.y_min,
            self.z_max - self.z_min,
        ])

        # Create the bounding box mesh and apply the rotation
        bounding_box = pv.Cube(center=bbox_center, x_length=bbox_lengths[0], y_length=bbox_lengths[1],
                               z_length=bbox_lengths[2])
        rotation_matrix = pv.transformations.axis_angle_rotation(axis=(1, 0, 0), angle=45)
        bounding_box = bounding_box.transform(rotation_matrix)

        # Apply the inverse rotation to the original points
        inverse_rotation_matrix = np.linalg.inv(rotation_matrix)
        transformed_points = pv.PolyData(self.refined_mesh.points).transform(inverse_rotation_matrix).points

        # Define axis-aligned bounding box (AABB) in the transformed space
        transformed_bbox_min = np.array([self.x_min, self.y_min, self.z_min])
        transformed_bbox_max = np.array([self.x_max, self.y_max, self.z_max])

        # Filter points that lie within the AABB
        mask = (
                (transformed_points[:, 0] >= transformed_bbox_min[0]) & (
                    transformed_points[:, 0] <= transformed_bbox_max[0]) &
                (transformed_points[:, 1] >= transformed_bbox_min[1]) & (
                            transformed_points[:, 1] <= transformed_bbox_max[1]) &
                (transformed_points[:, 2] >= transformed_bbox_min[2]) & (
                            transformed_points[:, 2] <= transformed_bbox_max[2])
        )

        selected_points = self.refined_mesh.extract_points(mask)

        # Calculate the average strain in the bounding box
        average_strain = selected_points['strain'].mean()
        print(f"Average strain in the bounding box: {average_strain:.4f}")

        # Visualize the entire refined mesh with strain distribution and visible edges
        self.plotter.add_mesh(self.refined_mesh, scalars='strain', cmap='coolwarm', scalar_bar_args={'title': 'Strain'},
                              show_edges=True)

        # Visualize the bounding box as a wireframe
        self.plotter.add_mesh(bounding_box, color='red', style='wireframe')

        # Visualize the selected points inside the rotated bounding box
        self.plotter.add_mesh(selected_points, color='yellow', point_size=10, render_points_as_spheres=True)

        # Add a 3D label at the center of the bounding box with simple styling and always visible
        label_text = f"Average Strain: {average_strain:.4f}"
        bbox_center_rotated = bounding_box.center

        self.plotter.add_point_labels(
            [bbox_center_rotated], [label_text],
            point_size=0, font_size=24, text_color='white', shape='rect',
            always_visible=True  # Ensure the label is visible from all angles
        )

        # Show the orientation marker and global coordinate system
        self.plotter.show_axes()
        self.plotter.add_axes(interactive=True)

        # Render the updated scene
        self.plotter.render()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
