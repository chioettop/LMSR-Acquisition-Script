# This is a script to plot reflectivity measurements from a CSV file.
# Valid file format from measurement n. 19 onwards.

import numpy as np
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import glob
from pathlib import Path
from scipy.signal import savgol_filter
import ast
import csv

def load_measurement(file, lin_coeffs=None):
    """Load a measurement CSV and return dark-subtracted spectra.

    The first line is a '#'-prefixed dict of parameters (e.g. int_time).
    If lin_coeffs (one callable per pixel) is given, linearization is applied.
    Returns (wl, direct1, reflected, direct2, int_time).
    """
    # Read the first row as a dictionary of parameters
    with open(file, 'r') as f:
        params_line = f.readline()
        if params_line.startswith('#'):
            params_line = params_line[1:]
        params = ast.literal_eval(params_line)
        int_time = params.get('int_time', None)
    # Load the rest of the file as CSV data
    wl, dark1, direct1, dark2, reflected, dark3, direct2 = np.loadtxt(file, unpack=True)
    direct1 -= dark1
    reflected -= dark2
    direct2 -= dark3
    
    if lin_coeffs is not None:
        # Apply linearization coefficients
        def linearize(x):
            return np.array([x[i] * lin_coeffs[i](x[i]) for i in range(len(x))])
        direct1 = linearize(direct1)
        reflected = linearize(reflected)
        direct2 = linearize(direct2)

    return wl, direct1, reflected, direct2, int_time


def save_measurement(file, out_file=None, lin_coeffs=None):
    """Compute reflectivity for a measurement file and save it as CSV (wl, reflectivity).

    Defaults to <file>.reflectivity.csv. Returns the output path.
    """
    wl, direct1, reflected, direct2, int_time = load_measurement(file, lin_coeffs)

    # reflectivity = I_r / avg of I_d, same formula as plot_measurement
    rft = reflected / ((direct1 + direct2) / 2)
    rft[np.isinf(rft)] = np.nan  # In case there were div by zero errors

    if out_file is None:
        out_file = Path(file).with_suffix('.reflectivity.csv')

    with open(out_file, 'w', newline='') as f:
        f.write(f"# int_time={int_time}, lin_coeffs_applied={lin_coeffs is not None}\n")
        writer = csv.writer(f)
        writer.writerow(['wl', 'reflectivity'])
        writer.writerows(zip(wl, rft))

    return out_file


def plot_measurement(file, ref=None, wl_window=None, lin_coeffs=None, savgol_params=(51, 3)):
    """Plot reflectivity, direct1/direct2 ratio and darks for one measurement.

    ref: optional (wavelength, reflectivity) reference curve, drawn with a �1% band.
    wl_window: optional (min, max) wavelength range in nm.
    savgol_params: (window, polyorder) of the Savitzky-Golay smoothing.
    Returns the matplotlib Figure.
    """
    window, poly = savgol_params

    wl, direct1, reflected, direct2, int_time = load_measurement(file, lin_coeffs)

    fig = plt.figure()
    gs = gridspec.GridSpec(2, 2)  # Create a 2x2 grid

    ax1 = fig.add_subplot(gs[:, 0])  # Spans all rows, first column
    ax2 = fig.add_subplot(gs[0, 1])  # First row, second column
    ax3 = fig.add_subplot(gs[1, 1])  # Second row, second column

    plt.suptitle(file)
    ax = ax1
    ax.set_title
    if wl_window is not None:
        i_range = np.where((wl >= wl_window[0]) & (wl <= wl_window[1]))
    else:
        i_range = slice(None)
    # reflectivity = I_r / avgs of I_d
    rft = reflected / ((direct1 + direct2) / 2)
    rft = rft[i_range]
    wl = wl[i_range]
    rft[np.isinf(rft)] = np.nan  # In case there were div by zero errors
    ax.plot(wl, rft, alpha=.2, color='C0', label='Reflectivity')
    ax.plot(wl, savgol_filter(rft, window, poly), color='C0')
    if ref is not None:
        ref_wl, ref_r = ref
        ax.plot(ref_wl, ref_r, color='C1', label='Reference')
        ax.fill_between(ref_wl, ref_r*1.01, ref_r*.99, color='C1', alpha=.3, label='±1%')
    if wl_window:
        ax.set_xlim(wl_window[0], wl_window[1])
    ax.set_ylim(np.nanmin(rft), np.nanmax(rft))
    ax.grid()
    ax.legend()
    ax.set_ylabel('Reflectivity')

    ax = ax2
    ax.set_title('Direct1 / Direct2')
    dratio = (direct1[i_range] / direct2[i_range])
    ax.plot(wl, dratio)
    ax.plot(wl, savgol_filter(dratio, window, poly))
    if wl_window:
        ax.set_xlim(wl_window[0], wl_window[1])
    ax.set_ylim(np.nanmin(dratio), np.nanmax(dratio))
    ax.grid()

    ax = ax3
    ax.plot(wl, dark1[i_range], label='Dark 1')
    ax.plot(wl, dark2[i_range], label='Dark 2')
    ax.plot(wl, dark3[i_range], label='Dark 3')
    ax.legend()  
    if wl_window:
        ax.set_xlim(wl_window[0], wl_window[1])
    ax.grid()
    ax.set_title('Darks')

    fig.supxlabel('Wavelength (nm)')
    #plt.tight_layout()

    return fig

def plot_measurements(measurements, ref=None, wl_window=None, savgol_params=(51, 3), fig_size=(10, 6), error=0.015):
    """Overlay several reflectivity curves on one plot.

    measurements: dict label -> {'wl', 'rft', optionally 'int_time'}.
    error: relative width of the band drawn around ref (None to disable).
    Returns the matplotlib Figure.
    """
    
    fig, ax = plt.subplots(figsize=fig_size)
    y_lim_min, y_lim_max = 1, 0
    window, poly = savgol_params

    for label in measurements.keys():
        m = measurements[label]
        wl = m['wl']
        i_range = np.where((wl >= wl_window[0]) & (wl <= wl_window[1])) if wl_window else slice(None)
        wl = wl[i_range]
        rft = m['rft'][i_range]
        y_lim_min = min(y_lim_min, np.nanmin(rft))
        y_lim_max = max(y_lim_max, np.nanmax(rft))
        l, = ax.plot(wl, rft, alpha=.4, marker='.', markersize=1, ls='None')
        rft[np.isnan(rft)] = 0  # so savgol does not trip
        ax.plot(wl, savgol_filter(rft, window, poly), color=l.get_color(), label=label+(f" (int_time={m['int_time']} ms)" if 'int_time' in m else ''))

    if ref is not None:
        ref_wl, ref_r = ref
        l, = ax.plot(ref_wl, ref_r, ls='--', lw=2, label='Reference')
        # "error" band
        if error is not None:
            ax.fill_between(ref_wl, ref_r*(1+error), ref_r*(1-error), color=l.get_color(), alpha=.3, label='±1.5%')
        ref_range = np.where((ref_wl >= wl_window[0]) & (ref_wl <= wl_window[1])) if wl_window else slice(None)
        y_lim_min = min(y_lim_min, np.nanmin(ref_r[ref_range]*.95))
        y_lim_max = max(y_lim_max, np.nanmax(ref_r[ref_range]*1.05))


    if wl_window:
        ax.set_xlim(wl_window[0], wl_window[1])
    ax.set_ylim(y_lim_min, y_lim_max)  
    ax.grid()
    ax.legend()
    ax.set_xlabel('Wavelength (nm)')
    ax.set_ylabel('Reflectivity')

    return fig

def compare_measurements(files, ref=None, wl_window=None, lin_coeffs=None, savgol_params=(51, 3), avg=False, fig_size=(10, 6), error=0.015):
    """Load several measurement files and plot their reflectivities together.

    If avg is True, only the average over all files is plotted.
    Returns the matplotlib Figure.
    """
    window, poly = savgol_params

    measurements = {}

    avg_rft = 0
    for file in files:
        label = Path(file).stem
        wl, direct1, reflected, direct2, int_time = load_measurement(file, lin_coeffs)
        rft = (reflected) / ((direct1 + direct2) / 2)
        rft[np.isinf(rft)] = np.nan  # In case there were div by zero errors

        measurements[label] = {
            'wl': wl,
            'rft': rft,
            'int_time': int_time
        }
        avg_rft += rft

    avg_rft /= len(files)
    if avg:
        measurements = {
            "Avg. of "+str(len(files))+" meas.": {
                'wl': wl,
                'rft': avg_rft
            }
        }

    fig = plot_measurements(measurements, ref=ref, wl_window=wl_window, savgol_params=savgol_params, fig_size=fig_size, error=error)
    
    return fig

def avg_reflectivity(files, lin_coeffs=None):
    """Return (wl, mean reflectivity, standard deviation) over several measurement files."""
    avg_rft = 0
    sigma = 0
    for file in files:
        wl, direct1, reflected, direct2, _ = load_measurement(file, lin_coeffs)
        rft = reflected / ((direct1 + direct2) / 2)
        rft[np.isinf(rft)] = np.nan  # In case there were div by zero errors
        avg_rft += rft
        sigma += rft**2
    avg_rft /= len(files)
    sigma = np.sqrt(sigma/len(files) - avg_rft**2)
    return wl, avg_rft, sigma


if __name__ == "__main__":
    ref = np.loadtxt("data/Filmetrics_Al_5nmoxide.txt", skiprows=1, unpack=True)
    measurements =  [31, 32, 33, 34, 35]
    files = [glob.glob("data/"+str(measurement)+"*.csv")[0] for measurement in measurements]
    compare_measurements(files, ref, wl_window=(550, 1050), savgol_params=(51, 3), avg=True)
    #compare_measurements(files, ref, wl_window=(550, 1050), savgol_params=(51, 3))
    plt.show()
    
    