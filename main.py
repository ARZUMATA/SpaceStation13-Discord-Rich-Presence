import psutil
import time
import byond
import server_lookup
from discord_rpc import DiscordRPC
from config import CLIENT_ID, UPDATE_INTERVAL
import os
import ctypes
from ctypes import wintypes

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

def get_documents_folder():
    """Get the user's Documents folder using Windows API."""
    CSIDL_PERSONAL = 5  # CSIDL for My Documents
    buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, 0, buf)
    return buf.value

def get_pager_recent_server():
    """Read recent-url and recent-name from BYOND's pager.txt."""
    documents = get_documents_folder()
    pager_path = os.path.join(documents, "BYOND", "cfg", "pager.txt")

    if not os.path.exists(pager_path):
        print(f"pager.txt not found: {pager_path}")
        return None, None

    recent_url = None
    recent_name = None

    try:
        with open(pager_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("recent-url "):
                     recent_url = line.strip()[11:].split("|")[0]  # Strip "recent-url " and extra parts
                elif line.startswith("recent-name "):
                    recent_name = line.strip()[12:].split("|")[0]  # Strip "recent-name " and extra parts

        if recent_url and recent_name:
            # Parse: recent_url is like "byond://host:port"
            if recent_url.startswith("byond://"):
                addr = recent_url[8:].split("|")[0]  # Strip protocol and extra parts
                host_port = addr.split(":")
                if len(host_port) == 2:
                    host, port_str = host_port
                    if port_str.isdigit():
                        return (host.strip(), int(port_str)), recent_name.strip()
                        
    except Exception as e:
        print(f"Error reading pager.txt: {e}")

    return None, None


def build_activity(server_info, status_data):
    activity = {
        "details": server_info["name"],
        "large_image": server_info["icon"],
        "large_text": server_info["name"],
    }

    if not status_data:
        activity["state"] = "In Lobby"
        return activity

    players = status_data.get("players", "Unknown")
    activity["party_size"] = [int(players)] if players.isdigit() else [0]
    activity["party_size"].append(0)  # We never know player cap

    return activity

def main():
    rpc = DiscordRPC(CLIENT_ID)
    last_ip_port = None

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
            (pager_addr, pager_port), pager_name = get_pager_recent_server()

            pager_addr, pager_port = pager_addr, pager_port

            if not pager_addr:
                time.sleep(5)
                continue

            if (pager_addr, pager_port) != last_ip_port:
                print(f"Connected to {pager_addr}:{pager_port}")
                server_info = server_lookup.get_server_info(pager_addr, pager_port)
                print(f"Detected server: {server_info['name']}")
                last_ip_port = (pager_addr, pager_port)

            if pager_addr and pager_addr != (pager_addr, pager_port):
                # Use pager's custom name if it's for this server
                print(f"Using pager-saved name: {pager_name}")
                server_info = {
                    "name": pager_name,
                    "icon": server_info.get("icon", "ss13_default")  # Keep detected icon
                }
            elif pager_addr and pager_addr != (pager_addr, pager_port):
                print(f"Warning: Dreamseeker connected to {pager_addr}:{pager_port}, but pager shows {pager_addr}")

            # Query BYOND status
            status_data = byond.query_byond_server(pager_addr, pager_port)
            activity = build_activity(server_info, status_data)
            rpc.update(**activity)

            time.sleep(UPDATE_INTERVAL)

        except KeyboardInterrupt:
            print("\nShutting down...")
            rpc.clear()
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()