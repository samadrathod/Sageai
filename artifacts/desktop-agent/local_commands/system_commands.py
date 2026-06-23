"""
system_commands.py — System-level hardware and info handlers.
"""

from __future__ import annotations
import os
import platform
import subprocess
import ctypes
from typing import Any
import system_manager

IS_WINDOWS = platform.system() == "Windows"


def _fmt_sysinfo(info: dict) -> str:
    """Format system info for presentation."""
    m = info["memory"]
    d = info["disk"]
    c = info["cpu"]
    return (
        f"System: {info['platform']} {info['platform_version'][:40]}\n"
        f"CPU: {c['count']} cores @ {c['usage_percent']}% usage\n"
        f"RAM: {m['used_gb']} GB / {m['total_gb']} GB ({m['percent']}% used)\n"
        f"Disk: {d['used_gb']} GB / {d['total_gb']} GB ({d['percent']}% used)"
    )


def handle_system_info(target: str | None, extra: dict) -> str:
    """Show system resource snapshot."""
    info = system_manager.get_system_info()
    return _fmt_sysinfo(info)


def handle_volume_control(target: str, extra: dict) -> str:
    """Control system volume (up, down, mute, unmute) with zero dependency on Windows."""
    if not IS_WINDOWS:
        return "Volume control is currently only supported on Windows in this offline engine."

    # Virtual Key Codes:
    # VK_VOLUME_MUTE = 0xAD
    # VK_VOLUME_DOWN = 0xAE
    # VK_VOLUME_UP   = 0xAF
    
    if target == "up":
        # Press Volume Up 5 times (each press is 2% change on Windows)
        for _ in range(5):
            ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)
        return "Increased system volume."
        
    elif target == "down":
        # Press Volume Down 5 times
        for _ in range(5):
            ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)
        return "Decreased system volume."
        
    elif target in ("mute", "unmute", "toggle"):
        ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)
        return "Toggled system mute."
        
    return "Unknown volume control command."


def handle_brightness_control(target: str, extra: dict) -> str:
    """Control display brightness on Windows via WMI."""
    if not IS_WINDOWS:
        return "Brightness control is only supported on Windows."

    def get_brightness() -> int:
        try:
            cmd = "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness"
            res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=2)
            if res.returncode == 0 and res.stdout.strip():
                return int(res.stdout.strip())
        except Exception:
            pass
        return 50

    def set_brightness(level: int) -> str:
        level = max(0, min(100, level))
        cmd = f"(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"
        res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=3)
        if res.returncode != 0:
            return f"Could not set monitor brightness. (WMI error: {res.stderr.strip()})"
        return f"Brightness set to {level}%."

    if target == "up":
        curr = get_brightness()
        return set_brightness(curr + 10)
    elif target == "down":
        curr = get_brightness()
        return set_brightness(curr - 10)
    elif target == "set":
        level = extra.get("level", 50)
        return set_brightness(level)
        
    return "Unknown brightness command."


def handle_wifi_toggle(target: str, extra: dict) -> str:
    """Toggle Wi-Fi radio or network adapter states on Windows."""
    if not IS_WINDOWS:
        return "Wi-Fi control is only supported on Windows."
        
    if target == "toggle":
        # Get status: Up or Down
        cmd_status = "Get-NetAdapter | Where-Object {$_.InterfaceDescription -like '*Wireless*' -or $_.Name -like '*Wi-Fi*'} | Select-Object -ExpandProperty Status"
        res = subprocess.run(["powershell", "-Command", cmd_status], capture_output=True, text=True)
        current = res.stdout.strip().lower()
        target = "off" if "up" in current else "on"
        
    enabled = (target == "on")
    action = "Enable-NetAdapter" if enabled else "Disable-NetAdapter"
    cmd = f"Get-NetAdapter | Where-Object {{$_.InterfaceDescription -like '*Wireless*' -or $_.Name -like '*Wi-Fi*';}} | {action} -Confirm:$false"
    
    res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
    if res.returncode == 0:
        return f"Wi-Fi turned {target}."
    
    # Fallback to netsh
    state = "enabled" if enabled else "disabled"
    netsh_cmd = f"netsh interface set interface Wi-Fi admin={state}"
    res2 = subprocess.run(["powershell", "-Command", netsh_cmd], capture_output=True, text=True)
    if res2.returncode == 0:
        return f"Wi-Fi turned {target}."
        
    return f"Failed to turn Wi-Fi {target}. Administrator rights may be required to toggle network adapters."


def handle_bluetooth_toggle(target: str, extra: dict) -> str:
    """Toggle Bluetooth radio on Windows using WinRT APIs with driver fallbacks."""
    if not IS_WINDOWS:
        return "Bluetooth control is only supported on Windows."
        
    if target == "toggle":
        # Get current state via WinRT radio query
        ps_get = """
        Add-Type -AssemblyName System.Runtime.WindowsRuntime
        $asTaskGeneric = ([System.Runtime.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
        function Await($WinRtTask, $ResultType) {
            $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
            $netTask = $asTask.Invoke($null, @($WinRtTask))
            $netTask.Wait(-1) | Out-Null
            $netTask.Result
        }
        [Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
        $radios = Await ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
        $bluetooth = $radios | Where-Object { $_.Kind -eq 'Bluetooth' }
        if ($bluetooth) { Write-Output $bluetooth.State } else { Write-Output "NotFound" }
        """
        res = subprocess.run(["powershell", "-Command", ps_get], capture_output=True, text=True)
        state_str = res.stdout.strip().lower()
        target = "off" if "on" in state_str else "on"
            
    state = "On" if target == "on" else "Off"
    ps_cmd = f"""
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $asTaskGeneric = ([System.Runtime.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{ $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }})[0]
    function Await($WinRtTask, $ResultType) {{
        $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
        $netTask = $asTask.Invoke($null, @($WinRtTask))
        $netTask.Wait(-1) | Out-Null
        $netTask.Result
    }}
    [Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
    [Windows.Devices.Radios.RadioAccessStatus,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
    Await ([Windows.Devices.Radios.Radio]::RequestAccessAsync()) ([Windows.Devices.Radios.RadioAccessStatus]) | Out-Null
    $radios = Await ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
    $bluetooth = $radios | Where-Object {{ $_.Kind -eq 'Bluetooth' }}
    if ($bluetooth) {{
        [Windows.Devices.Radios.RadioState,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
        Await ($bluetooth.SetStateAsync('{state}')) ([Windows.Devices.Radios.RadioAccessStatus]) | Out-Null
        Write-Output "Success"
    }} else {{
        Write-Output "NotFound"
    }}
    """
    res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
    if "Success" in res.stdout:
        return f"Bluetooth turned {target}."
        
    # Driver-level fallback (requires admin)
    action = "Enable-PnpDevice" if target == "on" else "Disable-PnpDevice"
    pnp_cmd = f"Get-PnpDevice -Class Bluetooth | {action} -Confirm:$false"
    res2 = subprocess.run(["powershell", "-Command", pnp_cmd], capture_output=True, text=True)
    if res2.returncode == 0:
        return f"Bluetooth turned {target} (via PnpDevice driver)."
        
    return f"Failed to turn Bluetooth {target}. Administrative privileges may be required to modify hardware radios."


def handle_shutdown(target: str | None, extra: dict) -> str:
    """Shutdown the computer."""
    if IS_WINDOWS:
        subprocess.Popen(["shutdown", "/s", "/t", "0"])
        return "Initiating system shutdown..."
    return "Shutdown command is only supported on Windows in this offline engine."


def handle_restart(target: str | None, extra: dict) -> str:
    """Restart the computer."""
    if IS_WINDOWS:
        subprocess.Popen(["shutdown", "/r", "/t", "0"])
        return "Initiating system restart..."
    return "Restart command is only supported on Windows in this offline engine."


def handle_sleep(target: str | None, extra: dict) -> str:
    """Put the computer to sleep."""
    if IS_WINDOWS:
        # Run DLL command for Sleep state
        subprocess.Popen(["rundll32.exe", "powrprof.dll", "SetSuspendState", "0", "1", "0"])
        return "Putting the computer to sleep..."
    return "Sleep command is only supported on Windows in this offline engine."
