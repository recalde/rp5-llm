"""Live hardware snapshot. RAM and the device name come from the machine, not a constant."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
from pathlib import Path


def collect(detect_script: Path) -> dict:
    detected = _run_detect(detect_script)
    model = str(detected.get("model") or "unknown")
    mem_kib = _optional_int(detected.get("mem_kib"))
    avail_kib = _optional_int(detected.get("root_avail_kib"))
    temp_c = _temperature_c()
    vulkan = _vulkan()
    ip = lan_ipv4()
    return {
        "model": model,
        "device": device_name(model),
        "os": detected.get("os") or "unknown",
        "kernel": detected.get("kernel") or "unknown",
        "arch": detected.get("arch") or "unknown",
        "cpuCores": detected.get("cpu_cores") or "unknown",
        "mem": detected.get("mem") or "unknown",
        "memKib": mem_kib,
        "rootAvailKib": avail_kib,
        "rootFilesystem": detected.get("root_fstype") or "unknown",
        "temperatureC": temp_c,
        "vulkan": vulkan,
        "ip": ip,
    }


def checks(info: dict) -> list[dict]:
    items = []
    linux_ok = info.get("os") == "Linux" and info.get("arch") == "aarch64"
    items.append(_check("linux", "pass" if linux_ok else "warn", f"{info.get('os')} {info.get('arch')}"))
    avail = info.get("rootAvailKib")
    if isinstance(avail, int) and avail >= 8 * 1024 * 1024:
        items.append(_check("storage", "pass", f"{avail // 1024} MiB free"))
    elif isinstance(avail, int):
        items.append(_check("storage", "warn", f"{avail // 1024} MiB free"))
    else:
        items.append(_check("storage", "warn", "free space unknown"))
    items.append(_check("networking", "pass" if info.get("ip") else "warn", info.get("ip") or "no IPv4 address"))
    vulkan = info.get("vulkan") or {}
    items.append(
        _check(
            "vulkan",
            "pass" if vulkan.get("present") else "warn",
            "tools found" if vulkan.get("present") else "not detected",
        )
    )
    temp = info.get("temperatureC")
    if temp is None:
        items.append(_check("temperature", "warn", "no thermal zone"))
    elif temp >= 90:
        items.append(_check("temperature", "warn", f"{temp:.0f} C"))
    else:
        items.append(_check("temperature", "pass", f"{temp:.0f} C"))
    return items


def device_name(model: str) -> str:
    lowered = model.lower()
    if "retroid" in lowered or "rp5" in lowered or "sm8250" in lowered:
        return "Retroid Pocket 5"
    if model and model != "unknown":
        return model
    return "unknown"


def lan_ipv4() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 80))
        address = sock.getsockname()[0]
    except OSError:
        return ""
    finally:
        sock.close()
    if address.startswith("127."):
        return ""
    return address


def _check(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


def _run_detect(script: Path) -> dict:
    if not script.is_file():
        return {}
    try:
        completed = subprocess.run(
            [str(script), "--json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if completed.returncode != 0:
        return {}
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _temperature_c() -> float | None:
    zone = Path("/sys/class/thermal")
    if not zone.is_dir():
        return None
    hottest = None
    for path in zone.glob("thermal_zone*/temp"):
        try:
            raw = int(path.read_text().strip())
        except (OSError, ValueError):
            continue
        celsius = raw / 1000 if raw > 1000 else float(raw)
        hottest = celsius if hottest is None else max(hottest, celsius)
    return hottest


def _vulkan() -> dict:
    present = shutil.which("vulkaninfo") is not None
    icd = Path("/usr/share/vulkan/icd.d")
    if icd.is_dir() and any(icd.glob("*.json")):
        present = True
    return {"present": present}


def _optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
