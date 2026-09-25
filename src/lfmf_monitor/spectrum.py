import numpy as np
from datetime import datetime


def compute_spectrum(
    samples: np.ndarray,
    sample_rate_hz: float,
    center_frequency_hz: float,
    timestamp: datetime,
):
    """
    Compute a centered FFT power spectrum from complex IQ samples.

    Args:
        samples:
            Complex I/Q samples for one block.

        sample_rate_hz:
            RTL-SDR sample rate in Hz.

        center_frequency_hz:
            RTL-SDR center frequency in Hz.

        timestamp:
            UTC timestamp associated with the beginning of
            the IQ block.

    Returns:
        timestamp:
            Timestamp of the IQ block.

        frequencies_hz:
            Frequency corresponding to each FFT bin.

        power:
            Raw FFT power for each frequency bin.

        power_db:
            Relative power in dB, with the strongest bin
            normalized to 0 dB.
    """

    n = len(samples)

    if n == 0:
        raise ValueError("No IQ samples supplied")

    # Apply Hann window to reduce spectral leakage.
    window = np.hanning(n)
    windowed = samples * window

    # Compute FFT and shift zero frequency to the center.
    fft = np.fft.fftshift(np.fft.fft(windowed))

    # Calculate frequency of each FFT bin.
    frequencies = np.fft.fftshift(
        np.fft.fftfreq(n, d=1.0 / sample_rate_hz)
    )

    # Calculate FFT power.
    power = np.abs(fft) ** 2

    # Convert relative frequencies to actual RF frequencies.
    frequencies_hz = center_frequency_hz + frequencies

    # Convert to relative dB.
    # The strongest FFT bin is defined as 0 dB.
    max_power = np.max(power)

    if max_power > 0:
        power_db = 10.0 * np.log10(power / max_power)
    else:
        power_db = np.full_like(
            power,
            -np.inf,
            dtype=np.float64,
        )

    return timestamp, frequencies_hz, power, power_db