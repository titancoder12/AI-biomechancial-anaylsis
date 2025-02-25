import asyncio
from bleak import BleakScanner

async def main():
    devices = await BleakScanner.discover(timeout=5.0)
    for d in devices:
        print(d)

asyncio.run(main())
"""import asyncio
from bleak import BleakScanner

async def main():
    print("🔍 Scanning for Bluetooth devices...")
    devices = await BleakScanner.discover(timeout=5.0)
    for device in devices:
        print(f"✅ Found: {device.name} - {device.address}")

# For Windows, avoid asyncio.run()
loop = asyncio.get_event_loop()
loop.run_until_complete(main())"""