from pathlib import Path
import subprocess


class LogBackup:
    """Back up the watchdog log to the VPS."""

    def __init__(
        self,
        log_path: str = "data/logs/watchdog.log",
        vps_host: str = "169.58.129.177",
        vps_user: str = "jgurubalan",
        vps_path: str = "~/projects/lfmf_monitoring/data/backups/watchdog/",
    ):
        self.log_path = Path(log_path)
        self.vps_host = vps_host
        self.vps_user = vps_user
        self.vps_path = vps_path

    def backup(self):
        """Copy the current watchdog log to the VPS."""

        if not self.log_path.exists():
            print(">>> Watchdog log does not exist.")
            return False

        destination = (
            f"{self.vps_user}@{self.vps_host}:{self.vps_path}"
        )

        command = [
            "scp",
            str(self.log_path),
            destination,
        ]

        try:
            subprocess.run(
                command,
                check=True,
                timeout=60,
            )

            print(">>> Watchdog log backup completed.")
            return True

        except subprocess.TimeoutExpired:
            print(">>> Watchdog log backup timed out.")
            return False

        except subprocess.CalledProcessError as exc:
            print(
                f">>> Watchdog log backup failed "
                f"(exit code {exc.returncode})."
            )
            return False

        except OSError as exc:
            print(f">>> Watchdog log backup error: {exc}")
            return False