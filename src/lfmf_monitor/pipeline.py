from lfmf_monitor.receiver import RTLSDR
from lfmf_monitor.spectrum import compute_spectrum
from lfmf_monitor.buffer import SignalBuffer
from lfmf_monitor.transport import Transport


def run():
    """Run the receiver, spectrum-processing, detection, and transport pipeline."""

    receiver = RTLSDR()
    buffer = SignalBuffer()
    transport = Transport()

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
        print(
            f"Minimum SNR: "
            f"{buffer.min_snr_db:.2f} dB"
        )
        print(
            f"Minimum Peak Power: "
            f"{buffer.min_peak_power_db:.2f} dB"
        )
        print(
            f"Transport: "
            f"{'enabled' if transport.enabled else 'disabled'}"
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
            # 3. Display the spectrum measurements
            # -------------------------------------------------

            print(
                f"{result['timestamp'].isoformat()} | "
                f"Peak: "
                f"{result['peak_frequency_hz'] / 1e6:.6f} MHz | "
                f"Peak Power: "
                f"{result['peak_power_db']:.2f} dB | "
                f"Noise Floor: "
                f"{result['noise_floor_db']:.2f} dB | "
                f"SNR: "
                f"{result['signal_above_noise_db']:.2f} dB"
            )

            # -------------------------------------------------
            # 4. Send spectrum result to buffer
            # -------------------------------------------------

            stored = buffer.store(
                {
                    "timestamp": result["timestamp"].isoformat(),
                    "peak_frequency_hz": result["peak_frequency_hz"],
                    "peak_power_db": result["peak_power_db"],
                    "noise_floor_db": result["noise_floor_db"],
                    "snr_db": result["signal_above_noise_db"],
                }
            )

            # -------------------------------------------------
            # 5. Send only significant detections to VPS
            # -------------------------------------------------

            if stored:
                print(
                    ">>> Significant signal detected "
                    "and stored in database."
                )

                response = transport.send(
                    {
                        "type": "EVENT",
                        **stored,
                    }
                )

                print(
                    f">>> VPS response: {response}"
                )

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        receiver.stop()
        print("RTL-SDR stopped.")


if __name__ == "__main__":
    run()