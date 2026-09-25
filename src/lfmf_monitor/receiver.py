import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml


class RTLSDR:
    """Interface to an RTL-SDR device using the rtl_sdr command."""

    def __init__(
        self,
        center_frequency_hz: int | None = None,
        sample_rate_hz: int | None = None,
        block_size: int | None = None,
        gain: str | None = None,
        device: int | None = None,
    ):
        # Project root:
        #
        # lfmf_monitor/
        # ├── config/
        # │   └── receiver.yaml
        # └── src/
        #     └── lfmf_monitor/
        #         └── receiver.py
        #
        project_root = Path(__file__).resolve().parents[2]
        config_path = project_root / "config" / "receiver.yaml"

        # Load receiver configuration.
        with config_path.open("r", encoding="utf-8") as file:
            config = yaml.safe_load(file)

        if "receiver" not in config:
            raise ValueError(
                "receiver.yaml does not contain a 'receiver' section"
            )

        receiver_config = config["receiver"]

        # Use explicitly supplied values if provided.
        # Otherwise use values from receiver.yaml.
        self.center_frequency_hz = (
            center_frequency_hz
            if center_frequency_hz is not None
            else receiver_config["center_frequency_hz"]
        )

        self.sample_rate_hz = (
            sample_rate_hz
            if sample_rate_hz is not None
            else receiver_config["sample_rate_hz"]
        )

        self.block_size = (
            block_size
            if block_size is not None
            else receiver_config["block_size"]
        )

        self.gain = (
            gain
            if gain is not None
            else receiver_config.get("gain", "auto")
        )

        self.device = (
            device
            if device is not None
            else receiver_config.get("device", 0)
        )

        if self.block_size <= 0:
            raise ValueError("block_size must be greater than zero")

        if self.sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be greater than zero")

        self.process = None

    def start(self) -> None:
        """Start rtl_sdr and begin streaming IQ samples."""

        if self.process is not None:
            raise RuntimeError("RTL-SDR is already running")

        command = [
            "rtl_sdr",
            "-d",
            str(self.device),
            "-f",
            str(self.center_frequency_hz),
            "-s",
            str(self.sample_rate_hz),
        ]

        if self.gain != "auto":
            command.extend(["-g", str(self.gain)])

        # "-" tells rtl_sdr to send raw IQ samples to stdout.
        command.append("-")

        print("Starting RTL-SDR:")
        print(" ".join(command))

        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "rtl_sdr command was not found. "
                "Make sure the rtl-sdr package is installed."
            ) from exc

    def read_samples(
        self,
        num_samples: int | None = None,
    ) -> tuple[datetime, np.ndarray]:
        """
        Read one block of complex I/Q samples.

        Returns:
            timestamp:
                UTC timestamp representing the beginning of the
                block read operation.

            samples:
                Complex I/Q samples.
        """

        if self.process is None or self.process.stdout is None:
            raise RuntimeError("RTL-SDR is not running")

        # Use configured block size unless explicitly overridden.
        if num_samples is None:
            num_samples = self.block_size

        if num_samples <= 0:
            raise ValueError("num_samples must be greater than zero")

        # Record the timestamp before reading the block.
        #
        # This timestamp represents the beginning of the block
        # acquisition from the Python application's perspective.
        timestamp = datetime.now(timezone.utc)

        # Each RTL-SDR sample contains:
        #
        #   I byte + Q byte
        #
        # Therefore there are 2 bytes per complex sample.
        num_bytes = num_samples * 2

        raw = bytearray()

        while len(raw) < num_bytes:
            chunk = self.process.stdout.read(num_bytes - len(raw))

            if not chunk:
                raise RuntimeError(
                    f"RTL-SDR stream ended early: "
                    f"received {len(raw)} of {num_bytes} bytes"
                )

            raw.extend(chunk)

        # Convert raw bytes into unsigned 8-bit values.
        iq = np.frombuffer(raw, dtype=np.uint8)

        # Center the unsigned 8-bit values around zero.
        i = iq[0::2].astype(np.float32) - 127.5
        q = iq[1::2].astype(np.float32) - 127.5

        # Combine I and Q into complex samples.
        samples = (i + 1j * q).astype(np.complex64)

        return timestamp, samples

    def stop(self) -> None:
        """Stop rtl_sdr and release the RTL-SDR device."""

        if self.process is None:
            return

        self.process.terminate()

        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()

        self.process = None