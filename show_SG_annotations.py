# region Import necessary libraries
import re
# endregion

# region Filter the list of name of reference channels (in this case Ch_2) from each CS_SG_Ch object
list_of_all_coordinate_systems = DataModel.Project.GetChildren(DataModelObjectCategory.CoordinateSystem,True)
list_of_names_of_CS_SG_channels = [list_of_all_coordinate_systems[i].Name 
                                   for i in range(len(list_of_all_coordinate_systems))
                                   if list_of_all_coordinate_systems[i].Name.Contains("CS_SG_Ch_")
                                   and list_of_all_coordinate_systems[i].ObjectState != ObjectState.Suppressed]
# Regular expression to match channel names where y = 2, possibly followed by an underscore and more characters
pattern = r'CS_SG_Ch_(\d+)_2(_|$)'
# Filtered list using regular expression
list_of_filtered_names_of_CS_SG_channels = [
    channel for channel in list_of_names_of_CS_SG_channels if re.search(pattern, channel)]
# Extract SG reference numbers as well
list_of_SG_reference_numbers = [
    int(re.search(pattern, channel).group(1))  # Capture the group 1 which is the reference number
    for channel in list_of_filtered_names_of_CS_SG_channels if re.search(pattern, channel)]
# endregion

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

# region Check if SG labels already exist within the memory, if they do, delete and re-create them
label_manager = Graphics.LabelManager
list_of_obj_of_SG_label_calculation = \
    [label_manager.Labels[i]
     for i in range(len(label_manager.Labels))
     if label_manager.Labels[i].Note.Contains("SG_")]
label_manager.DeleteLabels(list_of_obj_of_SG_label_calculation)
# endregion

# region Configure the graphics settings
label_manager.LabelObscureStyle = MechanicalEnums.Graphics.ObscuredLabelStyle.eHiddenStyle
# Create a color scale for the labels to be generated
def normalize_data(data):
    min_val = min(data)
    max_val = max(data)
    range_val = max_val - min_val
    if range_val == 0:  # to avoid division by zero if all numbers are the same
        return [0.5 for _ in data]  # midpoint in hue range
    return [(float(i - min_val) / range_val) for i in data]

def map_to_hsv(normalized_data, start_hue=240, end_hue=270):
    # Convert normalized value to a hue value between start_hue and end_hue
    return [(start_hue + (end_hue - start_hue) * x, 1.0, 1.0) for x in normalized_data]

def hsv_to_rgb(hsv_colors):
    # Convert HSV to RGB
    return [tuple(int(i * 255) for i in colorsys.hsv_to_rgb(h * 360.0 / 360, s, v)) for h, s, v in hsv_colors]

def generate_color_list(data):
    normalized_data = normalize_data(data)
    hsv_colors = map_to_hsv(normalized_data)
    rgb_colors = hsv_to_rgb(hsv_colors)
    return rgb_colors

# Generate the rainbow scale
color_list = generate_color_list(list_of_SG_reference_numbers)
# endregion

# region Create SG labels on the screen
# Refractoring collector list for a better readability of the code
xyz_list = None
xyz_list = list_of_coordinates_of_all_filtered_names_of_CS_SG_channels
# Initialize list of label objects
list_of_obj_of_SG_label_calculation = []

colors_of_SG_labels = map_values_to_colors(list_of_SG_reference_numbers, 14)
with Graphics.Suspend():
    with Transaction():
        # Assign a background color for each numerical value
        for i in range(len(xyz_list)):
            obj_of_SG_label_calculation = label_manager.CreateLabel(sol_selected_environment)
            obj_of_SG_label_calculation.Note = "SG_" + str(list_of_SG_reference_numbers[i])
            obj_of_SG_label_calculation.Scoping.XYZ = Point((xyz_list[i][0], xyz_list[i][1], xyz_list[i][2]), 'm')
            obj_of_SG_label_calculation.ShowAlways = True
            obj_of_SG_label_calculation.Color = Ansys.ACT.Common.Graphics.Color(red=color_list[i][0], 
                                                                                green=color_list[i][1], 
                                                                                blue=color_list[i][2], 
                                                                                alpha=0)
            list_of_obj_of_SG_label_calculation.append(obj_of_SG_label_calculation)
# endregion