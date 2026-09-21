# SRMS – Spectral Reflectivity Measurement Setup

Tools to acquire and analyse reflectivity spectra (M1 mirror coating samples) with a StellarNet spectrometer.

## Files

| File | Description |
|------|-------------|
| `srmsapp.py` | PySide6/pyqtgraph GUI: live spectrometer readout in a background thread, with saving of spectra to CSV. |
| `sn_refl_meas.py` | Tkinter/Matplotlib real-time plotter and reflectivity measurement routine (dark / direct / reflected sequence). |
| `sn_linearizer.py` | Detector linearization analysis from integration-time scans (`*_it test.csv`). |
| `reflectivity2.py` | Analysis library: load measurement CSVs, compute/plot/compare/average reflectivity, optional linearization. Running it directly plots measurements 31–35 against a Filmetrics reference. |
| `data/` | Measurement CSVs, integration-time tests, linearization coefficients (`.npy`) and reference curves (Filmetrics `.txt`). |

## Setup

Requires Python 3.12 on Windows.

```powershell
python -m venv .srms
.srms\Scripts\Activate.ps1
pip install numpy scipy matplotlib PySide6 pyqtgraph
```

`tkinter` ships with the standard Python installer.

### StellarNet driver

The spectrometer driver (`stellarnet_driverLibs/`, containing `stellarnet_driver3`) is proprietary and **not** in this repository.
Copy it from the StellarNet SpectraWiz/Python package into the repository root, so that
`from stellarnet_driverLibs import stellarnet_driver3` works. The analysis in `reflectivity2.py` does not need it.

## Usage

```powershell
python srmsapp.py        # GUI
python sn_refl_meas.py   # measurement routine
python reflectivity2.py  # example analysis (edit __main__ for your files)
```
