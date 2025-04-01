from bluetooth_hid import BluetoothHID
import time

if __name__ == "__main__":
    try:
        with BluetoothHID() as hid:
            print("=== 蓝牙HID键盘模拟器 ===")

            # 发现设备
            devices = hid.discover_devices()
            if not devices:
                print("未找到可用设备")
                exit()

            print("\n发现以下设备：")
            for i, (addr, name) in enumerate(devices):
                print(f"[{i+1}] {name} - {addr}")

            # 选择设备
            choice = int(input("\n请选择要连接的设备编号: ")) - 1
            target_addr = devices[choice][0]

            if hid.connect(target_addr):
                print("\n连接成功！每2秒自动发送字母'T'...")
                while True:
                    hid.send_key_event(0x1C)  # 发送'T'键
                    time.sleep(2)
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        print("程序已退出")