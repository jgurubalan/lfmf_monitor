| File | Main Role | What It Does | Input | Output |
|---|---|---|---|---|
| `main.py` | **Orchestrator** | Controls the overall workflow and tells the other modules what to do and when | Configuration + results from other modules | Runs the monitoring process |
| `rtl.py` | **SDR Interface** | Starts/stops the RTL-SDR, sets frequency/sample rate/gain, and reads I/Q samples | RTL-SDR hardware | Raw/complex I/Q samples |
| `buffer.py` | **Data Buffer** | Temporarily stores and organizes the continuous stream of I/Q samples into manageable blocks | I/Q samples from `rtl.py` | Blocks of I/Q samples |
| `spectrum.py` | **Signal Processing** | Performs FFT analysis and calculates signal power across frequencies | I/Q sample blocks | Frequencies + power/spectrum |
| `transport.py` | **Data Transport** | Sends processed measurements to another computer/server or service | Spectrum/measurement data | Network messages/data |
| `__init__.py` | **Python Package** | Identifies `lfmf_monitor` as a Python package and can expose package-level items | Python package | Enables imports such as `from lfmf_monitor.rtl import RTLSDR` |