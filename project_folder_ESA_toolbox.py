import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')

from System.Windows.Forms import OpenFileDialog, FolderBrowserDialog, DialogResult, MessageBox, MessageBoxButtons, MessageBoxIcon
import System.IO

# Create an OpenFileDialog object
dialog = OpenFileDialog()

# Customize dialog
dialog.CheckFileExists = False  # Disable the requirement that the file must exist
dialog.CheckPathExists = True  # Ensure the path must exist
dialog.FileName = "Folder Selection."  # Set the file name to a dummy name
dialog.ValidateNames = False  # Disable validation of file names (since we're looking for folders)

# Show the dialog and get the result
if dialog.ShowDialog() == DialogResult.OK:
    # Get the directory of the selected "file" (which is actually a folder)
    project_path = System.IO.Path.GetDirectoryName(dialog.FileName)
    print("Selected project folder/path: ", project_path)
else:
    print("No folder selected")


code_string = """
def after_post(this, solution):

    pass

project_path = r"{project_path_value}"
""".format(project_path_value=project_path)


list_of_obj_of_plot_SG_channels_FEA = []
def check_for_duplicate_codes_in_tree():
    list_of_obj_of_all_python_codes = DataModel.Project.GetChildren(
                                      DataModelObjectCategory.PythonCodeEventBased,True)
    list_of_obj_of_plot_SG_channels_FEA = [
        list_of_obj_of_all_python_codes[i]
        for i in range(len(list_of_obj_of_all_python_codes))
        if list_of_obj_of_all_python_codes[i].Name.Contains("Project Folder")]

    if len(list_of_obj_of_plot_SG_channels_FEA)>=1:
        
        # Define the message, caption, and buttons for the message box
        message = r"""There is already at least one duplicate Python Code object in the tree. Please delete it first to be able to run this button again."""
        caption = "Warning"
        buttons = MessageBoxButtons.OK
        icon = MessageBoxIcon.Warning
        # Show the message box
        result = MessageBox.Show(message, caption, buttons, icon)
        
    if len(list_of_obj_of_plot_SG_channels_FEA)==0:
        plot_SG_FEA = sol_selected_environment.AddPythonCodeEventBased()
        plot_SG_FEA.Name = "Project Folder"
        plot_SG_FEA.TargetCallback=PythonCodeTargetCallback.OnAfterPost
        plot_SG_FEA.PropertyByName("EngineType").InternalValue = 1  # Set as CPython
        plot_SG_FEA.Text = code_string
        plot_SG_FEA.ScriptExecutionScope = '__python_code_666__'
        plot_SG_FEA.Connect()

check_for_duplicate_codes_in_tree()