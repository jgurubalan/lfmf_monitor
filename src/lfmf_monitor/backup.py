from datetime import datetime, timezone
from pathlib import Path
import logging
import subprocess
import time

import yaml


class LogBackup:
    """Back up LFMF logs to the VPS every 15 minutes."""

    BACKUP_INTERVAL_SECONDS = 15 * 60

    CONFIG_PATH = Path("config/receiver.yaml")

    def __init__(
        self,
        log_directory: str = "data/logs",
        ssh_alias: str = "lfmf-monitor-vps",
        remote_base_path: str = (
            "/home/jgurubalan/"
            "projects/lfmf_monitoring/"
            "data/backups/watchdog"
        ),
    ):
        self.log_directory = Path(log_directory)

        self.ssh_alias = ssh_alias
        self.remote_base_path = remote_base_path

        # -----------------------------------------------------
        # Load station ID
        # -----------------------------------------------------

        self.station_id = self._load_station_id()

        # -----------------------------------------------------
        # Remote destination for this station
        # -----------------------------------------------------

        self.remote_path = (
            f"{self.remote_base_path}/{self.station_id}"
        )

        # -----------------------------------------------------
        # Local log files to back up
        # -----------------------------------------------------

        self.watchdog_log = (
            self.log_directory / "watchdog.log"
        )

        self.errors_log = (
            self.log_directory / "errors.log"
        )

        self.pipeline_errors_log = (
            self.log_directory / "pipeline_errors.log"
        )

        self.telemetry_log = (
            Path("data/telemetry/station_telemetry.log")
        )

        self.connection_state = None

        self._setup_logging()

    # ---------------------------------------------------------
    # Station ID
    # ---------------------------------------------------------

    @classmethod
    def _load_station_id(cls):
        """Load the station ID from receiver.yaml."""

        with cls.CONFIG_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            config = yaml.safe_load(file) or {}

        station = config.get("station", {})
        station_id = station.get("station_id")

        if not station_id:
            raise ValueError(
                f"station_id not found in "
                f"{cls.CONFIG_PATH}"
            )

        return str(station_id)

    # ---------------------------------------------------------
    # Logging
    # ---------------------------------------------------------

    def _setup_logging(self):
        """Configure backup logging."""

        self.log_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.logger = logging.getLogger("backup")

        self.logger.setLevel(logging.INFO)

        self.logger.propagate = False

        if not self.logger.handlers:

            handler = logging.FileHandler(
                self.watchdog_log
            )

            handler.setLevel(logging.INFO)

            formatter = BackupLogFormatter(
                self.station_id
            )

            handler.setFormatter(formatter)

            self.logger.addHandler(handler)

    # ---------------------------------------------------------
    # VPS connection check
    # ---------------------------------------------------------

    def check_connection(self):
        """Check whether the VPS is reachable over SSH."""

        try:

            subprocess.run(
                [
                    "ssh",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "ConnectTimeout=10",
                    self.ssh_alias,
                    "true",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=15,
            )

            connected = True

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            OSError,
        ):

            connected = False

        # -----------------------------------------------------
        # Log only when connection state changes
        # -----------------------------------------------------

        if self.connection_state is None:

            self.connection_state = connected

            if connected:

                self.logger.info(
                    "VPS connection established."
                )

            else:

                self.logger.warning(
                    f"VPS is not reachable: "
                    f"{self.ssh_alias}."
                )

        elif connected and not self.connection_state:

            self.connection_state = True

            self.logger.info(
                "VPS connection restored."
            )

        elif not connected and self.connection_state:

            self.connection_state = False

            self.logger.warning(
                "VPS connection lost."
            )

        return connected

    # ---------------------------------------------------------
    # Backup one file
    # ---------------------------------------------------------

    def _backup_file(self, log_path: Path):
        """Copy one log file to the station's VPS folder."""

        if not log_path.exists():

            self.logger.warning(
                f"Log file does not exist: "
                f"{log_path}"
            )

            return False

        try:

            subprocess.run(
                [
                    "scp",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "ConnectTimeout=10",
                    str(log_path),
                    f"{self.ssh_alias}:"
                    f"{self.remote_path}/",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=60,
            )

            self.logger.info(
                f"Backup completed: "
                f"{log_path.name}."
            )

            return True

        except subprocess.TimeoutExpired:

            self.logger.error(
                f"Backup timed out: "
                f"{log_path.name}."
            )

            return False

        except subprocess.CalledProcessError as exc:

            self.logger.error(
                f"Backup failed: "
                f"{log_path.name} "
                f"(exit code {exc.returncode})."
            )

            return False

        except OSError as exc:

            self.logger.error(
                f"Backup error: "
                f"{log_path.name}: {exc}"
            )

            return False

    # ---------------------------------------------------------
    # Create remote directory
    # ---------------------------------------------------------

    def _ensure_remote_directory(self):
        """Make sure the station backup directory exists on the VPS."""

        try:

            subprocess.run(
                [
                    "ssh",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "ConnectTimeout=10",
                    self.ssh_alias,
                    f"mkdir -p '{self.remote_path}'",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=30,
            )

            return True

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            OSError,
        ):

            self.logger.error(
                "Unable to create remote station "
                f"backup directory: {self.remote_path}"
            )

            return False

    # ---------------------------------------------------------
    # Perform backup
    # ---------------------------------------------------------

    def backup(self):
        """
        Back up watchdog.log, errors.log,
        pipeline_errors.log, and telemetry.log.
        """

        self.logger.info(
            "Starting log backup."
        )

        # -----------------------------------------------------
        # Check VPS connection first
        # -----------------------------------------------------

        if not self.check_connection():

            self.logger.warning(
                "Log backup skipped because "
                "the VPS is not reachable."
            )

            return False

        # -----------------------------------------------------
        # Make sure station remote directory exists
        # -----------------------------------------------------

        if not self._ensure_remote_directory():

            return False

        # -----------------------------------------------------
        # Back up watchdog.log
        # -----------------------------------------------------

        watchdog_success = self._backup_file(
            self.watchdog_log
        )

        # -----------------------------------------------------
        # Back up errors.log
        # -----------------------------------------------------

        errors_success = self._backup_file(
            self.errors_log
        )

        # -----------------------------------------------------
        # Back up pipeline_errors.log
        # -----------------------------------------------------

        pipeline_errors_success = self._backup_file(
            self.pipeline_errors_log
        )

        # -----------------------------------------------------
        # Back up telemetry.log
        # -----------------------------------------------------

        telemetry_success = self._backup_file(
            self.telemetry_log
        )

        # -----------------------------------------------------
        # Overall result
        # -----------------------------------------------------

        if (
            watchdog_success
            or errors_success
            or pipeline_errors_success
            or telemetry_success
        ):

            self.logger.info(
                "Log backup cycle completed."
            )

            return True

        self.logger.warning(
            "Log backup cycle completed "
            "without successfully backing up any logs."
        )

        return False

    # ---------------------------------------------------------
    # Main backup loop
    # ---------------------------------------------------------

    def run(self):
        """Continuously back up logs every 15 minutes."""

        self.logger.info(
            "LFMF log backup started."
        )

        self.logger.info(
            "Station ID: "
            f"{self.station_id}"
        )

        self.logger.info(
            "Backup interval: "
            f"{self.BACKUP_INTERVAL_SECONDS // 60} minutes."
        )

        self.logger.info(
            f"VPS: {self.ssh_alias}"
        )

        self.logger.info(
            f"Remote base directory: "
            f"{self.remote_base_path}"
        )

        self.logger.info(
            f"Station backup directory: "
            f"{self.remote_path}"
        )

        self.logger.info(
            f"Watchdog log: {self.watchdog_log}"
        )

        self.logger.info(
            f"Error log: {self.errors_log}"
        )

        self.logger.info(
            f"Pipeline errors log: "
            f"{self.pipeline_errors_log}"
        )

        self.logger.info(
            f"Telemetry log: "
            f"{self.telemetry_log}"
        )

        try:

            while True:

                self.backup()

                self.logger.info(
                    "Next log backup in 15 minutes."
                )

                time.sleep(
                    self.BACKUP_INTERVAL_SECONDS
                )

        except KeyboardInterrupt:

            self.logger.info(
                "LFMF log backup stopped by user."
            )


# -------------------------------------------------------------
# Custom formatter with station ID, UTC and local timestamps
# -------------------------------------------------------------

class BackupLogFormatter(logging.Formatter):

    def __init__(self, station_id):
        super().__init__()
        self.station_id = station_id

    def format(self, record):

        utc_now = datetime.now(
            timezone.utc
        )

        local_now = utc_now.astimezone()

        return (
            f"{utc_now.isoformat()} UTC | "
            f"{local_now.isoformat()} LOCAL | "
            f"STATION: {self.station_id} | "
            f"{record.levelname} | "
            f"{record.name} | "
            f"{record.getMessage()}"
        )


# -------------------------------------------------------------
# Entry point
# -------------------------------------------------------------

def main():
    """Start the periodic log backup."""

    backup = LogBackup()

    backup.run()


if __name__ == "__main__":
    main()