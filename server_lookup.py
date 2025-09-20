from config import SERVER_OVERRIDES

def get_server_info(ip: str, port: int):
    """Get server info from config overrides, or return default."""
    key = (ip.strip(), int(port))
    override = SERVER_OVERRIDES.get(key)
    if override:
        return override.copy()  # Return mutable copy
    # Default fallback
    return {
        "name": f"{ip}:{port}",
        "icon": "ss13_default",
        "template": "Players {players}"
    }