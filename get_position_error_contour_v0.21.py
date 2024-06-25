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
        self.setFixedWidth(300)  # Adjust the width as needed
        layout = QVBoxLayout()

        self.label = QLabel('Enter the max distance:')
        font = self.label.font()
        font.setPointSize(12)
        font.setBold(True)
        self.label.setFont(font)
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
            max_abs_error = max(max_abs_error, abs(absolute_error))
            max_rel_error = max(max_rel_error, abs(relative_error))
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
