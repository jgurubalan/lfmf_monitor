import os
import socket
import time
from datetime import datetime, timezone
from pathlib import Path


CHECK_INTERVAL_SECONDS = 5

# ---------------------------------------------------------
# Log files
# ---------------------------------------------------------

LOG_PATH = Path("data/logs/watchdog.log")
ERROR_LOG_PATH = Path("data/logs/errors.log")

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

# ---------------------------------------------------------
# VPS connection
# ---------------------------------------------------------
# Replace these with the actual VPS endpoint used by
# transport.py.

VPS_HOST = "127.0.0.1"
VPS_PORT = 5000


class Watchdog:
    """Independently monitor the LFMF pipeline and VPS connection."""

    def __init__(
        self,
        log_path: Path = LOG_PATH,
        error_log_path: Path = ERROR_LOG_PATH,
        pipeline_pid_file: Path = PIPELINE_PID_FILE,
        watchdog_pid_file: Path = WATCHDOG_PID_FILE,
        pipeline_stop_request_file: Path = (
            PIPELINE_STOP_REQUEST_FILE
        ),
    ):
        self.log_path = Path(log_path)
        self.error_log_path = Path(error_log_path)

        self.pipeline_pid_file = Path(
            pipeline_pid_file
        )

        self.watchdog_pid_file = Path(
            watchdog_pid_file
        )

        self.pipeline_stop_request_file = Path(
            pipeline_stop_request_file
        )

        self.pipeline_running = None
        self.vps_connected = None

        self._initialize_directories()

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
        """Write one log entry."""

        utc_timestamp, local_timestamp = (
            self._timestamps()
        )

        entry = (
            f"{utc_timestamp} UTC | "
            f"{local_timestamp} LOCAL | "
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

            return

        # -----------------------------------------------------
        # Nothing changed
        # -----------------------------------------------------

        self.pipeline_running = running

    # ---------------------------------------------------------
    # VPS connection test
    # ---------------------------------------------------------

    @staticmethod
    def check_vps_connection():
        """
        Test whether the VPS TCP endpoint is reachable.

        Returns:
            True if the connection succeeds.
            False if the connection is refused or otherwise
            fails.
        """

        with socket.create_connection(
            (VPS_HOST, VPS_PORT),
            timeout=5,
        ):
            return True

    # ---------------------------------------------------------
    # VPS monitoring
    # ---------------------------------------------------------

    def check_vps(self):
        """Check the VPS connection and log state changes."""

        try:

            connected = (
                self.check_vps_connection()
            )

        except ConnectionRefusedError:

            connected = False

            self.error(
                "transport",
                f"VPS connection refused: "
                f"{VPS_HOST}:{VPS_PORT}",
            )

        except TimeoutError:

            connected = False

            self.error(
                "transport",
                f"VPS connection timed out: "
                f"{VPS_HOST}:{VPS_PORT}",
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
                    f"{VPS_HOST}:{VPS_PORT}.",
                )

            else:

                self.warning(
                    "transport",
                    f"VPS is not reachable: "
                    f"{VPS_HOST}:{VPS_PORT}.",
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
                f"{VPS_HOST}:{VPS_PORT}.",
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
                f"{VPS_HOST}:{VPS_PORT}.",
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

        print(
            f"VPS: "
            f"{VPS_HOST}:{VPS_PORT}"
        )

        print(
            f"Watchdog log: "
            f"{self.log_path}"
        )

        print(
            f"Error log: "
            f"{self.error_log_path}"
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

            self.alert(
                "watchdog",
                "Watchdog stopped because of an "
                "unexpected error.",
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