from lfmf_monitor.receiver import RTLSDR
from lfmf_monitor.spectrum import compute_spectrum


def run():
    """Run the receiver and spectrum-processing pipeline."""

    receiver = RTLSDR()

    try:
        receiver.start()

        print("Monitoring started.")
        print(
            f"Center frequency: "
            f"{receiver.center_frequency_hz / 1e6:.3f} MHz"
        )
        print(
            f"Sample rate: "
            f"{receiver.sample_rate_hz / 1e6:.3f} MS/s"
        )
        print(
            f"Block size: "
            f"{receiver.block_size} samples"
        )
        print()

        while True:

            # Get one block of IQ samples
            timestamp, samples = receiver.read_samples()

            # Convert IQ samples into a frequency spectrum
            (
                timestamp,
                frequencies_hz,
                power,
                power_db,
            ) = compute_spectrum(
                samples=samples,
                sample_rate_hz=receiver.sample_rate_hz,
                center_frequency_hz=receiver.center_frequency_hz,
                timestamp=timestamp,
            )

            # Find strongest frequency in this spectrum
            peak_index = power.argmax()

            peak_frequency_hz = frequencies_hz[peak_index]
            peak_power_db = power_db[peak_index]

            print(
                f"{timestamp.isoformat()} | "
                f"Peak: {peak_frequency_hz / 1e6:.6f} MHz | "
                f"Power: {peak_power_db:.2f} dB"
            )

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        receiver.stop()
        print("RTL-SDR stopped.")


if __name__ == "__main__":
    run()