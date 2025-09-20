import socket
import struct
import json
import urllib.parse

# http://www.byond.com/forum/post/2158640
# http://www.byond.com/forum/post/33090
# http://www.byond.com/forum/post/2017937
# http://www.byond.com/forum/post/1928990

def query_byond_server(ip: str, port: int, query: str = "?status") -> dict:
    """
    Query a BYOND server using the topic() interface.
     Sends a raw packet with the given query and returns parsed response.
    Returns parsed key-value response.

       Args:
        ip (str): Server IP address or hostname
        port (int): Server port
        query (str): The query string, e.g. '?status', '?players', '?info'

    Returns:
        dict: Parsed key-value data from server, or {} on failure
    """

    try:
        # Ensure query starts with '?'
        if not query.startswith("?"):
            query = f"?{query}"

        # This is the BYOND protocol magic identifier for a "topic" request.
        # \x00\x83 is a 2-byte header meaning:
        # \x00 = null byte (padding or stream identifier)
        # \x83 = command code for "client topic" request
        # struct.pack('>H', len(query) + 6) — Packet Length (2 bytes)

        # >H means:
        # > = big-endian (network byte order)
        # H = unsigned short (2 bytes)
        # So this packs a 2-byte integer representing the total packet length.

        # Why len(query) + 6?
        # The full packet includes:
        # 2 bytes: header (\x00\x83)
        # 2 bytes: length field itself
        # 5 bytes: unknown/reserved (\x00\x00\x00\x00\x00)
        # N bytes: URL query string (e.g., ?status)
        # 1 byte: null terminator (\x00)

        # So total size = 2 + 2 + 5 + len(query) + 1 = len(query) + 10
        # But the length field only covers from after itself onward, so it excludes the first 4 bytes (header + length).

        # Therefore:
        # Length to send = 5 + len(query) + 1 = len(query) + 6

        message = (
            b"\x00\x83" +
            struct.pack('>H', len(query) + 6) +
            b"\x00\x00\x00\x00\x00" +
            query.encode() +
            b"\x00"
        )

        # b"\x00\x00\x00\x00\x00" — Reserved / Unknown Bytes (5 bytes)
        # These are fixed padding bytes required by the protocol.
        # Their exact purpose is undocumented (legacy behavior), but they must be present.
        # Omitting them will cause the server to ignore or disconnect the request.`

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((ip, port))
        sock.sendall(message)
        response = sock.recv(4096)
        sock.close()

        if len(response) < 6:
            return {}

        # Extract body: skip first 5 bytes, strip trailing null
        body = response[5:-1].decode('utf-8', errors='replace')

        # Try parsing as JSON first
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            # Fall back to legacy key=value parsing
            parsed = urllib.parse.parse_qs(body)
            return {k: v[0] if isinstance(v, list) else v for k, v in parsed.items()}

    except Exception as e:
        print(f"BYOND query failed: {e}")
        return {}