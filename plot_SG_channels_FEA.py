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
folder_path = sol_selected_environment.WorkingDir[:-1]
folder_path = folder_path.Replace("\\", "\\\\")
file_name = 'SG_FEA_microstrain_data.csv'

cpython_code = """
import sys
import os
import pandas as pd
import plotly.graph_objects as go
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from plotly.offline import plot

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
        self.setWindowTitle("SG Channels (FEA)")
        self.setGeometry(100, 100, 800, 600)
        self.folder_name = folder_name
        self.file_name = file_name
        self.initUI()

    def initUI(self):
        file_path = os.path.join(self.folder_name, self.file_name)
        data = pd.read_csv(file_path)
        data_long = data.melt(id_vars='Time', var_name='Gauge Channel', value_name='µe')

        fig = go.Figure()
        for label, df in data_long.groupby('Gauge Channel'):
            fig.add_trace(go.Scatter(
                x=df['Time'], 
                y=df['µe'], 
                mode='lines', 
                name=label,
                hoverinfo='text',
                text=df.apply(lambda row: f'Gauge Channel={label}<br>Time={row["Time"]} s<br>µe={row["µe"]}', axis=1)
            ))

        # Set layout options
        fig.update_layout(
            title_text='SG Channels (FEA)',
            xaxis_title='Time',
            yaxis_title='µe',
        )

        self.viewer = PlotlyViewer(fig)
        
        layout = QVBoxLayout()
        layout.addWidget(self.viewer)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    mainWindow = PlotWindow('""" + folder_path + """', '""" + file_name + """')
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
# endregion
