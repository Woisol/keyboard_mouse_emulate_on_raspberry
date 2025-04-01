#!/usr/bin/python3
#
# Bluetooth keyboard/Mouse emulator DBUS Service
#
# !2025-03-31 23:34:01 拼尽全力无法战胜，始终只能在配对时accept而重连不行

# 对于L2CAP协议，不能直接重用现有的蓝牙连接创建socket。L2CAP需要单独创建socket并绑定到特定端口，即使设备已配对也需要重新建立L2CAP层的连接。

from __future__ import absolute_import, print_function
from optparse import OptionParser, make_option
import os
import sys
import uuid
import dbus
import dbus.service
import dbus.mainloop.glib
import time
import socket
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop
import logging
from logging import debug, info, warning, error
import bluetooth
from bluetooth import *

logging.basicConfig(level=logging.DEBUG)


class BTKbDevice():
    # change these constants
    MY_ADDRESS = "B0:AC:82:FB:BE:EC"
    MY_DEV_NAME = "ISer"
    TARGET_ADDRESS = "74:97:79:E3:6E:A2"

    # define some constants
    P_CTRL = 17  # Service port - must match port configured in SDP record
    P_INTR = 19  # Interrupt port - must match port configured in SDP record
    # dbus path of the bluez profile we will create
    # file path of the sdp record to load
    SDP_RECORD_PATH = sys.path[0] + "/sdp_record.xml"
    UUID = "00001124-0000-1000-8000-00805f9b34fb"

    def __init__(self):
        print("2. Setting up BT device")
        self.init_bt_device()
        self.init_bluez_profile()

    # configure the bluetooth hardware device
    def init_bt_device(self):
        print("3. Configuring Device name " + BTKbDevice.MY_DEV_NAME)
        # set the device class to a keybord and set the name
        os.system("hciconfig hci0 up")
        os.system("hciconfig hci0 name " + BTKbDevice.MY_DEV_NAME)
        # make the device discoverable
        os.system("hciconfig hci0 piscan")

    # set up a bluez profile to advertise device capabilities from a loaded service record
    def init_bluez_profile(self):
        print("4. Configuring Bluez Profile")
        # setup profile options
        service_record = self.read_sdp_service_record()
        opts = {
            "AutoConnect": True,
            "ServiceRecord": service_record
        }
        # retrieve a proxy for the bluez profile interface
        bus = dbus.SystemBus()
        manager = dbus.Interface(bus.get_object(
            "org.bluez", "/org/bluez"), "org.bluez.ProfileManager1")
        try:
            manager.RegisterProfile("/org/bluez/hci0", BTKbDevice.UUID, opts)
            print("6. Profile registered ")
        except dbus.exceptions.DBusException as e:
            if "Already Exists" in str(e):
                print("6. Profile already registered")
            else:
                raise
        os.system("hciconfig hci0 class 0x0025C0")

    # read and return an sdp record from a file
    def read_sdp_service_record(self):
        print("5. Reading service record")
        try:
            fh = open(BTKbDevice.SDP_RECORD_PATH, "r")
        except:
            sys.exit("Could not open the sdp record. Exiting...")
        return fh.read()

    # listen for incoming client connections
    def listen(self):
        print("\033[0;33m7. Waiting for connections\033[0m")

        # Check if target device is already connected
        try:
            # 检查物理连接状态和socket有效性
            result = os.popen("hcitool con").read()
            connected = BTKbDevice.TARGET_ADDRESS.lower() in result.lower()

            # 连接存在且socket有效
            if connected and hasattr(self, 'ccontrol') and hasattr(self, 'cinterrupt') \
                and self.ccontrol.fileno() != -1 and self.cinterrupt.fileno() != -1:
                print("\033[0;32mUsing existing valid connections\033[0m")
                return

            # 连接存在但socket失效
            if connected:
                print("\033[0;33mConnection exists but sockets invalid, resetting...\033[0m")
                # 安全关闭旧socket
                for sock in ['ccontrol', 'cinterrupt', 'scontrol', 'sinterrupt']:
                    if hasattr(self, sock):
                        getattr(self, sock).close()
                        delattr(self, sock)

                # Initialize sockets if not already done
                # 检查socket是否存在且有效
                if not hasattr(self, 'scontrol') or not hasattr(self, 'sinterrupt') \
                        or self.scontrol.fileno() == -1 or self.sinterrupt.fileno() == -1:
                    # 关闭旧socket（如果存在）
                    if hasattr(self, 'scontrol'):
                        self.scontrol.close()
                    if hasattr(self, 'sinterrupt'):
                        self.sinterrupt.close()
                    # 创建新socket
                    self.scontrol = socket.socket(
                        socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)
                    self.sinterrupt = socket.socket(
                        socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)
                    self.scontrol.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self.sinterrupt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self.scontrol.bind((socket.BDADDR_ANY, self.P_CTRL))
                    self.sinterrupt.bind((socket.BDADDR_ANY, self.P_INTR))
                    self.scontrol.listen(5)
                    self.sinterrupt.listen(5)
                self.ccontrol, cinfo = self.scontrol.accept()
                print("\033[0;32mGot a connection on the control channel from %s \033[0m" % cinfo[0])
                self.cinterrupt, cinfo = self.sinterrupt.accept()
                print("\033[0;32mGot a connection on the interrupt channel from %s \033[0m" % cinfo[0])
                return
        except Exception as e:
            print(f"Error checking device connection: {e}")

        # 检查socket连接有效性
        if hasattr(self, 'ccontrol') and hasattr(self, 'cinterrupt') and \
           self.ccontrol.fileno() != -1 and self.cinterrupt.fileno() != -1:
            print("\033[0;32mUsing existing valid connections\033[0m")
            return

        # 当连接不存在时初始化socket
        if not hasattr(self, 'scontrol') or not hasattr(self, 'sinterrupt') or \
           not hasattr(self, 'ccontrol') or not hasattr(self, 'cinterrupt'):

            self.scontrol = socket.socket(
                socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)
            self.sinterrupt = socket.socket(
                socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)
            self.scontrol.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sinterrupt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # bind these sockets to a port - port zero to select next available
            self.scontrol.bind((socket.BDADDR_ANY, self.P_CTRL))
            self.sinterrupt.bind((socket.BDADDR_ANY, self.P_INTR))

            # Start listening on the server sockets
            self.scontrol.listen(5)
            self.sinterrupt.listen(5)

            self.ccontrol, cinfo = self.scontrol.accept()
            print("\033[0;32mGot a connection on the control channel from %s \033[0m" % cinfo[0])

            self.cinterrupt, cinfo = self.sinterrupt.accept()
            print("\033[0;32mGot a connection on the interrupt channel from %s \033[0m" % cinfo[0])
        else:
            print("\033[0;32mUsing existing connections\033[0m")

    # send a string to the bluetooth host machine
    def send_string(self, message):
        try:
            if not hasattr(self, 'cinterrupt') or self.cinterrupt.fileno() == -1:
                raise OSError("Socket not connected")
            self.cinterrupt.send(bytes(message))
        except (OSError, AttributeError, socket.error) as err:
            error(err)
            raise


class BTKbService(dbus.service.Object):

    def __init__(self):
        print("1. Setting up service")
        # set up as a dbus service
        bus_name = dbus.service.BusName(
            "org.thanhle.btkbservice", bus=dbus.SystemBus())
        dbus.service.Object.__init__(
            self, bus_name, "/org/thanhle/btkbservice")
        # create and setup our device
        self.device = BTKbDevice()
        # start listening for connections
        self.device.listen()

    @dbus.service.method('org.thanhle.btkbservice', in_signature='yay')
    def send_keys(self, modifier_byte, keys):
        print("Get send_keys request through dbus")
        print("key msg: ", keys)
        state = [ 0xA1, 1, 0, 0, 0, 0, 0, 0, 0, 0 ]
        state[2] = int(modifier_byte)
        count = 4
        for key_code in keys:
            if(count < 10):
                state[count] = int(key_code)
            count += 1

        while True:
            try:
                self.device.send_string(state)
                break
            except (OSError, AttributeError) as err:
                print(f"Connection error: {err}, attempting to reconnect...")
                try:
                    # Clean up old connections
                    if hasattr(self.device, 'ccontrol'):
                        self.device.ccontrol.close()
                    if hasattr(self.device, 'cinterrupt'):
                        self.device.cinterrupt.close()

                    # Reinitialize device and connections
                    self.device = BTKbDevice()
                    self.device.listen()
                    time.sleep(1)
                except Exception as e:
                    print(f"Reconnect failed: {e}")
                    time.sleep(3)
        else:
            print("Max retries reached. Please check Bluetooth connection.")

    @dbus.service.method('org.thanhle.btkbservice', in_signature='yay')
    def send_mouse(self, modifier_byte, keys):
        state = [0xA1, 2, 0, 0, 0, 0]
        count = 2
        for key_code in keys:
            if(count < 6):
                state[count] = int(key_code)
            count += 1
        self.device.send_string(state)


# main routine
if __name__ == "__main__":
    # we an only run as root
    try:
        if not os.geteuid() == 0:
            sys.exit("Only root can run this script")

        DBusGMainLoop(set_as_default=True)
        myservice = BTKbService()
        loop = GLib.MainLoop()
        loop.run()
    except KeyboardInterrupt:
        sys.exit()
