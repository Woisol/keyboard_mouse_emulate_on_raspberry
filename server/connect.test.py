import bluetooth

TARGET_ADDRESS = "74:97:79:E3:6E:A2"
message = [161, 1, 0, 0, 23, 0, 0, 0, 0, 0]


def get_paired_devices():
    return bluetooth.discover_devices(lookup_names=True)

def connect_to_device(target_address):
    scontrol = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    sock.connect((target_address, 19))
    return sock

def send_message(sock, message):
    sock.send(message)

# 示例用法
if __name__ == "__main__":
    # 获取已配对设备
    # devices = get_paired_devices()
    # print("可用设备:")
    # for addr, name in devices:
#         print(f"{name} - {addr}")

    # 连接设备
    try:
    	sock = connect_to_device(TARGET_ADDRESS)

    # 发送消息
    	send_message(sock, bytes(message))
    except bluetooth.BluetoothError as err:
        error(err)

    sock.close()
