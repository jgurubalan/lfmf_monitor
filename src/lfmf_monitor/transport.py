from pathlib import Path
import json
import socket

import yaml


class Transport:
    """Send detection data to the LFMF server."""

    def __init__(
        self,
        config_path: str = "config/receiver.yaml",
    ):
        self.config_path = Path(config_path)

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
        self.timeout_seconds = transport.get("timeout_seconds", 10)

    def send(self, result: dict):
        """Send one detection to the server."""

        if not self.enabled:
            return None

        message = json.dumps(result) + "\n"

        with socket.create_connection(
            (self.host, self.port),
            timeout=self.timeout_seconds,
        ) as connection:

            connection.sendall(message.encode("utf-8"))

            response = connection.recv(4096)

        return response.decode("utf-8").strip()