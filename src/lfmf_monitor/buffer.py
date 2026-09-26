from pathlib import Path
import sqlite3

import yaml


class SignalBuffer:
    """Buffer spectrum measurements and store significant signals in SQLite."""

    def __init__(
        self,
        config_path: str = "config/receiver.yaml",
        database_path: str = "data/lfmf_monitor.db",
    ):
        self.config_path = Path(config_path)
        self.database_path = Path(database_path)

        self.station_id = None
        self.min_snr_db = None
        self.min_peak_power_db = None

        self._load_config()
        self._initialize_database()

    def _load_config(self):
        """Load station identity and detection thresholds from receiver.yaml."""

        with self.config_path.open("r") as file:
            config = yaml.safe_load(file)

        station = config.get("station", {})
        detection = config.get("signal_detection", {})

        self.station_id = station["station_id"]
        self.min_snr_db = detection["min_snr_db"]
        self.min_peak_power_db = detection["min_peak_power_db"]

    def _initialize_database(self):
        """Create the SQLite database and detections table."""

        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    peak_frequency_hz REAL NOT NULL,
                    peak_power_db REAL NOT NULL,
                    noise_floor_db REAL NOT NULL,
                    snr_db REAL NOT NULL
                )
                """
            )

            connection.commit()

    def is_significant(self, result: dict) -> bool:
        """Determine whether a spectrum measurement is significant."""

        return (
            result["peak_power_db"] >= self.min_peak_power_db
            and result["snr_db"] >= self.min_snr_db
        )

    def store(self, result: dict):
        """Store and return a significant detection."""

        if not self.is_significant(result):
            return False

        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO detections (
                    timestamp,
                    peak_frequency_hz,
                    peak_power_db,
                    noise_floor_db,
                    snr_db
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    result["timestamp"],
                    result["peak_frequency_hz"],
                    result["peak_power_db"],
                    result["noise_floor_db"],
                    result["snr_db"],
                ),
            )

            connection.commit()

        return {
            "station_id": self.station_id,
            **result,
        }