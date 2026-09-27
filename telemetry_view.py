import json
from pathlib import Path


TELEMETRY_LOG = Path("data/telemetry/station_telemetry.log")


def load_latest_record():
    """Load the latest valid JSON record from the telemetry log."""

    if not TELEMETRY_LOG.exists():
        raise FileNotFoundError(
            f"Telemetry log not found: {TELEMETRY_LOG}"
        )

    latest = None

    with TELEMETRY_LOG.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                latest = json.loads(line)
            except json.JSONDecodeError:
                continue

    if latest is None:
        raise ValueError("No valid telemetry records found.")

    return latest


def show(record):
    timestamps = record.get("timestamps", {})
    station = record.get("station", {})
    system = record.get("system", {})
    power = system.get("raspberry_pi_power", {})
    throttled = power.get("throttled", {})
    cpu = record.get("cpu", {})
    temperature = cpu.get("temperature", {})
    memory = record.get("memory", {})
    ram = memory.get("ram", {})
    swap = memory.get("swap", {})
    disk = record.get("disk", {})
    rtl_sdr = record.get("rtl_sdr", {})
    processes = record.get("lfmf_processes", {})
    network = record.get("network", {})

    print()
    print("=" * 60)
    print("              LFMF STATION TELEMETRY")
    print("=" * 60)

    print(f"Station       : {station.get('station_id', 'Unknown')}")
    print(f"Hostname      : {system.get('hostname', 'Unknown')}")
    print(f"Local time    : {timestamps.get('local', 'Unknown')}")
    print(f"UTC time      : {timestamps.get('utc', 'Unknown')}")
    print()

    print("SYSTEM")
    print("-" * 60)
    print(f"Uptime        : {system.get('uptime_seconds', 0):,.0f} seconds")
    print(f"Processes     : {system.get('process_count', 'Unknown')}")
    print(f"Python        : {system.get('python_version', 'Unknown')}")
    print()

    print("CPU")
    print("-" * 60)
    print(f"Usage         : {cpu.get('usage_percent', 0):.1f} %")
    print(f"Temperature   : {temperature.get('temperature_c', 0):.2f} °C")
    print(
        f"Frequency     : "
        f"{cpu.get('frequency', {}).get('current_mhz', 0):.0f} MHz"
    )
    print(
        f"Load average  : "
        f"{cpu.get('load_average', {}).get('1_min', 0):.2f} / "
        f"{cpu.get('load_average', {}).get('5_min', 0):.2f} / "
        f"{cpu.get('load_average', {}).get('15_min', 0):.2f}"
    )
    print()

    print("MEMORY")
    print("-" * 60)
    print(f"RAM usage     : {ram.get('usage_percent', 0):.1f} %")
    print(f"RAM available : {ram.get('available_bytes', 0) / 1024**2:.0f} MB")
    print(f"Swap usage    : {swap.get('usage_percent', 0):.1f} %")
    print()

    print("RASPBERRY PI POWER / THERMAL")
    print("-" * 60)
    print(f"Currently throttled      : {throttled.get('currently_throttled')}")
    print(
        f"Frequency capped now    : "
        f"{throttled.get('arm_frequency_capped_now')}"
    )
    print(
        f"Soft temperature limit  : "
        f"{throttled.get('soft_temperature_limit_now')}"
    )
    print(
        f"Throttling occurred     : "
        f"{throttled.get('throttling_occurred')}"
    )
    print(
        f"Frequency cap occurred  : "
        f"{throttled.get('arm_frequency_capped_occurred')}"
    )
    print(
        f"Soft temp limit occurred: "
        f"{throttled.get('soft_temperature_limit_occurred')}"
    )
    print()

    print("LFMF PROCESSES")
    print("-" * 60)

    if isinstance(processes, list):
        for process in processes:
            print(
                f"{process.get('command', 'unknown'):35} "
                f"PID {process.get('pid', '?'):>7}  "
                f"CPU {process.get('cpu_percent', 0):>5.1f}%  "
                f"MEM {process.get('memory_percent', 0):>5.2f}%"
            )

    print()

    print("RTL-SDR")
    print("-" * 60)
    print(f"Available     : {rtl_sdr.get('available')}")
    print(f"Detected      : {rtl_sdr.get('detected')}")

    if rtl_sdr.get("devices"):
        for device in rtl_sdr["devices"]:
            print(f"Device        : {device}")

    print()

    print("NETWORK")
    print("-" * 60)

    for name, interface in network.items():
        if not interface.get("is_up"):
            status = "DOWN"
        else:
            status = "UP"

        print(
            f"{name:<8} {status:<5} "
            f"RX {interface.get('bytes_received', 0):>12,} bytes  "
            f"TX {interface.get('bytes_sent', 0):>12,} bytes"
        )

    print()

    print("DISK")
    print("-" * 60)
    print(f"Path          : {disk.get('path', 'Unknown')}")
    print(f"Usage         : {disk.get('usage_percent', 0):.1f} %")
    print(
        f"Free          : "
        f"{disk.get('free_bytes', 0) / 1024**3:.2f} GB"
    )

    print()
    print("=" * 60)


def main():
    try:
        record = load_latest_record()
        show(record)

    except Exception as error:
        print(f"ERROR: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()