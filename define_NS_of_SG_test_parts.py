import clr
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import MessageBox, MessageBoxButtons, MessageBoxIcon


list_of_names_of_NS_children = [Model.NamedSelections.Children[i].Name 
                                for i in range(len(Model.NamedSelections.Children))]

try:
    NS_of_faces_of_SG_test_parts = DataModel.GetObjectsByName("NS_of_faces_of_SG_test_parts")[0]
    NS_of_faces_of_SG_test_parts_not_found = False
except:
    NS_of_faces_of_SG_test_parts_not_found = True


if (NS_of_faces_of_SG_test_parts_not_found):
    
    # Define the message, caption, and buttons for the message box
    message = r"""Please define a named selection of bodies called "NS_of_faces_of_SG_test_parts" and re-run this button to create contacts between strain gauges and test parts automatically. """
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
      
    # Define the message, caption, and buttons for the message box
    message = r""""NS_of_faces_of_SG_test_parts" object is already defined. Ensure that it is assigned to correct parts to create contacts between strain gauges and test parts automatically. """

    caption = "Warning"
    buttons = MessageBoxButtons.OK
    icon = MessageBoxIcon.Warning
    # Show the message box
    result = MessageBox.Show(message, caption, buttons, icon)
    
    list_of_IDs_of_selections_of_NS_of_faces_of_SG_test_parts = NS_of_faces_of_SG_test_parts.Location.Ids
      
