from pathlib import Path
import subprocess


class LogBackup:
    """Back up the watchdog log to the LFMF Monitor VPS."""

    def __init__(
        self,
        log_path: str = "data/logs/watchdog.log",
        ssh_alias: str = "lfmf-monitor-vps",
        remote_path: str = (
            "/home/jgurubalan/"
            "projects/lfmf_monitoring/"
            "data/backups/watchdog"
        ),
    ):
        self.log_path = Path(log_path)
        self.ssh_alias = ssh_alias
        self.remote_path = remote_path

    def backup(self):
        """Copy the watchdog log to the VPS."""

        if not self.log_path.exists():
            print(">>> Watchdog log does not exist.")
            return False

        try:
            # Make sure the remote directory exists.
            subprocess.run(
                [
                    "ssh",
                    self.ssh_alias,
                    f"mkdir -p '{self.remote_path}'",
                ],
                check=True,
                timeout=30,
            )

            # Copy the watchdog log.
            subprocess.run(
                [
                    "scp",
                    str(self.log_path),
                    f"{self.ssh_alias}:{self.remote_path}/",
                ],
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