import socket

# DNS cache
DNS_CACHE = {}

def reverse_dns(ip: str) -> str:
    if ip not in DNS_CACHE:
        try:
            DNS_CACHE[ip] = socket.gethostbyaddr(ip)[0]
        except Exception:
            DNS_CACHE[ip] = ip  # Fallback to IP if DNS fails
    return DNS_CACHE[ip]

def get_server_info(remote_ip: str, remote_port: int):
    """Return server name and icon by (ip, port), or generic fallback."""
    from config import SERVER_OVERRIDES

    # Direct lookup
    key = (remote_ip, remote_port)
    if key in SERVER_OVERRIDES:
        entry = SERVER_OVERRIDES[key]
        return {
            "name": entry["name"],
            "icon": entry["icon"],
        }

    # Fallback
    domain = reverse_dns(remote_ip)
    return {
        "name": f"SS13 Server ({domain})",
        "icon": "ss13",  # Make sure you have 'ss13' asset in Discord
    }