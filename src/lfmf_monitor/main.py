import random
import socket
import time
from datetime import datetime, timezone

from src.common.config import load_config
from src.common.models import Station, SpectrumMeasurement
from src.common.protocol import (
    parse_message,
    spectrum_to_message,
    station_to_message,
    status_to_message,
)


SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8765
CONFIG_PATH = "config/station.yaml"


def send_message(connection, message: str) -> dict:
    connection.sendall((message + "\n").encode("utf-8"))

    response = connection.recv(65536).decode("utf-8").strip()

    return parse_message(response)


def create_test_spectrum(
    station_id: str,
    config: dict,
) -> SpectrumMeasurement:

    center_frequency = config["rf"]["center_frequency_hz"]

    frequencies = [
        center_frequency - 25000 + (i * 500)
        for i in range(101)
    ]

    power = []

    for frequency in frequencies:
        noise = random.uniform(-95.0, -85.0)

        distance = abs(frequency - center_frequency)

        if distance <= 1000:
            signal = -45.0 + random.uniform(-3.0, 3.0)
        else:
            signal = noise

        power.append(signal)

    return SpectrumMeasurement(
        station_id=station_id,
        timestamp=datetime.now(timezone.utc),
        center_frequency_hz=center_frequency,
        sample_rate_hz=config["rf"]["sample_rate_hz"],
        frequencies_hz=frequencies,
        power_db=power,
    )


def main():
    config = load_config(CONFIG_PATH)

    station = Station(
        station_id=config["station_id"],
        name=config["name"],
        location="unknown",
    )

    print(f"Connecting to {SERVER_HOST}:{SERVER_PORT}")

    with socket.create_connection((SERVER_HOST, SERVER_PORT)) as connection:

        response = send_message(
            connection,
            station_to_message(station),
        )

        print(f"HELLO response: {response}")

        response = send_message(
            connection,
            status_to_message(
                station_id=station.station_id,
                status="online",
            ),
        )

        print(f"STATUS response: {response}")

        print("Starting simulated spectrum stream")

        while True:
            measurement = create_test_spectrum(
                station.station_id,
                config,
            )

            response = send_message(
                connection,
                spectrum_to_message(measurement),
            )

            print(f"SPECTRUM response: {response}")

            time.sleep(5)


if __name__ == "__main__":
    main()