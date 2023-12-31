import context_menu
import clr
clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import OpenFileDialog, DialogResult
from itertools import chain
import time

# Record the start time
start_time = time.time()


# Create an OpenFileDialog object
dialog = OpenFileDialog()

# Set properties
dialog.Filter = 'Ansys part database files (*.pmdb)|*.pmdb|All files (*.*)|*.*'  # Filter for pmdb files
dialog.Title = 'Select an SG part database file'

# Show the dialog and get the result
if dialog.ShowDialog() == DialogResult.OK:
    file_path_of_selected_SG_Part_from_library = dialog.FileName
    print("Selected SG part database file: " + file_path_of_selected_SG_Part_from_library)
else:
    print("No SG part database file selected")

try:
    obj_of_solution = sol_selected_environment
except:
    # Define the message, caption, and buttons for the message box
    message = r"""An analysis environment for solution is not selected,changed/deleted or the mechanical session is restarted. Please select the "Solution Object" again."""
    caption = "Error"
    buttons = MessageBoxButtons.OK
    icon = MessageBoxIcon.Error
    # Show the message box
    result = MessageBox.Show(message, caption, buttons, icon)

#Instances
create_geo_selection = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)


# Extracting reference points and their IDs for strain gauges.
list_of_obj_of_CS_SG_ref_points = [
    Model.CoordinateSystems.Children[i]
    for i in range(len(Model.CoordinateSystems.Children))
    if Model.CoordinateSystems.Children[i].Name.Contains("CS_SG_Ref")
]

list_of_IDs_of_CS_SG_ref_points = [
    Model.CoordinateSystems.Children[i].ObjectId
    for i in range(len(Model.CoordinateSystems.Children))
    if Model.CoordinateSystems.Children[i].Name.Contains("CS_SG_Ref")
]

# Importing and configuring geometry for each strain gauge.
for i in range(len(list_of_IDs_of_CS_SG_ref_points)):
    geometry_import_group = Model.GeometryImportGroup
    geometry_import = geometry_import_group.AddGeometryImport()
    geometry_import.Name = "SG_" + str(i + 1) +"_Geometry_Import"
    geometry_import_format = Ansys.Mechanical.DataModel.Enums.GeometryImportPreference.Format.Automatic
    geometry_import_preferences = Ansys.ACT.Mechanical.Utilities.GeometryImportPreferences()
    
    geometry_import.Import(file_path_of_selected_SG_Part_from_library, geometry_import_format, geometry_import_preferences)
    
    list_of_obj_of_bodies = DataModel.GetObjectsByType(Ansys.ACT.Automation.Mechanical.Body)
    list_of_IDs_of_underdefined_SG_grids = [
        list_of_obj_of_bodies[k].ObjectId
        for k in range(len(list_of_obj_of_bodies))
        if (list_of_obj_of_bodies[k].Thickness == Quantity('0 [m]') and 
            list_of_obj_of_bodies[k].Material == '' and 
            list_of_obj_of_bodies[k].Name.Contains("SG_"))
    ]
    
    # Updating properties of underdefined gauges.
    j = 1
    for each_ID_of_underdefined_SG_grids in list_of_IDs_of_underdefined_SG_grids:
        tree_object_of_gauge = DataModel.GetObjectById(each_ID_of_underdefined_SG_grids)
        tree_object_of_gauge.StiffnessOption = ShellElementStiffnessOption.StressEvaluationOnly
        tree_object_of_gauge.Material = "Structural Steel"
        tree_object_of_gauge.Color = 55295
        tree_object_of_gauge.Name = "SG_Grid_Body_" + str(i + 1) + "_" + str(j)
        
        # Add local grid coordinates and orient them
        CS_SG_grid = Model.CoordinateSystems.AddCoordinateSystem()
        CS_SG_grid.Name = "CS_SG_Ch_" + str(i + 1) + "_" + str(j)
        body_selection_single_channel_of_an_SG = create_geo_selection
        body_selection_single_channel_of_an_SG.Ids = [tree_object_of_gauge.GetGeoBody().Id]
        face_selection_single_channel_of_an_SG = create_geo_selection
        face_selection_single_channel_of_an_SG.Ids = [tree_object_of_gauge.GetGeoBody().Faces[0].Id]
        CS_SG_grid.OriginLocation = body_selection_single_channel_of_an_SG
        CS_SG_grid.PrimaryAxis = CoordinateSystemAxisType.PositiveZAxis
        CS_SG_grid.PrimaryAxisDefineBy = CoordinateSystemAlignmentType.Associative
        CS_SG_grid.PrimaryAxisLocation = face_selection_single_channel_of_an_SG
        
        # Find the long edge of the grid 
        grid_edge_lengths=[tree_object_of_gauge.GetGeoBody().Edges[m].Length 
                           for m in range(len(tree_object_of_gauge.GetGeoBody().Edges))]
        # Index and ID of the longest edge of the grid
        m_of_longest_edge = grid_edge_lengths.index(max(grid_edge_lengths))
        ID_of_longest_edge = tree_object_of_gauge.GetGeoBody().Edges[m_of_longest_edge].Id
        
        # Use the long edge of the grid to orient the local grid CS
        long_edge_selection_single_channel_of_an_SG = create_geo_selection
        long_edge_selection_single_channel_of_an_SG.Ids = [ID_of_longest_edge]
        CS_SG_grid.SecondaryAxis = CoordinateSystemAxisType.PositiveXAxis
        CS_SG_grid.SecondaryAxisDefineBy = CoordinateSystemAlignmentType.Associative
        CS_SG_grid.SecondaryAxisLocation = long_edge_selection_single_channel_of_an_SG
        
        # Ensure that the directions of secondary axes are correct and are initially towards the preferred axis
        string_of_CS_SG_grid_direction_vector_X = CS_SG_grid.XAxisData
        string_of_CS_SG_grid_direction_vector_X = string_of_CS_SG_grid_direction_vector_X.strip('[]').split()
        list_of_CS_SG_grid_direction_vector_X = [float(num) for num in string_of_CS_SG_grid_direction_vector_X]
        # Flip the local grid X if it is in the negative global X direction 
        if list_of_CS_SG_grid_direction_vector_X[0] < 0:
            CS_SG_grid.FlipX()
            CS_SG_grid.FlipZ() # Correct Z direction due to X flip
        
        # Add element orientations to each grid
        ExtAPI.SelectionManager.ClearSelection()
        tree_object_of_gauge = DataModel.GetObjectById(each_ID_of_underdefined_SG_grids)
        body_selection_single_channel_of_an_SG.Ids = [tree_object_of_gauge.GetGeoBody().Id]
        
        grid_element_orientation = Model.Geometry.AddElementOrientation()
        grid_element_orientation.Name = "Orient_CS_SG_Ch" + str(i + 1) + "_" + str(j)
        grid_element_orientation.OrientationGuideDefinedBy = ElementOrientationGuide.CoordinateSystemGuide
        grid_element_orientation.CoordinateSystem = CS_SG_grid
        grid_element_orientation.BodyLocation = body_selection_single_channel_of_an_SG
        
        normal_strain_x_SG_grid = obj_of_solution.AddNormalElasticStrain()
        normal_strain_x_SG_grid.Location = body_selection_single_channel_of_an_SG
        normal_strain_x_SG_grid.CoordinateSystem = None  # Results will be in Solution CS
        normal_strain_x_SG_grid.Name = "StrainX_SG_" + str(i + 1) + "_" + str(j)
        
        j += 1
    
    # Get the body selection of all grids of a body
    body_selection_of_all_channels_of_an_SG = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
    body_selection_of_all_channels_of_an_SG.Ids = [
        DataModel.GetObjectById(each_ID_of_underdefined_SG_grids).GetGeoBody().Id
        for each_ID_of_underdefined_SG_grids in list_of_IDs_of_underdefined_SG_grids
    ]
    
    # Configuring part transformation.
    part_transform = Model.AddPartTransform()
    part_transform.Name = "SG_" + str(i + 1) + "_Geometry_Placement"
    part_transform.Location = body_selection_of_all_channels_of_an_SG
    part_transform.DefineBy = PartTransformationDefinitionType.CoordinateSystem
    part_transform.TargetCoordinateSystem = list_of_obj_of_CS_SG_ref_points[i]

    # Create surface bonds/connection groups for SG bodies
    connection_group_of_an_SG = Model.Connections.AddConnectionGroup()
    connection_group_of_an_SG.Name = "Contacts_SG_" + str(i+1)
    connection_group_of_an_SG.FaceFace = True
    connection_group_of_an_SG.GroupBy = ContactGroupingType.Parts
    connection_group_of_an_SG.SearchAcross = ContactSearchingType.AcrossParts
    
    try:
        selection_info_of_connection_group_of_an_SG= \
        ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
        
        # Create the list of selection info IDs of each connection group
        list_of_IDs_of_selection_info_of_connection_group_of_an_SG = \
        [list_of_IDs_of_selections_of_NS_of_bodies_of_SG_test_parts] + \
        [body_selection_of_all_channels_of_an_SG]
        # Flatten the nested list
        list_of_IDs_of_selection_info_of_connection_group_of_an_SG = \
        list(chain.from_iterable(list_of_IDs_of_selection_info_of_connection_group_of_an_SG))
        
        # Assign the selection info IDs to the selection info of connection group
        selection_info_of_connection_group_of_an_SG.Ids = \
        list_of_IDs_of_selection_info_of_connection_group_of_an_SG
        
        # Define bodies of the connection group
        connection_group_of_an_SG.Location = \
        selection_info_of_connection_group_of_an_SG
        connection_group_of_an_SG.Activate()
        connection_group_of_an_SG.CreateAutomaticConnections()
        
    except:
        print("Children of Contacts_SG_" + str(i+1) + " could not be generated")
        
        # Define bodies of the connection group
        connection_group_of_an_SG.Location = body_selection_of_all_channels_of_an_SG

# Transforming mesh.
part_transform_group = Model.PartTransformGroup
part_transform_group.RegenerateContacts = False
part_transform_group.TransformMesh = True
part_transform_group.Activate()
context_menu.DoTransformGeometry(ExtAPI)



def group_SG_objects_created():
    
    # Create the lists of objects of different types to group
    list_of_obj_of_CS_SG_Ch_of_grids = [
        Model.CoordinateSystems.Children[i]
        for i in range(len(Model.CoordinateSystems.Children))
        if Model.CoordinateSystems.Children[i].Name.Contains("CS_SG_Ch")]
    
    list_of_obj_all_element_orientations = DataModel.Project.GetChildren(DataModelObjectCategory.ElementOrientation,True)
    list_of_obj_of_grid_element_orientations = [
        list_of_obj_all_element_orientations[i]
        for i in range(len(list_of_obj_all_element_orientations))
        if list_of_obj_all_element_orientations[i].Name.Contains("Orient_CS_SG_Ch")]
    
    list_of_obj_of_all_bodies = DataModel.Project.GetChildren(DataModelObjectCategory.Body,True)
    list_of_obj_of_SG_grid_bodies = [
        list_of_obj_of_all_bodies[i]
        for i in range(len(list_of_obj_of_all_bodies))
        if list_of_obj_of_all_bodies[i].Name.Contains("SG_Grid_Body_")
        and list_of_obj_of_all_bodies[i].Thickness == Quantity('0 [m]')
        and list_of_obj_of_all_bodies[i].ObjectState == ObjectState.FullyDefined]
    
    list_of_obj_of_all_part_transforms = DataModel.Project.GetChildren(DataModelObjectCategory.PartTransform,True)
    list_of_obj_of_SG_part_transforms_initial_placements = [
        list_of_obj_of_all_part_transforms[i]
        for i in range(len(list_of_obj_of_all_part_transforms))
        if list_of_obj_of_all_part_transforms[i].Name.Contains("SG_")
        and list_of_obj_of_all_part_transforms[i].Name.Contains("Geometry_Placement")]
        
    list_of_obj_of_all_geometry_imports = DataModel.Project.GetChildren(DataModelObjectCategory.GeometryImport,True)
    list_of_obj_of_SG_geometry_imports = [
        list_of_obj_of_all_geometry_imports[i]
        for i in range(len(list_of_obj_of_all_geometry_imports))
        if list_of_obj_of_all_geometry_imports[i].Name.Contains("SG_")
        and list_of_obj_of_all_geometry_imports[i].Name.Contains("_Geometry_Import")]
    
    list_of_obj_of_all_elastic_strains = DataModel.Project.GetChildren(DataModelObjectCategory.NormalElasticStrain,True)
    list_of_obj_of_SG_grid_strains = [
        list_of_obj_of_all_elastic_strains[i]
        for i in range(len(list_of_obj_of_all_elastic_strains))
        if list_of_obj_of_all_elastic_strains[i].Name.Contains("StrainX_SG_")]
    
    list_of_obj_of_connection_groups_of_SG_bodies = [
    Model.Connections.Children[i]
    for i in range(len(Model.Connections.Children))
    if Model.Connections.Children[i].Name.Contains("Contacts_SG_")]
    
    # Group the coordinate systems of each grid channel
    ExtAPI.DataModel.Tree.Activate(list_of_obj_of_CS_SG_Ch_of_grids)
    context_menu.DoCreateGroupingFolderInTree(ExtAPI)
    DataModel.GetObjectsByName("New Folder")[0].Name = "CS_SG_Ch"
    
    # Group the element orientations created
    ExtAPI.DataModel.Tree.Activate(list_of_obj_of_grid_element_orientations)
    context_menu.DoCreateGroupingFolderInTree(ExtAPI)
    DataModel.GetObjectsByName("New Folder")[0].Name = "Orient_CS_SG_Ch"
    
    # Group the SG grid bodies created
    ExtAPI.DataModel.Tree.Activate(list_of_obj_of_SG_grid_bodies)
    context_menu.DoCreateGroupingFolderInTree(ExtAPI)
    DataModel.GetObjectsByName("New Folder")[0].Name = "SG_Grid_Body"
    
    # Group the SG geometry imports from library
    ExtAPI.DataModel.Tree.Activate(list_of_obj_of_SG_geometry_imports)
    context_menu.DoCreateGroupingFolderInTree(ExtAPI)
    DataModel.GetObjectsByName("New Folder")[0].Name = "SG_Geometry_Imports"
    
    # Group the strain result objects of SG grids
    ExtAPI.DataModel.Tree.Activate(list_of_obj_of_SG_grid_strains)
    context_menu.DoCreateGroupingFolderInTree(ExtAPI)
    DataModel.GetObjectsByName("New Folder")[0].Name = "StrainX_SG"
    
    # Group the connection group objects of SG grids/bodies
    ExtAPI.DataModel.Tree.Activate(list_of_obj_of_connection_groups_of_SG_bodies)
    context_menu.DoCreateGroupingFolderInTree(ExtAPI)
    DataModel.GetObjectsByName("New Folder")[0].Name = "Contacts_SG"
    
    return list_of_obj_of_connection_groups_of_SG_bodies

#Execute grouping function with some output
list_of_obj_of_connection_groups_of_SG_bodies = \
group_SG_objects_created()


# Create contact regions of SG grids/bodies
ExtAPI.DataModel.Tree.Activate(list_of_obj_of_connection_groups_of_SG_bodies)
Model.Connections.CreateAutomaticConnections()

def change_contact_region_properties_SG_bodies():
    
    # Change contact properties of contact regions of SG grids/bodies
    for f in range(len(list_of_obj_of_connection_groups_of_SG_bodies)):
        for g in range(len(list_of_obj_of_connection_groups_of_SG_bodies[f].Children)):
            
            each_SG_contact_region = list_of_obj_of_connection_groups_of_SG_bodies[f].Children[g]
            
            # Flip Contact/Target of SG Contact Regions
            each_SG_contact_region.FlipContactTarget()
            # Change contact formulations of SG Contact Regions
            each_SG_contact_region.ContactFormulation = ContactFormulation.AugmentedLagrange
            each_SG_contact_region.DetectionMethod=ContactDetectionPoint.Combined
            each_SG_contact_region.ContactShellFace = ShellFaceType.Bottom

change_contact_region_properties_SG_bodies()




# Record the end time
end_time = time.time()

# Calculate the execution time
execution_time = end_time - start_time

# Print the execution time in seconds
print("Execution time: {:.2f} seconds".format(execution_time))