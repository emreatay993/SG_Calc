import sys
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QFileDialog
from PyQt5.QtCore import Qt
from scipy.interpolate import griddata
import pyvista as pv
from pyvistaqt import BackgroundPlotter

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("PyQt5 with PyVista")
        self.setGeometry(100, 100, 800, 600)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.vtk_widget = VTKWidget()
        self.tabs.addTab(self.vtk_widget, "3D Plot")

        self.show()
        self.openFileNameDialog()

    def openFileNameDialog(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv);;All Files (*)")
        if fileName:
            self.vtk_widget.processFile(fileName)
        else:
            print("No file selected.")
            sys.exit(1)


class VTKWidget(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        self.plotter = BackgroundPlotter(show=False)  # Initialize the PyVista plotter
        layout.addWidget(self.plotter.interactor)
        self.setLayout(layout)

    def processFile(self, file_path):
        # Load the data
        data = pd.read_csv(file_path, sep='\t')

        # Extract X, Y, Z coordinates and strain values
        x = data['X Location (mm)'].values
        y = data['Y Location (mm)'].values
        z = data['Z Location (mm)'].values
        strain = data['Normal Elastic Strain (mm/mm)'].values

        # Create a PyVista PolyData for the original points
        points = np.vstack((x, y, z)).T
        polydata = pv.PolyData(points)
        polydata['Strain [µε]'] = strain

        # Define the finer grid for interpolation
        grid_x, grid_y = np.mgrid[x.min():x.max():2000j, y.min():y.max():2000j]

        # Perform the interpolation for z and strain values
        grid_z = griddata(points[:, :2], z, (grid_x, grid_y), method='linear')
        grid_strain = griddata(points[:, :2], strain, (grid_x, grid_y), method='linear')

        # Mask to filter out invalid points
        mask = ~np.isnan(grid_z) & ~np.isnan(grid_strain)

        # Reshape grid for structured grid creation
        grid_x = grid_x[mask].reshape(grid_z[mask].shape)
        grid_y = grid_y[mask].reshape(grid_z[mask].shape)
        grid_z = grid_z[mask].reshape(grid_z[mask].shape)
        grid_strain = grid_strain[mask].reshape(grid_strain[mask].shape)

        # Create a structured grid
        structured_grid = pv.StructuredGrid(grid_x, grid_y, grid_z)
        structured_grid['Strain [µε]'] = grid_strain

        # Add the original points to the plotter
        self.plotter.add_mesh(polydata, scalars='Strain [µε]', cmap='turbo', point_size=15, render_points_as_spheres=True)

        # Add the surface mesh to the plotter
        self.plotter.add_mesh(structured_grid, scalars='Strain [µε]', cmap='turbo', opacity=0.7)

        # Render the plot
        self.plotter.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    sys.exit(app.exec_())
