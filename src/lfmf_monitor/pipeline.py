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

            # -------------------------------------------------
            # 1. Get one block of IQ samples
            # -------------------------------------------------

            timestamp, samples = receiver.read_samples()

            # -------------------------------------------------
            # 2. Calculate the complete spectrum
            # -------------------------------------------------

            result = compute_spectrum(
                samples=samples,
                sample_rate_hz=receiver.sample_rate_hz,
                center_frequency_hz=receiver.center_frequency_hz,
                timestamp=timestamp,
            )

            # -------------------------------------------------
            # 3. Extract spectrum measurements
            # -------------------------------------------------

            timestamp = result["timestamp"]

            frequencies_hz = result["frequencies_hz"]
            power = result["power"]
            power_db = result["power_db"]

            noise_floor_db = result["noise_floor_db"]

            peak_frequency_hz = result["peak_frequency_hz"]
            peak_power = result["peak_power"]
            peak_power_db = result["peak_power_db"]

            signal_above_noise_db = result[
                "signal_above_noise_db"
            ]

            # -------------------------------------------------
            # 4. Display the measurements
            # -------------------------------------------------

            print(
                f"{timestamp.isoformat()} | "
                f"Peak: {peak_frequency_hz / 1e6:.6f} MHz | "
                f"Peak Power: {peak_power_db:.2f} dB | "
                f"Noise Floor: {noise_floor_db:.2f} dB | "
                f"SNR: {signal_above_noise_db:.2f} dB"
            )

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        receiver.stop()
        print("RTL-SDR stopped.")


if __name__ == "__main__":
    run()