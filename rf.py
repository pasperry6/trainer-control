import asyncio
from bleak import BleakScanner, BleakClient

class FitnessMachineController:
    # UUIDS
    FTMS_UUID = "00001826-0000-1000-8000-00805f9b34fb"  # FTMS Service UUID
    FTMS_CONTROL_POINT_UUID = "00002ad9-0000-1000-8000-00805f9b34fb"  # FTMS Control Point Characteristic UUID

    # OPCODES
    PWR_OPCODE = 0x05  # Op Code 0x05 (Set Target Power)
    RESISTANCE_OPCODE = 0x04  # Op Code 0x04 (Set Target Resistance)
    REQUEST_CONTROL_OPCODE = 0x00  # Request control of the fitness machine (Op Code 0x00)

    # OTHER CONSTANTS
    MIN_PWR = 0
    MAX_PWR = 800

    def __init__(self):
        self.client = None
        self.control_point_char = None

    async def scan_and_connect(self):
        print("Scanning for BLE devices broadcasting FTMS data...")
        devices = await BleakScanner.discover()
        for device in devices:
            uuids = device.metadata.get("uuids", [])

            if self.FTMS_UUID in uuids:
                print(f"FTMS Device Found: {device.name} ({device.address})")
                print("Attempting to connect...")
                self.client = BleakClient(device.address)
                async with self.client as client:
                    print("Connected. Discovering services...")
                    services = await client.get_services()
                    for service in services:
                        if service.uuid == self.FTMS_UUID:
                            print("FTMS Service found.")
                            self.control_point_char = next(
                                (c for c in service.characteristics if c.uuid == self.FTMS_CONTROL_POINT_UUID),
                                None
                            )
                            if self.control_point_char:
                                print(f"Found Control Point Characteristic: {self.control_point_char.uuid}")
                                await self.enable_notifications()
                                await self.request_control()
                                await self.adjust_power()
                                await self.disable_notifications()
                            else:
                                print("Control Point Characteristic not found.")
                            return
        print("No FTMS devices found.")

    async def enable_notifications(self):
        async def notification_handler(sender, data):
            op_code = data[0]
            request_op_code = data[1]
            result_code = data[2]
            print(f"\nNotification Received:\n  Sender: {sender}\n  Op Code: {op_code}\n  Request Op Code: {request_op_code}\n  Result Code: {result_code}\n")
            if op_code == 0x80 and request_op_code == 0x00:  # Response to Request Control Op Code
                if result_code == 0x01:  # Success
                    print("Control successfully granted.")
                else:
                    print(f"Control request failed with result code: {result_code}")

        if "indicate" in self.control_point_char.properties:
            await self.client.start_notify(self.control_point_char, notification_handler)
            print("Notifications enabled.")

    async def disable_notifications(self):
        if "indicate" in self.control_point_char.properties:
            await self.client.stop_notify(self.control_point_char)
            print("Notifications disabled.")

    async def request_control(self):
        request_control_command = bytearray([self.REQUEST_CONTROL_OPCODE])
        try:
            await self.client.write_gatt_char(self.control_point_char.uuid, request_control_command, response=True)
            print("Requested control of the fitness machine. Waiting for response...")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Failed to request control: {e}")

    async def adjust_power(self):
        for percentage in range(0, 101, 10):
            power = int(self.MIN_PWR + (percentage / 100) * (self.MAX_PWR - self.MIN_PWR))
            adjust_command = bytearray([self.PWR_OPCODE, power & 0xFF, (power >> 8) & 0xFF])
            try:
                await self.client.write_gatt_char(self.control_point_char.uuid, adjust_command, response=True)
                print(f"Power set to {percentage}% ({power} Watts). Waiting 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Failed to set power: {e}")

if __name__ == "__main__":
    controller = FitnessMachineController()
    asyncio.run(controller.scan_and_connect())
