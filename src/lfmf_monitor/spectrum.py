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

    The FFT is calculated for one IQ block. Power is NOT normalized
    independently for each block, so power measurements can be
    compared across time.

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
            RF frequency corresponding to each FFT bin.

        power:
            Raw FFT power for each frequency bin.

        power_db:
            Power expressed in dB relative to the FFT reference.
    """

    n = len(samples)

    if n == 0:
        raise ValueError("No IQ samples supplied")

    # Apply Hann window to reduce spectral leakage.
    window = np.hanning(n)
    windowed = samples * window

    # Compute FFT and shift zero frequency to the center.
    fft = np.fft.fftshift(
        np.fft.fft(windowed)
    )

    # Calculate frequency offset of each FFT bin.
    frequencies = np.fft.fftshift(
        np.fft.fftfreq(
            n,
            d=1.0 / sample_rate_hz
        )
    )

    # Calculate FFT power.
    power = np.abs(fft) ** 2

    # Convert frequency offsets to actual RF frequencies.
    frequencies_hz = center_frequency_hz + frequencies

    # ---------------------------------------------------------
    # Convert power to dB WITHOUT normalizing each block
    # to its own maximum.
    # ---------------------------------------------------------

    # Prevent log10(0).
    power_db = 10.0 * np.log10(
        np.maximum(power, 1e-20)
    )

    return (
        timestamp,
        frequencies_hz,
        power,
        power_db,
    )