from pathlib import Path
import sqlite3
from datetime import datetime, timezone


class Watchdog:
    """Record operational events from the monitoring system."""

    def __init__(
        self,
        database_path: str = "data/lfmf_watchdog.db",
        log_path: str = "data/logs/watchdog.log",
    ):
        self.database_path = Path(database_path)
        self.log_path = Path(log_path)

        # Track VPS connectivity state.
        self.vps_online = None

        self._initialize_database()
        self._initialize_log_directory()

    def _initialize_database(self):
        """Create the watchdog database and events table."""

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS watchdog_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    component TEXT NOT NULL,
                    message TEXT NOT NULL
                )
                """
            )

            connection.commit()

    def _initialize_log_directory(self):
        """Create the directory containing the watchdog log."""

        self.log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def record(
        self,
        level: str,
        component: str,
        message: str,
    ):
        """Record one watchdog event."""

        timestamp = datetime.now(timezone.utc).isoformat()

        # Save to SQLite.
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO watchdog_events (
                    timestamp,
                    level,
                    component,
                    message
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    timestamp,
                    level,
                    component,
                    message,
                ),
            )

            connection.commit()

            event_id = cursor.lastrowid

        # Save to text log.
        log_entry = (
            f"{timestamp} | "
            f"{level} | "
            f"{component} | "
            f"{message}\n"
        )

        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(log_entry)

        return event_id

    def info(
        self,
        component: str,
        message: str,
    ):
        """Record an informational event."""

        return self.record(
            level="INFO",
            component=component,
            message=message,
        )

    def warning(
        self,
        component: str,
        message: str,
    ):
        """Record a warning event."""

        return self.record(
            level="WARNING",
            component=component,
            message=message,
        )

    def alert(
        self,
        component: str,
        message: str,
    ):
        """Record an alert event."""

        return self.record(
            level="ALERT",
            component=component,
            message=message,
        )

    def vps_offline(self, message: str):
        """Record that the VPS connection is unavailable."""

        # Do not repeatedly log the same offline condition.
        if self.vps_online is False:
            return None

        self.vps_online = False

        return self.warning(
            "transport",
            message,
        )

    def vps_restored(self):
        """Record that the VPS connection has been restored."""

        # Only log restoration if we previously knew the VPS was offline.
        if self.vps_online is not False:
            self.vps_online = True
            return None

        self.vps_online = True

        return self.info(
            "transport",
            "VPS connection restored.",
        )