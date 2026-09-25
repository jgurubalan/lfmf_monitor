import numpy as np

from lfmf_monitor.rtl import RTLSDR
from lfmf_monitor.spectrum import compute_spectrum


def main():
    center_frequency_hz = 1_000_000
    sample_rate_hz = 2_400_000
    num_samples = 240_000

    rtl = RTLSDR(
        center_frequency_hz=center_frequency_hz,
        sample_rate_hz=sample_rate_hz,
        gain="auto",
    )

    try:
        rtl.start()

        samples = rtl.read_samples(num_samples)

        frequencies, power, power_db = compute_spectrum(
            samples,
            sample_rate_hz=sample_rate_hz,
            center_frequency_hz=center_frequency_hz,
        )

        peak_index = np.argmax(power)

        print()
        print("Spectrum test successful")
        print(f"IQ samples:       {len(samples)}")
        print(f"FFT bins:         {len(power)}")
        print(f"Frequency range:  {frequencies[0]:.0f} Hz to {frequencies[-1]:.0f} Hz")
        print(f"Peak frequency:   {frequencies[peak_index]:.2f} Hz")
        print(f"Peak power:       {power[peak_index]:.2f}")
        print(f"Power range:      {np.min(power_db):.2f} dB to {np.max(power_db):.2f} dB")

    finally:
        rtl.stop()


if __name__ == "__main__":
    main()
