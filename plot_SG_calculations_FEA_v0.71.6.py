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
file_name_of_SG_calculations = 'SG_calculations.csv'
file_path_of_SG_calculations = os.path.join(solution_directory_path, file_name_of_SG_calculations)

cpython_script_name = "plot_SG_calculations_cpython_code_only.py"
cpython_script_path = sol_selected_environment.WorkingDir + cpython_script_name
cpython_code ="""
# region Import necessary modules
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
try:
    import sys
    import time as time_module
    import socket
    import threading
    import pandas as pd
    import numpy as np
    import plotly.graph_objects as go
    from plotly.offline import plot
    import plotly.express as px
    import plotly.figure_factory as ff
    from plotly_resampler import FigureResampler
    import os
    import re
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
    from PyQt5 import QtCore
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QLineEdit, QDialog, QHBoxLayout,
                                 QVBoxLayout, QWidget, QMessageBox, QComboBox, QCheckBox, QFileDialog,
                                 QLabel, QSizePolicy, QPushButton, QTableWidget, QTableWidgetItem, 
                                 QHeaderView, QProgressBar)
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    import concurrent.futures
    from concurrent.futures import ThreadPoolExecutor

    import dash
    from dash import Dash, Input, Output, callback_context, dcc, html, no_update, State
    import dash_bootstrap_components as dbc
    #from dash_extensions.enrich import DashProxy, Serverside, ServersideOutputTransform
except ImportError as e:

    app_messagebox = QApplication(sys.argv)
    QMessageBox.critical(None, "Import Error", f"Failed to import a required module: {str(e)}")
    sys.exit(1)
# endregion

# region Define classes and global functions/variables
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
my_discrete_color_scheme = px.colors.qualitative.Light24
global selected_group
global my_fig
my_fig = FigureResampler()
global current_figure_main
current_figure_main = None
selected_group = None
selected_ref_number = None
output_data = None
trace_columns = None
global comparison_data
comparison_data = None
global comparison_trace_columns  
comparison_trace_columns = None
global current_comparison_figure
current_comparison_figure = None

class FlatLineEdit(QLineEdit):
    def __init__(self, placeholder_text=""):
        super(FlatLineEdit, self).__init__()
        self.setPlaceholderText(placeholder_text)
        self.setStyleSheet("QLineEdit {border: 1px solid #bfbfbf; border-radius: 5px; padding: 5px; background-color: #ffffff;} QLineEdit:focus {border: 2px solid #0077B6;}")

class MaterialPropertiesDialog(QDialog):
    def __init__(self, parent=None):
        super(MaterialPropertiesDialog, self).__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Enter Material Properties')
        self.setGeometry(100, 100, 100, 100)
        self.fullWidth = 500
        self.fullHeight = 400
        self.reducedWidth = 400
        self.reducedHeight = 200

        self.setStyleSheet("QWidget { font-size: 11px; } QPushButton { background-color: #0077B6; color: white; border-radius: 5px; padding: 6px; } QLineEdit { border: 1px solid #ccc; border-radius: 5px; padding: 5px; background-color: #ffffff; } QLabel { color: #333; }")

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Adjusting the layout for labels and line edits
        formLayout = QVBoxLayout()

        self.labelE = QLabel("Young's Modulus [GPa]:")
        self.lineEditE = QLineEdit(self)
        formLayout.addWidget(self.labelE)
        formLayout.addWidget(self.lineEditE)

        self.labelV = QLabel("Poisson's Ratio:")
        self.lineEditV = QLineEdit(self)
        formLayout.addWidget(self.labelV)
        formLayout.addWidget(self.lineEditV)

        layout.addLayout(formLayout)

        # Checkbox for time-dependent input
        self.checkbox = QCheckBox("Time Dependent Input:")
        self.checkbox.stateChanged.connect(self.toggle_time_dependent_input)
        layout.addWidget(self.checkbox)

        # File selection and data table visibility
        fileLayout = QHBoxLayout()
        self.fileLabel = QLabel("Select a directory for 'T vs. E, v' data:")
        self.fileLabel.setVisible(False)
        self.selectFileButton = QPushButton("Select File")
        self.selectFileButton.clicked.connect(self.select_file)
        self.selectFileButton.setVisible(False)
        fileLayout.addWidget(self.fileLabel)
        fileLayout.addWidget(self.selectFileButton)
        layout.addLayout(fileLayout)

        self.filePathLineEdit = QLineEdit(self)
        self.filePathLineEdit.setReadOnly(True)
        self.filePathLineEdit.setVisible(False)
        layout.addWidget(self.filePathLineEdit)

        # Table to display the data
        self.dataTable = QTableWidget(self)
        self.dataTable.setColumnCount(3)
        self.dataTable.setHorizontalHeaderLabels(["Temperature [°C]", "Young's Modulus [GPa]", "Poisson's Ratio"])
        self.dataTable.setVisible(False)
        self.dataTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.dataTable)

        # OK and Cancel buttons
        buttonLayout = QHBoxLayout()
        self.okButton = QPushButton('OK')
        self.okButton.clicked.connect(self.acceptInputs)
        cancelButton = QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(self.okButton)
        buttonLayout.addWidget(cancelButton)
        layout.addLayout(buttonLayout)

        self.resize(self.reducedWidth, self.reducedHeight+100)

    def toggle_time_dependent_input(self, state):
        is_checked = state == Qt.Checked
        if is_checked:
            self.resize(self.fullWidth, self.fullHeight)
            self.lineEditE.clear()
            self.lineEditV.clear()
            self.lineEditE.setStyleSheet("background-color: #e0e0e0;")  # Light grey background
            self.lineEditV.setStyleSheet("background-color: #e0e0e0;")  # Light grey background
        else:
            self.resize(self.reducedWidth, self.reducedHeight)
            self.lineEditE.setStyleSheet("background-color: #ffffff;")  # White background
            self.lineEditV.setStyleSheet("background-color: #ffffff;")  # White background
        self.lineEditE.setDisabled(is_checked)
        self.lineEditV.setDisabled(is_checked)
        self.fileLabel.setVisible(is_checked)
        self.selectFileButton.setVisible(is_checked)
        self.filePathLineEdit.setVisible(is_checked)
        self.dataTable.setVisible(is_checked)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv);;All Files (*)")
        if file_path:
            self.filePathLineEdit.setText(file_path)
            self.load_data(file_path)

    def load_data(self, file_path):
        try:
            data = pd.read_csv(file_path, encoding='ISO-8859-1')
            self.populate_table(data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load the file: {str(e)}")

    def populate_table(self, data):
        self.dataTable.setRowCount(len(data))
        for i, (index, row) in enumerate(data.iterrows()):
            self.dataTable.setItem(i, 0, QTableWidgetItem(str(row[0])))
            self.dataTable.setItem(i, 1, QTableWidgetItem(str(row[1])))
            self.dataTable.setItem(i, 2, QTableWidgetItem(str(row[2])))
        self.dataTable.setVisible(True)

    def acceptInputs(self):
            try:
                E = float(self.lineEditE.text())
                E = E*1e9  # Convert the [GPa] to SI units [Pa]
                v = float(self.lineEditV.text())
                # Optionally add validation rules here
                if E <= 0 or v <= 0 or v >= 0.5:
                    raise ValueError("Please enter valid values: E > 0, 0 < v < 0.5")
                self.user_input = {'E': E, 'v': v}
                self.accept()  # Close the dialog and return success
            except ValueError as ve:
                QMessageBox.critical(self, "Input Error", str(ve))

class PlotlyViewer(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.qdash = QDash()
        self.load(QtCore.QUrl("http://127.0.0.1:8050"))

    def update_plot(self, fig):
        self.qdash.update_graph(fig)
        self.reload()

class PlotWindow(QMainWindow):
    def __init__(self, folder_name, file_name):
        super().__init__()
        self.setWindowTitle('SG Calculations : """ + sol_selected_environment.Parent.Name + """')
        self.setGeometry(100, 100, 1000, 550)
        self.folder_name = folder_name
        self.file_name = file_name
        self.initProgressBar()
        self.initUI()
    plot_started = pyqtSignal()
    plot_progress = pyqtSignal(int)
    plot_finished = pyqtSignal()

    def initUI(self):
        file_path = os.path.join(self.folder_name, self.file_name)
        global output_data
        try:
            if os.path.exists(file_path):
                reply = QMessageBox.question(
                    self,
                    'File Found',
                    "An SG_calculations.csv is found inside the solution directory. Would you like to plot the results for it?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    output_data = pd.read_csv(file_path)
                else:
                    output_data = output_SG_data_w_raw
            else:
                output_data = output_SG_data_w_raw
            
            time_df = pd.DataFrame(time).reset_index(drop=True)
            output_data = pd.concat([time_df, output_data.reset_index(drop=True)], axis=1)
            output_data = output_data.sort_values(by='Time')
            
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Failed to read the file: {str(e)}")
            sys.exit(1)
    
        # Ensure 'Time' is the first column
        cols = ['Time'] + [col for col in output_data if col != 'Time']
        output_data = output_data[cols]

        # Filter Data label setup
        self.label = QLabel("Filter Data:")
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Channel label setup
        self.label_channel = QLabel("Rosette Channel:")
        self.label_channel.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_channel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Combobox setups
        self.comboBox = QComboBox()
        self.comboBox.addItem("All")
        self.comboBox.addItem("Raw Strain Data")
        # Add data groups to the combobox
        self.add_combobox_items()

        self.refNumberComboBox = QComboBox()
        self.refNumberComboBox.addItem("-")  # Similar to "All" functionality
        self.add_ref_number_items()

        self.comboBox.currentIndexChanged.connect(self.update_plot)
        self.refNumberComboBox.currentIndexChanged.connect(self.update_plot)
        self.viewer = PlotlyViewer()
        self.savePlotButton = QPushButton("Save current plot as HTML file")
        self.savePlotButton.clicked.connect(self.save_current_plot)

        self.offsetZeroButton = QPushButton("Offset-Zero SG's")
        self.offsetZeroButton.clicked.connect(self.offset_zero_sgs)  # Connect to the new function
        
        self.offsetStartTimeButton = QPushButton("Offset-Zero Start Time")  # New button
        self.offsetStartTimeButton.clicked.connect(self.offset_start_time)  # Connect to the new function

        self.writeCSVButton = QPushButton("Write Full Data to CSV (Main Data)")
        self.writeCSVButton.clicked.connect(self.write_full_data_to_csv)

        self.update_plot(0)  # Initialize plot

        # Modify the layout setup to add the label and combobox horizontally
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.label)
        filter_layout.addWidget(self.comboBox)
        filter_layout.addWidget(self.label_channel)
        filter_layout.addWidget(self.refNumberComboBox)
        filter_layout.addWidget(self.savePlotButton)
        filter_layout.addWidget(self.offsetZeroButton)
        filter_layout.addWidget(self.offsetStartTimeButton)
        filter_layout.addWidget(self.writeCSVButton)
        filter_layout.addStretch()  # Add stretch to push everything to the left

        # Create the main layout
        layout = QVBoxLayout()

        # Add the filter layout to the main layout using addLayout
        layout.addLayout(filter_layout)

        # Add the rest of your widgets to the layout
        layout.addWidget(self.viewer)
        layout.addWidget(self.progressBar)

        # Set the layout to the central widget
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def initProgressBar(self):
        self.progressBar = QProgressBar(self)
        self.progressBar.setGeometry(30, 40, 300, 25)
        self.progressBar.setMaximum(100)
        self.progressBar.setVisible(False)

        self.plot_started.connect(self.on_plot_started)
        self.plot_progress.connect(self.on_plot_progress)
        self.plot_finished.connect(self.on_plot_finished)

    def on_plot_started(self):
        self.progressBar.setVisible(True)
        self.progressBar.setValue(0)

    def on_plot_progress(self, value):
        self.progressBar.setValue(value)

    def on_plot_finished(self):
        self.progressBar.setValue(100)
        QTimer.singleShot(500, self.hide_progress_bar)

    def hide_progress_bar(self):
        self.progressBar.setVisible(False)

    def add_combobox_items(self):
        suffixes = set()
        global output_data
        for col in output_data.columns:
            if '_' in col and not col.split('_')[1].isdigit():
                suffix = col.split('_', 1)[1]
                suffixes.add(suffix)

        for suffix in sorted(suffixes):
            self.comboBox.addItem(suffix)

    def add_ref_number_items(self):
        global output_data
        ref_numbers = set(col.split('_')[1] for col in output_data.columns if '_' in col and col.split('_')[1].isdigit())
        for ref_number in sorted(ref_numbers, key=int):
            self.refNumberComboBox.addItem(ref_number)

    def update_plot(self, index):
        fig: FigureResampler = FigureResampler()
        global selected_group 
        global selected_ref_number
        global output_data
        global trace_columns
        selected_group = self.comboBox.currentText()
        selected_ref_number = self.refNumberComboBox.currentText()

        # Determine columns based on the selected suffix
        if selected_group == "All":
            trace_columns = [col for col in output_data.columns if col != 'Time']
            self.refNumberComboBox.setEnabled(False)
            self.refNumberComboBox.setCurrentIndex(0)
        elif selected_group == "Raw Strain Data":
            trace_columns = [col for col in output_data.columns if re.match(r'SG\d+_\d+$', col)]
            self.refNumberComboBox.setEnabled(True)
        else:
            trace_columns = [col for col in output_data.columns if col.endswith(selected_group)]
            self.refNumberComboBox.setEnabled(False)
            self.refNumberComboBox.setCurrentIndex(0)

        # Further filter columns based on the selected reference number
        if selected_ref_number != "-":
            trace_columns = [col for col in trace_columns if col.split('_')[1] == selected_ref_number]

        # Debug output
        print(f"Filtered columns: {trace_columns}")

        self.viewer.update_plot(fig)

    def save_current_plot(self):
        # Retrieve the parent name from the environment for the filename
        parent_name = '''""" + sol_selected_environment.Parent.Name + """'''
        # Construct the filename
        filename = f"SG_Calculations__{parent_name}__{selected_group}.html"

        # Save the current figure to an interactive HTML file
        plot(my_fig, filename=os.path.join(self.folder_name, filename),
             output_type='file', auto_open=False)
        QMessageBox.information(self, "Plot Saved", f"The plot has been saved as {filename} in the solution directory.")# endregion

    def offset_zero_sgs(self):
        # Get the unique time points as strings for the combo box
        time_points = [str(tp) for tp in output_data['Time'].unique()]
        
        dialog = OffsetZeroDialog(self, time_points)
        if dialog.exec_() == QDialog.Accepted:
            selected_time = dialog.get_selected_time()
            self.apply_offset_zero(selected_time)
    
    def apply_offset_zero(self, selected_time):
        global output_data, initial_SG_raw_data
    
        # Define a small epsilon value
        epsilon = 1e-10
        
        # Make a copy of the raw SG data
        raw_data_copy = initial_SG_raw_data.copy()
        
        # Get the strain columns (assume columns with 'SG' in their name)
        strain_columns = [col for col in raw_data_copy.columns if 'SG' in col]
        
        # Extract strain data 
        strain_data = raw_data_copy[strain_columns]
        
        # Add epsilon to any zero values in the strain columns before the offset calculations
        strain_data = strain_data.apply(lambda x: x + (x == 0) * epsilon)
        
        # Find the index of the selected time
        selected_time_index = output_data[output_data['Time'] == selected_time].index
        if selected_time_index.empty:
            QMessageBox.critical(self, "Error", "Selected time point not found in the data.")
            return
        selected_time_index = selected_time_index[0]
        
        # Extract the strain values at the selected time point
        offset_values = strain_data.iloc[selected_time_index]
        
        # Subtract the strains at the selected time point from all strain values
        strain_data = strain_data - offset_values
        
        # Set all strain values before the selected time point to zero
        strain_data[:selected_time_index] = 0
        
        # Add epsilon to any zero values again after the offset calculations
        strain_data = strain_data.apply(lambda x: x + (x == 0) * epsilon)
        
        # Recalculate the SG variables
        output_SG_data_w_raw = calculate_all_SG_variables(strain_data, rosette_angles_df)
        output_SG_data_w_raw.insert(0, 'Time', output_data['Time'])
        #output_SG_data_w_raw.set_index('Time', inplace=True)
    
        output_data = output_SG_data_w_raw
    
        # Update the plot
        self.update_plot(0)

    def offset_start_time(self):
        # Get the unique time points as strings for the combo box
        time_points = [str(tp) for tp in output_data['Time'].unique()]
        
        dialog = OffsetZeroDialog(self, time_points)
        if dialog.exec_() == QDialog.Accepted:
            selected_time = dialog.get_selected_time()
            self.apply_offset_start_time(selected_time)
    
    def apply_offset_start_time(self, selected_time):
        global output_data
    
        # Find the index of the selected time
        selected_time_index = output_data[output_data['Time'] == selected_time].index
        if selected_time_index.empty:
            QMessageBox.critical(self, "Error", "Selected time point not found in the data.")
            return
        selected_time_index = selected_time_index[0]
    
        # Drop data before the selected time point
        output_data = output_data.loc[selected_time_index:].reset_index(drop=True)
    
        # Offset the time so that the selected time point becomes the new zero
        output_data['Time'] = output_data['Time'] - selected_time
    
        # Update the plot
        self.update_plot(0)

    def write_full_data_to_csv(self):
        global output_data  # Ensure this references the correct DataFrame
        file_path = os.path.join(self.folder_name, self.file_name)
    
        try:
            output_data.to_csv(file_path, index=False)
            QMessageBox.information(self, "CSV Saved", f"The full data has been saved as {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to write the CSV file: {str(e)}")

# region Add styles for frontend GUI
tab_style={'width': '25%', 'height': '3vh', 'line-height': '3vh', 'padding': '0', 'margin': '0','font-size': '10px'}
selected_tab_style={'width': '25%', 'height': '3vh', 'line-height': '3vh', 'padding': '0', 'margin': '0', 'font-size': '10px'}
# endregion

class QDash(QtCore.QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = my_dash_app
        self.app.layout = html.Div([
            dcc.Tabs(id="tabs-example", value='tab-1', children=[
                dcc.Tab(label='Main Data', value='tab-1', style=tab_style, selected_style=selected_tab_style),
                dcc.Tab(label='Comparison', value='tab-2', style=tab_style, selected_style=selected_tab_style),
            ], style={'width': '50%', 'height': '3vh', 'line-height': '3vh', 'padding': '0', 'margin': '0'}),
            html.Div(id='tabs-content-example', style={'padding': '0'}),
            html.Div(id='comparison-data-loaded', style={'display': 'none'})
        ])

    @property
    def app(self):
        return self._app

    def update_graph(self, fig):
        pass

class OffsetZeroDialog(QDialog):
    def __init__(self, parent=None, time_points=None):
        super(OffsetZeroDialog, self).__init__(parent)
        self.setWindowTitle('Select Time Point for Offset-Zero')
        self.setGeometry(100, 100, 300, 100)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.label = QLabel("Select Time Point:")
        layout.addWidget(self.label)

        self.comboBox = QComboBox()
        self.comboBox.addItems(time_points)
        self.comboBox.setEditable(True)
        layout.addWidget(self.comboBox)

        buttonLayout = QHBoxLayout()
        self.okButton = QPushButton('OK')
        self.okButton.clicked.connect(self.accept)
        cancelButton = QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(self.okButton)
        buttonLayout.addWidget(cancelButton)
        layout.addLayout(buttonLayout)

    def get_selected_time(self):
        return float(self.comboBox.currentText())
# endregion

my_dash_app = Dash(__name__)
# Update the callback to render the content of each tab
@my_dash_app.callback(
    Output('tabs-content-example', 'children'),
    [Input('tabs-example', 'value')],
    [State('comparison-data-loaded', 'children')],
    prevent_initial_call=False,
)
def render_content(tab, comparison_data_loaded):
    if tab == 'tab-1':
        graph = dcc.Graph(
            id="graph-id",
            config={
                'displaylogo': False  # Disable the plotly logo
            },
            style={'width': '100%', 'height': 'calc(100vh - 12vh)', 'overflow': 'auto'}
        )
        if current_figure_main:
            graph.figure = current_figure_main  # Set the current figure if it exists
        return html.Div([
            html.Button("Click to Plot", id="plot-button", n_clicks=0, style={'width': '12%', 'margin': '0.5vh','font-size': '10px'}),
            graph
        ])
    elif tab == 'tab-2':
        graph_comparison = dcc.Graph(
            id="graph-comparison-id",
            config={
                'displaylogo': False  # Disable the plotly logo
            },
            style={'width': '100%', 'height': 'calc(100vh - 12vh)', 'overflow': 'auto'}
        )
        return html.Div([
            html.Button("Click to Plot", id="plot-comparison-button", n_clicks=0, style={'width': '12%', 'margin': '0.5vh','font-size': '10px'}),
            html.Button("Load Comparison CSV", id="load-comparison-csv-button", n_clicks=0, style={'width': '15%', 'margin': '0.5vh','font-size': '10px'}),
            graph_comparison
        ])

# Update the callback to plot the graph
@my_dash_app.callback(
    Output("graph-id", "figure"),
    Input("plot-button", "n_clicks"),
    prevent_initial_call=False,
)
def plot_graph(n_clicks):
    ctx = callback_context
    global current_figure_main  # Declare the global variable
    if len(ctx.triggered) and "plot-button" in ctx.triggered[0]["prop_id"]:
        global my_fig
        global output_data
        global trace_columns
        
        mainWindow.plot_started.emit() # Emit the plot started signal
        
        if len(my_fig.data):
            my_fig.replace(go.Figure())

        time_data_in_x_axis = output_data['Time']
        total_no_of_traces_to_add = len(trace_columns)
        
        for idx, col in enumerate(trace_columns):
            color_idx = idx % len(my_discrete_color_scheme)
            my_fig.add_trace(go.Scattergl(
                x=time_data_in_x_axis,
                y=output_data[col],
                name=col,
                line=dict(color=my_discrete_color_scheme[color_idx]),
                hovertemplate='%{meta}<br>Time = %{x:.2f} s<br>Data = %{y:.1f}<extra></extra>',
                hoverlabel=dict(font_size=14, bgcolor='rgba(255, 255, 255, 0.5)'),
                meta=col
            ))
            progress = int((idx + 1) / total_no_of_traces_to_add * 100)
            mainWindow.plot_progress.emit(progress)  # Emit the plot progress signal
            
            my_fig.update_layout(
                title_text='SG Calculations : """ + sol_selected_environment.Parent.Name + """ ' + "( " + selected_group + " )",
                title_x=0.45,
                title_y=0.95,
                legend_title_text='Result',
                template="plotly_white",
                plot_bgcolor='rgba(0,0,0,0.005)',
                xaxis_title='Time [s]',
                yaxis_title='Data',
                font=dict(family="Arial, sans-serif", size=12, color="#0077B6"),
                xaxis=dict(showline=True, showgrid=True, showticklabels=True, linewidth=2,
                           tickfont=dict(family='Arial, sans-serif', size=12), tickmode='auto', nticks=30),
                yaxis=dict(showgrid=True, zeroline=False, showline=False, showticklabels=True,
                           linecolor='rgb(204, 204, 204)', tickmode='auto', nticks=30),
                hovermode='closest',
                margin=dict(t=40,b=0)  # Adjust the top margin to bring the graph closer to the title
            )
        
        current_figure_main = my_fig  # Update the global variable with the new figure
        mainWindow.plot_finished.emit()  # Emit the plot finished signal
        return my_fig
    else:
        return no_update
# endregion

@my_dash_app.callback(
    Output('comparison-data-loaded', 'children'),
    Input('load-comparison-csv-button', 'n_clicks'),
    prevent_initial_call=True,
)
def load_comparison_csv(n_clicks):
    if n_clicks:
        global comparison_data
        global comparison_trace_columns
        file_path, _ = QFileDialog.getOpenFileName(None, 'Open comparison CSV file', '', 'CSV Files (*.csv)')
        if file_path:
            comparison_data = pd.read_csv(file_path)
            comparison_trace_columns = [col for col in comparison_data.columns if col != 'Time']
            return 'loaded'
    return no_update

@my_dash_app.callback(
    Output("graph-comparison-id", "figure"),
    Input("plot-comparison-button", "n_clicks"),
    prevent_initial_call=False,
)
def plot_comparison_graph(n_clicks):
    ctx = callback_context
    global my_fig
    global comparison_data
    global comparison_trace_columns

    if len(ctx.triggered) and "plot-comparison-button" in ctx.triggered[0]["prop_id"]:
        if comparison_data is not None and comparison_trace_columns is not None:
            my_fig.replace(go.Figure())  # Reset the figure

            time_data_in_x_axis = comparison_data['Time']
            total_no_of_traces_to_add = len(comparison_trace_columns)

            for idx, col in enumerate(comparison_trace_columns):
                color_idx = idx % len(my_discrete_color_scheme)
                my_fig.add_trace(go.Scattergl(
                    x=time_data_in_x_axis,
                    y=comparison_data[col],
                    name=col,
                    line=dict(color=my_discrete_color_scheme[color_idx]),
                    hovertemplate='%{meta}<br>Time = %{x:.2f} s<br>Data = %{y:.1f}<extra></extra>',
                    hoverlabel=dict(font_size=14, bgcolor='rgba(255, 255, 255, 0.5)'),
                    meta=col
                ))
                progress = int((idx + 1) / total_no_of_traces_to_add * 100)
                mainWindow.plot_progress.emit(progress)  # Emit the plot progress signal

                my_fig.update_layout(
                    title_text='Comparison Data',
                    title_x=0.45,
                    title_y=0.95,
                    legend_title_text='Result',
                    template="plotly_white",
                    plot_bgcolor='rgba(0,0,0,0.005)',
                    xaxis_title='Time [s]',
                    yaxis_title='Data',
                    font=dict(family="Arial, sans-serif", size=12, color="#0077B6"),
                    xaxis=dict(showline=True, showgrid=True, showticklabels=True, linewidth=2,
                               tickfont=dict(family='Arial, sans-serif', size=12), tickmode='auto', nticks=30),
                    yaxis=dict(showgrid=True, zeroline=False, showline=False, showticklabels=True,
                               linecolor='rgb(204, 204, 204)', tickmode='auto', nticks=30),
                    hovermode='closest',
                    margin=dict(t=40, b=0)  # Adjust the top margin to bring the graph closer to the title
                )

            return my_fig
    return no_update

# region Select the input SG raw channel data (in microstrains) and rosette configuration file via dialog boxes
# Initialize the QApplication instance
app_dialog = QApplication(sys.argv)

# File selection for raw strain data
file_path_SG_raw_data, _ = QFileDialog().getOpenFileName(None, 'Open raw data file for SG rosettes',r'"""+solution_directory_path+"""' , 'All Files (*);;CSV Files (*.csv)')

# Check if a file was selected for SG data
if file_path_SG_raw_data:
    print("Selected SG data:", file_path_SG_raw_data)
else:
    print("No raw SG data file selected.")
    # Handle the case when no file is selected, or set file_path to a default value
    # file_path = 'default_raw_SG_data.csv'

# File selection for rosette angles data
angles_file_path, _ = QFileDialog().getOpenFileName(None, 'Open SG rosette angles configuration file', '', 'All Files (*);;CSV Files (*.csv)')

# Check if a file was selected for rosette angles data
if angles_file_path:
    print("Selected rosette angles data:", angles_file_path)
else:
    print("No rosette angles data file selected.")
    # Handle the case when no file is selected, or set angles_file_path to a default value
    # angles_file_path = 'default_angles_data.csv'
# endregion

# region Load the CSV file containing the rosette angles
#angles_file_path = 'rosette_angles_v3.csv'
rosette_angles_df = pd.read_csv(angles_file_path)
print("Selected rosette angles data:", angles_file_path)
# endregion

# region Load the CSV file extracted from raw SG data in microstrains, using "Strain Gage Toolbox" inside ANSYS Mechanical
if file_path_SG_raw_data:
    data = pd.read_csv(file_path_SG_raw_data)
    time = data['Time']
    initial_SG_raw_data = data.iloc[:, 1:].filter(regex='SG')
    initial_SG_raw_data.reset_index(drop=True, inplace=True)
    time.reset_index(drop=True, inplace=True)
else:
    print("The input file is not read. Check whether it is in the correct directory or has the correct file extension")

print("Selected raw data from directory:   ", file_path_SG_raw_data)
initial_SG_raw_data
# endregion

# region Define material properties
input_dialog = MaterialPropertiesDialog()
if input_dialog.exec_() == QDialog.Accepted:
    E = input_dialog.user_input.get('E')
    v = input_dialog.user_input.get('v')

    # Convert to numpy column arrays to get individual E and v at each index (therefore, at each time step) later
    E = (np.full(time.shape, E))
    v = (np.full(time.shape, v))
else:
    sys.exit("Material properties input was canceled or failed.")
# endregion

# region Functions for main calculation loop
def process_sg_number(sg_number, strain_gauge_data, E, v):
    sg_cols = [col for col in strain_gauge_data.columns if f'SG{sg_number}_' in col]
    new_columns = []
    if len(sg_cols) == 3:
        rosette_row = rosette_angles_df[rosette_angles_df['SG'] == sg_number]
        if not rosette_row.empty:
            current_angles = rosette_row.iloc[0, 1:].values
            strains = strain_gauge_data[sg_cols].values.astype(dtype=np.float64)
            theta_A, theta_B, theta_C = np.radians(current_angles)
            
            # Matrix T and its inverse T_inv
            T = np.array([
                [np.cos(theta_A)**2, np.sin(theta_A)**2, np.sin(theta_A) * np.cos(theta_A)],
                [np.cos(theta_B)**2, np.sin(theta_B)**2, np.sin(theta_B) * np.cos(theta_B)],
                [np.cos(theta_C)**2, np.sin(theta_C)**2, np.sin(theta_C) * np.cos(theta_C)]
            ])
            T_inv = np.linalg.inv(T)
            
            # Vectorized global strains transformation
            global_strains = strains @ T_inv.T
            
            # Vectorized principal strains calculation
            # epsilon_x = global_strains[:, 0]
            # epsilon_y = global_strains[:, 1]
            C = (global_strains[:, 0] + global_strains[:, 1]) / 2
            R = np.sqrt(((global_strains[:, 0] - global_strains[:, 1]) / 2)**2 + (global_strains[:, 2] / 2)**2)
            principal_strains = np.stack((C + R, C - R), axis=-1)
            
            # Vectorized principal stresses calculation
            S = np.array([
                [1, v[0]],
                [v[0], 1]
            ]) * E[0] / (1 - v[0]**2)
            principal_stresses = (principal_strains / 1e6) @ S.T / 1e6  # Convert to MPa
            
            # Vectorized principal strain orientation calculation
            # gamma_xy  = global_strains[:, 2]
            # epsilon_x = global_strains[:, 0]
            # epsilon_y = global_strains[:, 1]
            theta_p_rad = 0.5 * np.arctan2(global_strains[:, 2], global_strains[:, 0] - global_strains[:, 1])
            theta_p = np.degrees(theta_p_rad)
            theta_p[theta_p < 0] += 180
            
            # Vectorized biaxiality ratio calculation
            sigma_1 = np.maximum(np.abs(principal_stresses[:, 0]), np.abs(principal_stresses[:, 1]))
            sigma_2 = np.minimum(np.abs(principal_stresses[:, 0]), np.abs(principal_stresses[:, 1]))
            biaxiality_ratios = sigma_2 / sigma_1
            
            # Vectorized von Mises stress calculation
            # S1 = principal_stresses[:, 0]
            # S2 = principal_stresses[:, 1]
            von_mises_stresses = np.sqrt(((principal_stresses[:, 0] - principal_stresses[:, 1])**2 + principal_stresses[:, 0]**2 + principal_stresses[:, 1]**2) / 2)
            
            # Collect results into new columns
            for i, strain_type in enumerate(['epsilon_x [µε]', 'epsilon_y [µε]', 'gamma_xy [µε]']):
                new_columns.append(pd.DataFrame({f'SG{sg_number}_{strain_type}': global_strains[:, i]}))
            new_columns.append(pd.DataFrame({
                f'SG{sg_number}_sigma_1 [MPa]': principal_stresses[:, 0],
                f'SG{sg_number}_sigma_2 [MPa]': principal_stresses[:, 1],
                f'SG{sg_number}_theta_p [°]': theta_p,
                f'SG{sg_number}_Biaxiality_Ratio': biaxiality_ratios,
                f'SG{sg_number}_von_Mises [MPa]': von_mises_stresses
            }))
        else:
            print(f'Angles for Rosette {sg_number} not found in angles file.')
    else:
        print(f'SG Cols: {sg_cols}')
        print(f'Unexpected number of columns for Rosette {sg_number}.')
    return new_columns

def calculate_all_SG_variables(strain_gauge_data, rosette_angles_df):
    # Start the timer
    start_time = time_module.time()
    
    matching_columns = [col for col in strain_gauge_data.columns if re.search(r'SG(\d+)_', col)]
    sg_numbers = sorted(set(int(re.search(r'SG(\d+)_', col).group(1)) for col in matching_columns))

    new_columns_list = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(lambda sg_number: process_sg_number(sg_number, strain_gauge_data, E, v), sg_numbers)
        for result in results:
            new_columns_list.extend(result)

    # Ensure the new columns are correctly concatenated
    if new_columns_list:
        strain_gauge_data = pd.concat([strain_gauge_data] + new_columns_list, axis=1)
    else:
        pass
        #QMessageBox.information(None, "Info", "No new columns generated during SG variable calculation.")

    # End the timer
    end_time = time_module.time()
    
    # Calculate elapsed time in seconds (two significant digits)
    elapsed_time = end_time - start_time
    elapsed_time_formatted = f"{elapsed_time:.2f}"
    
    # Show the completion message with the elapsed time
    QMessageBox.information(None, "Info", f"Calculation is completed in {elapsed_time_formatted} seconds.")
    
    return strain_gauge_data
# endregion

# region Calculate the SG results
if file_path_SG_raw_data:
    output_SG_data_w_raw = calculate_all_SG_variables(initial_SG_raw_data, rosette_angles_df)
    output_SG_data_w_raw.insert(0, 'Time', time)
    output_SG_data_w_raw.set_index('Time', inplace=True)
    output_SG_data_w_raw
# endregion

# region Write the resulting dataframe to a CSV file inside the solution folder
#output_SG_data_w_raw.to_csv(r'""" + file_path_of_SG_calculations + """')
# endregion

# region Show the results
try:
    def find_available_port(port_list):
        for port in port_list:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) != 0:
                    return port
        return None
    
    if __name__ == '__main__':
        app_plot = QApplication(sys.argv)
        
        # The plotly-resampler callback to update the graph after a relayout event (= zoom/pan)
        my_fig.register_update_graph_callback(app=my_dash_app, graph_id="graph-id")
        
        mainWindow = PlotWindow('""" + solution_directory_path + """', '""" + file_name_of_SG_calculations + """')
        mainWindow.show()
        available_port = find_available_port([8050, 8051, 8052, 8053])
        if available_port:
            threading.Thread(target=my_dash_app.run_server, kwargs={'debug': False, 'use_reloader': False, 'port': available_port}, daemon=True).start()
            print('Available Port: ' + str(available_port))
        sys.exit(app_plot.exec_())
        # os.remove(cpython_script_path)
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
# process.StartInfo.CreateNoWindow = True

process.StartInfo.UseShellExecute = True
# Set the command to run the Python interpreter with your script as the argument
process.StartInfo.WindowStyle = ProcessWindowStyle.Minimized
process.StartInfo.FileName = "cmd.exe"  # Use cmd.exe to allow window manipulation
process.StartInfo.Arguments = '/c python "' + cpython_script_path + '"'
# Start the process
process.Start()
# endregion