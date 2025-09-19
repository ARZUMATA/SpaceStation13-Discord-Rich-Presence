from pypresence import Presence
import time

class DiscordRPC:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.rpc = None
        self.connected = False

    def connect(self):
        try:
            self.rpc = Presence(self.client_id)
            self.rpc.connect()
            self.connected = True
            print("Connected to Discord RPC.")
        except Exception as e:
            print(f"Discord not running or client ID invalid: {e}")
            self.connected = False

    def update(self, **activity):
        if self.connected:
            try:
                self.rpc.update(**activity)
            except Exception as e:
                print(f"Failed to update presence: {e}")
                self.reconnect()
        else:
            self.connect()

    def clear(self):
        if self.connected:
            self.rpc.clear()
            self.connected = False

    def reconnect(self):
        try:
            self.rpc.close()
        except:
            pass
        self.connect()