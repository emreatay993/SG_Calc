# region Import libraries
import csv
import context_menu
import clr

clr.AddReference('mscorlib')  # Ensure the core .NET assembly is referenced
from System.IO import StreamWriter, FileStream, FileMode, FileAccess
from System.Text import UTF8Encoding
from System.Diagnostics import Process, ProcessWindowStyle
import os

# endregion

# region Define the plot function to be run
solution_directory_path = sol_selected_environment.WorkingDir[:-1]
solution_directory_path = solution_directory_path.Replace("\\", "\\\\")
file_name_of_SG_calculations = 'SG_calculations_FEA.csv'
file_path_of_SG_calculations = os.path.join(solution_directory_path, file_name_of_SG_calculations)

cpython_script_name = "plot_SG_calculations_FEA_cpython_code_only.py"
cpython_script_path = sol_selected_environment.WorkingDir + cpython_script_name
cpython_code ="""
# region Import necessary modules
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
try:
    import sys
    import threading
    import pandas as pd
    import numpy as np
    import plotly.graph_objects as go
    from plotly.offline import plot
    import plotly.express as px
    import plotly.figure_factory as ff
    import os
    import re
    from PyQt5.QtCore import Qt
    from PyQt5 import QtCore
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QLineEdit, QDialog, QHBoxLayout,
                                 QVBoxLayout, QWidget, QMessageBox, QComboBox, QCheckBox, QFileDialog,
                                 QLabel, QSizePolicy, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView)
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    import concurrent.futures
    from concurrent.futures import ThreadPoolExecutor

    import dash
    from dash import dcc, html
    import dash_bootstrap_components as dbc
except ImportError as e:

    app_messagebox = QApplication(sys.argv)
    QMessageBox.critical(None, "Import Error", f"Failed to import a required module: {str(e)}")
    sys.exit(1)
# endregion

# region Define classes and global functions/variables
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
my_discrete_color_scheme = px.colors.qualitative.Light24

class FlatLineEdit(QLineEdit):
    def __init__(self, placeholder_text=""):
        super(FlatLineEdit, self).__init__()
        self.setPlaceholderText(placeholder_text)
        self.setStyleSheet("QLineEdit {border: 1px solid #bfbfbf; border-radius: 5px; padding: 5px; background-color: #ffffff;} QLineEdit:focus {border: 2px solid #0077B6;}")

class MaterialPropertiesDialog(QDialog):
    def __init__(self, parent=None):
        super(MaterialPropertiesDialog, self).__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Enter Material Properties')
        self.setGeometry(100, 100, 100, 100)
        self.fullWidth = 500
        self.fullHeight = 400
        self.reducedWidth = 400
        self.reducedHeight = 200

        self.setStyleSheet("QWidget { font-size: 11px; } QPushButton { background-color: #0077B6; color: white; border-radius: 5px; padding: 6px; } QLineEdit { border: 1px solid #ccc; border-radius: 5px; padding: 5px; background-color: #ffffff; } QLabel { color: #333; }")

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Adjusting the layout for labels and line edits
        formLayout = QVBoxLayout()

        self.labelE = QLabel("Young's Modulus [GPa]:")
        self.lineEditE = QLineEdit(self)
        formLayout.addWidget(self.labelE)
        formLayout.addWidget(self.lineEditE)

        self.labelV = QLabel("Poisson's Ratio:")
        self.lineEditV = QLineEdit(self)
        formLayout.addWidget(self.labelV)
        formLayout.addWidget(self.lineEditV)

        layout.addLayout(formLayout)

        # Checkbox for time-dependent input
        self.checkbox = QCheckBox("Time Dependent Input:")
        self.checkbox.stateChanged.connect(self.toggle_time_dependent_input)
        layout.addWidget(self.checkbox)

        # File selection and data table visibility
        fileLayout = QHBoxLayout()
        self.fileLabel = QLabel("Select a directory for 'T vs. E, v' data:")
        self.fileLabel.setVisible(False)
        self.selectFileButton = QPushButton("Select File")
        self.selectFileButton.clicked.connect(self.select_file)
        self.selectFileButton.setVisible(False)
        fileLayout.addWidget(self.fileLabel)
        fileLayout.addWidget(self.selectFileButton)
        layout.addLayout(fileLayout)

        self.filePathLineEdit = QLineEdit(self)
        self.filePathLineEdit.setReadOnly(True)
        self.filePathLineEdit.setVisible(False)
        layout.addWidget(self.filePathLineEdit)

        # Table to display the data
        self.dataTable = QTableWidget(self)
        self.dataTable.setColumnCount(3)
        self.dataTable.setHorizontalHeaderLabels(["Temperature [°C]", "Young's Modulus [GPa]", "Poisson's Ratio"])
        self.dataTable.setVisible(False)
        self.dataTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.dataTable)

        # OK and Cancel buttons
        buttonLayout = QHBoxLayout()
        self.okButton = QPushButton('OK')
        self.okButton.clicked.connect(self.acceptInputs)
        cancelButton = QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(self.okButton)
        buttonLayout.addWidget(cancelButton)
        layout.addLayout(buttonLayout)

        self.resize(self.reducedWidth, self.reducedHeight+100)

    def toggle_time_dependent_input(self, state):
        is_checked = state == Qt.Checked
        if is_checked:
            self.resize(self.fullWidth, self.fullHeight)
            self.lineEditE.clear()
            self.lineEditV.clear()
            self.lineEditE.setStyleSheet("background-color: #e0e0e0;")  # Light grey background
            self.lineEditV.setStyleSheet("background-color: #e0e0e0;")  # Light grey background
        else:
            self.resize(self.reducedWidth, self.reducedHeight)
            self.lineEditE.setStyleSheet("background-color: #ffffff;")  # White background
            self.lineEditV.setStyleSheet("background-color: #ffffff;")  # White background
        self.lineEditE.setDisabled(is_checked)
        self.lineEditV.setDisabled(is_checked)
        self.fileLabel.setVisible(is_checked)
        self.selectFileButton.setVisible(is_checked)
        self.filePathLineEdit.setVisible(is_checked)
        self.dataTable.setVisible(is_checked)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv);;All Files (*)")
        if file_path:
            self.filePathLineEdit.setText(file_path)
            self.load_data(file_path)

    def load_data(self, file_path):
        try:
            data = pd.read_csv(file_path, encoding='ISO-8859-1')
            self.populate_table(data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load the file: {str(e)}")

    def populate_table(self, data):
        self.dataTable.setRowCount(len(data))
        for i, (index, row) in enumerate(data.iterrows()):
            self.dataTable.setItem(i, 0, QTableWidgetItem(str(row[0])))
            self.dataTable.setItem(i, 1, QTableWidgetItem(str(row[1])))
            self.dataTable.setItem(i, 2, QTableWidgetItem(str(row[2])))
        self.dataTable.setVisible(True)

    def acceptInputs(self):
            try:
                E = float(self.lineEditE.text())
                E = E*1e9  # Convert the [GPa] to SI units [Pa]
                v = float(self.lineEditV.text())
                # Optionally add validation rules here
                if E <= 0 or v <= 0 or v >= 0.5:
                    raise ValueError("Please enter valid values: E > 0, 0 < v < 0.5")
                self.user_input = {'E': E, 'v': v}
                self.accept()  # Close the dialog and return success
            except ValueError as ve:
                QMessageBox.critical(self, "Input Error", str(ve))

class PlotlyViewer(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.qdash = QDash()
        self.qdash.run(debug=True, use_reloader=False)
        self.load(QtCore.QUrl("http://127.0.0.1:8050"))

    def update_plot(self, fig):
        self.qdash.update_graph(fig)
        self.reload()

class PlotWindow(QMainWindow):
    def __init__(self, folder_name, file_name):
        super().__init__()
        self.setWindowTitle('SG Calculations - FEA: """ + sol_selected_environment.Parent.Name + """')
        self.setGeometry(100, 100, 800, 600)
        self.folder_name = folder_name
        self.file_name = file_name
        self.data = None
        self.initUI()

    def initUI(self):
        file_path = os.path.join(self.folder_name, self.file_name)
        try:
            self.data = pd.read_csv(file_path)
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Failed to read the file: {str(e)}")
            sys.exit(1)

        # Filter Data label setup
        self.label = QLabel("Filter Data:")
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Combobox setups
        self.comboBox = QComboBox()
        self.comboBox.addItem("All")
        self.comboBox.addItem("Raw Strain Data")
        # Add data groups to the combobox
        self.add_combobox_items()

        self.refNumberComboBox = QComboBox()
        self.refNumberComboBox.addItem("-")  # Similar to "All" functionality
        self.add_ref_number_items()

        self.comboBox.currentIndexChanged.connect(self.update_plot)
        self.refNumberComboBox.currentIndexChanged.connect(self.update_plot)
        self.viewer = PlotlyViewer()
        self.savePlotButton = QPushButton("Save current plot as HTML file")
        self.savePlotButton.clicked.connect(self.save_current_plot)

        self.update_plot(0)  # Initialize plot

        # Modify the layout setup to add the label and combobox horizontally
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.label)
        filter_layout.addWidget(self.comboBox)
        filter_layout.addWidget(self.refNumberComboBox)
        filter_layout.addWidget(self.savePlotButton)
        filter_layout.addStretch()  # Add stretch to push everything to the left

        # Create the main layout
        layout = QVBoxLayout()

        # Add the filter layout to the main layout using addLayout
        layout.addLayout(filter_layout)

        # Add the rest of your widgets to the layout
        layout.addWidget(self.viewer)

        # Set the layout to the central widget
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def add_combobox_items(self):
        suffixes = set()
        for col in self.data.columns:
            if '_' in col and not col.split('_')[1].isdigit():
                suffix = col.split('_', 1)[1]
                suffixes.add(suffix)

        for suffix in sorted(suffixes):
            self.comboBox.addItem(suffix)

    def add_ref_number_items(self):
        ref_numbers = set(col.split('_')[1] for col in self.data.columns if '_' in col and col.split('_')[1].isdigit())
        for ref_number in sorted(ref_numbers, key=int):
            self.refNumberComboBox.addItem(ref_number)

    def update_plot(self, index):
        fig = go.Figure()
        selected_group = self.comboBox.currentText()
        selected_ref_number = self.refNumberComboBox.currentText()

        # Determine columns based on the selected suffix
        if selected_group == "All":
            trace_columns = [col for col in self.data.columns if col != 'Time']
        elif selected_group == "Raw Strain Data":
            trace_columns = [col for col in self.data.columns if re.match(r'SG\d+_\d+$', col)]
        else:
            trace_columns = [col for col in self.data.columns if col.endswith(selected_group)]

        # Further filter columns based on the selected reference number
        if selected_ref_number != "-":
            trace_columns = [col for col in trace_columns if col.split('_')[1] == selected_ref_number]

        # Debug output
        print(f"Filtered columns: {trace_columns}")

        # Assign colors to visible traces based on their new filtered position
        for idx, col in enumerate(trace_columns):
            color_idx = idx % len(my_discrete_color_scheme)
            fig.add_trace(go.Scatter(
                x=self.data['Time'],
                y=self.data[col],
                mode='lines',
                name=col,
                line=dict(color=my_discrete_color_scheme[color_idx]),  # Assign color based on position in filtered list
                hovertemplate='%{meta}<br>Time = %{x:.2f} s<br>Data = %{y:.1f}<extra></extra>',
                hoverlabel=dict(font_size=10, bgcolor='rgba(255, 255, 255, 0.5)'),
                meta=col
            ))

        fig.update_layout(
            title_text='SG Calculations - FEA: ' + selected_group,
            title_x=0.5,
            legend_title_text='Result',
            template="plotly_white",
            plot_bgcolor='rgba(0,0,0,0.005)',
            xaxis_title='Time [s]',
            yaxis_title='Data',
            font=dict(family="Arial, sans-serif", size=12, color="#0077B6"),
            xaxis=dict(showline=True, showgrid=True, showticklabels=True, linewidth=2,
                       tickfont=dict(family='Arial, sans-serif', size=12), tickmode='auto', nticks=30),
            yaxis=dict(showgrid=True, zeroline=False, showline=False, showticklabels=True,
                       linecolor='rgb(204, 204, 204)', tickmode='auto', nticks=30)
        )

        self.viewer.update_plot(fig)

    def save_current_plot(self):
        # Retrieve the parent name from the environment for the filename
        parent_name = '''""" + sol_selected_environment.Parent.Name + """'''
        # Construct the filename
        filename = f"SG_Calculations_FEA__{parent_name}.html"

        # Debug: Print the figure data to verify its contents
        print("Saving plot with data:")
        print(self.viewer.qdash.app.layout.children[0].figure.data)

        # Save the current figure to an interactive HTML file
        plot(self.viewer.qdash.app.layout.children[0].figure, filename=os.path.join(self.folder_name, filename),
             output_type='file', auto_open=False)
        QMessageBox.information(self, "Plot Saved", f"The plot has been saved as {filename} in the solution directory.")# endregion

class QDash(QtCore.QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.app.layout = html.Div()

    @property
    def app(self):
        return self._app

    def update_graph(self, fig):
        self.app.layout = html.Div([
            dcc.Graph(
                figure=fig,
                config={
                    'displaylogo': False  # Disable the plotly logo
                },
                style={'width': '100%', 'height': '100vh'}
            )
        ])

    def run(self, **kwargs):
        threading.Thread(target=self.app.run_server, kwargs=kwargs, daemon=True).start()

# region Engineering Formulas
def transform_strains_to_global(epsilon_A, epsilon_B, epsilon_C, angles):
    theta_A, theta_B, theta_C = np.radians(angles)
    T = np.array([
        [np.cos(theta_A)**2, np.sin(theta_A)**2, 1 * np.sin(theta_A) * np.cos(theta_A)],
        [np.cos(theta_B)**2, np.sin(theta_B)**2, 1 * np.sin(theta_B) * np.cos(theta_B)],
        [np.cos(theta_C)**2, np.sin(theta_C)**2, 1 * np.sin(theta_C) * np.cos(theta_C)]
    ])
    T_inv = np.linalg.inv(T)
    local_strains = np.array([epsilon_A, epsilon_B, epsilon_C])
    global_strains = T_inv @ local_strains
    return global_strains

def calculate_principal_strains(epsilon_x, epsilon_y, gamma_xy):
    C = (epsilon_x + epsilon_y) / 2
    R = np.sqrt(((epsilon_x - epsilon_y) / 2)**2 + (gamma_xy / 2)**2)
    epsilon_1 = C + R  # Maximum principal strain
    epsilon_2 = C - R  # Minimum principal strain
    return np.array([epsilon_1, epsilon_2])

def calculate_principal_stresses(principal_strains, E, v):
    #S = np.array([
    #    [1, v, 0],
    #    [v, 1, 0],
    #    [0, 0, (1-v)/2]
    #]) * E / (1 - v**2)
    S = np.array([
        [1, v],
        [v, 1]
    ]) * E / (1 - v**2)

    principal_stresses = S @ (principal_strains /1e6)
    return principal_stresses / 1e6  # Convert Pa to MPa

def calculate_principal_strain_orientation(epsilon_x, epsilon_y, gamma_xy):
    # Calculate the angle to the maximum principal strain
    theta_p_rad = 0.5 * np.arctan2(gamma_xy, epsilon_x - epsilon_y)
    theta_p = np.degrees(theta_p_rad)

    # Adjust the angle to ensure it's within the 0-180 degree range
    if theta_p < 0:
        theta_p += 180

    return theta_p

def calculate_biaxiality_ratio(S1, S2):
    # Ensure that sigma_1 is the larger one in absolute terms
    sigma_1 = np.where(np.abs(S1) >= np.abs(S2), S1, S2)
    sigma_2 = np.where(np.abs(S1) >= np.abs(S2), S2, S1)

    # Calculate the biaxiality ratio
    biaxiality_ratio = sigma_2 / sigma_1

    return biaxiality_ratio

def calculate_von_mises_stress(S1, S2, S3=0):
    # Calculate the von Mises stress using the principal stresses
    sigma_vm = np.sqrt(((S1 - S2)**2 + (S1 - S3)**2 + (S2 - S3)**2) / 2)
    return sigma_vm
# endregion

# region Selecting the input SG FEA channel data (in microstrains) and rosette configuration file via a dialog box
# Initialize the QApplication instance
app_dialog = QApplication(sys.argv)

# File selection for FEA strain data
file_path_FEA, _ = QFileDialog().getOpenFileName(None, 'Open FEA raw data file for SG rosettes',r'"""+solution_directory_path+"""' , 'All Files (*);;CSV Files (*.csv)')

# Check if a file was selected for FEA data
if file_path_FEA:
    print("Selected FEA data:", file_path_FEA)
else:
    print("No FEA data file selected.")
    # Handle the case when no file is selected, or set file_path to a default value
    # file_path = 'default_FEA_data.csv'

# File selection for rosette angles data
angles_file_path, _ = QFileDialog().getOpenFileName(None, 'Open SG rosette angles configuration file', '', 'All Files (*);;CSV Files (*.csv)')

# Check if a file was selected for rosette angles data
if angles_file_path:
    print("Selected rosette angles data:", angles_file_path)
else:
    print("No rosette angles data file selected.")
    # Handle the case when no file is selected, or set angles_file_path to a default value
    # angles_file_path = 'default_angles_data.csv'
# endregion

# region Load the CSV file containing the rosette angles
#angles_file_path = 'rosette_angles_v3.csv'
rosette_angles_df = pd.read_csv(angles_file_path)
print("Selected rosette angles data:", angles_file_path)
# endregion

# region Load the CSV file extracted from FEA, using "Strain Gage Toolbox" inside ANSYS Mechanical
if file_path_FEA:
    data = pd.read_csv(file_path_FEA)
    time = data['Time']
    strain_gauge_data_FEA = data.iloc[:, 1:].filter(regex='SG')
    strain_gauge_data_FEA.reset_index(drop=True, inplace=True)
    time.reset_index(drop=True, inplace=True)
else:
    print("The input file is not read. Check whether it is in the correct directory or has the correct file extension")

print("Selected FEA data from directory:   ", file_path_FEA)
strain_gauge_data_FEA
# endregion
# endregion

# region Define material properties
input_dialog = MaterialPropertiesDialog()
if input_dialog.exec_() == QDialog.Accepted:
    E = input_dialog.user_input.get('E')
    v = input_dialog.user_input.get('v')

    # Convert to numpy column arrays to get individual E and v at each index (therefore, at each time step) later
    E = (np.full(time.shape, E))
    v = (np.full(time.shape, v))
else:
    sys.exit("Material properties input was canceled or failed.")
# # endregion

# region Functions for main calculation loop
def process_sg_number(sg_number, strain_gauge_data, E, v):
    sg_cols = [col for col in strain_gauge_data.columns if f'SG{sg_number}_' in col]
    new_columns = []
    if len(sg_cols) == 3:
        rosette_row = rosette_angles_df[rosette_angles_df['SG'] == sg_number]
        if not rosette_row.empty:
            current_angles = rosette_row.iloc[0, 1:].values
            strains = strain_gauge_data[sg_cols].values.astype(dtype=np.float64)
            global_strains = np.array([transform_strains_to_global(*strain, current_angles) for strain in strains])
            principal_strains = np.array([calculate_principal_strains(strain[0], strain[1], strain[2]) for strain in global_strains])
            principal_stresses = np.array([calculate_principal_stresses(strain, E[i], v[i]) for i, strain in enumerate(principal_strains)])
            principal_strain_orientation = np.array([calculate_principal_strain_orientation(strain[0], strain[1], strain[2]) for strain in global_strains])
            biaxiality_ratios = calculate_biaxiality_ratio(principal_stresses[:, 0], principal_stresses[:, 1])
            von_mises_stresses = np.array([calculate_von_mises_stress(*stress) for stress in principal_stresses])
            for i, strain_type in enumerate(['epsilon_x [??]', 'epsilon_y [??]', 'gamma_xy [??]']):
                new_columns.append(pd.DataFrame({f'SG{sg_number}_{strain_type}': global_strains[:, i]}))
            new_columns.append(pd.DataFrame({f'SG{sg_number}_sigma_1 [MPa]': principal_stresses[:, 0],
                                             f'SG{sg_number}_sigma_2 [MPa]': principal_stresses[:, 1],
                                             f'SG{sg_number}_theta_p [°]': principal_strain_orientation,
                                             f'SG{sg_number}_Biaxiality_Ratio': biaxiality_ratios,
                                             f'SG{sg_number}_von_Mises [MPa]': von_mises_stresses}))
        else:
            print(f'Angles for Rosette {sg_number} not found in angles file.')
    else:
        print(f'SG Cols: {sg_cols}')
        print(f'Unexpected number of columns for Rosette {sg_number}.')
    return new_columns

def calculate_all_SG_variables(strain_gauge_data, rosette_angles_df):
    matching_columns = [col for col in strain_gauge_data.columns if re.search(r'SG(\d+)_', col)]
    sg_numbers = sorted(set(int(re.search(r'SG(\d+)_', col).group(1)) for col in matching_columns))

    new_columns_list = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(lambda sg_number: process_sg_number(sg_number, strain_gauge_data, E, v), sg_numbers)
        for result in results:
            new_columns_list.extend(result)

    strain_gauge_data = pd.concat([strain_gauge_data] + new_columns_list, axis=1)
    return strain_gauge_data
# endregion

# region Calculate the SG results (FEA)
if file_path_FEA:
    strain_gauge_data_FEA = calculate_all_SG_variables(strain_gauge_data_FEA, rosette_angles_df)
    strain_gauge_data_FEA.insert(0, 'Time', time)
    strain_gauge_data_FEA.set_index('Time', inplace=True)
    strain_gauge_data_FEA
# endregion

# region Write the resulting dataframe to a CSV file inside the solution folder
strain_gauge_data_FEA.to_csv(r'""" + file_path_of_SG_calculations + """')
# endregion

# region Show the results
try:
    if __name__ == '__main__':
        app_plot = QApplication(sys.argv)
        mainWindow = PlotWindow('""" + solution_directory_path + """', '""" + file_name_of_SG_calculations + """')
        mainWindow.show()
        sys.exit(app_plot.exec_())
        # os.remove(cpython_script_path)
except Exception as e:
        print(f"An error occurred: {e}")
        input("Press Enter to close...")
# endregion
"""

# Use StreamWriter with FileStream to write the file with UTF-8 encoding
with StreamWriter(FileStream(cpython_script_path, FileMode.Create, FileAccess.Write), UTF8Encoding(True)) as writer:
    writer.Write(cpython_code)

print("Python file created successfully with UTF-8 encoding.")
# endregion

# Run the CPython script asynchronously
process = Process()
# Configure the process to hide the window and not use the shell execute feature
# process.StartInfo.CreateNoWindow = True

process.StartInfo.UseShellExecute = True
# Set the command to run the Python interpreter with your script as the argument
process.StartInfo.WindowStyle = ProcessWindowStyle.Minimized
process.StartInfo.FileName = "cmd.exe"  # Use cmd.exe to allow window manipulation
process.StartInfo.Arguments = '/c python "' + cpython_script_path + '"'
# Start the process
process.Start()
# endregion