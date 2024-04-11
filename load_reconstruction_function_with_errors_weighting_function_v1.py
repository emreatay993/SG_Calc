# Load Reconstruction

"""
Estimates the loads applied on a system based on the measured strains from each SG channel.
The load estimation is based on two inputs, "SG_FEA_strain_data.csv" and "strain_sensitivity_matrix.csv". 
This button searches the measured SG results file from FEA ("SG_FEA_strain_data.csv") for measured strains created by the "SG Strain" command, 
inside the solution folder of the selected analysis environment. 
However, the "strain_sensitivity_matrix.csv" file is searched inside 
the project folder specified by the "Project Folder" button.

"""

# region Import necessary libraries
import os
from System.Drawing import Color, Font, FontStyle, Size, Point, SolidBrush, Pen
from System.Windows.Forms import *
from System.Diagnostics import Process, ProcessWindowStyle
from System.IO import StreamWriter, FileStream, FileMode, FileAccess, StreamReader
from System.Text import UTF8Encoding
# endregion

# ----------------------------------------------------------------------------------------------------------------

# region Import the necessary classes and functions for the GUI
class FlatTextBox(TextBox):
    # Custom Textbox with no border for a flat design
    def __init__(self):
        super().__init__()
        self.BackColor = Color.White
        self.Font = Font("Segoe UI", 9)
        self.SetStyle(ControlStyles.UserPaint, True)

    def OnPaint(self, e):
        super().OnPaint(e)
        # Paint background color
        e.Graphics.FillRectangle(SolidBrush(self.BackColor), 0, 0, self.Width, self.Height)
        # Paint text
        e.Graphics.DrawString(self.Text, self.Font, SolidBrush(self.ForeColor), 2, 2)
        # Draw border if focused
        if self.Focused:
            e.Graphics.DrawRectangle(Pen(Color.FromArgb(204, 228, 247)), 0, 0, self.Width - 1, self.Height - 1)

class InputForm(Form):
    def __init__(self):
        self.InitializeComponent()
    
    def InitializeComponent(self):
        self.Text = 'Parameter Input'
        self.Size = Size(365, 290)
        self.FormBorderStyle = FormBorderStyle.FixedDialog
        self.BackColor = Color.White
        self.MaximizeBox = False
        self.MinimizeBox = False
        self.StartPosition = FormStartPosition.CenterScreen
    
        label_font = Font("Segoe UI", 9, FontStyle.Regular)
        self.flowPanel = FlowLayoutPanel()
        self.flowPanel.FlowDirection = FlowDirection.TopDown
        self.flowPanel.Location = Point(20, 20)
        self.flowPanel.Size = Size(350, 240)
        self.flowPanel.AutoScroll = True
    
        # Labels and TextFields for each parameter
        self.labels_text = ['Overall Signal Noise (microstrains):', 'Gage Factor Error (%):', 'Positioning Error (%):']
        self.textFields = []
        default_values = ['20', '1', '5']  # Default values for the text fields
    
        for i, text in enumerate(self.labels_text):
            label = Label()
            label.Text = text
            label.Size = Size(300, 20)
            label.Font = label_font
            label.Margin = Padding(5, 5, 5, 0)
            self.flowPanel.Controls.Add(label)
    
            textField = TextBox()
            textField.Size = Size(300, 20)
            textField.Font = label_font
            textField.Margin = Padding(5, 0, 5, 5)
            textField.Text = default_values[i]  # Set the default value here
            self.flowPanel.Controls.Add(textField)
            self.textFields.append(textField)
    
        # OK Button
        self.okButton = Button()
        self.okButton.Text = 'OK'
        self.okButton.Size = Size(300, 40)
        self.okButton.Font = Font("Segoe UI", 10, FontStyle.Bold)
        self.okButton.FlatStyle = FlatStyle.Flat
        self.okButton.FlatAppearance.BorderSize = 0
        self.okButton.BackColor = Color.FromArgb(204, 228, 247)
        self.okButton.ForeColor = Color.White
        self.okButton.Click += self.OkButtonClick
        self.okButton.Margin = Padding(5, 10, 5, 5)
        self.flowPanel.Controls.Add(self.okButton)
    
        self.Controls.Add(self.flowPanel)

    def OkButtonClick(self, sender, args):
        try:
            # Parse the input values
            self.signal_noise_microstrains = float(self.textFields[0].Text)
            self.gage_factor_error_percent = float(self.textFields[1].Text)
            self.positioning_error_percent = float(self.textFields[2].Text)
            self.DialogResult = DialogResult.OK
            self.Close()
        except ValueError:
            MessageBox.Show("Please enter valid numerical values.", "Input Error", MessageBoxButtons.OK, MessageBoxIcon.Error)

def show_input_form():
    form = InputForm()
    result = form.ShowDialog()
    if result == DialogResult.OK:
        return form.signal_noise_microstrains, form.gage_factor_error_percent, form.positioning_error_percent
    else:
        return None
# endregion

# ----------------------------------------------------------------------------------------------------------------

# # region Run the form to get the test parameters (noise, positioning error etc.)
# Initialize parameters
signal_noise_microstrains, gage_factor_error_percent, positioning_error_percent = (None,None,None)
parameters = show_input_form()
if parameters:
    signal_noise_microstrains, gage_factor_error_percent, positioning_error_percent = parameters
# endregion

# ----------------------------------------------------------------------------------------------------------------

# region Get the existing CSV files from sensitivity_matrix_file_path and measured_SG_strain_FEA_file_path
solution_directory_path = sol_selected_environment.WorkingDir[:-1]
solution_directory_path = solution_directory_path.Replace("\\", "\\\\")
project_path = project_path.Replace("\\", "\\")

measured_SG_strain_FEA_file_name = 'SG_FEA_strain_data.csv'
measured_SG_strain_FEA_file_path = os.path.join(solution_directory_path, measured_SG_strain_FEA_file_name)

# Define the path the cpython script will be executed
cpython_script_name = "load_reconstruction_FEA_cpython_code_only.py"
cpython_script_path = sol_selected_environment.WorkingDir + cpython_script_name
# strain_sensitivity_matrix_file_path will be obtained during the execution of cpython code
# endregion

# Define the load reconstruction function and the plotter of the estimated loads to be run
cpython_code ="""
# region Import necessary libraries
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
try:
    import sys
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.offline import plot
    import plotly.express as px
    import os
    import re
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QMessageBox, QComboBox
    from PyQt5.QtWebEngineWidgets import QWebEngineView

except ImportError as e:
    app = QApplication(sys.argv)
    QMessageBox.critical(None, "Import Error", f"Failed to import a required module: {str(e)}")
    sys.exit(1)
# endregion

# Set the color scheme for plot traces
my_discrete_color_scheme = px.colors.qualitative.Light24

# region Import the necessary classes and functions for the GUI
class PlotlyViewer(QWebEngineView):
    def __init__(self, fig, parent=None):
        super(PlotlyViewer, self).__init__(parent)
        self.figure = fig
        self.initUI()

    def initUI(self):
        raw_html = plot(self.figure, include_plotlyjs='cdn', output_type='div', config={'staticPlot': False})
        self.setHtml(raw_html)

class PlotWindow(QMainWindow):
    def __init__(self, folder_name, file_name):
        super(PlotWindow, self).__init__()
        self.setWindowTitle('Load Reconstruction - FEA: """ + sol_selected_environment.Parent.Name + """')
        self.setGeometry(100, 100, 800, 600)
        self.folder_name = folder_name
        self.file_name = file_name
        self.initUI()
        
    def extract_sort_key(self, channel_name):
        match = re.match(r'SG(\d+)_(\d+)', channel_name)
        if match:
            return tuple(map(int, match.groups()))
        return (0, 0)  # Return a default sort key for safety

    def initUI(self):
        try:
            file_path = os.path.join(self.folder_name, self.file_name)
            data = pd.read_csv(file_path)
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Failed to read the file: {str(e)}")
            sys.exit(1)
    
        data_long = data.melt(id_vars='Time [s]', var_name='Component', value_name='Load Factor')
    
        # Apply the sorting key extraction function and sort
        data_long['SortKey'] = data_long['Component'].apply(self.extract_sort_key)
        data_long_sorted = data_long.sort_values(by='SortKey')
    
        fig = go.Figure()
        for label, df in data_long.groupby('Component', sort=False):
            hover_text = df.apply(lambda row: f'Component={label}<br>Time={row["Time [s]"]} s<br>Load Factor={row["Load Factor"]}', axis=1)
            
            # Calculate trace_index here
            trace_index = list(data_long['Component'].unique()).index(label)
            
            # Then use trace_index to determine the color for the current trace
            trace_color = my_discrete_color_scheme[trace_index % len(my_discrete_color_scheme)]
            
            fig.add_trace(go.Scatter(
                x=df['Time [s]'], 
                y=df['Load Factor'], 
                mode='lines', 
                name=label,
                line=dict(color=trace_color),
                hoverinfo='text',
                text=hover_text,
                hoverlabel = dict(
                    font_size = 10,
                    bgcolor='rgba(255, 255, 255, 0.5)')
            ))

        fig.update_layout(
            title_text='Load Reconstruction - FEA: """ + sol_selected_environment.Parent.Name + """',
            title_x=0.5,  # Center the title
            legend_title_text='Component',
            template="plotly_white",
            plot_bgcolor='rgba(0,0,0,0.005)',
            xaxis_title='Time [s]',
            yaxis_title='Load Factor',
            
            font=dict(
                family="Arial, sans-serif",  # Setting a universal font for the plot
                size=12,
                color="#0077B6"  # light sky blue
                ),
                
            xaxis=dict(
                showline=True,
                showgrid=True,
                showticklabels=True,
                linewidth=2,
                tickfont=dict(
                    family='Arial, sans-serif',
                    size=12,
                    ),
                tickmode='auto',
                nticks=30
                ),
            grid=dict(
                rows=1,
                columns=1,
                pattern="independent"
                ),
                
            yaxis=dict(
                showgrid=True,
                zeroline=False,
                showline=False,
                showticklabels=True,
                linecolor='rgb(204, 204, 204)',
                tickmode='auto',
                nticks=30
                ),
            )
            
        
        # Hover mode configuration for better interaction
        fig.update_traces(
        line=dict(width=2),
        marker=dict(size=3),
        mode='markers+lines'
        )
        
        fig.update_yaxes(
        showspikes=False,
        spikecolor="#0077B6",  # Set spike color
        spikethickness=1,  # Set spike thickness
        spikedash='dot',  # Set spike style
        )
        
        fig.update_xaxes(
        showspikes=False,
        spikecolor="#0077B6",  # Set spike color
        spikethickness=1,  # Set spike thickness
        spikedash='dot',  # Set spike style
        )
        
        # Generate an offline (html) version of the plotly graph
        plot(fig, filename=os.path.join(self.folder_name, 'Load_Reconstruction_FEA_""" + sol_selected_environment.Parent.Name + """.html'), auto_open=False) 
        self.viewer = PlotlyViewer(fig)
        
        layout = QVBoxLayout()
        layout.addWidget(self.viewer)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
# endregion

# region Find files containing "strain_sensitivity_matrix" in their names in the project folder
def find_files_with_strain_sensitivity_matrix(project_path):
    # Initialize an empty list to store the paths of files containing "strain_sensitivity_matrix"
    matching_files = []

    # Walk through the directory
    for root, dirs, files in os.walk(project_path):
        for file in files:
            # Check if "strain_sensitivity_matrix" is in the file name and the file is a .csv file
            if "strain_sensitivity_matrix" in file and file.endswith('.csv'):
                # Add the file path to the list
                matching_files.append(os.path.join(root, file))
                print(matching_files)

    # Check if more than one file was found
    if len(matching_files) > 1:
        # Initialize the QApplication
        app = QApplication([])

        # Show an error messagebox
        QMessageBox.critical(None, "Error", "More than one file with 'strain_sensitivity_matrix' is found. There should be only one strain_sensitivity_matrix.csv inside the folder for the program to continue.")

        # No need to explicitly destroy the QApplication
    if len(matching_files) == 1:
        strain_sensitivity_matrix_file_path = matching_files[0]
        
    # Return the list of matching files
    return strain_sensitivity_matrix_file_path

strain_sensitivity_matrix_file_path = find_files_with_strain_sensitivity_matrix(r'""" + project_path + """')
# endregion

# region Define and run the reconstruction function
def estimate_loads_from_strains_with_errors_per_gauge(
measured_SG_strain_FEA_file_path, 
sensitivity_matrix_file_path,
signal_noise_microstrains,
gage_factor_error_percent,
positioning_error_percent):
    # Load the CSV files
    S_df = pd.read_csv(measured_SG_strain_FEA_file_path)
    A_df = pd.read_csv(sensitivity_matrix_file_path, header=None)

    # Extract strain measurements and sensitivity matrix
    S_matrix = S_df.iloc[:, 1:].values
    A_matrix = A_df.values

    # Calculate variances from different error sources for each gauge
    signal_noise = signal_noise_microstrains * 1e-6
    signal_noise_variance = signal_noise ** 2

    # Calculate RMS strain for each gauge
    rms_strain_per_gauge = np.sqrt(np.mean(S_matrix**2, axis=0))

    gage_factor_error = gage_factor_error_percent / 100
    positioning_error = positioning_error_percent / 100

    # Total variance for each strain gauge measurement
    total_variance_per_gauge = (signal_noise_variance +
                                (gage_factor_error ** 2) * rms_strain_per_gauge ** 2 +
                                (positioning_error ** 2) * rms_strain_per_gauge ** 2)
    
    total_variance_per_gauge[total_variance_per_gauge == 0] = 1e-10  # replace 0 with a small number

    # Creating the W matrix for each gauge
    W = np.diag(1 / total_variance_per_gauge)

    # Perform the weighted least squares estimate calculation
    A_T_W = A_matrix.T @ W
    A_T_W_A_inv = np.linalg.inv(A_T_W @ A_matrix)
    L_hat = A_T_W_A_inv @ A_T_W @ S_matrix.T

    # Transpose to get the original shape
    L_hat_timeseries = L_hat.T

    # Create a DataFrame for the results
    estimated_loads_df = pd.DataFrame(L_hat_timeseries, columns=[f'Load {i+1}' for i in range(A_matrix.shape[1])])
    estimated_loads_df.insert(0, 'Time [s]', S_df.iloc[:, 0])

    # Save to CSV
    estimated_loads_csv_file_name = 'estimated_loads_with_errors_per_gauge_RMS.csv'
    estimated_loads_csv_file_path = os.path.join('""" + solution_directory_path + """', estimated_loads_csv_file_name)
    estimated_loads_df.to_csv(estimated_loads_csv_file_path, index=False)
    estimated_loads_df.set_index('Time [s]', inplace=True)

    return estimated_loads_df, estimated_loads_csv_file_path

loads_df_with_errors_per_gauge, estimated_loads_csv_file_path = estimate_loads_from_strains_with_errors_per_gauge(
    r'""" + measured_SG_strain_FEA_file_path + """',
    strain_sensitivity_matrix_file_path,
    0, 0, 0  # Error parameters
)

print(loads_df_with_errors_per_gauge)  # Display the first few rows of the estimated loads
print("CSV file saved at: " + estimated_loads_csv_file_path)

# region Show the estimated loads
try:
    if __name__ == '__main__':
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # Enable high-DPI scaling
        app = QApplication(sys.argv)
        mainWindow = PlotWindow('""" + solution_directory_path + """', estimated_loads_csv_file_path)
        mainWindow.show()
        sys.exit(app.exec_())
        os.remove(cpython_script_path)
except Exception as e:
        print(f"An error occurred: {e}")
        input("Press Enter to close...")
# endregion
"""

# Use StreamWriter with FileStream to write the cpython file with UTF-8 encoding
with StreamWriter(FileStream(cpython_script_path, FileMode.Create, FileAccess.Write), UTF8Encoding(True)) as writer:
    writer.Write(cpython_code)

print("Python file created successfully with UTF-8 encoding.")
# endregion

# Run the CPython script asynchronously
process = Process()
# Configure the process to hide the window and not use the shell execute feature
#process.StartInfo.CreateNoWindow = True

process.StartInfo.UseShellExecute = True
# Set the command to run the Python interpreter with your script as the argument
process.StartInfo.WindowStyle = ProcessWindowStyle.Minimized
process.StartInfo.FileName = "cmd.exe"  # Use cmd.exe to allow window manipulation
process.StartInfo.Arguments = '/c python "' + cpython_script_path + '"'
# Start the process
process.Start()
# endregion