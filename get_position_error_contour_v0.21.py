import clr

clr.AddReference('mscorlib')  # Ensure the core .NET assembly is referenced
from System.IO import StreamWriter, FileStream, FileMode, FileAccess
from System.Text import UTF8Encoding
from System.Diagnostics import Process, ProcessWindowStyle
import os

ExtAPI.Application.ActiveUnitSystem = MechanicalUnitSystem.StandardNMM

# Define the reference coordinates
# region Filter the list of name of reference channels (in this case Ch_2) from each CS_SG_Ch object
list_of_all_coordinate_systems = DataModel.Project.GetChildren(DataModelObjectCategory.CoordinateSystem,True)
list_of_names_of_CS_SG_channels = [list_of_all_coordinate_systems[i].Name 
                                   for i in range(len(list_of_all_coordinate_systems))
                                   if list_of_all_coordinate_systems[i].Name.Contains("CS_SG_Ch_")
                                   and list_of_all_coordinate_systems[i].ObjectState != ObjectState.Suppressed]

# Regular expression to match channel names where y = 2, possibly followed by an underscore and more characters
pattern = r'CS_SG_Ch_(\d+)_2[^0-9]*'

# Filtered list using regular expression
list_of_filtered_names_of_CS_SG_channels = [
    channel for channel in list_of_names_of_CS_SG_channels if re.search(pattern, channel)]

# Extract the number from the channel name for sorting
def extract_number(channel_name):
    match = re.search(r'CS_SG_Ch_(\d+)_2', channel_name)
    return int(match.group(1)) if match else 0

# Sort the list of filtered names of CS_SG_Channels so that they are in natural order
list_of_filtered_names_of_CS_SG_channels.sort(key=extract_number)

# Extract SG reference numbers as well
list_of_SG_reference_numbers = [
    int(re.search(pattern, channel).group(1))  # Capture the group 1 which is the reference number
    for channel in list_of_filtered_names_of_CS_SG_channels if re.search(pattern, channel)]
# endregion

# region Get the corresponding objects from the tree and their coordinates
#ExtAPI.Application.ActiveUnitSystem = MechanicalUnitSystem.StandardMKS  # Set the unit system as 'm,kg,N'
list_of_coordinates_of_all_filtered_names_of_CS_SG_channels = []

for i in range(len(list_of_filtered_names_of_CS_SG_channels)):
    # Get the list of transformed coordinates of each reference SG channel as a list of strings
    list_of_coordinates_of_filtered_names_of_CS_SG_channels = []
    list_of_coordinates_of_filtered_names_of_CS_SG_channels = \
    DataModel.GetObjectsByName(list_of_filtered_names_of_CS_SG_channels[i])[0].TransformedConfiguration.rsplit()[1:-1]
    
    # Convert this list into a list of actual numbers
    list_of_coordinates_of_each_filtered_names_of_CS_SG_channels = \
    [float(item) for item in list_of_coordinates_of_filtered_names_of_CS_SG_channels]
    
    # Collect the list of x,y,z coordinates of each reference SG channel in a wrapper/collector list
    list_of_coordinates_of_all_filtered_names_of_CS_SG_channels.append(
        list_of_coordinates_of_each_filtered_names_of_CS_SG_channels)
# endregion

list_of_coordinates_of_all_filtered_names_of_CS_SG_channels = []
for i in range(len(list_of_filtered_names_of_CS_SG_channels)):
    # Get the list of transformed coordinates of each reference SG channel as a list of strings
    list_of_coordinates_of_filtered_names_of_CS_SG_channels = []
    list_of_coordinates_of_filtered_names_of_CS_SG_channels = \
    DataModel.GetObjectsByName(list_of_filtered_names_of_CS_SG_channels[i])[0].TransformedConfiguration.rsplit()[1:-1]
    # Convert this list into a list of actual numbers
    list_of_coordinates_of_each_filtered_names_of_CS_SG_channels = \
    [float(item) for item in list_of_coordinates_of_filtered_names_of_CS_SG_channels]
    # Collect the list of x,y,z coordinates of each reference SG channel in a wrapper/collector list
    list_of_coordinates_of_all_filtered_names_of_CS_SG_channels.append(
        list_of_coordinates_of_each_filtered_names_of_CS_SG_channels)
# endregion

solution_directory_path = sol_selected_environment.WorkingDir[:-1]
solution_directory_path = solution_directory_path.Replace("\\", "\\\\")

cpython_script_name = "calculate_distance_error_for_reference_nodes.py"
cpython_script_path = sol_selected_environment.WorkingDir + cpython_script_name
cpython_code = """
import numpy as np
import pandas as pd
import re
import math
import sys
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton

# Define classes for dialog windows etc.
class RadiusDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Specify Distance')
        layout = QVBoxLayout()

        self.label = QLabel('Enter the max distance [mm]:')
        self.setFixedWidth(600)
        layout.addWidget(self.label)

        self.radius_input = QLineEdit(self)
        layout.addWidget(self.radius_input)

        self.submit_button = QPushButton('Submit', self)
        self.submit_button.clicked.connect(self.submit)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)

    def submit(self):
        self.radius = float(self.radius_input.text())
        self.accept()

def get_user_radius():
    app = QApplication(sys.argv)
    dialog = RadiusDialog()
    if dialog.exec_() == QDialog.Accepted:
        return dialog.radius
    return None

# Define the function to calculate the distance between two points
def calculate_distance(point1, point2):
    return np.linalg.norm(np.array(point1) - np.array(point2))

# Read the dataset
file_name = r"C:\Users\emre_\OneDrive\Desktop\J\ANSYS\Benchmark\load_reconstruction_v0_files\dp0\SYS-6\MECH\distance_error.txt"
data = pd.read_csv(file_name, delimiter='\t')

# Define the reference coordinates
reference_coordinates = """ + str(list_of_coordinates_of_all_filtered_names_of_CS_SG_channels) + """

# User-specified radius
radius = get_user_radius()

if radius is None:
    print("No radius specified.")
    sys.exit()

# Function to find the closest node
def find_closest_node(ref_coord, data):
    distances = data.apply(lambda row: calculate_distance(ref_coord, [row['X Location (mm)'], row['Y Location (mm)'], row['Z Location (mm)']]), axis=1)
    closest_index = distances.idxmin()
    return data.loc[closest_index]

# Iterate over each reference coordinate and find nodes within the radius
all_nodes_with_errors = []
max_errors = []
results = []
for idx, ref_coord in enumerate(reference_coordinates):
    nodes_within_radius = []
    closest_node = find_closest_node(ref_coord, data)
    closest_value = closest_node['Equivalent (von-Mises) Stress (MPa)']
    
    max_abs_error = 0
    max_rel_error = 0
    
    for _, row in data.iterrows():
        if row['Node Number'] == closest_node['Node Number']:
            continue
        node_coord = [row['X Location (mm)'], row['Y Location (mm)'], row['Z Location (mm)']]
        distance = calculate_distance(ref_coord, node_coord)
        if distance <= radius:
            absolute_error = closest_value - row['Equivalent (von-Mises) Stress (MPa)']
            relative_error = (absolute_error / closest_value) * 100
            max_abs_error = max(max_abs_error, absolute_error)
            max_rel_error = max(max_rel_error, relative_error)
            node_data = {
                'X': row['X Location (mm)'],
                'Y': row['Y Location (mm)'],
                'Z': row['Z Location (mm)'],
                'Absolute Error': round(absolute_error, 2),
                'Relative Error': round(relative_error, 2)
            }
            nodes_within_radius.append(node_data)
            all_nodes_with_errors.append(node_data)
    
    results.append({
        'Reference Point': f"Reference Point {idx + 1}",
        'Closest Node': {
            'Node Number': closest_node['Node Number'],
            'X': closest_node['X Location (mm)'],
            'Y': closest_node['Y Location (mm)'],
            'Z': closest_node['Z Location (mm)'],
            'Stress (MPa)': closest_value
        },
        'Nodes Within Radius': nodes_within_radius
    })
    
    max_errors.append({
        'Reference Point': f"Reference Point {idx + 1}",
        'X': ref_coord[0],
        'Y': ref_coord[1],
        'Z': ref_coord[2],
        'Max Absolute Error': round(max_abs_error, 2),
        'Max Relative Error': round(max_rel_error, 2)
    })

# Convert the results to DataFrames
errors_df = pd.DataFrame(all_nodes_with_errors)
max_errors_df = pd.DataFrame(max_errors)

# Save the results to CSV files
errors_csv = r'""" + solution_directory_path + """\\results_errors.csv'
max_errors_csv = r'""" + solution_directory_path + """\\results_max_errors.csv'

errors_df.to_csv(errors_csv, index=False)
max_errors_df.to_csv(max_errors_csv, index=False)

# Print the results
for result in results:
    print(f"{result['Reference Point']}:")
    print(f"  Closest Node: {result['Closest Node']}")
    print("  Nodes Within Radius:")
    for node in result['Nodes Within Radius']:
        print(f"    {node}")
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
