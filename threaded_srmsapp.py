import sys
import time
import threading
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import pyqtgraph as pg
import numpy as np

# Mock Spectrograph Class (replace with your actual spectrograph)
class MockSpectrograph(QObject):
    """
    Simulates a spectrograph device.  Emits a signal with new data every so often.
    Replace this with your actual spectrograph interface.
    """
    data_ready = Signal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        """
        Simulates data acquisition.  Generates a sine wave with increasing frequency.
        """
        frequency = 0.1
        while self.running:
            # Simulate a small amount of noise around the sine wave
            noise = np.random.normal(0, 0.1, 100)
            # Generate the sine wave data
            data = np.sin(np.linspace(0, 10 * np.pi, 100) * frequency) + noise
            self.data_ready.emit(data)
            time.sleep(0.1)  # Simulate data acquisition rate
            frequency += 0.02  # Slowly increase the frequency

    def stop(self):
        """Stop the data acquisition thread."""
        self.running = False
        self.thread.join()

# Plotter Class
class Plotter(QObject):
    """
    Handles plotting of data received from the spectrograph.  Runs in its own thread.
    """
    def __init__(self, spectrograph):
        super().__init__()
        self.spectrograph = spectrograph
        self.running = True
        self.thread = QThread()  # Use QThread
        self.moveToThread(self.thread) # Move object to thread.
        self.spectrograph.data_ready.connect(self.plot_data)
        self.thread.started.connect(self.run) # connect run function.
        self.thread.start()

    def run(self):
        """
        Empty run function.  Necessary for QThread, but the actual work is done
        in plot_data, which is called via a signal.
        """
        pass

    def plot_data(self, data):
        """
        Plots the data using pyqtgraph.  This is called in the plotter thread.
        """
        if hasattr(self, 'plot_widget'): # Check if plot_widget exists
            self.plot_widget.plot(data, clear=True)

    def set_plot_widget(self, plot_widget):
        """
        Sets the pyqtgraph plot widget.  This needs to be called from the main thread.
        """
        self.plot_widget = plot_widget

    def stop(self):
        """Stop the plotting thread."""
        self.running = False
        self.thread.quit()
        self.thread.wait()

# Main Window Class
class MainWindow(QMainWindow):
    def __init__(self, spectrograph, plotter):
        super().__init__()
        self.spectrograph = spectrograph
        self.plotter = plotter

        self.setWindowTitle("Spectrograph Plotter")
        self.setGeometry(100, 100, 800, 600)

        # Main layout
        main_layout = QVBoxLayout()
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Create the pyqtgraph plot widget
        self.plot_widget = pg.PlotWidget()
        main_layout.addWidget(self.plot_widget)

        # Set the plot widget in the plotter.  This is crucial to do *after*
        # the plot widget is created and added to the layout.
        self.plotter.set_plot_widget(self.plot_widget)

    def closeEvent(self, event):
        """
        Stop the threads when the main window is closed.
        """
        self.spectrograph.stop()
        self.plotter.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Create the spectrograph and plotter objects
    spectrograph = MockSpectrograph()
    plotter = Plotter(spectrograph)  # Pass the spectrograph instance

    # Create the main window
    main_window = MainWindow(spectrograph, plotter)
    main_window.show()

    sys.exit(app.exec())
