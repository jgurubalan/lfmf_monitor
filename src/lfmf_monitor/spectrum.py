import numpy as np
from datetime import datetime


def compute_spectrum(
    samples: np.ndarray,
    sample_rate_hz: float,
    center_frequency_hz: float,
    timestamp: datetime,
):
    """
    Compute FFT spectrum and signal measurements for one IQ block.

    For each block this function calculates:

        - Frequency of every FFT bin
        - Raw FFT power
        - Power in dB
        - Estimated noise floor
        - Peak frequency
        - Peak power
        - Signal level above the noise floor (SNR)

    Args:
        samples:
            Complex I/Q samples for one block.

        sample_rate_hz:
            RTL-SDR sample rate in Hz.

        center_frequency_hz:
            RTL-SDR center frequency in Hz.

        timestamp:
            UTC timestamp associated with the IQ block.

    Returns:
        Dictionary containing all spectrum measurements.
    """

    n = len(samples)

    if n == 0:
        raise ValueError("No IQ samples supplied")

    # ---------------------------------------------------------
    # 1. Apply Hann window
    # ---------------------------------------------------------

    window = np.hanning(n)
    windowed = samples * window

    # ---------------------------------------------------------
    # 2. FFT
    # ---------------------------------------------------------

    fft = np.fft.fftshift(
        np.fft.fft(windowed)
    )

    # ---------------------------------------------------------
    # 3. Frequency corresponding to every FFT bin
    # ---------------------------------------------------------

    frequency_offsets = np.fft.fftshift(
        np.fft.fftfreq(
            n,
            d=1.0 / sample_rate_hz
        )
    )

    frequencies_hz = (
        center_frequency_hz
        + frequency_offsets
    )

    # ---------------------------------------------------------
    # 4. Calculate raw FFT power
    # ---------------------------------------------------------

    power = np.abs(fft) ** 2

    # ---------------------------------------------------------
    # 5. Convert power to dB
    #
    # IMPORTANT:
    # We do NOT normalize each block to 0 dB.
    # Therefore measurements can be compared between blocks.
    # ---------------------------------------------------------

    power_db = 10.0 * np.log10(
        np.maximum(power, 1e-20)
    )

    # ---------------------------------------------------------
    # 6. Estimate noise floor
    #
    # Median is used because strong signals should not
    # strongly influence the noise estimate.
    # ---------------------------------------------------------

    noise_floor_db = np.median(power_db)

    # ---------------------------------------------------------
    # 7. Find strongest FFT bin
    # ---------------------------------------------------------

    peak_index = np.argmax(power)

    peak_frequency_hz = frequencies_hz[peak_index]

    peak_power = power[peak_index]

    peak_power_db = power_db[peak_index]

    # ---------------------------------------------------------
    # 8. Calculate signal above noise floor
    #
    # This is effectively the peak SNR for the block.
    # ---------------------------------------------------------

    signal_above_noise_db = (
        peak_power_db - noise_floor_db
    )

    # ---------------------------------------------------------
    # 9. Return everything
    # ---------------------------------------------------------

    return {
        "timestamp": timestamp,

        # Complete spectrum
        "frequencies_hz": frequencies_hz,
        "power": power,
        "power_db": power_db,

        # Noise measurement
        "noise_floor_db": noise_floor_db,

        # Peak measurement
        "peak_frequency_hz": peak_frequency_hz,
        "peak_power": peak_power,
        "peak_power_db": peak_power_db,

        # Signal relative to noise
        "signal_above_noise_db": signal_above_noise_db,
    }