import json
from datetime import datetime


def event_to_message(
    station_id: str,
    timestamp: datetime,
    peak_frequency_hz: float,
    peak_power_db: float,
    noise_floor_db: float,
    snr_db: float,
) -> str:
    """Create a protocol message for a significant signal event."""

    message = {
        "type": "EVENT",
        "station_id": station_id,
        "timestamp": timestamp.isoformat(),
        "peak_frequency_hz": peak_frequency_hz,
        "peak_power_db": peak_power_db,
        "noise_floor_db": noise_floor_db,
        "snr_db": snr_db,
    }

    return json.dumps(message)


def parse_message(message: str) -> dict:
    """Convert a JSON protocol message into a Python dictionary."""

    return json.loads(message)