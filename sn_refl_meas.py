import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import threading
import time
import queue
from tkinter import filedialog  # Import the filedialog module
from tkinter import simpledialog # Import the simpledialog module
from stellarnet_driverLibs import stellarnet_driver3 as sn

class RealTimeSignalPlotter:
    """
    A class to visualize a signal in real-time using Tkinter and Matplotlib.

    Attributes:
        sampling_rate (float): The sampling rate of the signal in Hz.  Defaults to 100.
        buffer_size (int): The number of data points to display at once. Defaults to 500.
        update_interval (int): The interval in milliseconds at which the plot updates. Defaults to 100.
        signal_queue (queue.Queue): A queue to hold the incoming signal data.
        root (tk.Tk): The main Tkinter window.
        fig (plt.Figure): The Matplotlib figure.
        ax (plt.Axes): The Matplotlib axes.
        canvas (FigureCanvasTkAgg): The Matplotlib canvas embedded in the Tkinter window.
        lines (list): A list of line objects in the plot.
        x_data (np.ndarray): The x-axis data for the plot.
        y_data (np.ndarray): The y-axis data for the plot.
        is_running (bool): Flag to indicate if the signal generation is running.
        thread (threading.Thread): The thread for signal generation.
        amplitude_labels (list): List of labels to display the current amplitudes.
        amplitude_values (list): List of StringVars to hold the amplitude values.

    Methods:
        __init__(self, sampling_rate=100, buffer_size=500, update_interval=100):
            Initializes the RealTimeSignalPlotter object.
        setup_plot(self):
            Sets up the Matplotlib plot.
        update_plot(self):
            Updates the Matplotlib plot with new data from the queue.
        generate_signal(self):
            Generates a sample sine wave signal (in a separate thread).
        start(self):
            Starts the signal generation and plot updating.
        stop(self):
            Stops the signal generation.
        cleanup(self):
            Cleans up resources, called when the Tkinter window is closed.
        save_data(self):  # New method to save data
            Saves the current x and y data to a file.
        print_data(self): # New method to print data
            print(f"Current x data: {self.x_data}")
            print(f"Current y data: {self.y_data}")
        change_sampling_rate(self): # New method to change the sampling rate
            #use a dialog box to get the new sampling rate
            new_sampling_rate = simpledialog.askinteger("Input", "Enter new sampling rate:",
                                                    parent=self.root,
                                                    minvalue=1, maxvalue=100000) #set min and max values
            if new_sampling_rate is not None: #check if the user entered a value
                self.sampling_rate = new_sampling_rate
                self.x_data = np.arange(0, self.buffer_size / self.sampling_rate, 1 / self.sampling_rate)
                self.setup_plot() #reinitialize the plot
                # Restart the signal generation thread with the new sampling rate
                self.stop()  # Stop any existing thread
                self.__init__(sampling_rate=self.sampling_rate, buffer_size=self.buffer_size, update_interval=self.update_interval) #reinitilize
                self.start()
                print(f"Sampling rate changed to {self.sampling_rate} Hz")

    """
    def __init__(self, int_time=100, update_interval=500):
        """
        Initializes the RealTimeSignalPlotter object.

        Args:
            sampling_rate (float): The sampling rate of the signal in Hz.
            buffer_size (int): The number of data points to display at once.
            update_interval (int): The interval in milliseconds at which the plot updates.
        """
        self.sn_version = sn.version()
        self.int_time = int_time
        self.scansavg = 1 
        self.smooth = 0    
        self.xtiming = 3 
        self.update_interval = update_interval

        # init Spectrometer - Get BOTH spectrometer and wavelength
        self.spectrometer, self.wav = sn.array_get_spec(0) # 0 for first channel and 1 for second channel , up to 127 spectrometers
        sn.ext_trig(self.spectrometer, True)
        
        # Get device ID
        self.deviceID = sn.getDeviceId(self.spectrometer)
        #print('\nMy device ID: ', deviceID)

        # Get current device parameter
        self.currentParam = sn.getDeviceParam(self.spectrometer)

        # Call to Enable or Disable External Trigger to by default is Disbale=False -> with timeout
        # Enable or Disable Ext Trigger by Passing True or False, If pass True than Timeout function will be disable, so user can also use this function as timeout enable/disbale 
        sn.ext_trig(self.spectrometer,True)

        # Only call this function on first call to get spectrum or when you want to change device setting.
        # -- Set last parameter to 'True' throw away the first spectrum data because the data may not be true for its inttime after the update.
        # -- Set to 'False' if you don't want to do another capture to throw away the first data, however your next spectrum data might not be valid.
        sn.setParam(self.spectrometer, self.int_time, self.scansavg, self.smooth, self.xtiming, True) 

        # Get spectrometer data - Get BOTH X and Y in single return
        self.first_data = sn.getSpectrum_Y(self.spectrometer) # get specturm for the first time

        self.root = tk.Tk()
        self.root.title("Specular Reflectance Measurement")
        self.root.protocol("WM_DELETE_WINDOW", self.cleanup)  # Handle window close

        # Create the figure and subplots.  The first subplot will be larger
        self.fig = plt.figure(figsize=(8, 6))
        self.ax = [
            plt.subplot2grid((3, 2), (0, 0), rowspan=3),  # Main plot, spans 3 rows and 2 columns
            plt.subplot2grid((3, 2), (0, 1)),            # Top right
            plt.subplot2grid((3, 2), (1, 1)),            # Middle right
            plt.subplot2grid((3, 2), (2, 1)),            # Bottom right
        ]
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.x_data = self.wav
        self.y_data = self.first_data
        self.y_data_d1 = np.zeros_like(self.first_data)
        self.y_data_d2 = np.zeros_like(self.first_data)
        self.y_data_r = np.zeros_like(self.first_data)
        # Create four line objects, one for each subplot.
        self.lines = [
            self.ax[0].plot(self.x_data, self.y_data)[0],
            self.ax[1].plot(self.x_data, self.y_data_d1)[0],
            self.ax[2].plot(self.x_data, self.y_data_r)[0],
            self.ax[3].plot(self.x_data, self.y_data_d2)[0],
        ]

        # Add a button to save current spectrum 
        self.save_button = tk.Button(self.root, text="Direct1", command=lambda: self.save_spectrum('direct1'))
        self.save_button.pack(side=tk.LEFT) #pack the button to the right
        # Add a button to save current spectrum
        self.save_button = tk.Button(self.root, text="Reflected", command=lambda: self.save_spectrum('reflected'))
        self.save_button.pack(side=tk.LEFT) #pack the button to the right
        # Add a button to save current spectrum as direct 1
        self.save_button = tk.Button(self.root, text="Direct2", command=lambda: self.save_spectrum('direct2'))
        self.save_button.pack(side=tk.LEFT) #pack the button to the right

        # Add a button to save the data to the right of the plot
        self.save_button = tk.Button(self.root, text="Save Data", command=self.save_data)
        self.save_button.pack(side=tk.LEFT) #pack the button to the right

        # Add a button to print the data to the right of the plot
        self.print_button = tk.Button(self.root, text="Print Data", command=self.print_data)
        self.print_button.pack(side=tk.LEFT) #pack the button to the right

        # Add a button to change the sampling rate
        self.change_int_time_button = tk.Button(self.root, text="Change Sampling Rate", command=self.change_sampling_rate)
        self.change_int_time_button.pack(side=tk.LEFT)

        # Add labels and string variables to display the amplitudes for each subplot
        self.amplitude_values = [tk.StringVar() for _ in range(4)]
        self.amplitude_labels = [
            tk.Label(self.root, textvariable=self.amplitude_values[i], font=("Arial", 12)) for i in range(4)
        ]
        # Use a frame to pack the labels vertically to the right of the plot
        label_frame = tk.Frame(self.root)
        label_frame.pack(side=tk.RIGHT, padx=10)  # Pack frame to the right of the canvas
        for i, label in enumerate(self.amplitude_labels):
            label.pack(in_=label_frame, side=tk.TOP, pady=5)  # Pack labels into the frame, vertically

        # Initialize the StringVars with initial values
        for amp_value in self.amplitude_values:
            amp_value.set("0.00")

    def setup_plot(self):
        """
        Sets up the Matplotlib plot.  Now sets up all four subplots.
        """
        wl1, wl2 = 550, 1100  # nm
        
        self.ax[0].set_xlabel("Wavelength (nm)")
        self.ax[0].set_ylabel("Counts")
        self.ax[0].set_title("Live View")
        self.ax[0].set_xlim(wl1, wl2)
        #self.ax[0].set_ylim(-1.2, 1.2)
        self.ax[0].grid(True)

        for i in range(1, 4):  # Set up the smaller plots on the right
            #self.ax[i].set_xlabel("Wavelength (nm)")  # You might not want x labels on the smaller plots
            #self.ax[i].set_ylabel("Counts")
            self.ax[i].set_title(f"Signal {i}")
            self.ax[i].set_xlim(wl1, wl2)
            #self.ax[i].set_ylim(-1.2, 1.2)
            self.ax[i].grid(True)
            self.ax[i].tick_params(axis='x', labelsize=8)  # Smaller tick labels
            self.ax[i].tick_params(axis='y', labelsize=8)

    def update_plot(self):
        """
        Updates the Matplotlib plot with new data from the queue.
        This function runs in the main Tkinter thread.
        """
        self.y_data = sn.getSpectrum_Y(self.spectrometer)
        self.lines[0].set_ydata(self.y_data)

        self.canvas.draw()

        self.root.after(self.update_interval, self.update_plot)

    def cleanup(self):
        """
        Cleans up resources, called when the Tkinter window is closed.
        """
        # Release the spectrometer before ends the program
        sn.reset(self.spectrometer)
        plt.close(self.fig)
        self.root.destroy()

    def save_spectrum(self, command):
        if command == 'direct1':
            self.y_data_d1 = np.copy(self.y_data)
            self.lines[1].set_ydata(self.y_data_d1)
        elif command == 'reflected':
            self.y_data_r = self.y_data
            self.lines[2].set_ydata(self.y_data_r)
        elif command == 'direct2':
            self.y_data_d2 = self.y_data
            self.lines[3].set_ydata(self.y_data_d2)
        else:
            assert False

        self.canvas.draw()
    
    def save_data(self):
        """
        Saves the current x and y data to a file.  Handles file selection and writing.
        """
        try:
            filename = filedialog.asksaveasfilename(
                initialdir=".",
                title="Save Signal Data",
                filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
                defaultextension=".txt",
            )
            if filename:
                with open(filename, "w") as f:
                    f.write("Time (s),Amplitude 1,Amplitude 2,Amplitude 3,Amplitude 4\n")
                    # Save the data, transposing the x_data and y_data arrays
                    # Get the data from each of the lines.
                    y_data_arrays = [line.get_ydata() for line in self.lines]
                    for i, x in enumerate(self.x_data):
                        y_values = [y_data[i] if i < len(y_data) else 0 for y_data in y_data_arrays]
                        f.write(f"{x},{y_values[0]},{y_values[1]},{y_values[2]},{y_values[3]}\n")
                print(f"Data saved to {filename}")
        except Exception as e:
            print(f"Error saving data: {e}")

    def print_data(self):
        """
        Prints the current x and y data to the console.
        """
        print(f"Current x data: {self.x_data}")
        for i, line in enumerate(self.lines):
            print(f"Current y data {i+1}: {line.get_ydata()}")

    def change_sampling_rate(self):
        """
        Changes the sampling rate of the signal.  Opens a dialog box to get the new rate.
        """
        new_sampling_rate = simpledialog.askinteger(
            "Input",
            "Enter new sampling rate:",
            parent=self.root,
            minvalue=1,
            maxvalue=100000,
        )
        if new_sampling_rate is not None:
            self.sampling_rate = new_sampling_rate
            self.x_data = np.arange(0, self.buffer_size / self.sampling_rate, 1 / self.sampling_rate)
            self.setup_plot()  # Reinitialize the plot
            # Restart the signal generation thread with the new sampling rate
            self.stop()
            self.__init__(sampling_rate=self.sampling_rate, buffer_size=self.buffer_size, update_interval=self.update_interval)
            self.start()
            print(f"Sampling rate changed to {self.sampling_rate} Hz")

if __name__ == "__main__":
    plotter = RealTimeSignalPlotter(int_time=100, update_interval=500)
    plotter.setup_plot()
    plotter.update_plot()
    tk.mainloop()

