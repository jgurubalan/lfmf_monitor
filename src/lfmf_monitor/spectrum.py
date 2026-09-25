import numpy as np


def compute_spectrum(
    samples: np.ndarray,
    sample_rate_hz: float,
    center_frequency_hz: float,
):
    """Compute a centered FFT power spectrum from complex IQ samples."""

    n = len(samples)

    if n == 0:
        raise ValueError("No IQ samples supplied")

    window = np.hanning(n)
    windowed = samples * window

    fft = np.fft.fftshift(np.fft.fft(windowed))

    frequencies = np.fft.fftshift(
        np.fft.fftfreq(n, d=1.0 / sample_rate_hz)
    )

    power = np.abs(fft) ** 2

    frequencies_hz = center_frequency_hz + frequencies

    # Convert to relative dB.
    # The strongest FFT bin is defined as 0 dB.
    max_power = np.max(power)

    if max_power > 0:
        power_db = 10.0 * np.log10(power / max_power)
    else:
        power_db = np.full_like(power, -np.inf, dtype=np.float64)

    return frequencies_hz, power, power_db
