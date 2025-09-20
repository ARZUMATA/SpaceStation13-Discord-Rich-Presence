import psutil
import time
import byond
import server_lookup
from discord_rpc import DiscordRPC
from config import CLIENT_ID, UPDATE_INTERVAL, DEFAULT_TEMPLATE
import os
import ctypes
from ctypes import wintypes
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("rpc.log", encoding="utf-8"),
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)

def find_dreamseeker_process():
    """Finds the dreamseeker.exe process."""
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] and 'dreamseeker.exe' in proc.info['name'].lower():
            return proc
    return None

def get_connected_ip(proc):
    """Get the remote IP:port dreamseeker is connected to."""
    try:
        for conn in proc.connections():
            if conn.status == 'ESTABLISHED' and conn.raddr:
                ip, port = conn.raddr
                # Ignore localhost unless intentional
                if ip != '127.0.0.1' and port > 1024:
                    return ip, port
    except psutil.AccessDenied:
        pass
    except Exception as e:
        print(f"Connection access error: {e}")
    return None, None

def get_window_title(proc):
    """Get window title of the given process using Windows API. Works even if minimized."""
    try:
        pid = proc.info['pid']
        user32 = ctypes.windll.user32

        titles = []

        def enum_windows_callback(hwnd, _):
            # Skip completely invisible windows, but allow minimized ones
            if not user32.IsWindowVisible(hwnd):
                return True  # Keep enumerating

            window_pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            
            if window_pid.value == pid:
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    titles.append(buff.value)
            return True  # Continue enumeration

        user32.EnumWindows(
            ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(enum_windows_callback), 0
        )

        # Prefer non-empty Dream Seeker titles
        for title in titles:
            if title:
                return title
        return titles[0] if titles else None

    except Exception as e:
        logger.debug(f"Could not get window title for PID {pid}: {e}")
        return None
    


def build_activity(server_info, status_data):
    activity = {
        "details": server_info["name"],
        "large_image": server_info["icon"],
        "large_text": server_info["name"],
    }

    if not status_data:
        logger.info("No status data received. Setting state to 'In Lobby'")
        activity["state"] = "In Lobby"
        return activity

    # Log raw server response
    logger.debug(f"Raw status data: {status_data}")

    # Determine template
    template = server_info.get("template")
    if template is None:
        template = DEFAULT_TEMPLATE

    logger.info(f"Using template: '{template}'")

    try:
        # Convert all values to string (in case of int/bool)
        safe_data = {k: str(v) if v is not None else "" for k, v in status_data.items()}
        state = template.format(**safe_data)
        logger.info(f"Formatted status: '{state}'")
    except KeyError as e:
        # If a key is missing in status_data, replace it with "?"
        logger.warning(f"Template missing key {e}. Using fallback formatting")
        try:
            class MissingKeyDict(dict):
                def __missing__(self, key):
                    logger.debug(f"Template key '{key}' not found in response")
                    return "?"
            state = template.format_map(MissingKeyDict(safe_data))
            logger.info(f"Formatted status (with fallbacks): '{state}'")
        except Exception as e_inner:
            logger.error(f"Failed to format even with fallback: {e_inner}")
            state = "Unknown Status"
    except Exception as e:
        logger.error(f"Unexpected error formatting template: {e}")
        state = "Unknown Status"

    activity["state"] = state

    return activity

def main():
    rpc = DiscordRPC(CLIENT_ID)
    last_ip_port = None
    first_run = True  # Skip sleep on first iteration

    print("SS13 Discord RPC started. Waiting for dreamseeker.exe...")

    while True:
        try:
            proc = find_dreamseeker_process()
            if not proc:
                if last_ip_port:
                    print("Dreamseeker closed. Clearing presence...")
                    rpc.clear()
                    last_ip_port = None
                time.sleep(5)
                continue

            # Get server from pager.txt as fallback/confirmation
            ip, port = get_connected_ip(proc)
            title = get_window_title(proc)
            title_name = None
            if title:
                title_name = title
                logger.debug(f"Extracted server name from window title: '{title_name}'")

            pager_addr = ip
            pager_port = port
            pager_name = title_name
            
            if not pager_addr:
                time.sleep(5)
                continue

            current_server_key = (pager_addr, pager_port)

            if current_server_key != last_ip_port:
                print(f"Connected to {pager_addr}:{pager_port}")

                # Look up server override by (host, port)
                server_info = server_lookup.get_server_info(pager_addr, pager_port)

                # Override name only if pager provides a custom name
                if pager_name:
                    print(f"Using pager-saved name: {pager_name}")
                    # Preserve template, icon, etc. — only change name
                    server_info = server_info.copy()  # Don't modify cached version
                    server_info["name"] = pager_name
                
                print(f"Detected server: {server_info['name']}")
                last_ip_port = current_server_key

            # Query BYOND status
            status_data = byond.query_byond_server(pager_addr, pager_port)
            activity = build_activity(server_info, status_data)

            logger.debug(f"Final activity payload: {activity}")
            rpc.update(**activity)

            # Immediate check without waiting on first run
            if not first_run:
                time.sleep(UPDATE_INTERVAL)  # Normal delay between checks (e.g. 15s)
            else:
                first_run = False  # Disable first-run skip after initial check

        except KeyboardInterrupt:
            print("\nShutting down...")
            rpc.clear()
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()