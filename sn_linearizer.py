import numpy as np
import matplotlib.pyplot as plt

spectra = np.loadtxt('data/20250703 prova_it test.csv', skiprows=1)

wl = spectra[:,0]
int_t = np.arange(10, 260+1, 10) # from the CSV file header)

fit = np.polyfit(int_t, spectra[:,1:].T, 1)

# 
sn = spectra[:,1:] / spectra[:,13][:, np.newaxis]
