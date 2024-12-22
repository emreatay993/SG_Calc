import sys
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QFileDialog, QTabWidget, QListWidget, QSplitter, QSizePolicy, QDoubleSpinBox, QMessageBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QGuiApplication
import plotly.graph_objects as go
from scipy.interpolate import interp1d
from tempfile import NamedTemporaryFile

QGuiApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # Enable DPI scaling
QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)    # Use high DPI icons

class MetricsCalculator(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # Main layout
        layout = QVBoxLayout()

        # Dataset Selection for 1st dataset
        dataset1_layout = QHBoxLayout()
        self.dataset1_path = QLineEdit()
        self.dataset1_path.setReadOnly(True)
        self.dataset1_name = QLineEdit()
        browse1_button = QPushButton("...")
        browse1_button.clicked.connect(lambda: self.select_file(self.dataset1_path))

        dataset1_layout.addWidget(QLabel("Select 1st dataset:"))
        dataset1_layout.addWidget(browse1_button)
        dataset1_layout.addWidget(self.dataset1_path)
        dataset1_layout.addWidget(QLabel("Enter Dataset Name"))
        dataset1_layout.addWidget(self.dataset1_name)
        layout.addLayout(dataset1_layout)

        # Dataset Selection for 2nd dataset
        dataset2_layout = QHBoxLayout()
        self.dataset2_path = QLineEdit()
        self.dataset2_path.setReadOnly(True)
        self.dataset2_name = QLineEdit()
        browse2_button = QPushButton("...")
        browse2_button.clicked.connect(lambda: self.select_file(self.dataset2_path))

        dataset2_layout.addWidget(QLabel("Select 2nd dataset:"))
        dataset2_layout.addWidget(browse2_button)
        dataset2_layout.addWidget(self.dataset2_path)
        dataset2_layout.addWidget(QLabel("Enter Dataset Name"))
        dataset2_layout.addWidget(self.dataset2_name)
        layout.addLayout(dataset2_layout)

        # Calculate Button
        calculate_button = QPushButton("Calculate Statistical Metrics")
        calculate_button.clicked.connect(self.calculate_metrics)
        layout.addWidget(calculate_button)

        # Tab Widget for different visualizations
        self.tab_widget = QTabWidget()

        # Tab1: For Plotly visualization
        self.tab1 = QWidget()
        tab1_layout = QVBoxLayout()

        # Time Range Selection
        time_range_layout = QHBoxLayout()
        self.start_time_spinbox = QDoubleSpinBox()
        self.start_time_spinbox.setPrefix("Start Time: ")
        self.start_time_spinbox.setDecimals(3)
        self.start_time_spinbox.setRange(0, 10000)  # Adjust range based on dataset
        self.start_time_spinbox.valueChanged.connect(self.update_plot)

        self.end_time_spinbox = QDoubleSpinBox()
        self.end_time_spinbox.setPrefix("End Time: ")
        self.end_time_spinbox.setDecimals(3)
        self.end_time_spinbox.setRange(0, 10000)  # Adjust range based on dataset
        self.end_time_spinbox.valueChanged.connect(self.update_plot)

        time_range_layout.addWidget(self.start_time_spinbox)
        time_range_layout.addWidget(self.end_time_spinbox)
        tab1_layout.addLayout(time_range_layout)

        # List widget for column selection
        self.column_list_widget = QListWidget()
        self.column_list_widget.setSelectionMode(QListWidget.ExtendedSelection)  # Enable Shift + Control selection
        self.column_list_widget.setMinimumWidth(200)  # Initial minimum width
        self.column_list_widget.itemSelectionChanged.connect(self.update_plot)

        # Splitter to separate list widget and plot area
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.column_list_widget)

        # Plot area
        self.plot_view = QWebEngineView()
        self.plot_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter.addWidget(self.plot_view)

        # Set initial sizes for the splitter
        splitter.setSizes([200, 800])  # Initial widths: 200px for list, 800px for plot

        tab1_layout.addWidget(splitter)
        self.tab1.setLayout(tab1_layout)
        self.tab_widget.addTab(self.tab1, "Tab1")

        # Tab2: Placeholder
        self.tab2 = QWidget()
        self.tab_widget.addTab(self.tab2, "Tab2")

        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
        self.setWindowTitle("Statistical Metrics Calculator")

    def select_file(self, line_edit):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv)")
        if file_path:
            line_edit.setText(file_path)

    def calculate_metrics(self):
        try:
            # Load datasets
            dataset1_path = self.dataset1_path.text()
            dataset2_path = self.dataset2_path.text()
            print(f"Loading files:\nDataset 1: {dataset1_path}\nDataset 2: {dataset2_path}")

            if not dataset1_path or not dataset2_path:
                raise ValueError("Both dataset file paths must be selected!")

            df1 = pd.read_csv(dataset1_path)
            df2 = pd.read_csv(dataset2_path)

            # Validate first column is "Time"
            if df1.columns[0] != "Time" or df2.columns[0] != "Time":
                QMessageBox.critical(self, "Error", "The first column of both datasets must be named 'Time'.")
                return

            # Validate number of columns
            if df1.shape[1] != df2.shape[1]:
                QMessageBox.critical(self, "Error", "The number of columns in the two datasets is different!")
                return

            # Validate column names
            if not all(df1.columns == df2.columns):
                user_choice = QMessageBox.question(
                    self,
                    "Column Name Mismatch",
                    "The column names in the two datasets are different.\n"
                    "Would you like to use column names from the first dataset?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if user_choice == QMessageBox.Yes:
                    column_names = df1.columns
                else:
                    column_names = df2.columns

                # Rename columns in both datasets to match user selection
                df1.columns = column_names
                df2.columns = column_names

            print(f"Dataset 1:\n{df1.head()}")
            print(f"Dataset 2:\n{df2.head()}")

            # Populate the column list widget
            self.column_list_widget.clear()
            for col in df1.columns:
                if col != "Time":  # Exclude "Time" column
                    self.column_list_widget.addItem(col)

            # Interpolate and align datasets
            self.df1_aligned, self.df2_aligned = self.interpolate_and_align(df1, df2)

            # Set time range spinboxes
            self.start_time_spinbox.setRange(self.df1_aligned["Time"].min(), self.df1_aligned["Time"].max())
            self.end_time_spinbox.setRange(self.df1_aligned["Time"].min(), self.df1_aligned["Time"].max())
            self.start_time_spinbox.setValue(self.df1_aligned["Time"].min())
            self.end_time_spinbox.setValue(self.df1_aligned["Time"].max())

            # Initial plot with all columns selected
            self.update_plot()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")
            import traceback
            traceback.print_exc()

    def interpolate_and_align(self, df1, df2):
        """Interpolates and aligns two datasets by time."""
        max_time = min(df1["Time"].max(), df2["Time"].max())
        df1 = df1[df1["Time"] <= max_time]
        df2 = df2[df2["Time"] <= max_time]
        time_dense = df1["Time"].values if len(df1) > len(df2) else df2["Time"].values

        df1_interp = pd.DataFrame({"Time": time_dense})
        df2_interp = pd.DataFrame({"Time": time_dense})

        for col in df1.columns:
            if col != "Time":
                interp_func1 = interp1d(df1["Time"], df1[col], kind="linear", fill_value="extrapolate")
                interp_func2 = interp1d(df2["Time"], df2[col], kind="linear", fill_value="extrapolate")
                df1_interp[col] = interp_func1(time_dense)
                df2_interp[col] = interp_func2(time_dense)

        return df1_interp, df2_interp

    def update_plot(self):
        try:
            # Get selected columns
            selected_items = self.column_list_widget.selectedItems()
            selected_columns = [item.text() for item in selected_items]
            print(f"Selected Columns: {selected_columns}")

            # Filter by time range
            start_time = self.start_time_spinbox.value()
            end_time = self.end_time_spinbox.value()
            print(f"Selected Time Range: {start_time} to {end_time}")

            # Filter datasets by selected time range
            df1_filtered = self.df1_aligned[
                (self.df1_aligned["Time"] >= start_time) & (self.df1_aligned["Time"] <= end_time)
                ]
            df2_filtered = self.df2_aligned[
                (self.df2_aligned["Time"] >= start_time) & (self.df2_aligned["Time"] <= end_time)
                ]

            print(f"Filtered Dataset 1:\n{df1_filtered.head()}")
            print(f"Filtered Dataset 2:\n{df2_filtered.head()}")

            # Filter datasets by selected columns
            df1_filtered = df1_filtered[["Time"] + selected_columns]
            df2_filtered = df2_filtered[["Time"] + selected_columns]

            print(f"Filtered Dataset 1 (with selected columns):\n{df1_filtered.head()}")
            print(f"Filtered Dataset 2 (with selected columns):\n{df2_filtered.head()}")

            # Calculate metrics and update plot
            metrics = self.compare_datasets(df1_filtered, df2_filtered)
            print(f"Metrics:\n{metrics}")

            self.plot_metrics(metrics)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in updating plot: {str(e)}")
            import traceback
            traceback.print_exc()

    def compare_datasets(self, df1, df2):
        metrics = []
        columns = [col for col in df1.columns if col != "Time"]

        for col in columns:
            x = df1[col].values
            y = df2[col].values

            x_normalized = (x - np.mean(x)) / np.std(x)
            y_normalized = (y - np.mean(y)) / np.std(y)
            cross_corr = np.correlate(x_normalized, y_normalized, mode="full") / len(x)
            max_corr = np.max(cross_corr)
            lag_at_max_corr = np.argmax(cross_corr) - (len(x) - 1)

            mse = np.mean((x - y) ** 2)
            rmse = np.sqrt(mse)
            pearson_corr = np.corrcoef(x, y)[0, 1]

            metrics.append({
                "Channel": col,
                "Max Correlation": max_corr,
                "Lag at Max Correlation": lag_at_max_corr,
                "MSE": mse,
                "RMSE": rmse,
                "Pearson Correlation": pearson_corr
            })

        return metrics

    def plot_metrics(self, metrics):
        """Plots the change in metrics for each channel using Plotly."""
        try:
            # Get dataset names or use default values
            dataset1_name = self.dataset1_name.text() if self.dataset1_name.text() else "Test1"
            dataset2_name = self.dataset2_name.text() if self.dataset2_name.text() else "Test2"

            # Title with dataset names
            plot_title = f"Statistical Metrics - {dataset1_name} vs {dataset2_name}"

            # Dynamically determine scale factor based on DPI
            screen = QGuiApplication.primaryScreen()
            dpi = screen.logicalDotsPerInch()  # Get DPI of the primary screen
            scale_factor = dpi / 96  # Base DPI is 96 (standard)

            # Adjust font sizes using scale factor
            base_font_size = 10  # Base font size for 96 DPI
            title_font_size = int(base_font_size * 1.2 * scale_factor)
            axis_label_font_size = int(base_font_size * scale_factor)
            tick_font_size = int(base_font_size * 0.9 * scale_factor)
            legend_font_size = int(base_font_size * scale_factor)

            # Prepare metrics
            channels = [res["Channel"] for res in metrics]
            max_corr = [res["Max Correlation"] for res in metrics]
            lag_at_max_corr = [res["Lag at Max Correlation"] for res in metrics]
            mse = [res["MSE"] for res in metrics]
            rmse = [res["RMSE"] for res in metrics]
            pearson_corr = [res["Pearson Correlation"] for res in metrics]

            # Create the figure
            fig = go.Figure()
            fig.add_trace(go.Bar(x=channels, y=max_corr, name="Max Correlation"))
            fig.add_trace(go.Scatter(
                x=channels,
                y=lag_at_max_corr,
                name="Lag at Max Correlation",
                mode="lines+markers"
            ))
            fig.add_trace(go.Scatter(
                x=channels,
                y=mse,
                name="MSE",
                mode="lines+markers"
            ))
            fig.add_trace(go.Scatter(
                x=channels,
                y=rmse,
                name="RMSE",
                mode="lines+markers"
            ))
            fig.add_trace(go.Bar(
                x=channels,
                y=pearson_corr,
                name="Pearson Correlation",
                marker_color="purple"
            ))

            # Update layout with centered title and scaled fonts
            fig.update_layout(
                title=dict(
                    text=plot_title,
                    font=dict(size=title_font_size),
                    x=0.5,  # Center the title
                    xanchor='center',
                    yanchor='top'
                ),
                xaxis=dict(
                    title=dict(
                        text="Channel",
                        font=dict(size=axis_label_font_size)
                    ),
                    tickfont=dict(size=tick_font_size)
                ),
                yaxis=dict(
                    title=dict(
                        text="Metric Value",
                        font=dict(size=axis_label_font_size)
                    ),
                    tickfont=dict(size=tick_font_size)
                ),
                legend=dict(
                    font=dict(size=legend_font_size)
                ),
                barmode="group",
                template="plotly_white",
                autosize=True
            )

            # Save HTML to a temporary file
            with NamedTemporaryFile(delete=False, suffix=".html") as temp_file:
                fig.write_html(temp_file.name)
                temp_html_path = temp_file.name

            # Load the HTML file into QWebEngineView
            self.plot_view.setUrl(QUrl.fromLocalFile(temp_html_path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in plotting metrics: {str(e)}")
            import traceback
            traceback.print_exc()


# Run the application
app = QApplication(sys.argv)
window = MetricsCalculator()
window.show()
sys.exit(app.exec_())
