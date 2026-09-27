#!/usr/bin/env python3

"""
LFMF Monitor - Station System Telemetry

Collects system health information from the Raspberry Pi
monitoring station and writes periodic telemetry records.

Telemetry includes:

    - Timestamp
    - Hostname
    - Station ID
    - Uptime
    - CPU usage
    - CPU temperature
    - CPU frequency
    - CPU load
    - RAM usage
    - Swap usage
    - Disk usage
    - Disk I/O
    - Network traffic
    - Wi-Fi signal
    - Power/throttling status
    - Process count
    - LFMF monitor process information
    - RTL-SDR USB presence
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil
import yaml


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_FILE = PROJECT_ROOT / "config" / "receiver.yaml"

TELEMETRY_DIR = PROJECT_ROOT / "data" / "telemetry"
TELEMETRY_FILE = TELEMETRY_DIR / "station_telemetry.log"


# ============================================================
# Configuration
# ============================================================

TELEMETRY_INTERVAL_SECONDS = 60


# ============================================================
# Station information
# ============================================================

def get_station_id() -> str:
    """Read station ID from receiver.yaml."""

    try:
        with open(CONFIG_FILE, "r") as f:
            config = yaml.safe_load(f) or {}

        return config.get("station", {}).get(
            "station_id",
            "unknown",
        )

    except Exception:
        return "unknown"


# ============================================================
# CPU temperature
# ============================================================

def get_cpu_temperature() -> float | None:
    """Return CPU temperature in Celsius."""

    try:
        temperatures = psutil.sensors_temperatures()

        for name in ("cpu_thermal", "cpu_thermal_zone", "coretemp"):
            if name in temperatures:
                entries = temperatures[name]

                if entries:
                    return round(entries[0].current, 2)

        # Raspberry Pi fallback
        thermal_file = Path(
            "/sys/class/thermal/thermal_zone0/temp"
        )

        if thermal_file.exists():
            value = int(thermal_file.read_text().strip())
            return round(value / 1000.0, 2)

    except Exception:
        pass

    return None


# ============================================================
# CPU frequency
# ============================================================

def get_cpu_frequency() -> float | None:
    """Return current CPU frequency in MHz."""

    try:
        frequency = psutil.cpu_freq()

        if frequency:
            return round(frequency.current, 2)

    except Exception:
        pass

    return None


# ============================================================
# CPU governor
# ============================================================

def get_cpu_governor() -> str | None:
    """Return CPU frequency governor."""

    governor_file = Path(
        "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    )

    try:
        if governor_file.exists():
            return governor_file.read_text().strip()
    except Exception:
        pass

    return None


# ============================================================
# Raspberry Pi throttling
# ============================================================

def get_throttling_status() -> dict:
    """
    Read Raspberry Pi throttling state.

    vcgencmd is available on Raspberry Pi systems with
    the appropriate firmware utilities installed.
    """

    result = {
        "available": False,
        "raw": None,
    }

    try:
        process = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True,
            text=True,
            timeout=2,
        )

        if process.returncode == 0:
            result["available"] = True
            result["raw"] = process.stdout.strip()

    except Exception:
        pass

    return result


# ============================================================
# Wi-Fi signal
# ============================================================

def get_wifi_signal() -> dict:
    """Get Wi-Fi signal information using iwconfig."""

    result = {
        "interface": None,
        "signal_dbm": None,
        "link": None,
    }

    try:
        interfaces = psutil.net_if_stats()

        for interface in interfaces:

            if interface.startswith(("wl", "wlan")):

                result["interface"] = interface

                process = subprocess.run(
                    ["iw", "dev", interface, "link"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )

                output = process.stdout

                for line in output.splitlines():

                    line = line.strip()

                    if line.startswith("signal:"):
                        parts = line.split()

                        if len(parts) >= 2:
                            result["signal_dbm"] = float(parts[1])

                    elif line.startswith("SSID:"):
                        result["link"] = line.split(":", 1)[1].strip()

                break

    except Exception:
        pass

    return result


# ============================================================
# Network statistics
# ============================================================

def get_network_stats() -> dict:
    """Return network interface statistics."""

    stats = {}

    try:
        counters = psutil.net_io_counters(pernic=True)

        for interface, data in counters.items():

            stats[interface] = {
                "rx_bytes": data.bytes_recv,
                "tx_bytes": data.bytes_sent,
                "rx_packets": data.packets_recv,
                "tx_packets": data.packets_sent,
                "errors_in": data.errin,
                "errors_out": data.errout,
                "drops_in": data.dropin,
                "drops_out": data.dropout,
            }

    except Exception:
        pass

    return stats


# ============================================================
# Disk statistics
# ============================================================

def get_disk_stats() -> dict:
    """Return disk usage and disk I/O statistics."""

    result = {
        "usage": {},
        "io": {},
    }

    try:
        partitions = psutil.disk_partitions(
            all=False
        )

        for partition in partitions:

            mountpoint = partition.mountpoint

            try:
                usage = psutil.disk_usage(mountpoint)

                result["usage"][mountpoint] = {
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "percent": usage.percent,
                }

            except PermissionError:
                continue

    except Exception:
        pass

    try:
        io = psutil.disk_io_counters()

        if io:

            result["io"] = {
                "read_bytes": io.read_bytes,
                "write_bytes": io.write_bytes,
                "read_count": io.read_count,
                "write_count": io.write_count,
            }

    except Exception:
        pass

    return result


# ============================================================
# Memory
# ============================================================

def get_memory_stats() -> dict:
    """Return RAM and swap usage."""

    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "ram": {
            "total_bytes": memory.total,
            "used_bytes": memory.used,
            "available_bytes": memory.available,
            "percent": memory.percent,
        },
        "swap": {
            "total_bytes": swap.total,
            "used_bytes": swap.used,
            "free_bytes": swap.free,
            "percent": swap.percent,
        },
    }


# ============================================================
# Load
# ============================================================

def get_load() -> dict:
    """Return system load averages."""

    load1, load5, load15 = os.getloadavg()

    return {
        "1min": round(load1, 2),
        "5min": round(load5, 2),
        "15min": round(load15, 2),
    }


# ============================================================
# Process information
# ============================================================

def get_process_stats() -> dict:
    """Return process counts and LFMF process information."""

    result = {
        "process_count": 0,
        "lfmf_processes": [],
    }

    try:
        result["process_count"] = len(
            psutil.pids()
        )

        for process in psutil.process_iter(
            ["pid", "name", "cmdline", "cpu_percent", "memory_percent"]
        ):

            try:
                info = process.info

                cmdline = " ".join(
                    info.get("cmdline") or []
                )

                if (
                    "lfmf_monitor" in cmdline
                    or "lfmf_monitor" in (info.get("name") or "")
                ):

                    result["lfmf_processes"].append({
                        "pid": info["pid"],
                        "name": info["name"],
                        "cmdline": cmdline,
                        "cpu_percent": info["cpu_percent"],
                        "memory_percent": round(
                            info["memory_percent"] or 0,
                            2,
                        ),
                    })

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
            ):
                continue

    except Exception:
        pass

    return result


# ============================================================
# RTL-SDR detection
# ============================================================

def get_rtlsdr_status() -> dict:
    """Check whether an RTL-SDR device is visible."""

    result = {
        "present": False,
        "devices": [],
    }

    try:
        process = subprocess.run(
            ["lsusb"],
            capture_output=True,
            text=True,
            timeout=2,
        )

        if process.returncode == 0:

            for line in process.stdout.splitlines():

                lower = line.lower()

                if (
                    "rtl" in lower
                    or "realtek" in lower
                    or "r820" in lower
                    or "r828" in lower
                ):
                    result["present"] = True
                    result["devices"].append(
                        line.strip()
                    )

    except Exception:
        pass

    return result


# ============================================================
# Uptime
# ============================================================

def get_uptime() -> float:
    """Return system uptime in seconds."""

    try:
        return time.time() - psutil.boot_time()
    except Exception:
        return 0


# ============================================================
# Main telemetry collection
# ============================================================

def collect_telemetry() -> dict:
    """Collect one complete station telemetry record."""

    memory = get_memory_stats()

    telemetry = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),

        "hostname": socket.gethostname(),

        "station_id": get_station_id(),

        "uptime_seconds": round(
            get_uptime(),
            1,
        ),

        "cpu": {
            "usage_percent": psutil.cpu_percent(
                interval=1
            ),

            "cores_logical": psutil.cpu_count(
                logical=True
            ),

            "cores_physical": psutil.cpu_count(
                logical=False
            ),

            "temperature_c": get_cpu_temperature(),

            "frequency_mhz": get_cpu_frequency(),

            "governor": get_cpu_governor(),

            "load": get_load(),
        },

        "memory": memory,

        "disk": get_disk_stats(),

        "network": get_network_stats(),

        "wifi": get_wifi_signal(),

        "power": {
            "throttling": get_throttling_status(),
        },

        "processes": get_process_stats(),

        "rtlsdr": get_rtlsdr_status(),
    }

    return telemetry


# ============================================================
# Write telemetry
# ============================================================

def write_telemetry(data: dict) -> None:
    """Append telemetry as one JSON record."""

    TELEMETRY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        TELEMETRY_FILE,
        "a",
    ) as f:

        f.write(
            json.dumps(
                data,
                separators=(",", ":"),
            )
            + "\n"
        )


# ============================================================
# Main loop
# ============================================================

def main() -> None:

    print("LFMF Monitor Station Telemetry")
    print("--------------------------------")
    print(f"Config:     {CONFIG_FILE}")
    print(f"Log:        {TELEMETRY_FILE}")
    print(f"Station ID: {get_station_id()}")
    print(
        f"Interval:   "
        f"{TELEMETRY_INTERVAL_SECONDS} seconds"
    )
    print()

    while True:

        try:

            telemetry = collect_telemetry()

            write_telemetry(
                telemetry
            )

            print(
                f"{telemetry['timestamp']} | "
                f"CPU {telemetry['cpu']['usage_percent']:.1f}% | "
                f"Temp "
                f"{telemetry['cpu']['temperature_c']} C | "
                f"RAM "
                f"{telemetry['memory']['ram']['percent']:.1f}%"
            )

        except KeyboardInterrupt:

            print()
            print(
                "Station telemetry stopped."
            )
            break

        except Exception as exc:

            print(
                f"Telemetry error: {exc}"
            )

        time.sleep(
            TELEMETRY_INTERVAL_SECONDS
        )


if __name__ == "__main__":
    main()