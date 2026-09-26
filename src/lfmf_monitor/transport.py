from pathlib import Path
import json
import socket

import yaml

from lfmf_monitor.watchdog import Watchdog


class Transport:
    """Send detection data to the LFMF server."""

    def __init__(
        self,
        config_path: str = "config/receiver.yaml",
        watchdog: Watchdog | None = None,
    ):
        self.config_path = Path(config_path)
        self.watchdog = watchdog

        self.host = None
        self.port = None
        self.timeout_seconds = None
        self.enabled = False

        self._load_config()

    def _load_config(self):
        """Load transport settings from receiver.yaml."""

        with self.config_path.open("r") as file:
            config = yaml.safe_load(file)

        transport = config.get("transport", {})

        self.enabled = transport.get("enabled", False)
        self.host = transport["host"]
        self.port = transport["port"]
        self.timeout_seconds = transport.get(
            "timeout_seconds",
            10,
        )

    def check_connection(self):
        """Check whether the VPS accepts a TCP connection."""

        if not self.enabled:
            return False

        try:
            with socket.create_connection(
                (self.host, self.port),
                timeout=self.timeout_seconds,
            ):
                pass

            if self.watchdog is not None:
                self.watchdog.vps_restored()

            return True

        except ConnectionRefusedError:

            message = (
                "VPS connection refused. "
                "Server may be stopped."
            )

            print(f">>> {message}")

            if self.watchdog is not None:
                self.watchdog.vps_offline(message)

            return False

        except socket.timeout:

            message = "VPS connection timed out."

            print(f">>> {message}")

            if self.watchdog is not None:
                self.watchdog.vps_offline(message)

            return False

        except OSError as exc:

            message = f"VPS connection error: {exc}"

            print(f">>> {message}")

            if self.watchdog is not None:
                self.watchdog.vps_offline(message)

            return False

    def send(self, result: dict):
        """Send one detection to the server."""

        if not self.enabled:
            return None

        message = json.dumps(result) + "\n"

        try:
            with socket.create_connection(
                (self.host, self.port),
                timeout=self.timeout_seconds,
            ) as connection:

                connection.sendall(
                    message.encode("utf-8")
                )

                response = connection.recv(4096)

            if self.watchdog is not None:
                self.watchdog.vps_restored()

            return response.decode("utf-8").strip()

        except ConnectionRefusedError:

            message = (
                "VPS connection refused. "
                "Server may be stopped."
            )

            print(f">>> {message}")

            if self.watchdog is not None:
                self.watchdog.vps_offline(message)

            return None

        except socket.timeout:

            message = "VPS connection timed out."

            print(f">>> {message}")

            if self.watchdog is not None:
                self.watchdog.vps_offline(message)

            return None

        except ConnectionResetError:

            message = (
                "VPS connection was reset "
                "before a response was received."
            )

            print(f">>> {message}")

            if self.watchdog is not None:
                self.watchdog.vps_offline(message)

            return None

        except OSError as exc:

            message = f"VPS connection error: {exc}"

            print(f">>> {message}")

            if self.watchdog is not None:
                self.watchdog.vps_offline(message)

            return None