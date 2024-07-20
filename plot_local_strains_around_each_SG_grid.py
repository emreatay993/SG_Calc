import sys
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog
from scipy.interpolate import griddata
import pyvista as pv

class App(QWidget):

    def __init__(self):
        super().__init__()
        self.title = 'CSV File Selector'
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        layout = QVBoxLayout()

        # Create a button in the window
        self.button = QPushButton('Open CSV File', self)
        self.button.setToolTip('Click to open a CSV file')
        self.button.clicked.connect(self.openFileNameDialog)

        # Add the button to the layout
        layout.addWidget(self.button)
        self.setLayout(layout)

        self.show()

    def openFileNameDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv);;All Files (*)", options=options)
        if fileName:
            self.processFile(fileName)

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

        # Create a plotter object
        plotter = pv.Plotter()

        # Add the original points to the plotter
        plotter.add_mesh(polydata, scalars='Strain [µε]', cmap='turbo', point_size=15, render_points_as_spheres=True)

        # Add the surface mesh to the plotter
        plotter.add_mesh(structured_grid, scalars='Strain [µε]', cmap='turbo', opacity=0.7)

        # Show the plot
        plotter.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
