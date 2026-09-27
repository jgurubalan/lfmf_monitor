import time

from lfmf_monitor.receiver import RTLSDR
from lfmf_monitor.spectrum import compute_spectrum
from lfmf_monitor.buffer import SignalBuffer
from lfmf_monitor.transport import Transport


VPS_CHECK_INTERVAL_SECONDS = 60


def run():
    receiver = RTLSDR()
    buffer = SignalBuffer()
    transport = Transport()

    last_vps_check = 0.0

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
        print(
            f"VPS health check: "
            f"every {VPS_CHECK_INTERVAL_SECONDS} seconds"
        )
        print()

        while True:

            # -------------------------------------------------
            # Receive one block of IQ samples.
            #
            # receiver.py returns:
            #
            #   1. UTC timestamp
            #   2. Local timestamp
            #   3. IQ samples
            # -------------------------------------------------

            utc_timestamp, local_timestamp, samples = (
                receiver.read_samples()
            )

            # -------------------------------------------------
            # Process the IQ samples.
            # -------------------------------------------------

            result = compute_spectrum(
                samples=samples,
                sample_rate_hz=receiver.sample_rate_hz,
                center_frequency_hz=receiver.center_frequency_hz,
                timestamp=utc_timestamp,
            )

            # -------------------------------------------------
            # Add both timestamps to the result.
            # -------------------------------------------------

            result["utc_timestamp"] = (
                utc_timestamp.isoformat()
            )

            result["local_timestamp"] = (
                local_timestamp.isoformat()
            )

            # -------------------------------------------------
            # Display spectrum information.
            # -------------------------------------------------

            print(
                f"UTC: {result['utc_timestamp']} | "
                f"Local: {result['local_timestamp']} | "
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
            # Store only significant signals.
            # -------------------------------------------------

            stored = buffer.store(
                {
                    "timestamp": result["utc_timestamp"],
                    "local_timestamp": result["local_timestamp"],
                    "peak_frequency_hz": (
                        result["peak_frequency_hz"]
                    ),
                    "peak_power_db": (
                        result["peak_power_db"]
                    ),
                    "noise_floor_db": (
                        result["noise_floor_db"]
                    ),
                    "snr_db": (
                        result["signal_above_noise_db"]
                    ),
                }
            )

            # -------------------------------------------------
            # Send significant event to VPS.
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

            # -------------------------------------------------
            # Periodic VPS health check.
            # -------------------------------------------------

            current_time = time.monotonic()

            if (
                transport.enabled
                and current_time - last_vps_check
                >= VPS_CHECK_INTERVAL_SECONDS
            ):
                transport.check_connection()

                last_vps_check = current_time

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        receiver.stop()
        print("RTL-SDR stopped.")


if __name__ == "__main__":
    run()