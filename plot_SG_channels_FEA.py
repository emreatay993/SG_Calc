# region Import libraries
import csv
import context_menu
import clr
clr.AddReference('mscorlib')  # Ensure the core .NET assembly is referenced
from System.IO import StreamWriter, FileStream, FileMode, FileAccess
from System.Text import UTF8Encoding
from System.Diagnostics import Process, ProcessWindowStyle
import os
# endregion

# region Define the plot function to be run
solution_directory_path = sol_selected_environment.WorkingDir[:-1]
solution_directory_path = solution_directory_path.Replace("\\", "\\\\")
file_name = 'SG_FEA_microstrain_data.csv'

cpython_script_name = "plot_SG_channels_FEA_cpython_code_only.py"
cpython_script_path = sol_selected_environment.WorkingDir + cpython_script_name
cpython_code = """
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    import sys
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.offline import plot
    import plotly.express as px
    import os
    import re
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QLineEdit, QDialog, QHBoxLayout, 
                                 QVBoxLayout, QWidget, QMessageBox, QComboBox, QCheckBox, QFileDialog,
                                 QLabel, QSizePolicy, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView)
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    
except ImportError as e:
    app = QApplication(sys.argv)
    QMessageBox.critical(None, "Import Error", f"Failed to import a required module: {str(e)}")
    sys.exit(1)

my_discrete_color_scheme = px.colors.qualitative.Light24

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
        super().__init__()
        self.setWindowTitle('SG Strains - FEA: """ + sol_selected_environment.Parent.Name + """')
        self.setGeometry(100, 100, 800, 600)
        self.folder_name = folder_name
        self.file_name = file_name
        self.data = None
        self.initUI()
        
    def initUI(self):
        file_path = os.path.join(self.folder_name, self.file_name)
        try:
            self.data = pd.read_csv(file_path)
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Failed to read the file: {str(e)}")
            sys.exit(1)
        
        # Filter Data label setup
        self.label = QLabel("Filter Data:")
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        # Combobox setups
        self.comboBox = QComboBox()
        self.comboBox.addItem("All")
        self.comboBox.addItem("Raw Strain Data")
        # Add data groups to the combobox
        self.add_combobox_items()
        
        self.refNumberComboBox = QComboBox()
        self.refNumberComboBox.addItem("All Channels")  # Similar to "All" functionality
        self.add_ref_number_items()

        self.comboBox.currentIndexChanged.connect(self.update_plot)
        self.refNumberComboBox.currentIndexChanged.connect(self.update_plot)
        self.viewer = PlotlyViewer(go.Figure())
        self.savePlotButton = QPushButton("Save current plot as HTML file")
        self.savePlotButton.clicked.connect(self.save_current_plot)
        
        self.update_plot(0)  # Initialize plot

        # Modify the layout setup to add the label and combobox horizontally
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.label)
        #filter_layout.addWidget(self.comboBox)
        filter_layout.addWidget(self.refNumberComboBox)
        filter_layout.addWidget(self.savePlotButton)
        filter_layout.addStretch()  # Add stretch to push everything to the left

        # Create the main layout
        layout = QVBoxLayout()
        
        # Add the filter layout to the main layout using addLayout
        layout.addLayout(filter_layout)
        
        # Add the rest of your widgets to the layout
        layout.addWidget(self.viewer)
        
        # Set the layout to the central widget
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def add_combobox_items(self):
        suffixes = set()
        for col in self.data.columns:
            if '_' in col and not col.split('_')[1].isdigit():
                suffix = col.split('_', 1)[1]
                suffixes.add(suffix)
        
        for suffix in sorted(suffixes):
            self.comboBox.addItem(suffix)
            
    def add_ref_number_items(self):
        ref_numbers = set(col.split('_')[1] for col in self.data.columns if '_' in col and col.split('_')[1].isdigit())
        for ref_number in sorted(ref_numbers, key=int):
            self.refNumberComboBox.addItem(ref_number)

    def update_plot(self, index):
        fig = go.Figure()
        selected_group = self.comboBox.currentText()
        selected_ref_number = self.refNumberComboBox.currentText()
    
        # Determine columns based on the selected suffix
        if selected_group == "All":
            trace_columns = [col for col in self.data.columns if col != 'Time']
        elif selected_group == "Raw Strain Data":
            trace_columns = [col for col in self.data.columns if re.match(r'SG\d+_\d+$', col)]
        else:
            trace_columns = [col for col in self.data.columns if col.endswith(selected_group)]
    
        # Further filter columns based on the selected reference number
        if selected_ref_number != "All Channels":
            trace_columns = [col for col in trace_columns if col.split('_')[1] == selected_ref_number]
    
        # Debug output
        print(f"Filtered columns: {trace_columns}")
    
        # Assign colors to visible traces based on their new filtered position
        for idx, col in enumerate(trace_columns):
            color_idx = idx % len(my_discrete_color_scheme)
            fig.add_trace(go.Scatter(
                x=self.data['Time'],
                y=self.data[col],
                mode='lines',
                name=col,
                line=dict(color=my_discrete_color_scheme[color_idx]),  # Assign color based on position in filtered list
                hovertemplate='%{meta}<br>Time = %{x:.2f} s<br>µε = %{y:.1f}<extra></extra>',
                hoverlabel=dict(font_size=10, bgcolor='rgba(255, 255, 255, 0.5)'),
                meta=col
            ))
            
        fig.update_layout(
            title_text='SG Strains (FEA) - Grid Channel: ' + selected_ref_number,
            title_x=0.5,
            legend_title_text='Result',
            template="plotly_white",
            plot_bgcolor='rgba(0,0,0,0.005)',
            xaxis_title='Time [s]',
            yaxis_title='µε',
            font=dict(family="Arial, sans-serif", size=12, color="#0077B6"),
            xaxis=dict(showline=True, showgrid=True, showticklabels=True, linewidth=2, tickfont=dict(family='Arial, sans-serif', size=12), tickmode='auto', nticks=30),
            yaxis=dict(showgrid=True, zeroline=False, showline=False, showticklabels=True, linecolor='rgb(204, 204, 204)', tickmode='auto', nticks=30)
        )

        # Update the viewer's figure with the new figure
        self.viewer.fig = fig

        raw_html = plot(fig, include_plotlyjs='cdn', output_type='div', config={'staticPlot': False})
        self.viewer.setHtml(raw_html)
        
    def save_current_plot(self):
        # Retrieve the parent name from the environment for the filename
        parent_name = '''""" + sol_selected_environment.Parent.Name + """'''
        # Construct the filename
        filename = f"SG_Strains_FEA__{parent_name}.html"
        
        # Debug: Print the figure data to verify its contents
        print("Saving plot with data:")
        print(self.viewer.fig.data)
        
        # Save the current figure to an interactive HTML file
        plot(self.viewer.fig, filename=os.path.join(self.folder_name, filename), output_type='file', auto_open=False)
        QMessageBox.information(self, "Plot Saved", f"The plot has been saved as {filename} in the solution directory.")
# endregion

# region Show the results
try:
    if __name__ == '__main__':
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # Enable high-DPI scaling
        app = QApplication(sys.argv)
        mainWindow = PlotWindow('""" + solution_directory_path + """', '""" + file_name + """')
        mainWindow.show()
        sys.exit(app.exec_())
        os.remove(cpython_script_path)
except Exception as e:
        print(f"An error occurred: {e}")
        input("Press Enter to close...")
# endregion
"""

# Use StreamWriter with FileStream to write the file with UTF-8 encoding
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