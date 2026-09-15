import asyncio
from bleak import BleakClient, BleakScanner

async def find_bittle():
    """Scan for Bittle X device"""
    devices = await BleakScanner.discover()
    for device in devices:
        if "Bittle" in device.name:
            print(f"Found: {device.name} ({device.address})")
            return device.address
    return None

async def connect_and_control():
    address = await find_bittle()
    if not address:
        print("Bittle not found!")
        return

    async with BleakClient(address) as client:
        # List available services and characteristics
        for service in client.services:
            print(f"Service: {service.uuid}")
            for char in service.characteristics:
                print(f"  Characteristic: {char.uuid}")

        # Send a command (you'll need the correct UUID from above)
        # Example: move forward
        await client.write_gatt_char(characteristic_uuid, b'k')

asyncio.run(connect_and_control())
