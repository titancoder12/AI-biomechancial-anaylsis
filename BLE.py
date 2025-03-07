import asyncio
from bleak import BleakScanner

async def scan_ble():
    devices = await BleakScanner.discover()
    for device in devices:
        print(f"Device found: {device.name} - {device.address}")

asyncio.run(scan_ble())