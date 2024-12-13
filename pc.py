import asyncio
from bleak import BleakScanner, BleakClient
import warnings
from pynput import keyboard
warnings.simplefilter(action='ignore', category=FutureWarning)

class FitnessMachineController:
    # UUIDS
    FTMS_UUID = "00001826-0000-1000-8000-00805f9b34fb"  # FTMS Service UUID
    FTMS_CONTROL_POINT_UUID = "00002ad9-0000-1000-8000-00805f9b34fb"  # FTMS Control Point Characteristic UUID
    SUPPORTED_POWER_RANGE_UUID = "00002ad8-0000-1000-8000-00805f9b34fb"  # Supported Power Range Characteristic UUID
    SUPPORTED_RESISTANCE_RANGE_UUID = "00002ad6-0000-1000-8000-00805f9b34fb"  # Supported Resistance Range Characteristic UUID

    # OPCODES
    PWR_OPCODE = 0x05  # Op Code 0x05 (Set Target Power)
    RESISTANCE_OPCODE = 0x04  # Op Code 0x04 (Set Target Resistance)
    REQUEST_CONTROL_OPCODE = 0x00  # Request control of the fitness machine (Op Code 0x00)

    # Constants
    PWR_OR_RES = 1  # 0 for Power, 1 for Resistance

    def __init__(self):
        self.client = None
        self.control_point_char = None
        self.min_power = 0
        self.max_power = 800
        self.min_resistance = 0
        self.max_resistance = 100
        self.current_power = 0
        self.current_resistance = 0

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
                                if self.PWR_OR_RES == 0:
                                    await self.get_supported_power_range()
                                else:
                                    await self.get_supported_resistance_range()
                                await self.listen_for_keys()
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

    async def get_supported_power_range(self):
        try:
            power_range_data = await self.client.read_gatt_char(self.SUPPORTED_POWER_RANGE_UUID)
            self.min_power = int.from_bytes(power_range_data[0:2], byteorder="little", signed=False)
            self.max_power = int.from_bytes(power_range_data[2:4], byteorder="little", signed=False)
            self.current_power = self.min_power
            print(f"Supported Power Range: {self.min_power} to {self.max_power} Watts.")
        except Exception as e:
            print(f"Failed to read Supported Power Range: {e}")

    async def get_supported_resistance_range(self):
        try:
            resistance_range_data = await self.client.read_gatt_char(self.SUPPORTED_RESISTANCE_RANGE_UUID)
            self.min_resistance = int.from_bytes(resistance_range_data[0:2], byteorder="little")
            self.max_resistance = int.from_bytes(resistance_range_data[2:4], byteorder="little")
            self.current_resistance = self.min_resistance
            print(f"Supported Resistance Range: {self.min_resistance} to {self.max_resistance} dN.")
        except Exception as e:
            print(f"Failed to read Supported Resistance Range: {e}")

    async def adjust_power(self, increase):
        step = (self.max_power - self.min_power) * 0.05
        self.current_power += step if increase else -step
        self.current_power = max(self.min_power, min(self.current_power, self.max_power))
        adjust_command = bytearray([self.PWR_OPCODE, int(self.current_power) & 0xFF, (int(self.current_power) >> 8) & 0xFF])
        try:
            await self.client.write_gatt_char(self.control_point_char.uuid, adjust_command, response=True)
            print(f"Power set to {self.current_power} Watts.")
        except Exception as e:
            print(f"Failed to set power: {e}")

    async def adjust_resistance(self, increase):
        step = (self.max_resistance - self.min_resistance) * 0.05
        self.current_resistance += step if increase else -step
        self.current_resistance = max(self.min_resistance, min(self.current_resistance, self.max_resistance))
        adjust_command = bytearray([self.RESISTANCE_OPCODE, int(self.current_resistance) & 0xFF, (int(self.current_resistance) >> 8) & 0xFF])
        try:
            await self.client.write_gatt_char(self.control_point_char.uuid, adjust_command, response=True)
            print(f"Resistance set to {self.current_resistance} dN.")
        except Exception as e:
            print(f"Failed to set resistance: {e}")

    async def listen_for_keys(self):
        print("Listening for arrow key presses to adjust power or resistance...")

        def on_press(key):
            try:
                if key == keyboard.Key.up:
                    asyncio.create_task(self.adjust_power(True) if self.PWR_OR_RES == 0 else self.adjust_resistance(True))
                elif key == keyboard.Key.down:
                    asyncio.create_task(self.adjust_power(False) if self.PWR_OR_RES == 0 else self.adjust_resistance(False))
            except Exception as e:
                print(f"Error handling key press: {e}")

        with keyboard.Listener(on_press=on_press) as listener:
            await asyncio.sleep(30)  # Adjust duration as needed
            listener.stop()

if __name__ == "__main__":
    controller = FitnessMachineController()
    asyncio.run(controller.scan_and_connect())
