# region Import libraries
import csv
import context_menu
import clr
clr.AddReference('mscorlib')  # Ensure the core .NET assembly is referenced
from System.IO import StreamWriter, FileStream, FileMode, FileAccess
from System.Text import UTF8Encoding
import subprocess
import os
# endregion

# region Define the plot function to be run
solution_directory_path = sol_selected_environment.WorkingDir[:-1]
solution_directory_path = solution_directory_path.Replace("\\", "\\\\")
file_name = 'SG_FEA_microstrain_data.csv'

cpython_code = """
import sys
import os
import re
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView

try:
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.offline import plot
except ImportError as e:
    app = QApplication(sys.argv)
    QMessageBox.critical(None, "Import Error", f"Failed to import a required module: {str(e)}")
    sys.exit(1)

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
        self.setWindowTitle("Plot SG Channels (FEA)")
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
    
        data_long = data.melt(id_vars='Time', var_name='Gauge Channel', value_name='µe')
    
        # Apply the sorting key extraction function and sort
        data_long['SortKey'] = data_long['Gauge Channel'].apply(self.extract_sort_key)
        data_long_sorted = data_long.sort_values(by='SortKey')
    
        fig = go.Figure()
        for label, df in data_long.groupby('Gauge Channel', sort = False):
            hover_text = df.apply(lambda row: f'Gauge Channel={label}<br>Time={row["Time"]} s<br>µe={row["µe"]}', axis=1)
            fig.add_trace(go.Scatter(
                x=df['Time'], 
                y=df['µe'], 
                mode='lines', 
                name=label,
                hoverinfo='text',
                text=hover_text,
                hoverlabel = dict(
                    font_size = 10,
                    bgcolor='rgba(255, 255, 255, 0.5)')
            ))

        fig.update_layout(
            title_text='SG Channel Results (FEA)',
            title_x=0.5,  # Center the title
            legend_title_text='Gauge Channel',
            template="plotly_white",
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title='Time',
            yaxis_title='µe',
            
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
        plot(fig, filename=os.path.join(self.folder_name, "SG_FEA_plot.html"), auto_open=False) 
        self.viewer = PlotlyViewer(fig)
        
        layout = QVBoxLayout()
        layout.addWidget(self.viewer)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # Enable high-DPI scaling
    app = QApplication(sys.argv)
    mainWindow = PlotWindow('""" + solution_directory_path + """', '""" + file_name + """')
    mainWindow.show()
    sys.exit(app.exec_())
"""

cpython_script_name = "plot_SG_channels_FEA_cpython_code_only.py"
cpython_script_path = sol_selected_environment.WorkingDir + cpython_script_name

# Use StreamWriter with FileStream to write the file with UTF-8 encoding
with StreamWriter(FileStream(cpython_script_path, FileMode.Create, FileAccess.Write), UTF8Encoding(True)) as writer:
    writer.Write(cpython_code)

print("Python file created successfully with UTF-8 encoding.")
# endregion

# region Use subprocess to run the script
subprocess.call(['python', cpython_script_path])
# Delete the cpython script from the solution directory
os.remove(cpython_script_path)
# endregion