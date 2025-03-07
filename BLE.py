from bleak import BleakClient
import asyncio
ADDRESS = "F63F8735-29EA-2F5E-8653-DF2C1463A90B"  # Your BLE device address

async def list_services():
    async with BleakClient(ADDRESS) as client:
        services = await client.get_services()
        for service in services:
            print(f"🔹 Service: {service.uuid}")
            for char in service.characteristics:
                print(f"   📌 Characteristic: {char.uuid}, Properties: {char.properties}")

asyncio.run(list_services()) 