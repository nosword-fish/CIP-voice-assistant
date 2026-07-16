"""
Every function here is a tool the assistant is allowed to call.

SECURITY PRINCIPLE: the LLM never gets raw shell/subprocess access.
It can only call these specific, hand-written functions. Each one
validates its own inputs. If you want a new capability, add a new
function here deliberately -- don't add a generic "run_command" tool.
"""
import psutil
import subprocess
import os
import platform
import json

# Allowlist of apps this assistant is permitted to open.
# Add entries here as you trust more apps -- never let the model
# supply an arbitrary path/command.
ALLOWED_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
}

# Directories the assistant is allowed to read files/list contents from.
# Keeps it from being asked to snoop around the whole filesystem.
ALLOWED_READ_DIRS = [
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Documents"),
]


def get_system_stats() -> dict:
    """CPU, RAM, disk usage snapshot."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "ram_percent": psutil.virtual_memory().percent,
        "ram_used_gb": round(psutil.virtual_memory().used / 1e9, 1),
        "ram_total_gb": round(psutil.virtual_memory().total / 1e9, 1),
        "disk_percent": psutil.disk_usage("/").percent,
        "os": platform.platform(),
    }


def list_processes(top_n: int = 10) -> list:
    """Top N processes by memory usage."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: x.get("memory_percent") or 0, reverse=True)
    return procs[:top_n]


def open_app(app_name: str) -> str:
    """Open an application from the allowlist only."""
    key = app_name.strip().lower()
    if key not in ALLOWED_APPS:
        return f"'{app_name}' is not in the allowed app list. Allowed: {list(ALLOWED_APPS.keys())}"
    subprocess.Popen(ALLOWED_APPS[key])
    return f"Opened {app_name}."


def list_directory(dir_name: str) -> list:
    """List files in an allowed directory only (Desktop, Documents)."""
    matches = [d for d in ALLOWED_READ_DIRS if os.path.basename(d).lower() == dir_name.lower()]
    if not matches:
        return [f"'{dir_name}' is not an allowed directory. Allowed: Desktop, Documents"]
    return os.listdir(matches[0])


def get_network_connections() -> list:
    """List active outbound/listening network connections -- useful for security checks."""
    conns = []
    for c in psutil.net_connections(kind="inet"):
        if c.status == "LISTEN" or c.raddr:
            conns.append({
                "local": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else None,
                "remote": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else None,
                "status": c.status,
                "pid": c.pid,
            })
    return conns


def check_security_status() -> dict:
    """
    Check Windows Firewall (per network profile) and Windows Defender status.
    Runs two FIXED PowerShell commands -- the model cannot alter or supply
    its own command text, it can only trigger this exact function.
    """
    try:
        fw_result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetFirewallProfile | Select-Object Name, Enabled | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10
        )
        fw_data = json.loads(fw_result.stdout) if fw_result.stdout.strip() else "No firewall data returned"
    except Exception as e:
        fw_data = f"Could not read firewall status: {e}"

    try:
        defender_result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-MpComputerStatus | Select-Object AntivirusEnabled, RealTimeProtectionEnabled | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10
        )
        defender_data = (
            json.loads(defender_result.stdout)
            if defender_result.stdout.strip()
            else "Windows Defender status unavailable (may be using third-party antivirus instead)"
        )
    except Exception as e:
        defender_data = f"Could not read Defender status: {e}"

    return {"firewall_profiles": fw_data, "windows_defender": defender_data}


# Ports considered routine for a normal home/office machine. Anything outbound
# to a non-private IP on a port NOT in this set gets flagged for review --
# this is a simple heuristic, not a real threat-detection engine.
COMMON_SAFE_PORTS = {80, 443, 53, 123, 3389, 445, 135, 139}


def get_network_report() -> dict:
    """
    Active network connections with basic anomaly flags: outbound connections
    to public IPs on uncommon ports get called out separately.
    """
    conns = get_network_connections()
    flagged = []

    for c in conns:
        remote = c.get("remote")
        if not remote:
            continue
        ip, _, port_str = remote.rpartition(":")
        try:
            port_num = int(port_str)
        except ValueError:
            continue

        is_private = ip.startswith(("10.", "192.168.", "127.")) or ip.startswith("172.")
        if not is_private and port_num not in COMMON_SAFE_PORTS:
            flagged.append({**c, "reason": f"Outbound to external IP on uncommon port {port_num}"})

    return {
        "total_connections": len(conns),
        "flagged_count": len(flagged),
        "flagged": flagged,
        "all_connections": conns,
    }


# Common, expected Windows/user processes. Anything not on this list isn't
# necessarily malicious -- just unfamiliar enough to be worth a second look.
COMMON_WINDOWS_PROCESSES = {
    "svchost.exe", "explorer.exe", "system", "system idle process", "csrss.exe",
    "wininit.exe", "services.exe", "lsass.exe", "winlogon.exe", "smss.exe",
    "spoolsv.exe", "dwm.exe", "taskhostw.exe", "runtimebroker.exe", "conhost.exe",
    "searchindexer.exe", "sihost.exe", "fontdrvhost.exe", "audiodg.exe",
    "python.exe", "pythonw.exe", "chrome.exe", "firefox.exe", "msedge.exe",
    "code.exe", "notepad.exe", "calc.exe", "cmd.exe", "powershell.exe",
}


def audit_processes(top_n: int = 15) -> dict:
    """
    Audit running processes: flags high-CPU processes and ones not in the
    common/known-process list. This is a lightweight triage tool, not a
    replacement for real antivirus/EDR software.
    """
    all_procs = []
    for p in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            info = p.info
            info["cpu_percent"] = p.cpu_percent(interval=0.05)
            all_procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    all_procs.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
    top = all_procs[:top_n]

    flagged = []
    for proc in top:
        name = (proc.get("name") or "").lower()
        reasons = []
        if (proc.get("cpu_percent") or 0) > 30:
            reasons.append("high CPU usage")
        if name not in COMMON_WINDOWS_PROCESSES:
            reasons.append("not in common process allowlist")
        if reasons:
            flagged.append({**proc, "flags": reasons})

    return {"checked": len(all_procs), "flagged": flagged, "top_by_cpu": top}


# Tool schema definitions Claude will see. Keep descriptions precise --
# vague descriptions lead to the model calling the wrong tool.
TOOL_DEFINITIONS = [
    {
        "name": "get_system_stats",
        "description": "Get current CPU, RAM, and disk usage stats for this computer.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_processes",
        "description": "List the top processes running on this computer by memory usage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "description": "How many processes to return, default 10"}
            },
        },
    },
    {
        "name": "open_app",
        "description": "Open an allowed application on this computer (notepad, calculator, explorer, task manager).",
        "input_schema": {
            "type": "object",
            "properties": {"app_name": {"type": "string"}},
            "required": ["app_name"],
        },
    },
    {
        "name": "list_directory",
        "description": "List files in an allowed directory (Desktop or Documents only).",
        "input_schema": {
            "type": "object",
            "properties": {"dir_name": {"type": "string", "description": "'Desktop' or 'Documents'"}},
            "required": ["dir_name"],
        },
    },
    {
        "name": "get_network_connections",
        "description": "List active network connections on this computer -- useful for basic security checks (unexpected listening ports, unknown outbound connections).",
        "input_schema": {"type": "object", "properties": {}},
    },
]

# Maps tool name -> actual function to call
TOOL_FUNCTIONS = {
    "get_system_stats": lambda **kwargs: get_system_stats(),
    "list_processes": lambda **kwargs: list_processes(**kwargs),
    "open_app": lambda **kwargs: open_app(**kwargs),
    "list_directory": lambda **kwargs: list_directory(**kwargs),
    "get_network_connections": lambda **kwargs: get_network_connections(),
}
