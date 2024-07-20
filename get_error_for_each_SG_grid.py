# Import libraries
import clr
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import MessageBox, MessageBoxButtons, MessageBoxIcon
import context_menu

try:
    NS_of_faces_of_SG_test_parts = DataModel.GetObjectsByName("NS_of_faces_of_SG_test_parts")[0]
    NS_of_faces_of_SG_test_parts_not_found = False
except:
    NS_of_faces_of_SG_test_parts_not_found = True

# region Error handling to ensure test piece is correctly defined
if (NS_of_faces_of_SG_test_parts_not_found):
    
    # Define the message, caption, and buttons for the message box
    message = r"""Please define a named selection of bodies called "NS_of_faces_of_SG_test_parts" using "Test Part" button. """
    caption = "Warning"
    buttons = MessageBoxButtons.OK
    icon = MessageBoxIcon.Warning
    # Show the message box
    result = MessageBox.Show(message, caption, buttons, icon)

    NS_of_faces_of_SG_test_parts = Model.AddNamedSelection()
    NS_of_faces_of_SG_test_parts.Name = "NS_of_faces_of_SG_test_parts"
    NS_of_faces_of_SG_test_parts.SendToSolver = False
    
if (NS_of_faces_of_SG_test_parts_not_found == False and
    len(NS_of_faces_of_SG_test_parts.Location.Ids) == 0):
      
    # Define the message, caption, and buttons for the message box
    message = r""""NS_of_faces_of_SG_test_parts" object is already in the tree but the bodies of test parts are not defined. 
    
Ensure that it is assigned and this button is re-run. """

    caption = "Warning"
    buttons = MessageBoxButtons.OK
    icon = MessageBoxIcon.Warning
    # Show the message box
    result = MessageBox.Show(message, caption, buttons, icon)

if (NS_of_faces_of_SG_test_parts_not_found == False and
    len(NS_of_faces_of_SG_test_parts.Location.Ids) != 0):
      
    # # Define the message, caption, and buttons for the message box
    # message = r"NS_of_faces_of_SG_test_parts" object is already defined. Ensure that it is assigned to correct parts."

    # caption = "Warning"
    # buttons = MessageBoxButtons.OK
    # icon = MessageBoxIcon.Warning
    # # Show the message box
    # result = MessageBox.Show(message, caption, buttons, icon)
    
    list_of_IDs_of_selections_of_NS_of_faces_of_SG_test_parts = NS_of_faces_of_SG_test_parts.Location.Ids
# endregion

# region Get the id and name of each coordinate system of each SG channel
list_of_ids_of_each_CS_SG_Ch_ = [
    Model.CoordinateSystems.Children[i].ObjectId
    for i in range(len(Model.CoordinateSystems.Children))
    if Model.CoordinateSystems.Children[i].Name.Contains("CS_SG_Ch_")]
    
list_of_names_of_each_CS_SG_Ch_ = [
    Model.CoordinateSystems.Children[i].Name
    for i in range(len(Model.CoordinateSystems.Children))
    if Model.CoordinateSystems.Children[i].Name.Contains("CS_SG_Ch_")]
# endregion

# region Create a named selection of nodes around each SG channel
try:
    NS_of_nodes_of_SG_test_parts = DataModel.GetObjectsByName("NS_of_nodes_of_SG_test_parts")[0]
except:
    if not NS_of_nodes_of_SG_test_parts:
        NS_of_nodes_of_SG_test_parts = NS_of_faces_of_SG_test_parts.CreateNodalNamedSelection()
        NS_of_nodes_of_SG_test_parts.Name =  "NS_of_nodes_of_SG_test_parts"

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
# endregion

# region Create contour plot of strains for nodes around each CS_SG_Ch_
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
        # Show the message box
        result = MessageBox.Show(message, caption, buttons, icon)

# Get the list of all "NS_of_nodes_around_" objects in the tree
list_of_obj_of_NS = \
DataModel.Project.GetChildren(DataModelObjectCategory.NamedSelection,True)

list_of_obj_of_NS_of_nodes_around_each_SG = [
    list_of_obj_of_NS[i]
    for i in range(len(list_of_obj_of_NS))
    if list_of_obj_of_NS[i].Name.Contains("NS_of_nodes_around_")]

# Get the list of all "StrainX_around_" objects in the tree
list_of_obj_of_normal_strains = \
DataModel.Project.GetChildren(DataModelObjectCategory.NormalElasticStrain,True)

list_of_obj_of_StrainX_around = [
    list_of_obj_of_normal_strains[i]
    for i in range(len(list_of_obj_of_normal_strains))
    if list_of_obj_of_normal_strains[i].Name.Contains("StrainX_around_")]

# Group existing "NS_of_nodes_around_" objects
ExtAPI.DataModel.Tree.Activate(list_of_obj_of_NS_of_nodes_around_each_SG)
context_menu.DoCreateGroupingFolderInTree(ExtAPI)
DataModel.GetObjectsByName("New Folder")[0].Name = "NS_of_nodes_around_each_SG"

# Group existing "StrainX_around_" objects
ExtAPI.DataModel.Tree.Activate(list_of_obj_of_StrainX_around)
context_menu.DoCreateGroupingFolderInTree(ExtAPI)
DataModel.GetObjectsByName("New Folder")[0].Name = "StrainX_around_each_SG"
