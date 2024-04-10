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
    MessageBox.Show("Selected project folder/path: " + project_path, "Info", MessageBoxButtons.OK, MessageBoxIcon.Information)
else:
    MessageBox.Show("No folder selected", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error)
