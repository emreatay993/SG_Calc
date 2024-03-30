# region Import Libraries
import context_menu
import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')
from System.Windows.Forms import (Application, Form, Button, DataGridView,
                                  FolderBrowserDialog, DialogResult, OpenFileDialog,
                                  DataGridViewAutoSizeColumnMode, DataGridViewColumnHeadersHeightSizeMode,
                                  DataGridViewColumnSortMode, DataGridViewCellStyle, MessageBox,
                                  MessageBoxButtons, MessageBoxIcon, Keys, DataGridViewContentAlignment, Clipboard)
from System.Drawing import Size, Font, FontStyle, Color, ColorTranslator
from itertools import chain
import os
# endregion

#---------------------------------------------------------------------------------------------------------
list_of_selected_CAD_files_for_each_rosette_SG = []
# region Definition of SG CAD Geometries
class SGSelectionForm(Form):
    def __init__(self, num_rows):
        self.Text = "Rosette SG - Define Reference CAD Files"
        self.MinimumSize = Size(500, 700)
        self.AutoSize = True
        self.AutoSizeMode = System.Windows.Forms.AutoSizeMode.GrowAndShrink
        self.Font = Font("Calibri", 10)
        self.initialize_components(num_rows)

    def initialize_components(self, num_rows):
        self.proceed_button = Button()
        self.proceed_button.Text = "Click here to proceed with the selections below"
        self.proceed_button.Dock = System.Windows.Forms.DockStyle.Top
        self.proceed_button.Click += self.proceed_button_click

        self.folder_button = Button()
        self.folder_button.Text = "Click here to select the folder for .pmdb files..."
        self.folder_button.Dock = System.Windows.Forms.DockStyle.Top
        self.folder_button.Click += self.folder_button_click

        self.grid = DataGridView()
        self.grid.Dock = System.Windows.Forms.DockStyle.Fill
        self.grid.AllowUserToAddRows = False
        self.grid.RowHeadersVisible = False
        self.grid.ColumnCount = 2
        self.grid.Columns[0].Name = "Rosette Names"
        self.grid.Columns[0].ReadOnly = True
        self.grid.Columns[0].DefaultCellStyle.Font = Font(self.Font, FontStyle.Bold)
        #$self.grid.Columns[0].AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill
        self.grid.Columns[0].DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter
        self.grid.Columns[0].Width = 100
        self.grid.Columns[1].Name = "Rosette Model No"
        self.grid.Columns[1].AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill
        self.grid.Columns[1].DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter
        self.grid.ColumnHeadersDefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter
        self.grid.ColumnHeadersDefaultCellStyle.Font = Font(self.Font, FontStyle.Bold)
        self.grid.ColumnHeadersHeightSizeMode = DataGridViewColumnHeadersHeightSizeMode.DisableResizing
        self.grid.AllowUserToResizeRows = False
        self.grid.RowTemplate.Height = 25
        placeholder_font = Font("Calibri", 8, FontStyle.Italic)
        placeholder_text = "Copy the name of .pmdb file here, without its file extension"
        self.grid.Columns[1].DefaultCellStyle.Font = placeholder_font
        self.grid.Columns[1].DefaultCellStyle.ForeColor = Color.Gray

        for i in range(num_rows):
            self.grid.Rows.Add("SG_{}".format(i + 1), placeholder_text)

        self.grid.KeyDown += self.grid_key_down
        self.Controls.Add(self.grid)
        self.Controls.Add(self.folder_button)
        self.Controls.Add(self.proceed_button)

        self.project_path = None

    def folder_button_click(self, sender, event):
        folder_browser_dialog = FolderBrowserDialog()
        if folder_browser_dialog.ShowDialog() == DialogResult.OK:
            self.project_path = folder_browser_dialog.SelectedPath

    def proceed_button_click(self, sender, event):
        if not self.project_path:
            MessageBox.Show("Please select the project folder first.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error)
            return
        
        # Check if all Rosette Model No cells are populated
        all_models_defined = all(row.Cells["Rosette Model No"].Value and
                                 row.Cells["Rosette Model No"].Value != "Copy name of pmdb here, without file extension"
                                 for row in self.grid.Rows)
        if not all_models_defined:
            MessageBox.Show("Please define the models for all gauges and try again.", "Error",MessageBoxButtons.OK, MessageBoxIcon.Error)
            return
    
        # Retrieve the list of .pmdb files in the selected folder
        pmdb_files = [f for f in os.listdir(self.project_path) if f.endswith('.pmdb')]
    
        # Check if the user-defined model names correspond to .pmdb files in the folder
        missing_files = []
        for row in self.grid.Rows:
            model_name = row.Cells["Rosette Model No"].Value
            if model_name and "{}.pmdb".format(model_name) not in pmdb_files:
                missing_files.append((row.Cells["Rosette Names"].Value, model_name))
    
        if missing_files:
            error_message = "The following CAD names could not be found inside the folder for the following strain gauge names:\n"
            error_message += "\n".join("{}: {}".format(name, model) for name, model in missing_files)
            MessageBox.Show(error_message, "Error")
            return
    
        # If all checks pass, compile the list of CAD file names
        self.list_of_selected_CAD_files_for_each_rosette_SG = [os.path.join(self.project_path, row.Cells["Rosette Model No"].Value + ".pmdb") for row in self.grid.Rows]
        # Also define the list as a global variable to be used later
        global list_of_selected_CAD_files_for_each_rosette_SG  # Reference the global variable
        list_of_selected_CAD_files_for_each_rosette_SG = self.list_of_selected_CAD_files_for_each_rosette_SG
        
        # Proceed with the selections
        MessageBox.Show("Project path: {}\nSelected CAD files: {}".format(self.project_path, self.list_of_selected_CAD_files_for_each_rosette_SG) + ".Click the Exit icon at the top right corner of this window and the main GUI window to continue.", "Selections Made.")

    def grid_key_down(self, sender, e):
        if e.Control and e.KeyCode == Keys.V:
            clipboard_data = Clipboard.GetText()
            rows = clipboard_data.split('\r\n')
            start_row_index = self.grid.CurrentCell.RowIndex
            current_column_index = self.grid.CurrentCell.ColumnIndex
            for i, row_data in enumerate(rows):
                if start_row_index + i < self.grid.RowCount and current_column_index == 1:
                    cell_value = row_data.strip()
                    if cell_value:
                        self.grid.Rows[start_row_index + i].Cells[current_column_index].Value = cell_value
                        self.grid.Rows[start_row_index + i].Cells[current_column_index].Style = \
                            DataGridViewCellStyle(Font=self.Font, ForeColor=Color.Black)
# endregion

#---------------------------------------------------------------------------------------------------------

# region Check whether solution environment is selected
try:
    sol_selected_environment = DataModel.GetObjectsByName("Solution")[0]
    obj_of_solution = sol_selected_environment
except:
    # Define the message, caption, and buttons for the message box
    message = r"""An analysis environment for solution is not selected,changed/deleted or the mechanical session is restarted. Please select the "Solution Object" again."""
    caption = "Error"
    buttons = MessageBoxButtons.OK
    icon = MessageBoxIcon.Error
    # Show the message box
    result = MessageBox.Show(message, caption, buttons, icon)
# endregion

# region Extracting reference points and their IDs for strain gauges.
list_of_obj_of_CS_SG_ref_points = \
    [Model.CoordinateSystems.Children[i]
    for i in range(len(Model.CoordinateSystems.Children))
    if Model.CoordinateSystems.Children[i].Name.Contains("CS_SG_Ref")]

list_of_IDs_of_CS_SG_ref_points = \
    [Model.CoordinateSystems.Children[i].ObjectId
    for i in range(len(Model.CoordinateSystems.Children))
    if Model.CoordinateSystems.Children[i].Name.Contains("CS_SG_Ref")]
# endregion

# region Assign the each rosette SG with their corresponding CAD geometry
class_instance_of_SG_selector = SGSelectionForm(len(list_of_IDs_of_CS_SG_ref_points))
Application.Run(class_instance_of_SG_selector)
# endregion

# region Importing geometry for each strain gauge.
for i in range(len(list_of_IDs_of_CS_SG_ref_points)):
    geometry_import_group = Model.GeometryImportGroup
    geometry_import = geometry_import_group.AddGeometryImport()
    geometry_import.Name = "SG_" + str(i + 1) +"_Geometry_Import"
    geometry_import_format = Ansys.Mechanical.DataModel.Enums.GeometryImportPreference.Format.Automatic
    geometry_import_preferences = Ansys.ACT.Mechanical.Utilities.GeometryImportPreferences()
    geometry_import.Import(list_of_selected_CAD_files_for_each_rosette_SG[i], geometry_import_format, geometry_import_preferences)
# endregion

# region Find all underdefined SG grid shell bodies for preprocessing
list_of_obj_of_bodies = DataModel.GetObjectsByType(Ansys.ACT.Automation.Mechanical.Body)
list_of_IDs_of_underdefined_SG_grids = [
    list_of_obj_of_bodies[k].ObjectId
    for k in range(len(list_of_obj_of_bodies))
    if (list_of_obj_of_bodies[k].Thickness == Quantity('0 [m]') and 
        list_of_obj_of_bodies[k].Material == '' and 
        list_of_obj_of_bodies[k].Name.Contains("SG_"))
]
# endregion

# region Iterate over the properties of each individual SG grid shell bodies                
i=0
j=1
face_selection_of_all_channels_of_all_SGs = []
for each_ID_of_underdefined_SG_grids in list_of_IDs_of_underdefined_SG_grids:

    # region Create body and face selections for each SG grid shell body
    ExtAPI.SelectionManager.ClearSelection()
    tree_object_of_gauge = DataModel.GetObjectById(each_ID_of_underdefined_SG_grids)
    body_selection_single_channel_of_an_SG = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
    body_selection_single_channel_of_an_SG.Ids = [tree_object_of_gauge.GetGeoBody().Id]
    face_selection_single_channel_of_an_SG = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
    face_selection_single_channel_of_an_SG.Ids = [tree_object_of_gauge.GetGeoBody().Faces[0].Id]
    face_selection_of_all_channels_of_all_SGs.append(face_selection_single_channel_of_an_SG)
    # endregion

    # region Make SG grid shell bodies fully defined and rename them
    tree_object_of_gauge = DataModel.GetObjectById(each_ID_of_underdefined_SG_grids)
    tree_object_of_gauge.StiffnessOption = ShellElementStiffnessOption.StressEvaluationOnly
    tree_object_of_gauge.Material = "Structural Steel"
    tree_object_of_gauge.PropertyByName("Color").InternalValue = 55295
    tree_object_of_gauge.Name = "SG_Grid_Body_" + str(i + 1) + "_" + str(j)
    # endregion

    # region Add local grid coordinates and orient them
    CS_SG_grid = Model.CoordinateSystems.AddCoordinateSystem()
    CS_SG_grid.Name = "CS_SG_Ch_" + str(i + 1) + "_" + str(j)
    CS_SG_grid.OriginLocation = body_selection_single_channel_of_an_SG
    CS_SG_grid.PrimaryAxis = CoordinateSystemAxisType.PositiveZAxis
    CS_SG_grid.PrimaryAxisDefineBy = CoordinateSystemAlignmentType.Associative
    CS_SG_grid.PrimaryAxisLocation = face_selection_single_channel_of_an_SG
    # endregion

    # region Add element orientations to each grid
    grid_element_orientation = Model.Geometry.AddElementOrientation()
    grid_element_orientation.Name = "Orient_CS_SG_Ch" + str(i + 1) + "_" + str(j)
    grid_element_orientation.OrientationGuideDefinedBy = ElementOrientationGuide.CoordinateSystemGuide
    grid_element_orientation.CoordinateSystem = CS_SG_grid
    grid_element_orientation.BodyLocation = body_selection_single_channel_of_an_SG
    # endregion

    # region Find and use the long edge of the grid to orient the local grid CS
    grid_edge_lengths=[tree_object_of_gauge.GetGeoBody().Edges[m].Length 
                        for m in range(len(tree_object_of_gauge.GetGeoBody().Edges))]
    # Index and ID of the longest edge of the grid
    m_of_longest_edge = grid_edge_lengths.index(max(grid_edge_lengths))
    ID_of_longest_edge = tree_object_of_gauge.GetGeoBody().Edges[m_of_longest_edge].Id
    
    long_edge_selection_single_channel_of_an_SG = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
    long_edge_selection_single_channel_of_an_SG.Ids = [ID_of_longest_edge]
    CS_SG_grid.SecondaryAxis = CoordinateSystemAxisType.PositiveXAxis
    CS_SG_grid.SecondaryAxisDefineBy = CoordinateSystemAlignmentType.Associative
    CS_SG_grid.SecondaryAxisLocation = long_edge_selection_single_channel_of_an_SG
    # endregion

    # region Ensure that the directions of secondary axes are correct and are initially directed towards the preferred axis (X)
    string_of_CS_SG_grid_direction_vector_X = CS_SG_grid.XAxisData
    string_of_CS_SG_grid_direction_vector_X = string_of_CS_SG_grid_direction_vector_X.strip('[]').split()
    list_of_CS_SG_grid_direction_vector_X = [float(num) for num in string_of_CS_SG_grid_direction_vector_X]
    # Flip the local grid X if it is in the negative global X direction 
    if list_of_CS_SG_grid_direction_vector_X[0] < 0:
        CS_SG_grid.FlipX()
        CS_SG_grid.FlipZ() # Correct Z direction due to X flip
    # endregion

    # region Add strain results for each SG grid for postprocessing time vs strain data in each channel
    normal_strain_x_SG_grid = obj_of_solution.AddNormalElasticStrain()
    normal_strain_x_SG_grid.Location = body_selection_single_channel_of_an_SG
    normal_strain_x_SG_grid.CoordinateSystem = None  # Results will be in Solution CS
    normal_strain_x_SG_grid.Name = "StrainX_SG" + str(i + 1) + "_" + str(j)
    # endregion

    if j == 3:
        i = i + 1

    j = j + 1 if j < 3 else 1
# endregion

# region Get the body selection of all grids of all SG bodies
body_selection_of_all_channels_of_all_SGs = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
body_selection_of_all_channels_of_all_SGs.Ids = [DataModel.GetObjectById(each_ID_of_underdefined_SG_grids).GetGeoBody().Id 
                                                for each_ID_of_underdefined_SG_grids 
                                                in list_of_IDs_of_underdefined_SG_grids]
# endregion

# region Grouping SG grid IDs of each SG into sublists
original_list = body_selection_of_all_channels_of_all_SGs.Ids
grouped_list = []
group_size = 3

for i in range(0, len(original_list), group_size):
    group = []
    for j in range(group_size):
        if i + j < len(original_list):
            group.append(original_list[i + j])
    grouped_list.append(group)

grouped_list_of_SG_grids = grouped_list
# endregion

# region Iterate over the properties of each group of grids (namely, each SG)
i=0
for sublist in grouped_list_of_SG_grids:

    # region Create body selection of SG of interest
    body_selection_of_all_channels_of_an_SG = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
    body_selection_of_all_channels_of_an_SG.Ids = sublist
    # endregion

    # region Configuring part transformation.
    part_transform = Model.AddPartTransform()
    part_transform.Name = "SG_" + str(i + 1) + "_Geometry_Placement"
    part_transform.Location = body_selection_of_all_channels_of_an_SG
    part_transform.DefineBy = PartTransformationDefinitionType.CoordinateSystem
    part_transform.TargetCoordinateSystem = list_of_obj_of_CS_SG_ref_points[i]
    # endregion

    # region Add mesh sizing to the SG grid bodies
    obj_of_mesh_sizing_SG_grid_bodies = Model.Mesh.AddSizing()
    obj_of_mesh_sizing_SG_grid_bodies.Location = body_selection_of_all_channels_of_an_SG
    obj_of_mesh_sizing_SG_grid_bodies.ElementSize = Quantity(500, "mm")
    obj_of_mesh_sizing_SG_grid_bodies.Name = "Body_Sizing_SG_" + str(i+1)
    # endregion

    # region Create surface bonds/connection groups for SG bodies
    connection_group_of_an_SG = Model.Connections.AddConnectionGroup()
    connection_group_of_an_SG.Name = "Contacts_SG_" + str(i+1)
    connection_group_of_an_SG.FaceFace = True
    connection_group_of_an_SG.GroupBy = ContactGroupingType.Parts
    connection_group_of_an_SG.SearchAcross = ContactSearchingType.AcrossParts
    # endregion

    # region Create contacts/contact regions and define their properties
    try:
        selection_info_of_connection_group_of_an_SG= \
        ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
        
        # Create the list of selection info IDs of each connection group
        list_of_IDs_of_selection_info_of_connection_group_of_an_SG = [body_selection_of_all_channels_of_an_SG]
        
        # Assign the selection info IDs to the selection info of connection group
        selection_info_of_connection_group_of_an_SG.Ids = \
        list_of_IDs_of_selection_info_of_connection_group_of_an_SG[0].Ids
        
        # Define bodies of the connection group
        connection_group_of_an_SG.Location = \
        selection_info_of_connection_group_of_an_SG
        
    except:
        print("Check Contacts_SG_" + str(i+1) + " definitions")
        
        # Define bodies of the connection group
        connection_group_of_an_SG.Location = body_selection_of_all_channels_of_an_SG
    # endregion

    i += 1
# endregion

# region Transform mesh/geometry of SGs in order to position them.
part_transform_group = Model.PartTransformGroup
part_transform_group.RegenerateContacts = False
part_transform_group.TransformMesh = True
part_transform_group.Activate()
context_menu.DoTransformGeometry(ExtAPI)
# endregion

# region Group all the SG objects created in the Mechanical tree
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
    if list_of_obj_of_all_elastic_strains[i].Name.Contains("StrainX_SG")]

list_of_obj_of_connection_groups_of_SG_bodies = [
    Model.Connections.Children[i]
    for i in range(len(Model.Connections.Children))
    if Model.Connections.Children[i].Name.Contains("Contacts_SG_")]

list_of_obj_of_all_mesh_controls = DataModel.Project.GetChildren(DataModelObjectCategory.MeshControl,True)
list_of_obj_of_SG_mesh_controls = [
    list_of_obj_of_all_mesh_controls[i]
    for i in range(len(list_of_obj_of_all_mesh_controls))
    if list_of_obj_of_all_mesh_controls[i].Name.Contains("Body_Sizing_SG_")]

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

ExtAPI.DataModel.Tree.Activate(list_of_obj_of_SG_mesh_controls)
context_menu.DoCreateGroupingFolderInTree(ExtAPI)
DataModel.GetObjectsByName("New Folder")[0].Name = "Mesh_Controls_SG"
# endregion

# region Modify the contact regions of SG grids/bodies and their properties
# Add three contact regions under each SG contact group
h=0
for f in range(len(list_of_obj_of_connection_groups_of_SG_bodies)):
    [list_of_obj_of_connection_groups_of_SG_bodies[f].AddContactRegion() for _ in range(3)] 
# Change the properties of each contact region under each SG contact group
for f in range(len(list_of_obj_of_connection_groups_of_SG_bodies)):
    for g in range(len(list_of_obj_of_connection_groups_of_SG_bodies[f].Children)):
        #Select contact regions one by one:    
        each_SG_contact_region = list_of_obj_of_connection_groups_of_SG_bodies[f].Children[g]
        # Change contact formulations of contact regions:
        each_SG_contact_region.ContactFormulation = ContactFormulation.AugmentedLagrange
        each_SG_contact_region.DetectionMethod=ContactDetectionPoint.Combined
        each_SG_contact_region.Behavior=ContactBehavior.Symmetric
        each_SG_contact_region.ContactShellFace = ShellFaceType.Bottom
        # Define the scopings (contacts/targets) of each contact region
        each_SG_contact_region.SourceLocation = face_selection_of_all_channels_of_all_SGs[h]
        h += 1
        each_SG_contact_region.TargetLocation = NS_of_faces_of_SG_test_parts.Location
        # Set the bounds of each contact region
        each_SG_contact_region.PinballRegion=ContactPinballType.Radius
        each_SG_contact_region.PinballRadius = Quantity(max(grid_edge_lengths)*1.5, 'm')
        each_SG_contact_region.TrimContact=ContactTrimType.On
        each_SG_contact_region.TrimTolerance = Quantity(max(grid_edge_lengths)*1.5, 'm')
        each_SG_contact_region.RenameBasedOnDefinition()
# endregion