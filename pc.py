import asyncio
from bleak import BleakScanner, BleakClient

# UUIDS
FTMS_UUID = "00001826-0000-1000-8000-00805f9b34fb"  # FTMS Service UUID
FTMS_CONTROL_POINT_UUID = "00002ad9-0000-1000-8000-00805f9b34fb"  # FTMS Control Point Characteristic UUID
# OPCODES
PWR_OPCODE = 0x05 # Op Code 0x05 (Set Target Power)
RESISTANCE_OPCODE = 0x04 # Op Code 0x04 (Set Target Resistance)
REQUEST_CONTROL_OPCODE = 0x00 # Request control of the fitness machine (Op Code 0x00)
# OTHER CONSTANTS
# CHANGE LATER TO DO AUTOMATICALLY FOR POWER AND RESISTANCE
MIN_PWR = 0
MAX_PWR = 800

async def scan_and_connect():
    print("Scanning for BLE devices broadcasting FTMS data...")
    devices = await BleakScanner.discover()
    for device in devices:
        # Find all UUIDs associated with the device
        uuids = device.metadata.get("uuids", [])

        # Check for FTMS Service
        if FTMS_UUID in uuids:
            print(f"FTMS Device Found: {device.name} ({device.address})")
            print("Attempting to connect...")
            async with BleakClient(device.address) as client:
                print("Connected. Discovering services...")
                services = await client.get_services()
                for service in services:
                    if service.uuid == FTMS_UUID:
                        print("FTMS Service found.")
                        control_point_char = next(
                            (c for c in service.characteristics if c.uuid == FTMS_CONTROL_POINT_UUID),
                            None
                        )
                        if control_point_char:
                            print(f"Found Control Point Characteristic: {control_point_char.uuid}")

                            # Enable notifications (required for responses)
                            async def notification_handler(sender, data):
                                print(f"Notification from {sender}: {data}")
                                # Handle response to control request
                                if data[0] == 0x80 and data[1] == 0x00:  # Response to Request Control Op Code
                                    result_code = data[2]
                                    if result_code == 0x01:  # Success
                                        print("Control successfully granted.")
                                    else:
                                        print(f"Control request failed with result code: {result_code}")

                            if "indicate" in control_point_char.properties:
                                await client.start_notify(control_point_char, notification_handler)
                                print("Notifications enabled.")

                            # Request control of the fitness machine (Op Code 0x00)
                            request_control_command = bytearray([REQUEST_CONTROL_OPCODE])
                            try:
                                await client.write_gatt_char(control_point_char.uuid, request_control_command, response=True)
                                print("Requested control of the fitness machine. Waiting for response...")
                                await asyncio.sleep(2)  # Allow time for response
                            except Exception as e:
                                print(f"Failed to request control: {e}")
                                return

                            # Gradually increase power from 0% to 100%
                            for percentage in range(0, 101, 10):
                                power = int(MIN_PWR + (percentage / 100) * (MAX_PWR - MIN_)PWR))
                                adjust_command = bytearray([PWR_OPCODE, power & 0xFF, (power >> 8) & 0xFF]) # Op Code 0x05 (Set Target Power)
                                try:
                                    await client.write_gatt_char(control_point_char.uuid, adjust_command, response=True)
                                    print(f"Power set to {percentage}% ({resistance_dn} Watts). Waiting 5 seconds...")
                                    await asyncio.sleep(5)
                                except Exception as e:
                                    print(f"Failed to set resistance: {e}")
                            print("Resistance adjustment complete.")

                            if "indicate" in control_point_char.properties:
                                await client.stop_notify(control_point_char)
                        else:
                            print("Control Point Characteristic not found.")
                        break
            break
    else:
        print("No FTMS devices found.")

if __name__ == "__main__":
    asyncio.run(scan_and_connect())
