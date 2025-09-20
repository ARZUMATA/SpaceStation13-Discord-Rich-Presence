# SpaceStation13 Discord RPC

A lightweight presence tracker for Space Station 13 (SS13) clients running on Windows. Automatically detects when you connect to a server via Dreamseeker and updates your Discord status with server name, player count.

## Features

- Detects active Dreamseeker.exe connections via command line parsing (optional way to use connections state)
- Reads custom server names from BYOND's `pager.txt`
- Displays server name, icon, player count
- Supports configurable server overrides with custom icons
- Auto-creates configuration on first launch