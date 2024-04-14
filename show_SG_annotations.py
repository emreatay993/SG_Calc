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
    channel for channel in list_of_names_of_CS_SG_channels if re.search(pattern, channel)
]

# Extract SG reference numbers as well
list_of_SG_reference_numbers = [
    re.search(pattern, channel).group(1)  # Capture the group 1 which is the reference number
    for channel in list_of_filtered_names_of_CS_SG_channels if re.search(pattern, channel)
]

# endregion

# region Get the corresponding objects from the tree and their coordinates
ExtAPI.Application.ActiveUnitSystem = MechanicalUnitSystem.StandardMKS  # Set the unit system as 'mm,kg,N'
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

# region Create text labels on the screen
scene = ExtAPI.Graphics.Scene
# Refractoring collector list for a better readability of the code
xyz_list = None
xyz_list = list_of_coordinates_of_all_filtered_names_of_CS_SG_channels
scene.Clear()
for i in range(len(xyz_list)):
    SG_label_on_screen = scene.Factory3D.CreateText3D(xyz_list[i][0],
                                                      xyz_list[i][1],
                                                      xyz_list[i][2],
                                                      "  SG" + list_of_SG_reference_numbers[i])
    SG_label_on_screen.Color = (255<<16) + (0<<8) + 0  # RGB coloring for Red
# endregion




# "scene.Clear()
# scene = ExtAPI.Graphics.Scene

# obj_of_label_text_of_SG = scene.Factory3D.CreateText3D()




# anan.Color = (255<<16) + (0<<8) + 0
