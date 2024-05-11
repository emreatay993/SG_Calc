# region Import necessary libraries
import re
import csv
import os
import System
from System.Windows.Forms import (Form, ComboBox, Button, Label, 
                                  Application, MessageBox, MessageBoxButtons, 
                                  MessageBoxIcon, DialogResult, OpenFileDialog, Keys)
from System.Drawing import Font, FontStyle, Color, Size
from System.Drawing import Point as GUI_Point
# endregion

#--------------------------------------------------------------------------------------------

# region Class definition(s) for GUI
class DataSelectionForm(Form):
    def __init__(self, times, measurements):
        self.Text = "Data Selection"
        self.Width = 300
        self.Height = 220
        self.BackColor = Color.White

        # Define GUI fonts
        label_font = Font("Segoe UI", 10, FontStyle.Bold)
        combobox_font = Font("Segoe UI", 10, FontStyle.Regular)

        # Label for the time selection ComboBox
        self.timeLabel = Label()
        self.timeLabel.Text = "Select a time point"
        self.timeLabel.Location = GUI_Point(30, 20)
        self.timeLabel.Size = Size(240, 20)
        self.timeLabel.Font = label_font
        self.timeLabel.ForeColor = Color.LightSkyBlue
        self.timeLabel.Parent = self

        # Time selection ComboBox
        self.timeCombo = ComboBox()
        self.timeCombo.Parent = self
        self.timeCombo.Location = GUI_Point(30, 40)
        self.timeCombo.Size = Size(240, 30)
        self.timeCombo.Font = combobox_font
        self.timeCombo.ForeColor = Color.Black
        [self.timeCombo.Items.Add(time) for time in times]
        self.timeCombo.SelectedIndex = 0

        # Label for the measurement type selection ComboBox
        self.measurementLabel = Label()
        self.measurementLabel.Text = "Select a result set"
        self.measurementLabel.Location = GUI_Point(30, 80)
        self.measurementLabel.Size = Size(240, 20)
        self.measurementLabel.Font = label_font
        self.measurementLabel.ForeColor = Color.LightSkyBlue
        self.measurementLabel.Parent = self

        # Measurement type selection ComboBox
        self.measurementCombo = ComboBox()
        self.measurementCombo.Parent = self
        self.measurementCombo.Location = GUI_Point(30, 100)
        self.measurementCombo.Size = Size(240, 30)
        self.measurementCombo.Font = combobox_font
        self.measurementCombo.ForeColor = Color.Black
        [self.measurementCombo.Items.Add(m) for m in measurements]
        self.measurementCombo.SelectedIndex = 0

        # OK Button
        self.okButton = Button()
        self.okButton.Text = "OK"
        self.okButton.Font = label_font
        self.okButton.ForeColor = Color.Black
        self.okButton.BackColor = Color.LightSkyBlue
        self.okButton.Location = GUI_Point(100, 140)
        self.okButton.Size = Size(100, 30)
        self.okButton.Parent = self
        self.okButton.Click += self.button_clicked

        # Enable KeyPreview to catch key events before they reach other controls
        self.KeyPreview = True

        # Handle key down events on the form
        self.KeyDown += self.form_key_down

    def button_clicked(self, sender, args):
        # Actions to perform when OK button is clicked
        self.perform_actions()

    def form_key_down(self, sender, args):
        # Check if the Enter key was pressed
        if args.KeyCode == Keys.Enter:
            # Prevent further processing of the key event
            args.Handled = True
            # Perform the same actions as clicking the OK button
            self.perform_actions()

    def perform_actions(self):
        # Common actions to perform (previously in button_clicked)
        global time_value, measurement_type
        time_value = float(self.timeCombo.SelectedItem)
        measurement_type = self.measurementCombo.SelectedItem
        print("Selected Time:", time_value)
        print("Selected Measurement Type:", measurement_type)
        self.Close()
# endregion

#--------------------------------------------------------------------------------------------

# region Global function definitions
# Extract the number from the channel name for sorting
def extract_number(channel_name):
    match = re.search(r'CS_SG_Ch_(\d+)_2', channel_name)
    return int(match.group(1)) if match else 0
# Create a color scale for the labels to be generated
def interpolate_segment(color1, color2, segment_fraction):
    return tuple(color1[i] + (color2[i] - color1[i]) * segment_fraction for i in range(3))

def get_rainbow_color(value, min_val, max_val):
    # Define the color range for the gradient
    colors = [
             (255, 0, 0),
             (255, 178, 0),
             (255, 216, 0),
             (255, 255, 0),
             (216, 255, 0),
             (178, 255, 0),
             (89, 255, 0),
             (0, 255, 0),
             (0, 255, 89),
             (0, 255, 178),
             (0, 255, 216),
             (0, 255, 255),
             (0, 216, 255),
             (0, 178, 255),
             (0, 89, 255),
             (0, 0, 255),
             (0, 0, 255),
             (153, 153, 102)]
    # Reverse the color order so that colors go from violet-blue to red as they increase
    colors.reverse()
    
    # Determine how many segments there are
    num_segments = len(colors) - 1
    
    # Scale the value to the number of segments
    scaled_value = float(value - min_val) / float(max_val - min_val) * num_segments
    
    # Determine which two colors to interpolate between
    first_color_index = int(scaled_value)
    second_color_index = min(first_color_index + 1, num_segments)
    
    # Determine the fraction between the two colors
    segment_fraction = scaled_value - first_color_index
    
    # Interpolate between the two colors
    return interpolate_segment(colors[first_color_index], colors[second_color_index], segment_fraction)

def numbers_to_rainbow_colors(numbers):
    min_val = min(numbers)
    max_val = max(numbers)
    
    # Generate a color for each number
    colors = [get_rainbow_color(num, min_val, max_val) for num in numbers]
    
    # Convert to RGB format as integers from 0 to 255
    rgb_colors = [(int(r), int(g), int(b)) for r, g, b in colors]
    
    return rgb_colors
# Function to classify headers based on measurement types
def classify_headers_by_measurement(file_path):
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        headers = next(reader)  # Read the header row
        measurements = {}  # Dictionary to store measurement types and indices

        # Regex to extract measurement types from header names
        pattern_measurement = re.compile(r'SG\d+_(\w+)')

        for index, header in enumerate(headers):
            match = pattern_measurement.search(header)
            if match:
                measurement = match.group(1)
                if measurement not in measurements:
                    measurements[measurement] = []
                measurements[measurement].append(index)
            elif "Time" in header:
                measurements["Time"] = [index]

    return measurements
# Function to read a specific row based on "Time" and optionally filter by measurement type
def read_row_based_on_time_and_measurement(file_path, time_value, measurement_type=None):
    measurements = classify_headers_by_measurement(file_path)  # Get measurement groups
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        header = next(reader)
        time_index = header.index('Time')

        for row in reader:
            if float(row[time_index]) == float(time_value):
                if measurement_type:
                    # Filter for specific measurement type
                    indices = measurements.get(measurement_type, [])
                    return [float(row[i]) for i in indices]
                else:
                    # Return all values converted to float
                    return [float(value) for value in row]
# Function to classify headers and find unique time values
def prepare_data(file_path):
    times = set()
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # Skip the header
        for row in reader:
            times.add(row[0])  # Assuming time values are in the first column
    return sorted(times), ['epsilon_x', 'epsilon_y', 'von_Mises', 'gamma_xy', 'sigma_1', 'sigma_2', 'theta_p', 'Biaxiality_Ratio']
# endregion

#--------------------------------------------------------------------------------------------

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
# Sort the list of filtered names of CS_SG_Channels so that they are in natural order
list_of_names_of_CS_SG_channels.sort(key=extract_number)
# Extract SG reference numbers as well
list_of_SG_reference_numbers = [
    int(re.search(pattern, channel).group(1))  # Capture the group 1 which is the reference number
    for channel in list_of_filtered_names_of_CS_SG_channels if re.search(pattern, channel)]
# endregion

#--------------------------------------------------------------------------------------------

# region Get the corresponding objects from the tree and their coordinates
ExtAPI.Application.ActiveUnitSystem = MechanicalUnitSystem.StandardMKS  # Set the unit system as 'm,kg,N'
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

#--------------------------------------------------------------------------------------------

# region Check if SG labels already exist within the memory, if they do, delete and re-create them
label_manager = Graphics.LabelManager
list_of_obj_of_SG_label_calculation = \
    [label_manager.Labels[i]
     for i in range(len(label_manager.Labels))
     if label_manager.Labels[i].Note.Contains("SG_")]
label_manager.DeleteLabels(list_of_obj_of_SG_label_calculation)
# endregion

#--------------------------------------------------------------------------------------------

# region Configure the graphics settings
label_manager.LabelObscureStyle = MechanicalEnums.Graphics.ObscuredLabelStyle.eHiddenStyle
# endregion

#--------------------------------------------------------------------------------------------

# region Try to read the SG calculation results from solution folder path, if there is any file
solution_directory_path = sol_selected_environment.WorkingDir[:-1]
solution_directory_path = solution_directory_path.Replace("\\", "\\\\")
file_name_of_SG_calculations = 'SG_calculations_FEA.csv'
file_path_of_SG_calculations = os.path.join(solution_directory_path,file_name_of_SG_calculations)

if os.path.exists(file_path_of_SG_calculations):
    times, measurements = prepare_data(file_path_of_SG_calculations)
    form = DataSelectionForm(times, measurements)
    Application.Run(form)
    list_of_requested_SG_label_result = read_row_based_on_time_and_measurement(file_path_of_SG_calculations, time_value, measurement_type)
    list_of_requested_SG_label_result = [round(num, 2) for num in list_of_requested_SG_label_result] # round off the results to two significant digits
    # Determine the color scheme of labels based on calculated SG data
    color_list = numbers_to_rainbow_colors(list_of_requested_SG_label_result)
if not os.path.exists(file_path_of_SG_calculations):
    message = '"SG_calculations_FEA.csv" file is not found in the solution directory. Would you like to manually specify this file?'
    title = 'File Not Found'
    result = MessageBox.Show(message, title, MessageBoxButtons.YesNo, MessageBoxIcon.Warning)
    if result == DialogResult.Yes:
        file_dialog = OpenFileDialog()
        file_dialog.Filter = "CSV files (*.csv)|*.csv"
        file_dialog.Title = "Select a CSV file of SG Calculations"
        if file_dialog.ShowDialog() == DialogResult.OK:
            file_path_of_SG_calculations = file_dialog.FileName
            print("File selected:", file_path_of_SG_calculations)
            times, measurements = prepare_data(file_path_of_SG_calculations)
            form = DataSelectionForm(times, measurements)
            Application.Run(form)
            list_of_requested_SG_label_result = read_row_based_on_time_and_measurement(file_path_of_SG_calculations, time_value, measurement_type)
            list_of_requested_SG_label_result = [round(num, 2) for num in list_of_requested_SG_label_result]
            # Determine the color scheme of labels based on calculated SG data
            color_list = numbers_to_rainbow_colors(list_of_requested_SG_label_result)
    else:
        print("No files are selected. Only labels will be generated")
        list_of_requested_SG_label_result = [""]*len(list_of_coordinates_of_all_filtered_names_of_CS_SG_channels)
        # Determine the color scheme of labels based on SG numbers
        color_list = numbers_to_rainbow_colors(list_of_SG_reference_numbers)

# endregion

#--------------------------------------------------------------------------------------------

# region Create SG labels on the screen
#Define whether labels will always stay on the screen
if list_of_filtered_names_of_CS_SG_channels:
    message = 'Would you like the SG labels to always stay on the screen?'
    title = 'Select an option'
    result = MessageBox.Show(message, title, MessageBoxButtons.YesNo, MessageBoxIcon.Warning)
    if result == DialogResult.Yes:
        yes_no_choice_is_labels_always_on_screen = True
    elif result == DialogResult.No:
        yes_no_choice_is_labels_always_on_screen = False

# Refractoring collector list for a better readability of the code
xyz_list = None
xyz_list = list_of_coordinates_of_all_filtered_names_of_CS_SG_channels
# Initialize list of label objects
list_of_obj_of_SG_label_calculation = []

with Graphics.Suspend():
    with Transaction():
        # Assign a background color for each numerical value
        for i in range(len(xyz_list)):
            obj_of_SG_label_calculation = label_manager.CreateLabel(sol_selected_environment)
            obj_of_SG_label_calculation.Note = ("SG_" 
                                                + str(list_of_SG_reference_numbers[i]) 
                                                + ": "
                                                + str(list_of_requested_SG_label_result[i]))
            obj_of_SG_label_calculation.Scoping.XYZ = Point((xyz_list[i][0], xyz_list[i][1], xyz_list[i][2]), 'm')
            obj_of_SG_label_calculation.ShowAlways = yes_no_choice_is_labels_always_on_screen
            obj_of_SG_label_calculation.Color = Ansys.ACT.Common.Graphics.Color(red=color_list[i][0], 
                                                                                green=color_list[i][1], 
                                                                                blue=color_list[i][2], 
                                                                                alpha=0)
            list_of_obj_of_SG_label_calculation.append(obj_of_SG_label_calculation)
# endregion

ExtAPI.Application.ActiveUnitSystem = MechanicalUnitSystem.StandardNMM  # Revert the unit system back to 'mm,kg,N'
