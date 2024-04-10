# Strain Sensitivity Matrix

'''
Generates the strain sensitivity matrix [A]. 
To get the values of the matrix a unit load study should be specified, where each unit load case should be specified in a different analysis environment and also should contain "Unit_Load_Study_LC_" in their name in the Mechanical tree. 
The program gets each analysis environment from top to bottom, assuming that they go from the first unit load case (LC1) to the last unit load case (LC{end}). 
The columns of the matrix specifies are those load cases. 
Within each analysis environment, the results from each normal strain result objects with "StrainX_SG" in their names and that are NOT suppressed, are extracted. 
Each extracted value is the average value of that strain gauge result. 
The columns of sensitivity matrix correspond to the response of each strain gauge for each unit load case. 
Therefore the rows in each column correspond to sensitivity of each strain gage to that unit load case.
'''

# ----------------------------------------------------------------------------------------------------------

# region Import necessary libraries
import csv
import os
import context_menu
import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')
clr.AddReference("System")
from System import DateTime
from System.Drawing import *
from System.Windows.Forms import *
# endregion

# ----------------------------------------------------------------------------------------------------------

# region Import the necessary classes and function for the GUI
class FlatTextBox(TextBox):
    # Custom Textbox with no border for a flat design
    def __init__(self):
        self.BackColor = Color.White
        self.Font = Font("Segoe UI", 9)
        self.SetStyle(ControlStyles.UserPaint, True)

    def OnPaint(self, e):
        # Paint background color
        e.Graphics.FillRectangle(SolidBrush(self.BackColor), 0, 0, self.Width, self.Height)
        # Paint text
        e.Graphics.DrawString(self.Text, self.Font, SolidBrush(self.ForeColor), 2, 2)
        # Draw border
        if self.Focused:
            e.Graphics.DrawRectangle(Pen(Color.FromArgb(204, 228, 247)), 0, 0, self.Width - 1, self.Height - 1)

class Form(Form):
    def __init__(self):
        self.InitializeComponent()
    
    def InitializeComponent(self):
        self.Text = 'Load Step Input'
        self.Size = Size(325, 285)
        self.FormBorderStyle = FormBorderStyle.FixedDialog
        self.BackColor = Color.White
        self.MaximizeBox = False
        self.MinimizeBox = False
        self.StartPosition = FormStartPosition.CenterScreen
    
        # Fonts
        label_font = Font("Segoe UI", 9, FontStyle.Regular)
        
        maxWidth = 250
        
        # FlowLayoutPanel setup
        self.flowPanel = FlowLayoutPanel()
        self.flowPanel.FlowDirection = FlowDirection.TopDown
        self.flowPanel.Location = Point(20, 20)
        self.flowPanel.Size = Size(450, 260)
        self.flowPanel.AutoScroll = True
    
        # Label for unit load step
        self.label1 = Label()
        self.label1.Text = 'Select the unit load step:'
        self.label1.Size = Size(250, 20)
        self.label1.Font = label_font
        self.label1.Margin = Padding(5, 5, 5, 5)
        self.flowPanel.Controls.Add(self.label1)
    
        # Combobox for unit load step endtime
        self.comboBox1 = ComboBox()
        self.comboBox1.Size = Size(250, 20)
        self.comboBox1.Font = label_font
        self.comboBox1.SelectedIndexChanged += self.comboBox1_SelectedIndexChanged
        self.comboBox1.Margin = Padding(5, 5, 5, 5)
        self.flowPanel.Controls.Add(self.comboBox1)
        
        # Label for unit load step endtime
        self.label2 = Label()
        self.label2.Text = 'Step End Time [Seconds]:'
        self.label2.Size = Size(250, 20)
        self.label2.Font = label_font
        self.label2.Margin = Padding(5, 5, 5, 5)
        self.flowPanel.Controls.Add(self.label2)
        
    
        # Read-only FlatTextBox for displaying selected value or additional info
        self.readOnlyTextBox1 = FlatTextBox()
        self.readOnlyTextBox1.Size = Size(250, 20)
        self.readOnlyTextBox1.ReadOnly = True
        self.readOnlyTextBox1.BackColor = Color.LightGray
        self.readOnlyTextBox1.Margin = Padding(5, 5, 5, 5)
        self.flowPanel.Controls.Add(self.readOnlyTextBox1)
    
        # OK button setup
        self.okButton = Button()
        self.okButton.Text = 'OK'
        self.okButton.Size = Size(250, 40)
        self.okButton.Font = Font("Segoe UI", 10, FontStyle.Bold)
        self.okButton.FlatStyle = FlatStyle.Flat
        self.okButton.FlatAppearance.BorderSize = 0
        self.okButton.BackColor = Color.FromArgb(204, 228, 247)
        self.okButton.ForeColor = Color.White
        self.okButton.Click += self.OkButtonClick
        self.okButton.Margin = Padding(5, 5, 5, 5)
        self.flowPanel.Controls.Add(self.okButton)
    
        # Add controls to the form
        self.Controls.Add(self.flowPanel)
    
        # Get number_of_analysis_steps_of_unit_load_study
        global number_of_analysis_steps_of_unit_load_study
    
        # Populate combobox items
        for timestep in range(1, number_of_analysis_steps_of_unit_load_study + 1):
            self.comboBox1.Items.Add(str(timestep))
    
        # Optionally set the first item as selected in each combobox
        if number_of_analysis_steps_of_unit_load_study > 0:
            self.comboBox1.SelectedIndex = 0
            
    def comboBox1_SelectedIndexChanged(self, sender, args):
        selectedIndex = self.comboBox1.SelectedIndex  # Get the index of the selected item
        if selectedIndex >= 0 and selectedIndex < len(list_of_endtime_of_time_steps):
            # Ensure the selected index is valid and within the range of the list_of_endtime_of_time_steps
            selectedEndTime = list_of_endtime_of_time_steps[selectedIndex]  # Retrieve the corresponding end time
            self.readOnlyTextBox1.Text = str(selectedEndTime)  # Display the end time in the ReadOnlyTextBox
    
    def OkButtonClick(self, sender, args):
        try:
            # Attempt to parse the text as float
            # Assign the value to a 'result' attribute
            selectedIndex = self.comboBox1.SelectedIndex
            if selectedIndex >= 0 and selectedIndex < len(list_of_endtime_of_time_steps):
                # Retrieve the corresponding end time based on the selected index
                self.endtime_of_unit_load = float(list_of_endtime_of_time_steps[selectedIndex])
                # Assuming you have a way to determine the initial load end time, otherwise set a default or use user input
                self.endtime_of_initial_load = float(list_of_endtime_of_time_steps[selectedIndex-1])
                self.DialogResult = DialogResult.OK
                self.Close()
            else:
                # Handle the case where no valid selection is made
                MessageBox.Show("Please select a valid timestep.", "Selection Error", MessageBoxButtons.OK, MessageBoxIcon.Error)
        except ValueError:
            # Handle the case where the conversion to float fails
            MessageBox.Show("Invalid value for end time. Please ensure a valid timestep is selected.", "Value Error", MessageBoxButtons.OK, MessageBoxIcon.Error)
# endregion

# ----------------------------------------------------------------------------------------------------------

# region Filter all analysis environments that contains "Unit_Load_Study_LC_" in their names
list_of_obj_of_all_analysis_environments = DataModel.Project.GetChildren(DataModelObjectCategory.Analysis,True)
list_of_obj_of_analysis_environments_of_unit_load_studies = [
    list_of_obj_of_all_analysis_environments[i]
    for i in range(len(list_of_obj_of_all_analysis_environments))
    if list_of_obj_of_all_analysis_environments[i].Name.Contains("Unit_Load_Study_LC")]

# Throw an error if analysis environments named Unit_Load_Study_LC are not defined in the tree.
if len(list_of_obj_of_analysis_environments_of_unit_load_studies) == 0:
    message_no_analysis_found = "Analysis environments that starts with the name 'Unit_Load_Study_LC' are not defined in the tree. Please define these environments along with their SG result objects at each SG channel and try again."
    msg = Ansys.Mechanical.Application.Message(message_no_analysis_found, MessageSeverityType.Error)
    ExtAPI.Application.Messages.Add(msg)
# endregion

# ----------------------------------------------------------------------------------------------------------

# region Get the endtime of each load step in the analysis settings of unit load studies
DataModel.GetObjectById(list_of_obj_of_analysis_environments_of_unit_load_studies[0].ObjectId).AnalysisSettings.Activate()
Pane = ExtAPI.UserInterface.GetPane(MechanicalPanelEnum.TabularData)
Con = Pane.ControlUnknown

# Helper function to check if a string can be converted to float
def is_float(element):
    try:
        float(element)
        return True
    except ValueError:
        return False

list_of_endtime_of_time_steps = []
flat_list = []
for C in range(1, Con.ColumnsCount + 1):
    for R in range(1, Con.RowsCount + 1):
        Text = Con.cell(R, C).Text
        if Text is not None:
            flat_list.append(Text)

numeric_list = [float(item) for item in flat_list if is_float(item)]

num_elements_per_column = len(numeric_list) // 3
columns = [numeric_list[i * num_elements_per_column: (i + 1) * num_elements_per_column] for i in range(3)]

list_of_endtime_of_time_steps.append(columns[2])
list_of_endtime_of_time_steps = list_of_endtime_of_time_steps[0]
# endregion

# ----------------------------------------------------------------------------------------------------------

# region Run the GUI to get the requested timesteps as inputs.
# Get the first unit load study and its number of steps
number_of_analysis_steps_of_unit_load_study = list_of_obj_of_analysis_environments_of_unit_load_studies[0].AnalysisSettings.NumberOfSteps

form = Form()
Application.EnableVisualStyles()
Application.Run(form)

# After the form is closed, if OK was clicked, access the values
if form.DialogResult == DialogResult.OK:
    endtime_of_unit_load = form.endtime_of_unit_load
    endtime_of_initial_load = form.endtime_of_initial_load
# endregion

# ----------------------------------------------------------------------------------------------------------

# region Get results from environments
''' 
From environments with "Unit_Load_Study_LC_" in their names,
- Get the objects with SG_ in their names if:
    - Their result type is normal elastic strain contours and
    - They are NOT suppressed
    - They have "StrainX_SG" in their names
'''
list_of_list_of_obj_of_SG_results_of_unit_load_studies = [
    [list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children[k]
     for k in range(len(list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children))
     if list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children[k].Name.Contains("StrainX_SG")
     and list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children[k].DataModelObjectCategory == DataModelObjectCategory.NormalElasticStrain
     and list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children[k].Suppressed == False]
     for i in range(len(list_of_obj_of_analysis_environments_of_unit_load_studies))]
# Flatten the list
list_of_obj_of_SG_results_of_unit_load_studies = []
for sublist in list_of_list_of_obj_of_SG_results_of_unit_load_studies:
    for item in sublist:
        list_of_obj_of_SG_results_of_unit_load_studies.append(item)
# endregion 

# ----------------------------------------------------------------------------------------------------------

# region Set the endtime of SG results to be extracted
for i in range(len(list_of_obj_of_SG_results_of_unit_load_studies)):
    list_of_obj_of_SG_results_of_unit_load_studies[i].DisplayTime = Quantity(endtime_of_initial_load, "sec")
# endregion

# ----------------------------------------------------------------------------------------------------------

# region Evaluate all SG results
[list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.EvaluateAllResults() 
for i in range(len(list_of_obj_of_analysis_environments_of_unit_load_studies))]
# endregion

# ----------------------------------------------------------------------------------------------------------

# region Get the values of each SG due to their initial values (Bolt preload, shrink/rabbet fits etc.) 
list_of_SG_initial_strains_of_unit_load_studies = [
    [list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children[k].Average.Value
     for k in range(len(list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children))
     if list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children[k].Name.Contains("StrainX_SG")
     and list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children[k].DataModelObjectCategory == DataModelObjectCategory.NormalElasticStrain
     and list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children[k].Suppressed == False]
     for i in range(len(list_of_obj_of_analysis_environments_of_unit_load_studies))]
# endregion 

# ----------------------------------------------------------------------------------------------------------

# region Set the endtime of SG results to be extracted
for i in range(len(list_of_obj_of_SG_results_of_unit_load_studies)):
    list_of_obj_of_SG_results_of_unit_load_studies[i].DisplayTime = Quantity(endtime_of_unit_load, "sec")
# endregion

# ----------------------------------------------------------------------------------------------------------

# region Evaluate all SG results
[list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.EvaluateAllResults() 
for i in range(len(list_of_obj_of_analysis_environments_of_unit_load_studies))]
# endregion

# ----------------------------------------------------------------------------------------------------------

# region Get the values of each SG due to the application of unit loads only 
list_of_SG_results_of_unit_load_studies = [
    [list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children[k].Average.Value
     for k in range(len(list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children))
     if list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children[k].Name.Contains("StrainX_SG")
     and list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children[k].DataModelObjectCategory == DataModelObjectCategory.NormalElasticStrain
     and list_of_obj_of_analysis_environments_of_unit_load_studies[i].Solution.Children[k].Suppressed == False]
     for i in range(len(list_of_obj_of_analysis_environments_of_unit_load_studies))]
# endregion 

# ----------------------------------------------------------------------------------------------------------

# region Check if all inner lists have the same length
list_lengths = [len(inner) for inner in list_of_SG_results_of_unit_load_studies]
if min(list_lengths) != max(list_lengths):
    raise ValueError("The number of extracted values are different for each unit load application. Please check whether all the analyses have the same number of SGs with name StrainX_SG and they are all evaluated and their results are correct.")

list_lengths = [len(inner) for inner in list_of_SG_initial_strains_of_unit_load_studies]
if min(list_lengths) != max(list_lengths):
    raise ValueError("The number of extracted values are different for the initial load results of each unit load application. Please check whether all the analyses have the same number of SGs with name StrainX_SG and they are all evaluated and their results are correct.")
# endregion

# ----------------------------------------------------------------------------------------------------------

# Subtracting the effect of initial strains from unit load results
list_of_SG_results_of_unit_load_studies_only = [
    [result - initial for result, initial in zip(results_list, initial_list)]
    for results_list, initial_list in 
    zip(list_of_SG_results_of_unit_load_studies, list_of_SG_initial_strains_of_unit_load_studies)]

# Get the current date and time
current_time = DateTime.Now
# Format the date and time in the desired format and replace colons with underscores
formatted_time = current_time.ToString("dd_MM_yyyy__HH_mm_ss")
# Append the formatted date and time to the file name
csv_file_name = 'strain_sensitivity_matrix_{0}.csv'.format(formatted_time)

csv_file_path = os.path.join(project_path, csv_file_name)

# Write to CSV file into the specified project path
with open(csv_file_path, 'wb') as csvfile:
    writer = csv.writer(csvfile)
    
    # Use zip(*list_of_SG_results_of_unit_load_studies) to transpose the list of lists
    for row in zip(*list_of_SG_results_of_unit_load_studies_only):
        writer.writerow(row)
# endregion

# ----------------------------------------------------------------------------------------------------------

# region Show the generated strain sensitivity matrix [A]
message_success = r"""
The script for generating the strain sensitivity matrix [A] is run successfully.
Please verify the contents of the generated CSV file in the specified project path by the "Project Folder" button.
"""
msg = Ansys.Mechanical.Application.Message(message_success, MessageSeverityType.Info)
ExtAPI.Application.Messages.Add(msg)

#Open the CSV file with the default application
# try:
#     # Open the CSV file with the default application
#     if os.name == 'nt':  # For Windows
#         os.startfile(csv_file_path)