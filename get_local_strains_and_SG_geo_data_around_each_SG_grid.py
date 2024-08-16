# region Import libraries
import os
import sys
import csv
import clr
clr.AddReference("System.Windows.Forms")
clr.AddReference("Microsoft.VisualBasic")
from Microsoft.VisualBasic import Interaction
from System.Windows.Forms import MessageBox, MessageBoxButtons, MessageBoxIcon
import context_menu
# endregion

# region Initialize the preference settings of Mechanical
def initialize_mechanical_preferences():
    ExtAPI.Application.ScriptByName("jscript").ExecuteCommand(
        'WB.PreferenceMgr.Preference("PID_Show_Node_Numbers") = 1;')
    ExtAPI.Application.ScriptByName("jscript").ExecuteCommand(
        'WB.PreferenceMgr.Preference("PID_Show_Node_Location") = 1;')
    ExtAPI.Application.ScriptByName("jscript").ExecuteCommand(
        'WB.PreferenceMgr.Preference("PID_Show_Tensor_Components") = 1;')
    ExtAPI.Application.ActiveUnitSystem = MechanicalUnitSystem.StandardNMM
# endregion

# region Create local strain results around each SG with their respective SG orientations

# Get named selections
def get_named_selections():
    list_of_NS_of_nodes_around_each_SG = DataModel.GetObjectsByName("NS_of_nodes_around_each_SG")
    list_of_StrainX_around_each_SG = DataModel.GetObjectsByName("StrainX_around_each_SG")
    return list_of_NS_of_nodes_around_each_SG, list_of_StrainX_around_each_SG

# Check if NS_of_nodes_around_each_SG exists
def check_NS_existence(list_of_NS_of_nodes_around_each_SG):
    try:
        return len(list_of_NS_of_nodes_around_each_SG) == 0
    except:
        return False

# If NS_of_nodes_around_each_SG exists, delete and regenerate objects
def handle_existing_NS(list_of_NS_of_nodes_around_each_SG, list_of_StrainX_around_each_SG):
    if not check_NS_existence(list_of_NS_of_nodes_around_each_SG):
        message = r"""Some output objects are already in the Mechanical Tree. The program will now attempt to delete and regenerate all of these objects."""
        caption = "Warning"
        MessageBox.Show(message, caption, MessageBoxButtons.OK, MessageBoxIcon.Warning)

        try:
            list_of_NS_of_nodes_around_each_SG[0].DeleteTreeGroupAndChildren()
        except Exception as e:
            MessageBox.Show(str(e), "Error", MessageBoxButtons.OK, MessageBoxIcon.Error)

        try:
            list_of_StrainX_around_each_SG[0].DeleteTreeGroupAndChildren()
        except Exception as e:
            MessageBox.Show(str(e), "Error", MessageBoxButtons.OK, MessageBoxIcon.Error)

# Check if NS_of_faces_of_SG_test_parts exists
def check_test_parts_existence():
    try:
        NS_faces_test_parts = DataModel.GetObjectsByName("NS_of_faces_of_SG_test_parts")[0]
        return NS_faces_test_parts, False
    except:
        return None, True

# Ensure test piece is correctly defined
def ensure_test_piece_defined(NS_faces_test_parts, NS_faces_test_parts_not_found):
    if NS_faces_test_parts_not_found:
        message = r"""Please define a named selection of bodies called "NS_of_faces_of_SG_test_parts" using "Test Part" button. """
        caption = "Warning"
        MessageBox.Show(message, caption, MessageBoxButtons.OK, MessageBoxIcon.Warning)

        NS_faces_test_parts = Model.AddNamedSelection()
        NS_faces_test_parts.Name = "NS_of_faces_of_SG_test_parts"
        NS_faces_test_parts.SendToSolver = False

    if not NS_faces_test_parts_not_found and len(NS_faces_test_parts.Location.Ids) == 0:
        message = r""""NS_of_faces_of_SG_test_parts" object is already in the tree but the bodies of test parts are not defined. 
        Ensure that it is assigned and this button is re-run. """
        caption = "Warning"
        MessageBox.Show(message, caption, MessageBoxButtons.OK, MessageBoxIcon.Warning)

    return NS_faces_test_parts

# Get IDs and names of each coordinate system of each SG channel
def get_CS_SG_ids_and_names():
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
    return list_of_ids_of_each_CS_SG_Ch_, list_of_names_of_each_CS_SG_Ch_

# Prompt the user for input
def prompt_user_for_radius():
    message = "Please enter the radius [mm] of interest around each SG:"
    title = "Input Required"
    default_value = "10"
    radius_str = Interaction.InputBox(message, title, default_value)
    try:
        radius = float(radius_str)
        return radius
    except ValueError:
        MessageBox.Show("Invalid input. Please enter a numeric value.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error)
        sys.exit(1)

# Create a named selection of nodes around each SG channel
def create_NS_of_nodes_around_SG(NS_faces_test_parts, list_of_ids_of_each_CS_SG_Ch_, list_of_names_of_each_CS_SG_Ch_, radius):
    try:
        NS_nodes_SG_test_parts = DataModel.GetObjectsByName("NS_of_nodes_of_SG_test_parts")[0]
    except:
        # NS_nodes_SG_test_parts = NS_faces_test_parts.CreateNodalNamedSelection()
        NS_nodes_SG_test_parts = Model.AddNamedSelection()
        NS_nodes_SG_test_parts.ScopingMethod = GeometryDefineByType.Worksheet
        NS_nodes_SG_test_parts.GenerationCriteria.Add(None)
        NS_nodes_SG_test_parts.GenerationCriteria[0].EntityType = SelectionType.GeoFace
        NS_nodes_SG_test_parts.GenerationCriteria[0].Criterion = SelectionCriterionType.NamedSelection
        NS_nodes_SG_test_parts.GenerationCriteria[0].Operator = SelectionOperatorType.Equal
        NS_nodes_SG_test_parts.GenerationCriteria[0].Value = NS_faces_test_parts
        NS_nodes_SG_test_parts.GenerationCriteria.Add(None)
        NS_nodes_SG_test_parts.GenerationCriteria[1].Action = SelectionActionType.Convert
        NS_nodes_SG_test_parts.GenerationCriteria[1].EntityType = SelectionType.MeshNode
        NS_nodes_SG_test_parts.Generate()
        NS_nodes_SG_test_parts.Name = "NS_of_nodes_of_SG_test_parts"

    list_of_NS_test_part_strains = []

    for i in range(len(list_of_names_of_each_CS_SG_Ch_)):
        NS_test_part_strain = Model.AddNamedSelection()
        NS_test_part_strain.ScopingMethod = GeometryDefineByType.Worksheet

        NS_test_part_strain.GenerationCriteria.Add(None)
        NS_test_part_strain.GenerationCriteria[0].EntityType = SelectionType.MeshNode
        NS_test_part_strain.GenerationCriteria[0].Criterion = SelectionCriterionType.Distance
        NS_test_part_strain.GenerationCriteria[0].Operator = SelectionOperatorType.LessThanOrEqual
        NS_test_part_strain.GenerationCriteria[0].Value = Quantity(radius, 'mm')
        NS_test_part_strain.GenerationCriteria[0].CoordinateSystem = DataModel.GetObjectById(list_of_ids_of_each_CS_SG_Ch_[i])

        NS_test_part_strain.GenerationCriteria.Add(None)
        NS_test_part_strain.GenerationCriteria[1].Action = SelectionActionType.Filter
        NS_test_part_strain.GenerationCriteria[1].Criterion = SelectionCriterionType.NamedSelection
        NS_test_part_strain.GenerationCriteria[1].Operator = SelectionOperatorType.Equal
        NS_test_part_strain.GenerationCriteria[1].Value = NS_nodes_SG_test_parts

        NS_test_part_strain.Name = "NS_of_nodes_around_" + list_of_names_of_each_CS_SG_Ch_[i]
        NS_test_part_strain.Generate()

        list_of_NS_test_part_strains.append(NS_test_part_strain)

    return list_of_NS_test_part_strains

# Create contour plot of strains for nodes around each CS_SG_Ch_
def create_contour_plot_of_strains(list_of_names_of_each_CS_SG_Ch_, list_of_ids_of_each_CS_SG_Ch_, list_of_NS_test_part_strains):
    for i in range(len(list_of_names_of_each_CS_SG_Ch_)):
        try:
            obj_of_contour_of_nodes_around_each_SG_Ch = sol_selected_environment.AddNormalElasticStrain()
            obj_of_contour_of_nodes_around_each_SG_Ch.ScopingMethod = GeometryDefineByType.Component
            obj_of_contour_of_nodes_around_each_SG_Ch.Location = list_of_NS_test_part_strains[i]
            obj_of_contour_of_nodes_around_each_SG_Ch.Name = "StrainX_around_" + list_of_names_of_each_CS_SG_Ch_[i][3:]
            obj_of_contour_of_nodes_around_each_SG_Ch.CoordinateSystem = DataModel.GetObjectById(list_of_ids_of_each_CS_SG_Ch_[i])
            obj_of_contour_of_nodes_around_each_SG_Ch.CalculateTimeHistory = True
        except:
            message = r"""Please define the solution environment of interest by running "Solution Object" button. """
            caption = "Error"
            MessageBox.Show(message, caption, MessageBoxButtons.OK, MessageBoxIcon.Error)
            sys.exit(1)

# Group existing objects in the tree
def group_existing_objects(list_of_obj_of_NS_of_nodes_around_each_SG, list_of_obj_of_StrainX_around):
    ExtAPI.DataModel.Tree.Activate(list_of_obj_of_NS_of_nodes_around_each_SG)
    context_menu.DoCreateGroupingFolderInTree(ExtAPI)
    DataModel.GetObjectsByName("New Folder")[0].Name = "NS_of_nodes_around_each_SG"

    ExtAPI.DataModel.Tree.Activate(list_of_obj_of_StrainX_around)
    context_menu.DoCreateGroupingFolderInTree(ExtAPI)
    DataModel.GetObjectsByName("New Folder")[0].Name = "StrainX_around_each_SG"

# Evaluate all results
def evaluate_all_results():
    sol_selected_environment.Activate()
    sol_selected_environment.EvaluateAllResults()

# Create CSV files from each of these local SG strain results
def create_CSV_files_from_strain_results(list_of_obj_of_StrainX_around):
    solution_directory_path = sol_selected_environment.WorkingDir
    subfolder = os.path.join(solution_directory_path, "StrainX_around_each_SG")

    if not os.path.exists(subfolder):
        os.makedirs(subfolder)
        print("Folder '{}' created successfully.".format(subfolder))
    else:
        print("Folder '{}' already exists.".format(subfolder))

    for i in range(len(list_of_obj_of_StrainX_around)):
        file_name_of_StrainX_around_each_SG = list_of_obj_of_StrainX_around[i].Name + ".csv"
        file_path = os.path.join(subfolder, file_name_of_StrainX_around_each_SG)
        list_of_obj_of_StrainX_around[i].ExportToTextFile(file_path)

# Create CSV files containing the corner points of each SG grid body
def create_CSV_files_for_SG_grid_bodies():
    list_of_all_bodies_in_tree = DataModel.GetObjectsByType(DataModelObjectCategory.Body)

    list_of_of_SG_grid_bodies = [
        (each_body.GetGeoBody().Name, each_body.GetGeoBody().Vertices)
        for each_body in list_of_all_bodies_in_tree
        if each_body.Name.Contains("SG_Grid_Body_") 
    ]

    geo_data_SG =[]
    for each_SG_body in list_of_of_SG_grid_bodies:
        body_vertices = each_SG_body[1]
        for j, each_vertex in enumerate(body_vertices):
            geo_data_SG.append({
                'Body_Name': each_SG_body[0],
                'Vertex_No': j+1,
                'X [mm]': each_vertex.X,
                'Y [mm]': each_vertex.Y,
                'Z [mm]': each_vertex.Z
            })

    solution_directory_path = sol_selected_environment.WorkingDir
    subfolder = os.path.join(solution_directory_path, "StrainX_around_each_SG")
    file_path_CSV_SG_grid_data = os.path.join(subfolder, 'SG_grid_body_vertices.csv')

    with open(file_path_CSV_SG_grid_data, 'wb') as csvfile:
        fieldnames = ["Body_Name", "Vertex_No", "X [mm]", "Y [mm]", "Z [mm]"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(geo_data_SG)

    print("CSV file saved to {}".format(file_path_CSV_SG_grid_data))
    #os.startfile(file_path_CSV_SG_grid_data)

# Create CSV files containing the definition of coordinate system of the channel
def get_SG_coordinate_data(channel_name):
    SG_channel = DataModel.GetObjectsByName(channel_name)[0]
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
    expected_keys = [
        'CS Name', 'Origin_X', 'Origin_Y', 'Origin_Z', 
        'X_dir_i', 'X_dir_j', 'X_dir_k',
        'Y_dir_i', 'Y_dir_j', 'Y_dir_k',
        'Z_dir_i', 'Z_dir_j', 'Z_dir_k'
    ]

    fieldnames = [key for key in expected_keys if key in coordinate_data]
    write_header = not os.path.exists(file_path)

    with open(file_path, mode='ab') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow({key: coordinate_data.get(key, '') for key in fieldnames})

    print("Data saved to {}".format(file_path))

def create_CSV_files_for_coordinate_system():
    solution_directory_path = sol_selected_environment.WorkingDir
    subfolder = os.path.join(solution_directory_path, "StrainX_around_each_SG")
    file_name = "SG_coordinate_matrix.csv"
    file_path = os.path.join(subfolder, file_name)

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
        coordinate_data = get_SG_coordinate_data(channel_name)
        save_data_to_csv(coordinate_data, file_path)

    #os.startfile(file_path)

# region Main execution
initialize_mechanical_preferences()

list_of_NS_of_nodes_around_each_SG, list_of_StrainX_around_each_SG = get_named_selections()
handle_existing_NS(list_of_NS_of_nodes_around_each_SG, list_of_StrainX_around_each_SG)

NS_faces_test_parts, NS_faces_test_parts_not_found = check_test_parts_existence()
NS_faces_test_parts = ensure_test_piece_defined(NS_faces_test_parts, NS_faces_test_parts_not_found)

list_of_ids_of_each_CS_SG_Ch_, list_of_names_of_each_CS_SG_Ch_ = get_CS_SG_ids_and_names()

radius = prompt_user_for_radius()
list_of_NS_test_part_strains = create_NS_of_nodes_around_SG(NS_faces_test_parts, list_of_ids_of_each_CS_SG_Ch_, list_of_names_of_each_CS_SG_Ch_, radius)
create_contour_plot_of_strains(list_of_names_of_each_CS_SG_Ch_, list_of_ids_of_each_CS_SG_Ch_, list_of_NS_test_part_strains)

list_of_obj_of_NS_of_nodes_around_each_SG = [
    obj for obj in DataModel.Project.GetChildren(DataModelObjectCategory.NamedSelection, True) if obj.Name.Contains("NS_of_nodes_around_")
]
list_of_obj_of_StrainX_around = [
    obj for obj in DataModel.Project.GetChildren(DataModelObjectCategory.NormalElasticStrain, True) if obj.Name.Contains("StrainX_around_")
]

group_existing_objects(list_of_obj_of_NS_of_nodes_around_each_SG, list_of_obj_of_StrainX_around)
evaluate_all_results()

create_CSV_files_from_strain_results(list_of_obj_of_StrainX_around)
create_CSV_files_for_SG_grid_bodies()
create_CSV_files_for_coordinate_system()
# endregion
