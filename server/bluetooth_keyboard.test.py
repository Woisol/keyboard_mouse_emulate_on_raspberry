import bluetooth
import time
from bluetooth.btcommon import BluetoothError

# HID描述符 - 键盘
HID_DESCRIPTOR = bytes([
    0x05, 0x01,  # Usage Page (Generic Desktop)
    0x09, 0x06,  # Usage (Keyboard)
    0xA1, 0x01,  # Collection (Application)
    0x05, 0x07,  # Usage Page (Key Codes)
    0x19, 0xE0,  # Usage Minimum (224)
    0x29, 0xE7,  # Usage Maximum (231)
    0x15, 0x00,  # Logical Minimum (0)
    0x25, 0x01,  # Logical Maximum (1)
    0x75, 0x01,  # Report Size (1)
    0x95, 0x08,  # Report Count (8)
    0x81, 0x02,  # Input (Data, Variable, Absolute)
    0x95, 0x01,  # Report Count (1)
    0x75, 0x08,  # Report Size (8)
    0x81, 0x01,  # Input (Constant)
    0x95, 0x05,  # Report Count (5)
    0x75, 0x01,  # Report Size (1)
    0x05, 0x08,  # Usage Page (LEDs)
    0x19, 0x01,  # Usage Minimum (1)
    0x29, 0x05,  # Usage Maximum (5)
    0x91, 0x02,  # Output (Data, Variable, Absolute)
    0x95, 0x01,  # Report Count (1)
    0x75, 0x03,  # Report Size (3)
    0x91, 0x01,  # Output (Constant)
    0x95, 0x06,  # Report Count (6)
    0x75, 0x08,  # Report Size (8)
    0x15, 0x00,  # Logical Minimum (0)
    0x25, 0x65,  # Logical Maximum (101)
    0x05, 0x07,  # Usage Page (Key Codes)
    0x19, 0x00,  # Usage Minimum (0)
    0x29, 0x65,  # Usage Maximum (101)
    0x81, 0x00,  # Input (Data, Array)
    0xC0         # End Collection
])

class BluetoothKeyboard:
    def __init__(self):
        self.sock = None
        self.client_sock = None
        self.target_address = None

    def discover_devices(self):
        """发现附近的蓝牙设备"""
        print("正在搜索蓝牙设备...")
        devices = bluetooth.discover_devices(lookup_names=True)
        print("找到的设备:")
        for addr, name in devices:
            print(f"  {name} - {addr}")
        return devices

    def connect(self, target_address):
        """连接到目标蓝牙设备"""
        self.target_address = target_address
        self.sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)

        try:
            # 注册SDP服务
            from bluetooth import advertise_service
            advertise_service(
                self.sock,
                name="Raspberry Pi Keyboard",
                service_classes=[bluetooth.SERIAL_PORT_CLASS],
                profiles=[bluetooth.SERIAL_PORT_PROFILE],
                provider="Raspberry Pi",
                description="HID Keyboard Service",
                service_id="00001124-0000-1000-8000-00805F9B34FB"
            )

            # 绑定并监听蓝牙端口
            self.sock.bind(("", 1))
            self.sock.listen(1)
            print(f"正在等待 {target_address} 连接...")
            self.client_sock, address = self.sock.accept()
            print(f"已连接至 {address}")
            return True
        except BluetoothError as e:
            print(f"连接失败: {e}")
            return False
        except Exception as e:
            print(f"SDP注册失败: {e}")
            return False

    def is_connected(self):
        """检查连接状态"""
        try:
            if self.sock:
                # 尝试获取对端地址验证连接
                self.sock.getpeername()
                return True
            return False
        except BluetoothError:
            return False

    def reconnect(self):
        """尝试重新连接"""
        if self.target_address:
            self.disconnect()
            return self.connect(self.target_address)
        return False

    def send_key_event(self, key_code, modifier=0):
        """发送按键事件"""
        if not self.is_connected():
            print("连接已断开，尝试重连...")
            if not self.reconnect():
                return False

        if not self.sock:
            print("未连接到设备")
            return False

        # HID报告格式: [modifier, reserved, key1, key2, key3, key4, key5, key6]
        report = bytes([modifier, 0, key_code, 0, 0, 0, 0, 0])

        try:
            self.client_sock.send(report)
            # 发送空报告释放按键
            time.sleep(0.01)
            self.sock.send(bytes(8))
            return True
        except BluetoothError as e:
            print(f"发送失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.sock:
            try:
                # 注销SDP服务
                self.sock.stop_advertising()
            except Exception as e:
                print(f"服务注销异常: {e}")

            self.sock.close()
            self.sock = None
            print("已断开连接")

if __name__ == "__main__":
    keyboard = BluetoothKeyboard()

    # 发现设备
    devices = keyboard.discover_devices()
    if not devices:
        print("未找到设备")
        exit()

    # 连接第一个设备
    target_addr = devices[0][0]
    if not keyboard.connect(target_addr):
        exit()

    # 模拟按键
    while True:
        try:
            keyboard.send_key_event(ord('t'))
            time.sleep(1)
        except Exception as e:
            print(f"发生错误: {e}")
            keyboard.disconnect()
            break