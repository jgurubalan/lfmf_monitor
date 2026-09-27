import os
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml


CHECK_INTERVAL_SECONDS = 5

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

CONFIG_PATH = Path("config/receiver.yaml")

# ---------------------------------------------------------
# Log files
# ---------------------------------------------------------

LOG_PATH = Path("data/logs/watchdog.log")
ERROR_LOG_PATH = Path("data/logs/errors.log")
PIPELINE_ERROR_LOG_PATH = Path(
    "data/logs/pipeline_errors.log"
)

# ---------------------------------------------------------
# PID files
# ---------------------------------------------------------

PIPELINE_PID_FILE = Path("data/logs/pipeline.pid")
WATCHDOG_PID_FILE = Path("data/logs/watchdog.pid")

# ---------------------------------------------------------
# Intentional pipeline stop marker
# ---------------------------------------------------------

PIPELINE_STOP_REQUEST_FILE = Path(
    "data/logs/pipeline_stop_requested"
)


class Watchdog:
    """Independently monitor the LFMF pipeline and VPS connection."""

    def __init__(
        self,
        log_path: Path = LOG_PATH,
        error_log_path: Path = ERROR_LOG_PATH,
        pipeline_error_log_path: Path = (
            PIPELINE_ERROR_LOG_PATH
        ),
        pipeline_pid_file: Path = PIPELINE_PID_FILE,
        watchdog_pid_file: Path = WATCHDOG_PID_FILE,
        pipeline_stop_request_file: Path = (
            PIPELINE_STOP_REQUEST_FILE
        ),
    ):
        self.log_path = Path(log_path)
        self.error_log_path = Path(error_log_path)

        self.pipeline_error_log_path = Path(
            pipeline_error_log_path
        )

        self.pipeline_pid_file = Path(
            pipeline_pid_file
        )

        self.watchdog_pid_file = Path(
            watchdog_pid_file
        )

        self.pipeline_stop_request_file = Path(
            pipeline_stop_request_file
        )

        # -----------------------------------------------------
        # Load configuration from receiver.yaml
        # -----------------------------------------------------

        self.station_id = self._load_station_id()

        (
            self.vps_host,
            self.vps_port,
            self.transport_enabled,
        ) = self._load_transport_settings()

        self.pipeline_running = None
        self.vps_connected = None

        self._initialize_directories()

    # ---------------------------------------------------------
    # Station ID
    # ---------------------------------------------------------

    @staticmethod
    def _load_station_id():
        """Load the station ID from receiver.yaml."""

        with CONFIG_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            config = yaml.safe_load(file) or {}

        station = config.get("station", {})
        station_id = station.get("station_id")

        if not station_id:
            raise ValueError(
                f"station_id not found in {CONFIG_PATH}"
            )

        return str(station_id)

    # ---------------------------------------------------------
    # Transport configuration
    # ---------------------------------------------------------

    @staticmethod
    def _load_transport_settings():
        """
        Load VPS transport settings from receiver.yaml.

        Returns:
            tuple:
                host
                port
                enabled
        """

        with CONFIG_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            config = yaml.safe_load(file) or {}

        transport = config.get("transport", {})

        enabled = transport.get(
            "enabled",
            False,
        )

        host = transport.get("host")
        port = transport.get("port")

        if enabled and not host:
            raise ValueError(
                f"transport.host not found in {CONFIG_PATH}"
            )

        if enabled and not port:
            raise ValueError(
                f"transport.port not found in {CONFIG_PATH}"
            )

        return (
            str(host) if host else None,
            int(port) if port else None,
            bool(enabled),
        )

    # ---------------------------------------------------------
    # Initialisation
    # ---------------------------------------------------------

    def _initialize_directories(self):
        """Create the log and PID file directories."""

        self.log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.error_log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.pipeline_error_log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.pipeline_pid_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.watchdog_pid_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.pipeline_stop_request_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ---------------------------------------------------------
    # Watchdog PID
    # ---------------------------------------------------------

    def write_watchdog_pid(self):
        """Write the watchdog process PID to its PID file."""

        pid = os.getpid()

        self.watchdog_pid_file.write_text(
            str(pid),
            encoding="utf-8",
        )

        return pid

    def remove_watchdog_pid(self):
        """Remove the watchdog PID file."""

        try:
            self.watchdog_pid_file.unlink()

        except FileNotFoundError:
            pass

    # ---------------------------------------------------------
    # Intentional stop marker
    # ---------------------------------------------------------

    def intentional_stop_requested(self):
        """
        Check whether an intentional pipeline stop has
        been requested.
        """

        return self.pipeline_stop_request_file.exists()

    def remove_stop_request(self):
        """Remove the intentional pipeline stop marker."""

        try:
            self.pipeline_stop_request_file.unlink()

        except FileNotFoundError:
            pass

    # ---------------------------------------------------------
    # Timestamp
    # ---------------------------------------------------------

    @staticmethod
    def _timestamps():
        """Return UTC and local timestamps."""

        utc_now = datetime.now(timezone.utc)
        local_now = utc_now.astimezone()

        return (
            utc_now.isoformat(),
            local_now.isoformat(),
        )

    # ---------------------------------------------------------
    # Logging
    # ---------------------------------------------------------

    def _write_log(
        self,
        path: Path,
        level: str,
        component: str,
        message: str,
    ):
        """Write one log entry including the station ID."""

        utc_timestamp, local_timestamp = (
            self._timestamps()
        )

        entry = (
            f"{utc_timestamp} UTC | "
            f"{local_timestamp} LOCAL | "
            f"STATION: {self.station_id} | "
            f"{level} | "
            f"{component} | "
            f"{message}\n"
        )

        with path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(entry)

    def info(
        self,
        component: str,
        message: str,
    ):
        """Write an informational event."""

        self._write_log(
            self.log_path,
            "INFO",
            component,
            message,
        )

    def warning(
        self,
        component: str,
        message: str,
    ):
        """Write a warning event."""

        self._write_log(
            self.log_path,
            "WARNING",
            component,
            message,
        )

    def alert(
        self,
        component: str,
        message: str,
    ):
        """Write an alert event."""

        self._write_log(
            self.log_path,
            "ALERT",
            component,
            message,
        )

    def error(
        self,
        component: str,
        message: str,
    ):
        """Write an error to the separate error log."""

        self._write_log(
            self.error_log_path,
            "ERROR",
            component,
            message,
        )

    def pipeline_error(
        self,
        component: str,
        message: str,
    ):
        """Write an error to the pipeline error log."""

        self._write_log(
            self.pipeline_error_log_path,
            "ERROR",
            component,
            message,
        )

    # ---------------------------------------------------------
    # Pipeline detection
    # ---------------------------------------------------------

    def find_pipeline_pid(self):
        """
        Read the pipeline PID from the PID file.

        Returns:
            PID if the PID file contains a valid running process.
            None otherwise.
        """

        if not self.pipeline_pid_file.exists():
            return None

        try:
            pid = int(
                self.pipeline_pid_file.read_text(
                    encoding="utf-8"
                ).strip()
            )

        except (
            ValueError,
            OSError,
        ):
            return None

        if pid <= 0:
            return None

        try:
            os.kill(pid, 0)

        except ProcessLookupError:
            return None

        except PermissionError:
            # The process exists, but we cannot inspect it.
            return pid

        return pid

    # ---------------------------------------------------------
    # Pipeline monitoring
    # ---------------------------------------------------------

    def check_pipeline(self):
        """Check whether the monitoring pipeline is running."""

        pid = self.find_pipeline_pid()

        running = pid is not None

        # -----------------------------------------------------
        # First check
        # -----------------------------------------------------

        if self.pipeline_running is None:

            self.pipeline_running = running

            if running:

                self.info(
                    "monitoring",
                    f"Monitoring pipeline detected. "
                    f"PID: {pid}.",
                )

            else:

                self.warning(
                    "monitoring",
                    "Monitoring pipeline is not running.",
                )

            return

        # -----------------------------------------------------
        # Pipeline started
        # -----------------------------------------------------

        if not self.pipeline_running and running:

            self.pipeline_running = True

            self.info(
                "monitoring",
                f"Monitoring pipeline started. "
                f"PID: {pid}.",
            )

            return

        # -----------------------------------------------------
        # Pipeline stopped
        # -----------------------------------------------------

        if self.pipeline_running and not running:

            self.pipeline_running = False

            # -----------------------------------------------
            # Intentional stop
            # -----------------------------------------------

            if self.intentional_stop_requested():

                self.info(
                    "monitoring",
                    "Monitoring pipeline stopped "
                    "intentionally.",
                )

                self.remove_stop_request()

            # -----------------------------------------------
            # Unexpected stop / crash
            # -----------------------------------------------

            else:

                self.alert(
                    "monitoring",
                    "Monitoring pipeline crashed "
                    "unexpectedly.",
                )

                self.error(
                    "monitoring",
                    "Monitoring pipeline is no longer "
                    "running unexpectedly.",
                )

                self.pipeline_error(
                    "monitoring",
                    "Monitoring pipeline crashed "
                    f"unexpectedly. PID: {pid}.",
                )

            return

        # -----------------------------------------------------
        # Nothing changed
        # -----------------------------------------------------

        self.pipeline_running = running

    # ---------------------------------------------------------
    # VPS connection test
    # ---------------------------------------------------------

    def check_vps_connection(self):
        """
        Test whether the VPS TCP endpoint is reachable.

        Returns:
            True if the connection succeeds.
            False if the connection is refused or otherwise
            fails.
        """

        if not self.transport_enabled:
            return False

        with socket.create_connection(
            (self.vps_host, self.vps_port),
            timeout=5,
        ):
            return True

    # ---------------------------------------------------------
    # VPS monitoring
    # ---------------------------------------------------------

    def check_vps(self):
        """Check the VPS connection and log state changes."""

        # -----------------------------------------------------
        # Transport disabled
        # -----------------------------------------------------

        if not self.transport_enabled:

            if self.vps_connected is not False:

                self.vps_connected = False

                self.info(
                    "transport",
                    "VPS transport is disabled "
                    "in receiver.yaml.",
                )

            return

        try:

            connected = (
                self.check_vps_connection()
            )

        except ConnectionRefusedError:

            connected = False

            self.error(
                "transport",
                f"VPS connection refused: "
                f"{self.vps_host}:{self.vps_port}",
            )

        except TimeoutError:

            connected = False

            self.error(
                "transport",
                f"VPS connection timed out: "
                f"{self.vps_host}:{self.vps_port}",
            )

        except OSError as error:

            connected = False

            self.error(
                "transport",
                f"VPS connection error: {error}",
            )

        # -----------------------------------------------------
        # First check
        # -----------------------------------------------------

        if self.vps_connected is None:

            self.vps_connected = connected

            if connected:

                self.info(
                    "transport",
                    f"VPS connection established: "
                    f"{self.vps_host}:{self.vps_port}.",
                )

            else:

                self.warning(
                    "transport",
                    f"VPS is not reachable: "
                    f"{self.vps_host}:{self.vps_port}.",
                )

            return

        # -----------------------------------------------------
        # VPS connection restored
        # -----------------------------------------------------

        if not self.vps_connected and connected:

            self.vps_connected = True

            self.info(
                "transport",
                f"VPS connection restored: "
                f"{self.vps_host}:{self.vps_port}.",
            )

            return

        # -----------------------------------------------------
        # VPS connection lost
        # -----------------------------------------------------

        if self.vps_connected and not connected:

            self.vps_connected = False

            self.alert(
                "transport",
                f"VPS connection lost: "
                f"{self.vps_host}:{self.vps_port}.",
            )

            return

        # -----------------------------------------------------
        # Nothing changed
        # -----------------------------------------------------

        self.vps_connected = connected

    # ---------------------------------------------------------
    # Main watchdog loop
    # ---------------------------------------------------------

    def run(self):
        """Run the independent watchdog."""

        watchdog_pid = (
            self.write_watchdog_pid()
        )

        self.info(
            "watchdog",
            f"Watchdog started. "
            f"PID: {watchdog_pid}.",
        )

        print("LFMF watchdog started.")

        print(
            f"Station ID: {self.station_id}"
        )

        print(
            f"Watchdog PID: {watchdog_pid}"
        )

        print(
            f"Checking pipeline and VPS every "
            f"{CHECK_INTERVAL_SECONDS} seconds."
        )

        print(
            f"Pipeline PID file: "
            f"{self.pipeline_pid_file}"
        )

        print(
            f"Watchdog PID file: "
            f"{self.watchdog_pid_file}"
        )

        print(
            f"Stop request file: "
            f"{self.pipeline_stop_request_file}"
        )

        if self.transport_enabled:

            print(
                f"VPS: "
                f"{self.vps_host}:{self.vps_port}"
            )

        else:

            print(
                "VPS transport: disabled"
            )

        print(
            f"Watchdog log: "
            f"{self.log_path}"
        )

        print(
            f"Error log: "
            f"{self.error_log_path}"
        )

        print(
            f"Pipeline error log: "
            f"{self.pipeline_error_log_path}"
        )

        print()

        try:

            while True:

                self.check_pipeline()

                self.check_vps()

                time.sleep(
                    CHECK_INTERVAL_SECONDS
                )

        except KeyboardInterrupt:

            self.info(
                "watchdog",
                f"Watchdog stopped by user. "
                f"PID: {watchdog_pid}.",
            )

            print("\nWatchdog stopped.")

        except Exception as error:

            self.error(
                "watchdog",
                f"Watchdog crashed. "
                f"PID: {watchdog_pid}. "
                f"Error: {error}",
            )

            raise

        finally:

            self.remove_watchdog_pid()


def main():
    """Start the watchdog."""

    watchdog = Watchdog()
    watchdog.run()


if __name__ == "__main__":
    main()