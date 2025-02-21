import time
import os
import pandas as pd
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QHBoxLayout, QFileDialog, QPushButton
from PyQt5.QtCore import QTimer
from datetime import datetime
from PyAttoDRY import AttoDRY  # Ensure AttoDRY is properly imported
import sys
# Base directory for log storage
BASE_LOG_DIR = r"C:\Users\attocube\Desktop\Python Instrumentation Control\Log Files"

# Global variables for logging
log_file = None
log_start_time = None
log_initialized = False
live_plotter = None  # Live plotter instance

class LogPlotter(QMainWindow):
    """Live plot window that updates periodically using QTimer."""

    def __init__(self, log_file):
        super().__init__()
        self.setWindowTitle("Live Log Plot")
        self.setGeometry(100, 100, 1200, 800)
        self.log_file = log_file

        # Create main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout()

        # Dropdowns and plots layout
        control_layout = QHBoxLayout()
        plot_layout = QHBoxLayout()

        self.plots = []
        self.y_selectors = []

        for _ in range(4):
            # Create plot widget
            plot_widget = pg.PlotWidget()
            plot_widget.setLabel("bottom", "Time (s)")
            plot_layout.addWidget(plot_widget)
            self.plots.append(plot_widget)

            # Create dropdown for Y-axis selection
            y_selector = QComboBox()
            y_selector.currentIndexChanged.connect(self.update_plot)  # Update plot on selection change
            control_layout.addWidget(y_selector)
            self.y_selectors.append(y_selector)

        main_layout.addLayout(control_layout)
        main_layout.addLayout(plot_layout)
        self.central_widget.setLayout(main_layout)

        self.df = None  # Store log data

        # Start QTimer to update plots every 2 seconds
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(2000)  # Update every 2 seconds

        self.load_available_columns()

    def load_available_columns(self):
        """Reads log file headers and populates dropdown menus."""
        if not os.path.exists(self.log_file):
            return

        # Read headers only
        df = pd.read_csv(self.log_file, sep="\t", nrows=1)
        numeric_columns = [col for col in df.columns if col not in ["Error Status", "Action Message", "Time"]]

        for selector in self.y_selectors:
            selector.clear()
            selector.addItems(numeric_columns)
            if numeric_columns:
                selector.setCurrentIndex(0)  # Default to the first column

    def update_plot(self):
        """Reads log data and updates all four plots."""
        if not os.path.exists(self.log_file):
            return

        # Read latest data
        self.df = pd.read_csv(self.log_file, sep="\t")

        if "Time" not in self.df.columns:
            return

        for i, plot_widget in enumerate(self.plots):
            y_column = self.y_selectors[i].currentText()
            if y_column in self.df.columns:
                plot_widget.clear()
                plot_widget.plot(self.df["Time"], self.df[y_column], pen="r", symbol='o')
                plot_widget.setLabel("left", y_column)
                plot_widget.setTitle(f"{y_column} vs. Time")
def get_unique_log_filename(log_folder, base_name):
    """
    Checks for existing log files and appends a number to avoid overwriting.
    """
    base_path = os.path.join(log_folder, base_name)
    log_file = f"{base_path}.txt"
    counter = 2

    # Check if file already exists, and if so, append a number
    while os.path.exists(log_file):
        log_file = f"{base_path}{counter:02d}.txt"
        counter += 1

    return log_file

            
def Log(optional_description="", LivePlot=True):
    """
    Logs data to a text file and updates the live plot (if enabled).
    
    - `LivePlot=True` updates the live plot.
    - `LivePlot=False` skips live plotting.
    """
    global log_file, log_start_time, log_initialized, live_plotter

    headers = [
        "Time", "Temperature Setpoint", "Sample Temperature", "VTI Temperature",
        "Reservoir Temperature", "Sample Heater Power", "VTI Heater Power",
        "Reservoir Heater Power", "Magnet Temperature", "Magnetic Field",
        "Dump Pressure", "Cryostat In Pressure", "Cryostat Out Pressure",
        "Action Message", "Error Status"
    ]

    # Get current date info
    now = datetime.now()
    month_year = now.strftime("%B %Y")  # e.g., "May 2025"
    date_str = now.strftime("%d-%m-%y")  # e.g., "19-02-25"

    # Define log folder path
    log_folder = os.path.join(BASE_LOG_DIR, month_year)
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)

    # Ensure log_file is retained after initialization
    if log_file is None:  # Only set log_file if it hasn't been set already
        base_log_name = f"Log_File-{date_str}"
        if optional_description:
            base_log_name += f"_{optional_description}"

        log_file = get_unique_log_filename(log_folder, base_log_name)

    # Initialization step
    if not log_initialized:
        log_start_time = time.time()
        df = pd.DataFrame(columns=headers)
        df.to_csv(log_file, sep='\t', index=False)  # Create and store headers
        log_initialized = True
        print(f"Initialized log file: {log_file}")

        # Start live plotter (if enabled)
        if LivePlot:
            app = QApplication.instance() or QApplication([])
            global live_plotter
            live_plotter = LogPlotter(log_file)
            live_plotter.show()


    # Collect current values from AttoDRY
    current_data = {
        "Time": round(time.time() - log_start_time, 2),
        "Temperature Setpoint": AttoDRY.getUserTemperature(),
        "Sample Temperature": AttoDRY.getSampleTemperature(),
        "VTI Temperature": AttoDRY.getVtiTemperature(),
        "Reservoir Temperature": AttoDRY.getReservoirTemperature(),
        "Sample Heater Power": AttoDRY.getSampleHeaterPower(),
        "VTI Heater Power": AttoDRY.getVtiHeaterPower(),
        "Reservoir Heater Power": AttoDRY.getReservoirHeaterPower(),
        "Magnet Temperature": AttoDRY.get40KStageTemperature(),
        "Magnetic Field": AttoDRY.getMagneticField(),
        "Dump Pressure": AttoDRY.getDumpPressure(),
        "Cryostat In Pressure": AttoDRY.getCryostatInPressure(),
        "Cryostat Out Pressure": AttoDRY.getCryostatOutPressure(),
        "Action Message": AttoDRY.getActionMessage(),
        "Error Status": AttoDRY.getAttodryErrorStatus()
    }

    # Append data to the correct log file
    df = pd.DataFrame([current_data])
    df.to_csv(log_file, sep='\t', mode='a', header=False, index=False)

    # Update live plot (if enabled)
    if LivePlot and live_plotter:
        live_plotter.update_plot()


def PlotOldLog():
    """
    Opens a file dialog to select an old log file and plots it.
    """
    app = QApplication.instance() or QApplication([])
    
    # Open file dialog
    file_dialog = QFileDialog()
    log_file, _ = file_dialog.getOpenFileName(None, "Select Log File", BASE_LOG_DIR, "Text Files (*.txt)")

    if not log_file:
        print("No log file selected.")
        return

    print(f"Selected log file: {log_file}")

    # Start the plotter
    plotter = LogPlotter()
    plotter.initialize(log_file)
    plotter.show()
    app.exec_()

def StartWhenCold_and_Logger(target_script):
    """
    Monitors cooldown process and executes `target_script` once cooldown is complete.
    Calls `Log("Cooldown")` every 5 seconds during cooldown monitoring.
    """
    print("Monitoring cooldown process...")

    while AttoDRY.isGoingToBaseTemperature():
        Log(optional_description="Cooldown")
        time.sleep(5)  # Wait before checking again

    print(f"Cooldown complete. Executing {target_script}...")
    exec(open(target_script).read())
    
def is_temperature_stable(setpoint, settling_time, temp_tolerance):
    """
    Checks if the sample temperature remains within temp_tolerance of setpoint for settling_time seconds.
    """
    start_time = time.time()
    while time.time() - start_time < settling_time:
        current_temp = AttoDRY.getSampleTemperature()
        if abs(current_temp - setpoint) > temp_tolerance:
            start_time = time.time()  # Reset timer if temperature drifts
        time.sleep(1)
        Log(optional_description="RampingtoTempSetpoint")
        if round(time.time())%1000 == 0:
            print("Current Temperature is", current_temp)
    return True

def connect():
    print('Connecting to the AttoDRY...')
    AttoDRY.begin(setup_version=1)
    AttoDRY.Connect(COMPort='COM4')

    time.sleep(10)

    IN = AttoDRY.isDeviceInitialised()
    CN = AttoDRY.isDeviceConnected()

    if IN == 1 and CN == 1:
        print('The AttoDRY device is initialized and connected')
    else:
        print('Something went wrong.')
def cleanup():
    AttoDRY.Disconnect()
    time.sleep(2)
    AttoDRY.end()
    print("Disconnected.")

    # Forcefully terminate the process
    os.system("taskkill /IM python.exe /F")
    sys.exit()