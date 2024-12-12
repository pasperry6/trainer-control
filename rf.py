import asyncio
from bleak import BleakScanner, BleakClient

FTMS_UUID = "00001826-0000-1000-8000-00805f9b34fb"  # FTMS Service UUID
FTMS_FEATURE_UUID = "00002acc-0000-1000-8000-00805f9b34fb"  # FTMS Feature Characteristic UUID
FTMS_CONTROL_POINT_UUID = "00002ad9-0000-1000-8000-00805f9b34fb"  # FTMS Control Point Characteristic UUID

async def scan_and_connect():
    print("Scanning for BLE devices broadcasting FTMS data...")
    devices = await BleakScanner.discover()
    for device in devices:
        print(f"Found device: {device.name} ({device.address})")
        uuids = device.metadata.get("uuids", [])
        if uuids:
            print("UUIDs:")
            for uuid in uuids:
                print(f"  {uuid}")

        if FTMS_UUID in uuids:
            print(f"FTMS Device Found: {device.name} ({device.address})")
            print("Attempting to connect...")
            async with BleakClient(device.address) as client:
                print("Connected. Discovering services...")
                services = await client.get_services()
                for service in services:
                    if service.uuid == FTMS_UUID:
                        print("FTMS Service found.")
                        
                        # Retrieve FTMS Feature Characteristic
                        feature_char = next(
                            (c for c in service.characteristics if c.uuid == FTMS_FEATURE_UUID),
                            None
                        )
                        if feature_char and "read" in feature_char.properties:
                            print("Reading FTMS Feature Characteristic...")
                            feature_data = await client.read_gatt_char(feature_char.uuid)
                            # Parse the feature data (example for decoding resistance range)
                            if len(feature_data) >= 8:
                                min_resistance = int.from_bytes(feature_data[4:6], byteorder="little", signed=False)
                                max_resistance = int.from_bytes(feature_data[6:8], byteorder="little", signed=False)
                                print(f"Supported Resistance Range: {min_resistance} dN to {max_resistance} dN")
                            else:
                                print("FTMS Feature data is too short to contain resistance range.")
                        else:
                            print("FTMS Feature Characteristic not found or not readable.")
                        break
            break
    else:
        print("No FTMS devices found.")

if __name__ == "__main__":
    asyncio.run(scan_and_connect())
