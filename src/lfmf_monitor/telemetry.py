#!/usr/bin/env python3

"""
LFMF Monitor - Station Telemetry

Collects system and monitoring-station health information
and stores it locally as JSON Lines.

Telemetry includes:
    - Station ID
    - UTC timestamp
    - Local timestamp
    - Timezone
    - Hostname
    - OS / kernel
    - Python version
    - Uptime
    - CPU usage
    - CPU temperature
    - CPU frequency
    - CPU load
    - CPU governor
    - RAM
    - Swap
    - Disk usage
    - Disk I/O
    - Network traffic
    - Network errors/drops
    - Wi-Fi signal
    - Raspberry Pi throttling / undervoltage
    - LFMF process information
    - RTL-SDR presence
    - Telemetry log size

Output:
    data/telemetry/station_telemetry.log

Format:
    JSON Lines

The program runs continuously until Ctrl+C is pressed.
"""

import json
import os
import platform
import re
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import psutil
import yaml


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RECEIVER_CONFIG_FILE = (
    PROJECT_ROOT / "config" / "receiver.yaml"
)

LOCATION_CONFIG_FILE = (
    PROJECT_ROOT / "config" / "location.yaml"
)

TELEMETRY_DIR = (
    PROJECT_ROOT / "data" / "telemetry"
)

LOG_FILE = (
    TELEMETRY_DIR / "station_telemetry.log"
)


# ============================================================
# Configuration
# ============================================================

TELEMETRY_INTERVAL_SECONDS = 60


# ============================================================
# Load configuration
# ============================================================

def load_yaml(path):
    """Load a YAML configuration file."""

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:

            return yaml.safe_load(file) or {}

    except Exception:
        return {}


RECEIVER_CONFIG = load_yaml(
    RECEIVER_CONFIG_FILE
)

LOCATION_CONFIG = load_yaml(
    LOCATION_CONFIG_FILE
)


# ============================================================
# Station information
# ============================================================

STATION_CONFIG = RECEIVER_CONFIG.get(
    "station",
    {}
)

STATION_ID = STATION_CONFIG.get(
    "station_id",
    "unknown",
)


# ============================================================
# Timezone
# ============================================================

LOCATION_SECTION = LOCATION_CONFIG.get(
    "location",
    {}
)

LOCAL_TIMEZONE = LOCATION_SECTION.get(
    "timezone",
    "Asia/Kolkata",
)


# ============================================================
# Utility functions
# ============================================================

def run_command(command, timeout=5):
    """Run a system command safely."""

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        return result.stdout.strip()

    except Exception:
        return None


def get_file_size(path):
    """Return file size in bytes."""

    try:
        return path.stat().st_size

    except (
        FileNotFoundError,
        OSError,
    ):
        return 0


# ============================================================
# Timestamp
# ============================================================

def get_timestamps():
    """
    Return both UTC and local timestamps.

    UTC is used for station-to-station synchronization.

    Local time is useful for human-readable logs.
    """

    now_utc = datetime.now(
        timezone.utc
    )

    try:

        local_zone = ZoneInfo(
            LOCAL_TIMEZONE
        )

        now_local = now_utc.astimezone(
            local_zone
        )

    except Exception:

        now_local = now_utc

    return {
        "utc": now_utc.isoformat(),

        "local": now_local.isoformat(),

        "timezone": LOCAL_TIMEZONE,
    }


# ============================================================
# CPU temperature
# ============================================================

def get_cpu_temperature():
    """Get CPU temperature."""

    # First try psutil sensors
    try:

        temperatures = (
            psutil.sensors_temperatures()
        )

        if temperatures:

            for name, entries in temperatures.items():

                for entry in entries:

                    if entry.current is not None:

                        return {
                            "sensor": name,
                            "temperature_c": (
                                entry.current
                            ),
                        }

    except Exception:
        pass

    # Raspberry Pi fallback
    output = run_command(
        ["vcgencmd", "measure_temp"]
    )

    if output:

        match = re.search(
            r"([\d.]+)",
            output,
        )

        if match:

            return {
                "sensor": "vcgencmd",

                "temperature_c": float(
                    match.group(1)
                ),
            }

    return {
        "sensor": None,
        "temperature_c": None,
    }


# ============================================================
# CPU frequency
# ============================================================

def get_cpu_frequency():
    """Get CPU frequency."""

    try:

        frequency = psutil.cpu_freq()

        if frequency:

            return {
                "current_mhz": (
                    frequency.current
                ),

                "min_mhz": (
                    frequency.min
                ),

                "max_mhz": (
                    frequency.max
                ),
            }

    except Exception:
        pass

    return None


# ============================================================
# CPU governor
# ============================================================

def get_cpu_governor():
    """Get CPU frequency governor."""

    governors = []

    cpu_dir = Path(
        "/sys/devices/system/cpu"
    )

    for path in cpu_dir.glob(
        "cpu[0-9]*/cpufreq/scaling_governor"
    ):

        try:

            governor = (
                path.read_text()
                .strip()
            )

            governors.append(
                {
                    "cpu": path.parts[-3],
                    "governor": governor,
                }
            )

        except OSError:
            pass

    return governors


# ============================================================
# CPU
# ============================================================

def get_cpu():
    """Collect CPU information."""

    try:

        load_1, load_5, load_15 = (
            os.getloadavg()
        )

    except OSError:

        load_1 = None
        load_5 = None
        load_15 = None

    return {

        "usage_percent": (
            psutil.cpu_percent(
                interval=1
            )
        ),

        "usage_per_cpu_percent": (
            psutil.cpu_percent(
                interval=None,
                percpu=True,
            )
        ),

        "logical_cores": (
            psutil.cpu_count(
                logical=True
            )
        ),

        "physical_cores": (
            psutil.cpu_count(
                logical=False
            )
        ),

        "load_average": {

            "1_min": load_1,

            "5_min": load_5,

            "15_min": load_15,
        },

        "frequency": (
            get_cpu_frequency()
        ),

        "governor": (
            get_cpu_governor()
        ),

        "temperature": (
            get_cpu_temperature()
        ),
    }


# ============================================================
# Memory
# ============================================================

def get_memory():
    """Collect RAM and swap information."""

    memory = (
        psutil.virtual_memory()
    )

    swap = (
        psutil.swap_memory()
    )

    return {

        "ram": {

            "total_bytes": (
                memory.total
            ),

            "available_bytes": (
                memory.available
            ),

            "used_bytes": (
                memory.used
            ),

            "free_bytes": (
                memory.free
            ),

            "usage_percent": (
                memory.percent
            ),
        },

        "swap": {

            "total_bytes": (
                swap.total
            ),

            "used_bytes": (
                swap.used
            ),

            "free_bytes": (
                swap.free
            ),

            "usage_percent": (
                swap.percent
            ),
        },
    }


# ============================================================
# Disk
# ============================================================

def get_disk():
    """Collect filesystem and disk information."""

    disk_path = str(
        PROJECT_ROOT
    )

    usage = psutil.disk_usage(
        disk_path
    )

    result = {

        "path": disk_path,

        "total_bytes": (
            usage.total
        ),

        "used_bytes": (
            usage.used
        ),

        "free_bytes": (
            usage.free
        ),

        "usage_percent": (
            usage.percent
        ),

        "partitions": [],

        "io": None,
    }

    # Filesystem partitions
    try:

        partitions = (
            psutil.disk_partitions()
        )

        for partition in partitions:

            try:

                partition_usage = (
                    psutil.disk_usage(
                        partition.mountpoint
                    )
                )

                result["partitions"].append(
                    {

                        "device": (
                            partition.device
                        ),

                        "mountpoint": (
                            partition.mountpoint
                        ),

                        "filesystem": (
                            partition.fstype
                        ),

                        "total_bytes": (
                            partition_usage.total
                        ),

                        "used_bytes": (
                            partition_usage.used
                        ),

                        "free_bytes": (
                            partition_usage.free
                        ),

                        "usage_percent": (
                            partition_usage.percent
                        ),
                    }
                )

            except (
                PermissionError,
                OSError,
            ):
                pass

    except Exception:
        pass

    # Disk I/O
    try:

        io = (
            psutil.disk_io_counters()
        )

        if io:

            result["io"] = {

                "read_bytes": (
                    io.read_bytes
                ),

                "write_bytes": (
                    io.write_bytes
                ),

                "read_count": (
                    io.read_count
                ),

                "write_count": (
                    io.write_count
                ),

                "read_time_ms": (
                    io.read_time
                ),

                "write_time_ms": (
                    io.write_time
                ),
            }

    except Exception:
        pass

    return result


# ============================================================
# Network
# ============================================================

def get_network():
    """Collect network interface statistics."""

    interfaces = {}

    counters = (
        psutil.net_io_counters(
            pernic=True
        )
    )

    addresses = (
        psutil.net_if_addrs()
    )

    stats = (
        psutil.net_if_stats()
    )

    for interface, counter in (
        counters.items()
    ):

        interface_info = {

            "is_up": (
                stats[interface].isup
                if interface in stats
                else None
            ),

            "speed_mbps": (
                stats[interface].speed
                if interface in stats
                else None
            ),

            "bytes_sent": (
                counter.bytes_sent
            ),

            "bytes_received": (
                counter.bytes_recv
            ),

            "packets_sent": (
                counter.packets_sent
            ),

            "packets_received": (
                counter.packets_recv
            ),

            "errors_in": (
                counter.errin
            ),

            "errors_out": (
                counter.errout
            ),

            "drops_in": (
                counter.dropin
            ),

            "drops_out": (
                counter.dropout
            ),

            "addresses": [],
        }

        for address in (
            addresses.get(
                interface,
                []
            )
        ):

            interface_info[
                "addresses"
            ].append(
                {

                    "family": str(
                        address.family
                    ),

                    "address": (
                        address.address
                    ),

                    "netmask": (
                        address.netmask
                    ),
                }
            )

        interfaces[
            interface
        ] = interface_info

    return interfaces


# ============================================================
# Wi-Fi
# ============================================================

def get_wifi_signal():
    """Get Wi-Fi SSID and signal strength."""

    result = {}

    interfaces = (
        psutil.net_if_stats()
    )

    for interface in interfaces:

        if not (
            interface.startswith("wl")
            or interface.startswith("wlan")
        ):
            continue

        output = run_command(
            [
                "iw",
                "dev",
                interface,
                "link",
            ]
        )

        if not output:
            continue

        result[interface] = {

            "connected": (
                "Connected" in output
            ),

            "ssid": None,

            "signal_dbm": None,
        }

        ssid_match = re.search(
            r"SSID:\s*(.+)",
            output,
        )

        if ssid_match:

            result[interface][
                "ssid"
            ] = (
                ssid_match.group(1).strip()
            )

        signal_match = re.search(
            r"signal:\s*(-?\d+)\s*dBm",
            output,
        )

        if signal_match:

            result[interface][
                "signal_dbm"
            ] = int(
                signal_match.group(1)
            )

    return result


# ============================================================
# Raspberry Pi power / throttling
# ============================================================

def get_raspberry_pi_power():
    """
    Get Raspberry Pi throttling and
    undervoltage status.

    This does NOT measure actual watts.
    """

    result = {

        "available": False,

        "throttled": None,

        "raw": None,
    }

    output = run_command(
        ["vcgencmd", "get_throttled"]
    )

    if not output:
        return result

    result["available"] = True

    result["raw"] = output

    match = re.search(
        r"throttled=0x([0-9a-fA-F]+)",
        output,
    )

    if not match:
        return result

    value = int(
        match.group(1),
        16,
    )

    result["throttled"] = {

        "raw_value": value,

        "under_voltage_now": (
            bool(value & 0x1)
        ),

        "arm_frequency_capped_now": (
            bool(value & 0x2)
        ),

        "currently_throttled": (
            bool(value & 0x4)
        ),

        "soft_temperature_limit_now": (
            bool(value & 0x8)
        ),

        "under_voltage_occurred": (
            bool(value & 0x10000)
        ),

        "arm_frequency_capped_occurred": (
            bool(value & 0x20000)
        ),

        "throttling_occurred": (
            bool(value & 0x40000)
        ),

        "soft_temperature_limit_occurred": (
            bool(value & 0x80000)
        ),
    }

    return result


# ============================================================
# System information
# ============================================================

def get_system():
    """Collect general system information."""

    boot_time = (
        psutil.boot_time()
    )

    uptime_seconds = (
        time.time() - boot_time
    )

    return {

        "hostname": (
            socket.gethostname()
        ),

        "platform": (
            platform.platform()
        ),

        "system": (
            platform.system()
        ),

        "release": (
            platform.release()
        ),

        "machine": (
            platform.machine()
        ),

        "python_version": (
            platform.python_version()
        ),

        "boot_time": (
            datetime.fromtimestamp(
                boot_time,
                timezone.utc,
            ).isoformat()
        ),

        "uptime_seconds": int(
            uptime_seconds
        ),

        "process_count": len(
            psutil.pids()
        ),

        "raspberry_pi_power": (
            get_raspberry_pi_power()
        ),
    }


# ============================================================
# LFMF process monitoring
# ============================================================

def get_lfmf_processes():
    """Find running LFMF Monitor processes."""

    processes = []

    for process in psutil.process_iter(
        [
            "pid",
            "name",
            "cmdline",
            "cpu_percent",
            "memory_percent",
            "status",
        ]
    ):

        try:

            info = process.info

            cmdline = (
                info.get("cmdline")
                or []
            )

            command = " ".join(
                cmdline
            )

            name = (
                info.get("name")
                or ""
            )

            if (
                "lfmf_monitor" in command
                or "lfmf_monitor" in name
            ):

                processes.append(
                    {

                        "pid": info["pid"],

                        "name": name,

                        "command": command,

                        "cpu_percent": (
                            info["cpu_percent"]
                        ),

                        "memory_percent": (
                            info["memory_percent"]
                        ),

                        "status": (
                            info["status"]
                        ),
                    }
                )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
        ):

            continue

    return processes


# ============================================================
# RTL-SDR
# ============================================================

def get_rtl_sdr():
    """Check whether an RTL-SDR device is visible."""

    output = run_command(
        ["lsusb"]
    )

    if not output:

        return {

            "available": False,

            "detected": None,

            "devices": [],
        }

    devices = []

    for line in output.splitlines():

        lower = line.lower()

        if (
            "realtek" in lower
            or "rtl2832" in lower
            or "rtl-sdr" in lower
            or "r820" in lower
            or "r828" in lower
        ):

            devices.append(
                line.strip()
            )

    return {

        "available": True,

        "detected": (
            len(devices) > 0
        ),

        "devices": devices,
    }


# ============================================================
# Telemetry log information
# ============================================================

def get_telemetry_log():
    """Get telemetry log information."""

    return {

        "path": str(
            LOG_FILE
        ),

        "size_bytes": (
            get_file_size(
                LOG_FILE
            )
        ),
    }


# ============================================================
# Complete telemetry record
# ============================================================

def collect_telemetry():
    """Collect all telemetry."""

    return {

        "schema_version": 1,

        "type": "station_telemetry",

        "timestamps": (
            get_timestamps()
        ),

        "station": {

            "station_id": (
                STATION_ID
            ),
        },

        "system": (
            get_system()
        ),

        "cpu": (
            get_cpu()
        ),

        "memory": (
            get_memory()
        ),

        "disk": (
            get_disk()
        ),

        "network": (
            get_network()
        ),

        "wifi": (
            get_wifi_signal()
        ),

        "lfmf_processes": (
            get_lfmf_processes()
        ),

        "rtl_sdr": (
            get_rtl_sdr()
        ),

        "telemetry_log": (
            get_telemetry_log()
        ),
    }


# ============================================================
# Write telemetry
# ============================================================

def write_telemetry(telemetry):
    """Append telemetry record to JSONL file."""

    TELEMETRY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        LOG_FILE,
        "a",
        encoding="utf-8",
    ) as file:

        json.dump(
            telemetry,
            file,
            separators=(",", ":"),
        )

        file.write("\n")


# ============================================================
# Console summary
# ============================================================

def print_summary(telemetry):
    """Print short human-readable summary."""

    cpu = telemetry["cpu"]

    memory = telemetry["memory"]

    temperature = (
        cpu["temperature"]
    )

    temp = temperature.get(
        "temperature_c"
    )

    cpu_usage = (
        cpu.get("usage_percent")
    )

    ram_usage = (
        memory["ram"].get(
            "usage_percent"
        )
    )

    temp_text = (
        f"{temp:.1f} C"
        if temp is not None
        else "N/A"
    )

    timestamps = (
        telemetry["timestamps"]
    )

    print(
        f"{timestamps['local']} | "
        f"CPU {cpu_usage:.1f}% | "
        f"Temp {temp_text} | "
        f"RAM {ram_usage:.1f}%"
    )


# ============================================================
# Main
# ============================================================

def main():
    """Main telemetry loop."""

    print(
        "LFMF Monitor Station Telemetry"
    )

    print(
        "--------------------------------"
    )

    print(
        f"Config:     "
        f"{RECEIVER_CONFIG_FILE}"
    )

    print(
        f"Location:   "
        f"{LOCATION_CONFIG_FILE}"
    )

    print(
        f"Log:        "
        f"{LOG_FILE}"
    )

    print(
        f"Station ID: "
        f"{STATION_ID}"
    )

    print(
        f"Timezone:   "
        f"{LOCAL_TIMEZONE}"
    )

    print(
        f"Interval:   "
        f"{TELEMETRY_INTERVAL_SECONDS} seconds"
    )

    print()

    print(
        "Press Ctrl+C to stop telemetry."
    )

    print()

    try:

        while True:

            telemetry = (
                collect_telemetry()
            )

            write_telemetry(
                telemetry
            )

            print_summary(
                telemetry
            )

            time.sleep(
                TELEMETRY_INTERVAL_SECONDS
            )

    except KeyboardInterrupt:

        print()

        print(
            "--------------------------------"
        )

        print(
            "Telemetry stopped by user."
        )

        print(
            "--------------------------------"
        )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":

    main()