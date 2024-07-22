# Import libraries
import os
import sys
import csv
import clr
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import MessageBox, MessageBoxButtons, MessageBoxIcon
import context_menu

# Initialize the preference settings of Mechanical
ExtAPI.Application.ScriptByName("jscript").ExecuteCommand(
    'WB.PreferenceMgr.Preference("PID_Show_Node_Numbers") = 1;')
ExtAPI.Application.ScriptByName("jscript").ExecuteCommand(
    'WB.PreferenceMgr.Preference("PID_Show_Node_Location") = 1;')
ExtAPI.Application.ScriptByName("jscript").ExecuteCommand(
    'WB.PreferenceMgr.Preference("PID_Show_Tensor_Components") = 1;')
ExtAPI.Application.ActiveUnitSystem = MechanicalUnitSystem.StandardNMM

# region Create local strain results around each SG with their respective SG orientations

# Get named selections
list_of_NS_of_nodes_around_each_SG = DataModel.GetObjectsByName("NS_of_nodes_around_each_SG")
list_of_StrainX_around_each_SG = DataModel.GetObjectsByName("StrainX_around_each_SG")

# Check if NS_of_nodes_around_each_SG exists
try:
    NS_of_nodes_around_each_SG_not_found = len(list_of_NS_of_nodes_around_each_SG) == 0
except:
    NS_of_nodes_around_each_SG_not_found = False

# If NS_of_nodes_around_each_SG exists, delete and regenerate objects
if not NS_of_nodes_around_each_SG_not_found:
    message = r"""Some output objects are already in the Mechanical Tree. The program will now attempt to delete and regenerate all of these objects."""
    caption = "Warning"
    buttons = MessageBoxButtons.OK
    icon = MessageBoxIcon.Warning
    MessageBox.Show(message, caption, buttons, icon)

    try:
        list_of_NS_of_nodes_around_each_SG[0].DeleteTreeGroupAndChildren()
    except Exception as e:
        MessageBox.Show(str(e), "Error", MessageBoxButtons.OK, MessageBoxIcon.Error)

    try:
        list_of_StrainX_around_each_SG[0].DeleteTreeGroupAndChildren()
    except Exception as e:
        MessageBox.Show(str(e), "Error", MessageBoxButtons.OK, MessageBoxIcon.Error)

# Check if NS_of_faces_of_SG_test_parts exists
try:
    NS_of_faces_of_SG_test_parts = DataModel.GetObjectsByName("NS_of_faces_of_SG_test_parts")[0]
    NS_of_faces_of_SG_test_parts_not_found = False
except:
    NS_of_faces_of_SG_test_parts_not_found = True

# Ensure test piece is correctly defined
if NS_of_faces_of_SG_test_parts_not_found:
    message = r"""Please define a named selection of bodies called "NS_of_faces_of_SG_test_parts" using "Test Part" button. """
    caption = "Warning"
    buttons = MessageBoxButtons.OK
    icon = MessageBoxIcon.Warning
    MessageBox.Show(message, caption, buttons, icon)

    NS_of_faces_of_SG_test_parts = Model.AddNamedSelection()
    NS_of_faces_of_SG_test_parts.Name = "NS_of_faces_of_SG_test_parts"
    NS_of_faces_of_SG_test_parts.SendToSolver = False

if not NS_of_faces_of_SG_test_parts_not_found and len(NS_of_faces_of_SG_test_parts.Location.Ids) == 0:
    message = r""""NS_of_faces_of_SG_test_parts" object is already in the tree but the bodies of test parts are not defined. 
    Ensure that it is assigned and this button is re-run. """
    caption = "Warning"
    buttons = MessageBoxButtons.OK
    icon = MessageBoxIcon.Warning
    MessageBox.Show(message, caption, buttons, icon)

# Get IDs and names of each coordinate system of each SG channel
if not NS_of_faces_of_SG_test_parts_not_found and len(NS_of_faces_of_SG_test_parts.Location.Ids) != 0:
    list_of_IDs_of_selections_of_NS_of_faces_of_SG_test_parts = NS_of_faces_of_SG_test_parts.Location.Ids

list_of_ids_of_each_CS_SG_Ch_ = [
    Model.CoordinateSystems.Children[i].ObjectId
    for i in range(len(Model.CoordinateSystems.Children))
    if Model.CoordinateSystems.Children[i].Name.Contains("CS_SG_Ch_")
]

list_of_names_of_each_CS_SG_Ch_ = [
    Model.CoordinateSystems.Children[i].Name
    for i in range(len(Model.CoordinateSystems.Children))
    if Model.CoordinateSystems.Children[i].Name.Contains("CS_SG_Ch_")
]

# Create a named selection of nodes around each SG channel
try:
    NS_of_nodes_of_SG_test_parts = DataModel.GetObjectsByName("NS_of_nodes_of_SG_test_parts")[0]
except:
    NS_of_nodes_of_SG_test_parts = NS_of_faces_of_SG_test_parts.CreateNodalNamedSelection()
    NS_of_nodes_of_SG_test_parts.Name = "NS_of_nodes_of_SG_test_parts"

list_of_NS_of_test_part_strains = []

for i in range(len(list_of_names_of_each_CS_SG_Ch_)):
    NS_of_test_part_strain = Model.AddNamedSelection()
    NS_of_test_part_strain.ScopingMethod = GeometryDefineByType.Worksheet

    NS_of_test_part_strain.GenerationCriteria.Add(None)
    NS_of_test_part_strain.GenerationCriteria[0].EntityType = SelectionType.MeshNode
    NS_of_test_part_strain.GenerationCriteria[0].Criterion = SelectionCriterionType.Distance
    NS_of_test_part_strain.GenerationCriteria[0].Operator = SelectionOperatorType.LessThanOrEqual
    NS_of_test_part_strain.GenerationCriteria[0].Value = Quantity(10, 'mm')
    NS_of_test_part_strain.GenerationCriteria[0].CoordinateSystem = DataModel.GetObjectById(list_of_ids_of_each_CS_SG_Ch_[i])
    
    NS_of_test_part_strain.GenerationCriteria.Add(None)
    NS_of_test_part_strain.GenerationCriteria[1].Action = SelectionActionType.Filter
    NS_of_test_part_strain.GenerationCriteria[1].Criterion = SelectionCriterionType.NamedSelection
    NS_of_test_part_strain.GenerationCriteria[1].Operator = SelectionOperatorType.Equal
    NS_of_test_part_strain.GenerationCriteria[1].Value = NS_of_nodes_of_SG_test_parts

    NS_of_test_part_strain.Name = "NS_of_nodes_around_" + list_of_names_of_each_CS_SG_Ch_[i]
    NS_of_test_part_strain.Generate()
    
    list_of_NS_of_test_part_strains.append(NS_of_test_part_strain)

# Create contour plot of strains for nodes around each CS_SG_Ch_
for i in range(len(list_of_names_of_each_CS_SG_Ch_)):
    try:
        obj_of_contour_of_nodes_around_each_SG_Ch = sol_selected_environment.AddNormalElasticStrain()
        obj_of_contour_of_nodes_around_each_SG_Ch.ScopingMethod = GeometryDefineByType.Component
        obj_of_contour_of_nodes_around_each_SG_Ch.Location = list_of_NS_of_test_part_strains[i]
        obj_of_contour_of_nodes_around_each_SG_Ch.Name = "StrainX_around_" + list_of_names_of_each_CS_SG_Ch_[i][3:]
        obj_of_contour_of_nodes_around_each_SG_Ch.CoordinateSystem = DataModel.GetObjectById(list_of_ids_of_each_CS_SG_Ch_[i])
        obj_of_contour_of_nodes_around_each_SG_Ch.CalculateTimeHistory = True
    except:
        message = r"""Please define the solution environment of interest by running "Solution Object" button. """
        caption = "Error"
        buttons = MessageBoxButtons.OK
        icon = MessageBoxIcon.Error
        MessageBox.Show(message, caption, buttons, icon)
        sys.exit(1)

# Get the list of all "NS_of_nodes_around_" objects in the tree
list_of_obj_of_NS = DataModel.Project.GetChildren(DataModelObjectCategory.NamedSelection, True)
list_of_obj_of_NS_of_nodes_around_each_SG = [
    obj for obj in list_of_obj_of_NS if obj.Name.Contains("NS_of_nodes_around_")
]

# Get the list of all "StrainX_around_" objects in the tree
list_of_obj_of_normal_strains = DataModel.Project.GetChildren(DataModelObjectCategory.NormalElasticStrain, True)
list_of_obj_of_StrainX_around = [
    obj for obj in list_of_obj_of_normal_strains if obj.Name.Contains("StrainX_around_")
]

# Group existing "NS_of_nodes_around_" objects
ExtAPI.DataModel.Tree.Activate(list_of_obj_of_NS_of_nodes_around_each_SG)
context_menu.DoCreateGroupingFolderInTree(ExtAPI)
DataModel.GetObjectsByName("New Folder")[0].Name = "NS_of_nodes_around_each_SG"

# Group existing "StrainX_around_" objects
ExtAPI.DataModel.Tree.Activate(list_of_obj_of_StrainX_around)
context_menu.DoCreateGroupingFolderInTree(ExtAPI)
DataModel.GetObjectsByName("New Folder")[0].Name = "StrainX_around_each_SG"

# Evaluate all results
sol_selected_environment.Activate()
sol_selected_environment.EvaluateAllResults()

# endregion

# region Create CSV files from each of these local SG strain results

# Define the solution directory path
solution_directory_path = sol_selected_environment.WorkingDir

# Define the path for the subfolder inside the parent folder
subfolder = os.path.join(solution_directory_path, "StrainX_around_each_SG")

# Check if the subfolder already exists, and create it if it does not
if not os.path.exists(subfolder):
    os.makedirs(subfolder)
    print("Folder '{}' created successfully.".format(subfolder))
else:
    print("Folder '{}' already exists.".format(subfolder))

# Export strain results to CSV files in the subfolder
for i in range(len(list_of_obj_of_StrainX_around)):
    # Construct file name and path
    file_name_of_StrainX_around_each_SG = list_of_obj_of_StrainX_around[i].Name + ".csv"
    file_path = os.path.join(subfolder, file_name_of_StrainX_around_each_SG)
    
    # Export the strain object to a text file
    list_of_obj_of_StrainX_around[i].ExportToTextFile(file_path)

# endregion

# region Create CSV files containing the corner points of each SG grid body
list_of_all_bodies_in_tree = DataModel.GetObjectsByType(DataModelObjectCategory.Body)

list_of_of_SG_grid_bodies = [
    (each_body.GetGeoBody().Name, each_body.GetGeoBody().Vertices)
    for each_body in list_of_all_bodies_in_tree
    if each_body.Name.Contains("SG_Grid_Body_") 
    ]

# Prepare data for CSV file containing SG geobody metadata (vertices, and their coords)
geo_data_SG =[]
body_vertices = each_body.GetGeoBody().Vertices
for i, each_SG_body in enumerate(list_of_of_SG_grid_bodies):
    body_vertices = each_SG_body[1]
    for j, each_vertex in enumerate(body_vertices):
        geo_data_SG.append({
            'Body_Name': each_SG_body[0],
            'Vertex_No': j+1,
            'X [mm]': each_vertex.X,
            'Y [mm]': each_vertex.Y,
            'Z [mm]': each_vertex.Z
        })
        
# Define CSV file path
csv_file_path = os.path.join(subfolder, 'SG_grid_body_vertices.csv')

# Write data to CSV
with open(csv_file_path, 'wb') as csvfile:
    fieldnames = ["Body_Name", "Vertex_No", "X [mm]", "Y [mm]", "Z [mm]"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    
    writer.writeheader()
    writer.writerows(geo_data_SG)

print("CSV file saved to {}".format(csv_file_path))

os.startfile(csv_file_path)
# endregion

# region Create CSV files containing the definition of coordinate system of the channel
def get_sg_coordinate_data(channel_name):
    # Retrieve the strain gauge channel object using its name
    SG_channel = DataModel.GetObjectsByName(channel_name)[0]
    
    # Create a dictionary to hold the matrix of origins and directional vectors
    coordinate_data = {
        'CS Name': channel_name,
        'Origin_X': SG_channel.Origin[0],
        'Origin_Y': SG_channel.Origin[1],
        'Origin_Z': SG_channel.Origin[2],
        'X_dir_i': SG_channel.XAxis[0],
        'X_dir_j': SG_channel.XAxis[1],
        'X_dir_k': SG_channel.XAxis[2],
        'Y_dir_i': SG_channel.YAxis[0],
        'Y_dir_j': SG_channel.YAxis[1],
        'Y_dir_k': SG_channel.YAxis[2],
        'Z_dir_i': SG_channel.ZAxis[0],
        'Z_dir_j': SG_channel.ZAxis[1],
        'Z_dir_k': SG_channel.ZAxis[2]
    }
    
    return coordinate_data

def save_data_to_csv(coordinate_data, file_path):
    # Define the order of the columns explicitly based on expected keys
    expected_keys = [
        'CS Name', 'Origin_X', 'Origin_Y', 'Origin_Z', 
        'X_dir_i', 'X_dir_j', 'X_dir_k',
        'Y_dir_i', 'Y_dir_j', 'Y_dir_k',
        'Z_dir_i', 'Z_dir_j', 'Z_dir_k'
    ]
    
    # Verify keys and add any that might be missing (optional robustness step)
    fieldnames = [key for key in expected_keys if key in coordinate_data]
    
    # Check if the file already exists to decide on writing headers
    write_header = not os.path.exists(file_path)
    
    with open(file_path, mode='ab') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        if write_header:
            writer.writeheader()
        
        # Ensure data is in the correct order by using the fieldnames
        writer.writerow({key: coordinate_data.get(key, '') for key in fieldnames})

    print("Data saved to {}".format(file_path))

# Define the solution directory path
solution_directory_path = sol_selected_environment.WorkingDir

# Define the path for the subfolder inside the parent folder
subfolder = os.path.join(solution_directory_path, "StrainX_around_each_SG")
file_name = "SG_coordinate_matrix.csv"
file_path = os.path.join(subfolder, file_name)

# Remove the old file to start fresh
try:
    if os.path.exists(file_path):
        os.remove(file_path)
except OSError as e:
    print("Error: {} : {}".format(file_path, e.strerror))

list_of_names_of_each_CS_SG_Ch_ = [
    Model.CoordinateSystems.Children[i].Name
    for i in range(len(Model.CoordinateSystems.Children))
    if Model.CoordinateSystems.Children[i].Name.Contains("CS_SG_Ch_")
]

for channel_name in list_of_names_of_each_CS_SG_Ch_:
    coordinate_data = get_sg_coordinate_data(channel_name)
    save_data_to_csv(coordinate_data, file_path)
# endregion
