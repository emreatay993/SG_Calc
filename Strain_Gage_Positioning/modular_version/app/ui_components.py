# File: app/ui_components.py

import numpy as np
from PyQt5.QtWidgets import (QGroupBox, QVBoxLayout, QGridLayout, QLabel,
                             QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
                             QWidget)
from PyQt5.QtCore import Qt, pyqtSignal
from . import tooltips as tips


class ControlPanel(QGroupBox):
    """
    A widget containing all user controls for the analysis. This class is part of the
    "View" in the MVC pattern. It emits signals when user actions occur.
    """
    # Signal emitted when the user clicks the "Update" / "Run" button.
    analysis_requested = pyqtSignal(bool)  # bool indicates if it's a continued K-Means run

    # Signal emitted when the user clicks "Load Strain Data".
    file_load_requested = pyqtSignal()

    # Signal emitted when the display unit (strain/microstrain) changes.
    display_mode_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__("Positioning Controls", parent)
        self.setFixedWidth(280)
        self.setStyleSheet("""
            QGroupBox { 
                border: 1px solid #87CEFA; 
                border-radius: 5px; 
                margin-top: 10px; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                subcontrol-position: top left;
                left: 10px; 
                padding: 0 5px; 
                background-color: palette(window);
                color: #3F94D1; 
                font-weight: bold; 
            }
        """)

        self._setup_widgets()
        self._setup_layout()
        self._apply_tooltips()
        self._connect_signals()
        self._update_strategy_controls()

    def _setup_widgets(self):
        """Creates all the control widgets."""
        self.btn_load = QPushButton("Load Strain Data")
        self.lbl_file = QLabel("No file loaded")
        self.lbl_file.setWordWrap(True)

        self.combo_measurement = QComboBox()
        self.combo_measurement.addItems(["Rosette", "Uniaxial"])

        self.combo_strategy = QComboBox()
        self.combo_strategy.addItems([
            "Max Quality (Greedy Search)",
            "Max Coverage (K-Means)",
            "Quality-Filtered K-Means",
            "Greedy Gradient Search",
            "Region of Interest (ROI) Search"
        ])

        self.combo_quality = QComboBox()
        self.combo_quality.addItems([
            "Signal-Noise Ratio: |ε|/(σ+1e-12)",
            "Default: |ε|/(1+σ)",
            "Squared: |ε|/(1+σ²)",
            "Exponential: |ε|·exp(–1000σ)"
        ])

        self.combo_agg = QComboBox()
        self.combo_agg.addItems(["Max", "Average"])

        self.spin_candidate_count = QSpinBox()
        self.spin_candidate_count.setRange(1, 1000)
        self.spin_candidate_count.setValue(10)

        self.dspin_uniformity_radius = QDoubleSpinBox()
        self.dspin_uniformity_radius.setRange(0.1, 1000)
        self.dspin_uniformity_radius.setValue(10.0)
        self.dspin_uniformity_radius.setSingleStep(0.5)

        # --- Strategy-specific controls ---
        self.lbl_min_distance = QLabel("Min Distance [mm]:")
        self.dspin_min_distance = QDoubleSpinBox()
        self.dspin_min_distance.setRange(0, 10000)
        self.dspin_min_distance.setValue(10.0)

        self.lbl_quality_percentile = QLabel("Quality Filter [%ile]:")
        self.dspin_quality_percentile = QDoubleSpinBox()
        self.dspin_quality_percentile.setRange(0.0, 100.0)
        self.dspin_quality_percentile.setValue(75.0)

        # --- ROI Group Box ---
        self.roiGroup = QGroupBox("Region of Interest (Sphere)")
        roi_layout = QGridLayout(self.roiGroup)
        self.dspin_roi_x = QDoubleSpinBox();
        self.dspin_roi_x.setRange(-1e6, 1e6)
        self.dspin_roi_y = QDoubleSpinBox();
        self.dspin_roi_y.setRange(-1e6, 1e6)
        self.dspin_roi_z = QDoubleSpinBox();
        self.dspin_roi_z.setRange(-1e6, 1e6)
        self.dspin_roi_radius = QDoubleSpinBox();
        self.dspin_roi_radius.setRange(0, 1e6);
        self.dspin_roi_radius.setValue(50.0)

        roi_layout.addWidget(QLabel("Center X:"), 0, 0);
        roi_layout.addWidget(self.dspin_roi_x, 0, 1)
        roi_layout.addWidget(QLabel("Center Y:"), 1, 0);
        roi_layout.addWidget(self.dspin_roi_y, 1, 1)
        roi_layout.addWidget(QLabel("Center Z:"), 2, 0);
        roi_layout.addWidget(self.dspin_roi_z, 2, 1)
        roi_layout.addWidget(QLabel("Radius:"), 3, 0);
        roi_layout.addWidget(self.dspin_roi_radius, 3, 1)

        self.btn_update = QPushButton("Run Analysis")

    def _setup_layout(self):
        """Lays out all the control widgets."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)

        widgets_map = [
            (None, self.btn_load),
            (None, self.lbl_file),
            ("Measurement Mode:", self.combo_measurement),
            ("Selection Strategy:", self.combo_strategy),
            ("Quality Metrics Mode:", self.combo_quality),
            ("Aggregation (Multi-Load Case):", self.combo_agg),
            ("Candidate Points Requested:", self.spin_candidate_count),
            ("Uniformity Search Radius [mm]:", self.dspin_uniformity_radius),
            (self.lbl_min_distance, self.dspin_min_distance),
            (self.lbl_quality_percentile, self.dspin_quality_percentile),
            (None, self.roiGroup)
        ]

        for label, widget in widgets_map:
            if label:
                if isinstance(label, str):
                    main_layout.addWidget(QLabel(label))
                else:  # It's already a widget
                    main_layout.addWidget(label)
            main_layout.addWidget(widget)

        main_layout.addStretch(1)
        main_layout.addWidget(self.btn_update)

    def _apply_tooltips(self):
        """Applies all tooltips to the widgets in this panel."""
        self.btn_load.setToolTip(tips.LOAD_STRAIN_DATA)
        self.lbl_file.setToolTip(tips.FILE_LABEL)
        self.btn_update.setToolTip(tips.RUN_ANALYSIS)

        # Core Settings
        self.combo_measurement.setToolTip(tips.MEASUREMENT_MODE)
        self.spin_candidate_count.setToolTip(tips.CANDIDATE_COUNT)
        self.dspin_uniformity_radius.setToolTip(tips.UNIFORMITY_RADIUS)

        # Quality Metrics
        self.combo_quality.setToolTip(tips.QUALITY_MODE)

        # Aggregation Method (with dynamic item tooltips)
        self.combo_agg.setToolTip(tips.AGGREGATION_METHOD)
        agg_map = {
            "Max": tips.AGGREGATION_MAX,
            "Average": tips.AGGREGATION_AVERAGE,
        }
        for i, (text, tooltip) in enumerate(agg_map.items()):
            self.combo_agg.setItemData(i, tooltip, Qt.ToolTipRole)

        # Selection Strategy (with dynamic item tooltips)
        self.combo_strategy.setToolTip(tips.SELECTION_STRATEGY)
        strategy_map = {
            "Max Quality (Greedy Search)": tips.STRATEGY_QUALITY_GREEDY,
            "Max Coverage (K-Means)": tips.STRATEGY_KMEANS,
            "Quality-Filtered K-Means": tips.STRATEGY_FILTERED_KMEANS,
            "Greedy Gradient Search": tips.STRATEGY_GRADIENT_GREEDY,
            "Region of Interest (ROI) Search": tips.STRATEGY_ROI,
        }
        for i, (text, tooltip) in enumerate(strategy_map.items()):
            self.combo_strategy.setItemData(i, tooltip, Qt.ToolTipRole)

        # Strategy-Specific Parameters
        self.dspin_min_distance.setToolTip(tips.MIN_DISTANCE)
        self.dspin_quality_percentile.setToolTip(tips.QUALITY_PERCENTILE)
        self.roiGroup.setToolTip(tips.ROI_GROUP)

    def _connect_signals(self):
        """Connects widget signals to this panel's internal logic or output signals."""
        self.btn_load.clicked.connect(self.file_load_requested.emit)
        self.btn_update.clicked.connect(self._on_update_clicked)
        self.combo_strategy.currentTextChanged.connect(self._update_strategy_controls)

    def _on_update_clicked(self):
        """Determines if the analysis is a continuation of K-Means."""
        is_continuation = "Continue" in self.btn_update.text()
        self.analysis_requested.emit(is_continuation)

    def _update_strategy_controls(self):
        """Shows or hides GUI controls based on the selected strategy."""
        strategy = self.combo_strategy.currentText()
        is_greedy = "Greedy" in strategy or "ROI" in strategy
        is_roi = "ROI" in strategy
        is_filtered_kmeans = "Filtered" in strategy

        self.lbl_min_distance.setVisible(is_greedy)
        self.dspin_min_distance.setVisible(is_greedy)
        self.lbl_quality_percentile.setVisible(is_filtered_kmeans)
        self.dspin_quality_percentile.setVisible(is_filtered_kmeans)
        self.roiGroup.setVisible(is_roi)

        # Reset button text if strategy changes away from K-Means preview
        if "K-Means" not in strategy and "Continue" in self.btn_update.text():
            self.set_button_state_ready()

    def get_parameters(self):
        """Gathers all settings from the UI widgets into a dictionary."""
        return {
            "measurement_mode": self.combo_measurement.currentText(),
            "quality_mode": self.combo_quality.currentText(),
            "agg_method": self.combo_agg.currentText(),
            "uniformity_radius": self.dspin_uniformity_radius.value(),
            "strategy": self.combo_strategy.currentText(),
            "candidate_count": self.spin_candidate_count.value(),
            "min_distance": self.dspin_min_distance.value(),
            "quality_percentile": self.dspin_quality_percentile.value(),
            "roi_center": np.array([
                self.dspin_roi_x.value(),
                self.dspin_roi_y.value(),
                self.dspin_roi_z.value()
            ]),
            "roi_radius": self.dspin_roi_radius.value()
        }

    def set_file_label(self, text):
        """Public method to allow MainWindow to update the file label."""
        self.lbl_file.setText(text)

    def set_button_state_running(self):
        """Sets the update button to a 'running' state."""
        self.btn_update.setText("Running...")
        self.btn_update.setEnabled(False)

    def set_button_state_ready(self):
        """Sets the update button to a normal, ready state."""
        self.btn_update.setText("Run Analysis")
        self.btn_update.setEnabled(True)

    def set_button_state_kmeans_continue(self):
        """Sets the update button to the 'continue' state for K-Means."""
        self.btn_update.setText("Continue with K-Means")
        self.btn_update.setEnabled(True)