import requests


class VPSTransport:
    """Send significant detections to the VPS."""

    def __init__(
        self,
        server_url: str,
        timeout: int = 10,
    ):
        self.server_url = server_url
        self.timeout = timeout

    def send(self, result: dict) -> bool:
        """Send one detection to the VPS."""

        try:
            response = requests.post(
                self.server_url,
                json=result,
                timeout=self.timeout,
            )

            response.raise_for_status()

            return True

        except requests.RequestException as error:
            print(f"VPS transport error: {error}")
            return False