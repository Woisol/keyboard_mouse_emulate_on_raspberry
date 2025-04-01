import bluetooth
import time
from bluetooth.btcommon import BluetoothError

class BluetoothHID:
    def __init__(self):
        self.sock = None
        self.client_sock = None
        self.target_address = None
        self.hid_descriptor = bytes([
            0x05, 0x01, 0x09, 0x06, 0xA1, 0x01, 0x05, 0x07,
            0x19, 0xE0, 0x29, 0xE7, 0x15, 0x00, 0x25, 0x01,
            0x75, 0x01, 0x95, 0x08, 0x81, 0x02, 0x95, 0x01,
            0x75, 0x08, 0x81, 0x01, 0x95, 0x05, 0x75, 0x01,
            0x05, 0x08, 0x19, 0x01, 0x29, 0x05, 0x91, 0x02,
            0x95, 0x01, 0x75, 0x03, 0x91, 0x01, 0x95, 0x06,
            0x75, 0x08, 0x15, 0x00, 0x25, 0x65, 0x05, 0x07,
            0x19, 0x00, 0x29, 0x65, 0x81, 0x00, 0xC0
        ])

    def discover_devices(self):
        print("搜索蓝牙设备中...")
        try:
            devices = bluetooth.discover_devices(lookup_names=True, duration=8)
            return [(addr, name) for addr, name in devices if name]
        except BluetoothError as e:
            print(f"设备发现失败: {e}")
            return []

    def connect(self, target_address):
        try:
            self.sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.sock.bind(("", bluetooth.PORT_ANY))
            bluetooth.advertise_service(
                self.sock,
                service_name="HIDKeyboard",
                service_classes=[bluetooth.SERIAL_PORT_CLASS],
                profiles=[bluetooth.SERIAL_PORT_PROFILE],
                provider="Virtual HID Device",
                description="HID Keyboard Service"
            )
            self.sock.listen(1)
            self.client_sock, address = self.sock.accept()
            self.target_address = target_address
            print(f"已连接到 {address[0]}")
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False

    def send_key_event(self, key_code, modifier=0):
        if not self.client_sock:
            return False

        try:
            report = bytes([modifier, 0, key_code] + [0]*5)
            self.client_sock.send(report)
            time.sleep(0.02)
            self.client_sock.send(bytes(8))
            return True
        except BluetoothError as e:
            print(f"按键发送失败: {e}")
            return False

    def disconnect(self):
        if self.client_sock:
            self.client_sock.close()
        if self.sock:
            self.sock.close()
        print("连接已断开")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()