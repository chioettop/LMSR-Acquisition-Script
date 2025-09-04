import sys
import threading
import numpy as np
from PySide6 import QtWidgets, QtCore, QtGui 
import pyqtgraph as pg

from stellarnet_driverLibs import stellarnet_driver3 as sn

class sn_spectrometer_reader(QtCore.QObject):
    
    data_ready = QtCore.Signal(np.ndarray)
    
    def __init__(self, int_time=100, scansavg=1, smooth=0, xtiming=3):
        super().__init__()
        self.running = True

        self.sn_version = sn.version()
        self.int_time = int_time
        self.scansavg = scansavg
        self.smooth = smooth
        self.xtiming = xtiming

        # init Spectrometer - Get BOTH spectrometer and wavelength
        self.spectrometer = sn.array_get_spec_only(0) # 0 for first channel and 1 for second channel , up to 127 spectrometers
        self.wl = sn.getSpectrum_X(self.spectrometer) 
        sn.ext_trig(self.spectrometer, True)

        # Get device ID
        self.deviceID = sn.getDeviceId(self.spectrometer)

        # Call to Enable or Disable External Trigger to by default is Disbale=False -> with timeout
        # Enable or Disable Ext Trigger by Passing True or False, If pass True than Timeout function will be disable, so user can also use this function as timeout enable/disbale 
        #sn.ext_trig(self.spectrometer, True)

        # Only call this function on first call to get spectrum or when you want to change device setting.
        # -- Set last parameter to 'True' throw away the first spectrum data because the data may not be true for its inttime after the update.
        # -- Set to 'False' if you don't want to do another capture to throw away the first data, however your next spectrum data might not be valid.
        sn.setParam(self.spectrometer, self.int_time, self.scansavg, self.smooth, self.xtiming, True) 

        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()        

    def currentParam(self):
        return sn.getDeviceParam(self.spectrometer)

    def getSpectrum(self):
        return sn.getSpectrum_Y(self.spectrometer)
        
    def run(self):
        while self.running:
            spectrum = self.getSpectrum()
            self.data_ready.emit(spectrum)

    def stop(self):
        self.running = False
        self.thread.join()
        sn.reset(self.spectrometer)
    
    def setParam(self, int_time=100, scansavg=1, smooth=0, xtiming=3):
        self.int_time = int_time
        self.scansavg = scansavg
        self.smooth = smooth
        self.xtiming = xtiming

        sn.setParam(self.spectrometer, self.int_time, self.scansavg, self.smooth, self.xtiming, True)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, spectrometer):
        """Initialize the main window, plots, and controls."""
        super(MainWindow, self).__init__()

        self.setWindowTitle("Specular Reflectivity Measurement Setup")

        self.sn = spectrometer

        self.operations = ['Dark D1', 'Direct 1', 'Dark R', 'Reflected', 'Dark D2', 'Direct 2']
        self.next_op = 0

        # --- Main Layout ---
        # Create a central widget and a main horizontal layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QHBoxLayout(central_widget) # Horizontal layout

        # --- Plot Area (Left Side) ---
        # Create a GraphicsLayoutWidget - this is the main widget for arranging plots
        self.graphWidget = pg.GraphicsLayoutWidget()  # live spectrogram
        main_layout.addWidget(self.graphWidget, 1) # Add graph widget, stretch factor 1
        self.reflWidget = pg.GraphicsLayoutWidget()  # refl. meas.
        main_layout.addWidget(self.reflWidget, 1)
        
        # --- Control Panel (Right Side) ---
        control_panel_widget = QtWidgets.QWidget()
        control_layout = QtWidgets.QVBoxLayout(control_panel_widget) # Vertical layout for controls
        control_panel_widget.setMaximumWidth(200) # Set a max width for the control panel
        main_layout.addWidget(control_panel_widget, 0) # Add control panel, stretch factor 0

        # --- Plot 1: Live Spectrogram ---
        # Add the first plot to the layout in the graph widget
        self.p1 = self.graphWidget.addPlot(row=0, col=0, title="Live Spectrogram")
        self.p1.showGrid(x=True, y=True) # Add grid lines
        self.p1.setLabel('left', 'Counts')
        self.p1.setLabel('bottom', 'Wavelength (nm)')
        self.p1.addLegend()
        self.p1.setXRange(550, 1000)

        # Get live spectrum
        self.x = self.sn.wl
        self.dark = np.zeros_like(self.x)  # start with an empty dark
        self.spectrum = np.zeros_like(self.x)

        # Plot the static data with a blue pen
        self.liveview = self.p1.plot(self.x, self.spectrum, pen=pg.mkPen('w', width=1)) # 'b' for blue

        # --- Plot 2: Reflectivity ---
        # Add the second plot besides the first one in the graph widget
        self.p2 = self.reflWidget.addPlot(row=0, col=1, title="Reflectivity")
        self.p2.showGrid(x=True, y=True)
        self.p2.setLabel('left', 'Reflectivity')
        self.p2.setLabel('bottom', 'Wavelength (nm)')
        self.reflectivity = np.zeros_like(self.x)
        self.reflectivity_plot = self.p2.plot(self.x, self.reflectivity, pen=pg.mkPen('gold', width=1))
        self.p2.setXRange(550, 1000)
        self.p2.setYRange(0, 1)

        # --- Controls ---
        # Integrated signal label
        self.avg_sig_label = QtWidgets.QLabel("Avg. signal:")
        control_layout.addWidget(self.avg_sig_label)
        self.avg_sig_value = QtWidgets.QLabel("0")  # Placeholder for integrated signal
        control_layout.addWidget(self.avg_sig_value)

        control_layout.addWidget(QtWidgets.QLabel(""))  # spacer

        # Label for interval input
        int_t_label = QtWidgets.QLabel("Int. time (ms):")
        control_layout.addWidget(int_t_label)

        # Input field for interval
        self.int_t_input = QtWidgets.QLineEdit(str(self.sn.int_time)) # Default value 100ms
        # Set validator to only accept integers
        self.int_t_input.setValidator(QtGui.QIntValidator(1, 10000)) # Min 1ms, Max 10s
        control_layout.addWidget(self.int_t_input)

        # averaging
        avg_label = QtWidgets.QLabel("Averaging:")
        control_layout.addWidget(avg_label)

        # Input field for averaging
        self.avg_input = QtWidgets.QLineEdit(str(self.sn.scansavg)) # Default value 100ms
        # Set validator to only accept integers
        self.avg_input.setValidator(QtGui.QIntValidator(1, 10000)) # Min 1ms, Max 10s
        control_layout.addWidget(self.avg_input)

        # Button to apply the new params
        self.update_button = QtWidgets.QPushButton("Apply")
        self.update_button.clicked.connect(self.set_params) # Connect button click
        control_layout.addWidget(self.update_button)

        control_layout.addWidget(QtWidgets.QLabel(""))

        # next operation to perform
        self.next_op_label = QtWidgets.QLabel("Next: "+self.operations[self.next_op])
        control_layout.addWidget(self.next_op_label)

        # Get a measurement/dark
        self.meas_button = QtWidgets.QPushButton("Measure")
        self.meas_button.setMinimumHeight(40)
        #self.meas_button.setMinimumWidth(120)
        font = self.meas_button.font()
        font.setPointSize(12)
        font.setBold(True)
        self.meas_button.setFont(font)
        self.meas_button.clicked.connect(self.take_measurement)
        control_layout.addWidget(self.meas_button)

        self.measurements = {}  # Store measurements
        self.saved_plot = {}  # Store live plots for each measurement
        for label, color in zip(['Direct 1', 'Reflected', 'Direct 2'], ('blue', 'red', 'green')):
            self.saved_plot[label] = self.p1.plot(self.x, self.spectrum, pen=pg.mkPen(color, width=1), name=label)

        control_layout.addWidget(QtWidgets.QLabel(""))  # spacer

        # Save measurement
        self.save_button = QtWidgets.QPushButton("Save")
        self.save_button.clicked.connect(self.save_measurement) # Connect button click
        control_layout.addWidget(self.save_button)

        # Clear
        self.clear_button = QtWidgets.QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_measurement) # Connect button click
        control_layout.addWidget(self.clear_button)

        # Add a spacer to push controls to the top
        control_layout.addStretch(1)

        self.sn.data_ready.connect(self.get_spectrum)

    def get_spectrum(self, spectrum):
        self.spectrum = spectrum.copy()

        # Update the plot data
        self.liveview.setData(self.sn.wl, self.spectrum - self.dark)

        # Update the integrated signal value
        avg_signal = np.average(self.spectrum)
        self.avg_sig_value.setText(f"{avg_signal:.1f}")

    def op_inc(self):
        self.next_op = self.next_op + 1 if self.next_op < len(self.operations)-1 else 0
        self.next_op_label.setText("Next: "+self.operations[self.next_op])

    def take_measurement(self):   # take a measurement or dark
        meas = self.operations[self.next_op]
        self.measurements[meas] = self.spectrum.copy()  # take the currently displayed spectrum
        if meas.startswith('Dark'):
            self.dark = self.spectrum.copy()  # save the current spectrum as dark
        else:
            self.saved_plot[meas].setData(self.x, self.spectrum - self.dark)

            if meas=='Direct 2':
                reflected = self.measurements['Reflected'] - self.measurements['Dark R']
                direct1 = self.measurements['Direct 1'] - self.measurements['Dark D1']
                direct2 = self.measurements['Direct 2'] - self.measurements['Dark D2']
                self.reflectivity = reflected / ((direct1 + direct2) / 2)
                self.reflectivity_plot.setData(self.x, self.reflectivity)
        
        self.op_inc()
        
    def set_params(self):
        new_int_t = int(self.int_t_input.text())
        new_avg = int(self.avg_input.text())
        self.sn.setParam(int_time=new_int_t, scansavg=new_avg)
        print(f"Update params: str(self.sn.currentParam())") # Optional: feedback

    def save_measurement(self):
        filePath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,                  # Parent widget
            "Save File",            # Dialog title
            "",                     # Initial directory or filename (empty uses current dir)
            "Text Files (*.csv);;All Files (*)" # File filters
        )

        # Check if a file path was selected (user didn't cancel)
        if filePath:
            print(f"Selected file path for saving: {filePath}")
            # Here you would add the code to actually write your data to the file
            data = np.column_stack([self.x] + [self.measurements[k] for k in self.operations])
            try:
                np.savetxt(filePath, data, header=str(self.sn.currentParam())+'\n'+str(self.operations))
            except Exception as e:
                print(f"Error saving file: {e}")
        else:
            print("Save operation cancelled.")
    
    def clear_measurement(self):
        z = np.zeros_like(self.x)
        self.spectrum = z
        self.reflectivity = z
        self.reflectivity_plot.setData(self.x, self.reflectivity)
        for label in ['Direct 1', 'Reflected', 'Direct 2']:
            self.saved_plot[label].setData(self.x, z)
        self.measurements = {}
            
        self.next_op = 0
        self.next_op_label.setText("Next: "+self.operations[self.next_op])
        
    def closeEvent(self, event):
        self.sn.stop()
        event.accept()

# --- Application Execution ---
if __name__ == '__main__':
    # Create the Qt Application
    app = QtWidgets.QApplication(sys.argv)    
    
    # Initialize spectrometer reading thread
    spectrometer = sn_spectrometer_reader(int_time=200, scansavg=5)

    # Create and show the main window
    main = MainWindow(spectrometer)
    main.show()

    # Start the Qt event loop
    sys.exit(app.exec())

