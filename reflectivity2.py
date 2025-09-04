# This is a script to plot reflectivity measurements from a CSV file.
# Valid file format from measurement n. 19 onwards.

import numpy as np
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import glob
from pathlib import Path
from scipy.signal import savgol_filter

def load_measurement(file, lin_coeffs=None):
    wl, dark1, direct1, dark2, reflected, dark3, direct2 = np.loadtxt(file, skiprows=1, unpack=True)
    direct1 -= dark1
    reflected -= dark2
    direct2 -= dark3
    
    if lin_coeffs is not None:
        # Apply linearization coefficients
        def linearize(x):
            return np.array([x[i] * lin_coeffs[i](x[i]) for i in range(len(x))])
    else:
        def linearize(x):
            return x

    direct1 = linearize(direct1)
    reflected = linearize(reflected)
    direct2 = linearize(direct2)

    return wl, direct1, reflected, direct2


def plot_measurement(file, ref=None, wl_window=None, lin_coeffs=None, savgol_params=(51, 3)):
    window, poly = savgol_params

    wl, direct1, reflected, direct2 = load_measurement(file, lin_coeffs)

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

def compare_measurements(files, ref=None, wl_window=None, lin_coeffs=None, savgol_params=(51, 3), avg=False):
    window, poly = savgol_params

    measurements = {}
    y_lim_min, y_lim_max = 1, 0
    avg_rft = 0
    for file in files:
        label = Path(file).stem
        wl, direct1, reflected, direct2 = load_measurement(file, lin_coeffs)
        rft = (reflected) / ((direct1 + direct2) / 2)
        rft[np.isinf(rft)] = np.nan  # In case there were div by zero errors
        if wl_window is not None:
            i_range = np.where((wl >= wl_window[0]) & (wl <= wl_window[1]))
        else:
            i_range = slice(None)
        measurements[label] = {
            'wl': wl[i_range],
            'rft': rft[i_range]
        }
        avg_rft += rft[i_range]
        y_lim_min = min(y_lim_min, np.nanmin(rft[i_range]))
        y_lim_max = max(y_lim_max, np.nanmax(rft[i_range]))
    avg_rft /= len(files)
    if avg:
        measurements['Average'] = {
            'wl': wl[i_range],
            'rft': avg_rft
        }

    fig, ax = plt.subplots()
    for label in measurements.keys():
        m = measurements[label]
        wl = m['wl']
        rft = m['rft']
        l, = ax.plot(wl, rft, alpha=.4, marker='.', markersize=1, ls='None')
        ax.plot(wl, savgol_filter(rft, window, poly), color=l.get_color(), label=label)

    if ref is not None:
        ref_wl, ref_r = ref
        l, = ax.plot(ref_wl, ref_r, ls='--', lw=2, label='Reference')
        # +/-1.5% band
        ax.fill_between(ref_wl, ref_r*1.015, ref_r*.985, color=l.get_color(), alpha=.3, label='±1.5%')

    if wl_window:
        ax.set_xlim(wl_window[0], wl_window[1])
    ax.set_ylim(y_lim_min, y_lim_max)  # considers the last measurement
    ax.grid()
    ax.legend()
    ax.set_xlabel('Wavelength (nm)')
    ax.set_ylabel('Reflectivity')

    return fig

def avg_reflectivity(files):
    avg_rft = 0
    for file in files:
        wl, dark1, direct1, dark2, reflected, dark3, direct2 = np.loadtxt(file, skiprows=1, unpack=True)
        rft = (reflected - dark2) / ((direct1 - dark1 + direct2 - dark3) / 2)
        rft[np.isinf(rft)] = np.nan  # In case there were div by zero errors
        avg_rft += rft
    avg_rft /= len(files)
    return wl, avg_rft

if __name__ == "__main__":
    ref = np.loadtxt("Filmetrics_Al_5nmoxide.txt", skiprows=1, unpack=True)
    measurements =  [31, 32, 33, 34, 35]
    files = [glob.glob(str(measurement)+"*.csv")[0] for measurement in measurements]
    compare_measurements(files, ref, wl_window=(550, 1050), savgol_params=(51, 3), avg=True)
    #compare_measurements(files, ref, wl_window=(550, 1050), savgol_params=(51, 3))
    plt.show()
    
    