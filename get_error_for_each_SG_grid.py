# Import libraries
import clr
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import MessageBox, MessageBoxButtons, MessageBoxIcon

# 
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
    
Ensure that it is assigned and this button is re-run to correct parts to create contacts between strain gauges and test parts automatically. """

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
    obj_of_contour_of_nodes_around_each_SG_Ch = sol_selected_environment.AddNormalElasticStrain()
    obj_of_contour_of_nodes_around_each_SG_Ch.ScopingMethod = GeometryDefineByType.Component
    obj_of_contour_of_nodes_around_each_SG_Ch.Location = list_of_NS_of_test_part_strains[i]
    obj_of_contour_of_nodes_around_each_SG_Ch.Name = "StrainX_around_" + list_of_names_of_each_CS_SG_Ch_[i][3:]
    obj_of_contour_of_nodes_around_each_SG_Ch.CoordinateSystem = DataModel.GetObjectById(list_of_ids_of_each_CS_SG_Ch_[i])


#region Details View Action
sizing_33 = DataModel.GetObjectById(33)
sizing_33.ElementSize = Quantity(4, "mm")
#endregion

#region Context Menu Action
mesh_15 = Model.Mesh
mesh_15.GenerateMesh()
#endregion

#region Unpublished API
import context_menu
context_menu.DoModelPreviewMesh(ExtAPI)
#endregion

#region Unpublished API
import context_menu
context_menu.DoSolveDefaultHandler(ExtAPI)
#endregion

#region Unpublished API
import context_menu
context_menu.RefreshWorksheetPage(ExtAPI)
#endregion

#region Unpublished API
import context_menu
context_menu.DoExportToTextFile(ExtAPI)
#endregion

#region Unpublished API
import toolbar
toolbar.DoProbeAction(ExtAPI)
#endregion

#region Unpublished API
import context_menu
context_menu.DoExportToTextFile(ExtAPI)
#endregion

#region Details View Action
part_transform_200 = DataModel.GetObjectById(200)
part_transform_200.TranslationZ = Quantity(50, "mm")
#endregion

#region Unpublished API
import context_menu
context_menu.DoTransformGeometry(ExtAPI)
#endregion

#region Details View Action
part_transform_200.TranslationZ = Quantity(-0.05, "mm")
#endregion

#region Unpublished API
import context_menu
context_menu.DoTransformGeometry(ExtAPI)
#endregion

#region Unpublished API
import context_menu
context_menu.DoSolveDefaultHandler(ExtAPI)
#endregion

#region Unpublished API
import toolbar
toolbar.DoProbeAction(ExtAPI)
#endregion

#region Details View Action
part_transform_200.TranslationZ = Quantity(0.05, "mm")
#endregion

#region Unpublished API
import context_menu
context_menu.DoTransformGeometry(ExtAPI)
#endregion

#region Unpublished API
import context_menu
context_menu.DoSolveDefaultHandler(ExtAPI)
#endregion

#region Unpublished API
import toolbar
toolbar.DoProbeAction(ExtAPI)
#endregion

#region Details View Action
part_transform_200.TranslationZ = Quantity(-0.05, "mm")
#endregion

#region Unpublished API
import context_menu
context_menu.DoSolveDefaultHandler(ExtAPI)
#endregion

#region Details View Action
part_transform_200.TranslationZ = Quantity(-0.1, "mm")
#endregion

#region Unpublished API
import context_menu
context_menu.DoTransformGeometry(ExtAPI)
#endregion

#region Unpublished API
import context_menu
context_menu.DoSolveDefaultHandler(ExtAPI)
#endregion

#region Unpublished API
import toolbar
toolbar.DoProbeAction(ExtAPI)
#endregion

#region Details View Action
part_transform_200.TranslationZ = Quantity(0.05, "mm")
#endregion

#region Unpublished API
import context_menu
context_menu.DoTransformGeometry(ExtAPI)
#endregion

#region Unpublished API
import context_menu
context_menu.DoSolveDefaultHandler(ExtAPI)
#endregion

#region Unpublished API
import toolbar
toolbar.DoProbeAction(ExtAPI)
#endregion

#region Unpublished API
import context_menu
context_menu.AnnoGrid_ContextMenuHandler(ExtAPI,'ID_COPY_TEXT')
#endregion
