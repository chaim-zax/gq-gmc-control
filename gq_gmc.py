# -*- coding: utf-8 -*-
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#  Copyright (c) 2019, Chaim Zax <chaim.zax@gmail.com>

import sys
import serial
import struct
import platform
import ctypes
import signal

DEFAULT_CONFIG = '~/.gq-gmc-control.conf'
DEFAULT_BIN_FILE = 'gq-gmc-log.bin'
DEFAULT_CSV_FILE = 'gq-gmc-log.csv'
if platform.system() == 'Windows':
    DEFAULT_PORT = 'COM99'
else:
    DEFAULT_PORT = '/dev/gq-gmc'  # try '/dev/ttyUSB0' without udev rules
DEFAULT_BAUD_RATE = 115200
DEFAULT_CPM_TO_SIEVERT = '1000,6.50'
DEFAULT_OUTPUT_IN_CPM = False
DEFAULT_NO_PARSE = False
DEFAULT_SKIP_CHECK = False
DEFAULT_UNIT_CONVERSION_FROM_DEVICE = False
DEFAULT_DEVICE_TYPE = None
DEFAULT_FLASH_SIZE = 0x00100000  # 1 MByte
DEFAULT_CONFIGURATION_SIZE = 0x100  # 256 byte
DEFAULT_VERBOSE_LEVEL = 2

EOL = '\n'

ADDRESS_WIFI_ON_OFF = 0x00
ADDRESS_WIFI_SSID = 0x45
ADDRESS_WIFI_PASSWORD = 0x65
ADDRESS_SERVER_WEBSITE = 0x85
ADDRESS_SERVER_URL = 0xa5
ADDRESS_USER_ID = 0xc5
ADDRESS_COUNTER_ID = 0xe5
ADDRESS_CALIBRATE1_CPM = 0x08
ADDRESS_CALIBRATE1_SV = 0x0a
ADDRESS_CALIBRATE2_CPM = 0x0e
ADDRESS_CALIBRATE2_SV = 0x10
ADDRESS_CALIBRATE3_CPM = 0x14
ADDRESS_CALIBRATE3_SV = 0x16

FLASH_SIZE = {
    'GMC-280': 0x00010000,
    'GMC-300': 0x00010000,
    'GMC-320': 0x00100000,
    'GMC-500': 0x00100000
}

CONFIGURATION_BUFFER_SIZE = {
    'GMC-280': 0x100,
    'GMC-300': 0x100,
    'GMC-320': 0x100,
    'GMC-500': 0x200
}

m_device = None
m_device_type = None
m_device_name = DEFAULT_DEVICE_TYPE
m_config = None
m_config_data = None
m_verbose = DEFAULT_VERBOSE_LEVEL
m_terminate = False


def command_returned_ok():
    ret = ''
    for loop in range(10):
        ret = m_device.read(1)
        if ret != '':
            break

    if ret == '' or ord(ret) != 0xaa:
        return False
    return True


def clear_port():
    # close any pending previous command
    m_device.write(">>")

    # get rid off all buffered data still in the queue
    while True:
        x = m_device.read(1)
        if x == '':
            break


def check_device_type():
    global m_device_type, m_device_name

    m_device_type = get_device_type()

    if m_device_type == '' or len(m_device_type) < 8:
        print("ERROR: device not found or supported")
        return -1

    m_device_name = m_device_type[:7]

    if m_device_name == 'GMC-280' or \
       m_device_name == 'GMC-300' or \
       m_device_name == 'GMC-320' or \
       m_device_name == 'GMC-500':
        if m_verbose == 2:
            print("device found: {}".format(m_device_type))

    elif m_device_name[:3] == 'GMC':
        print("WARNING: device found ({}) but officially not supported, using defaults"
              .format(m_device_type))
        m_device_name = DEFAULT_DEVICE_TYPE

    else:
        print("ERROR: device not found or supported")
        return -1

    return 0


def get_device_type():
    if m_device is None:
        print('ERROR: no device connected')
        return ''

    m_device.write('<GETVER>>')
    return m_device.read(14)


def get_serial_number():
    if m_device is None:
        print('ERROR: no device connected')
        return -1

    m_device.write('<GETSERIAL>>')
    serial_number = m_device.read(7)

    if serial_number == '' or len(serial_number) < 7:
        print('WARNING: no valid serial number received')
        return ''

    ser = ''
    for x in range(7):
        ser += '{:02X}'.format(ord(serial_number[x]))
    return ser


def set_power(on=True):
    if m_device is None:
        print('ERROR: no device connected')
        return -1

    if on:
        m_device.write('<POWERON>>')
        if m_verbose == 2:
            print('device power on')
    else:
        m_device.write('<POWEROFF>>')
        if m_verbose == 2:
            print('device power off')


def get_voltage():
    if m_device is None:
        print('ERROR: no device connected')
        return -1

    m_device.write('<GETVOLT>>')
    voltage = m_device.read(3)

    if voltage == '' or len(voltage) < 3:
        print('WARNING: no valid voltage received')
        return ''

    return '{} V'.format(voltage)


def get_cpm(cpm_to_usievert=None):
    if m_device is None:
        print('ERROR: no device connected')
        return -1

    m_device.write('<GETCPM>>')
    cpm = m_device.read(2)

    if cpm == '' or len(cpm) < 2:
        print('WARNING: no valid cpm received')
        return ''

    value = struct.unpack(">H", cpm)[0]

    unit_value = (value, 'CPM')
    if cpm_to_usievert is not None:
        unit_value = convert_cpm_to_usievert(value, 'CPM', cpm_to_usievert)

    if unit_value[1] == 'uSv/h':
        return '{:.4f} {:s}'.format(unit_value[0], unit_value[1])
    else:
        return '{:d} {:s}'.format(unit_value[0], unit_value[1])


def get_data(address=0x000000, length=None, out_file=DEFAULT_BIN_FILE):
    if m_device is None:
        print('ERROR: no device connected')
        return -1

    if address is None:
        address = 0x000000
    if length is None:
        if m_device_name is not None and m_device_name in FLASH_SIZE:
            length = FLASH_SIZE[m_device_name]
        else:
            length = DEFAULT_FLASH_SIZE
    if out_file is None or out_file == '':
        out_file = DEFAULT_BIN_FILE

    total_len = 0
    sub_addr = address
    sub_len = 4096

    # make sure we don't have any data in the device buffer
    clear_port()

    if m_verbose >= 1:
        print("storing data to '" + out_file + "'")

    with open(out_file, 'wb') as f_out:
        while True:
            cmd = struct.pack('>BBBH',
                (sub_addr >> 16) & 0xff,
                (sub_addr >> 8) & 0xff,
                sub_addr & 0xff,
                sub_len)
            m_device.write('<SPIR' + cmd + '>>')

            data = m_device.read(sub_len)
            if data == '' or total_len >= length:
                break

            f_out.write(data)
            total_len += len(data)
            if m_verbose == 2:
                print("address: 0x%06x, size: %s, total size: %d bytes (%d%%)" %
                      (sub_addr, sub_len, total_len, int(total_len * 100 / length)))
            sub_addr += sub_len


def convert_cpm_to_usievert(cpm, unit, cpm_to_usievert):
    if cpm_to_usievert is None:
        return cpm, unit

    if unit == 'CPS':
        return cpm * cpm_to_usievert[1] / cpm_to_usievert[0] * 60, 'uSv/h'
    elif unit == 'CPM':
        return cpm * cpm_to_usievert[1] / cpm_to_usievert[0], 'uSv/h'
    elif unit == 'CPH':
        return cpm * cpm_to_usievert[1] / cpm_to_usievert[0] / 60, 'uSv/h'
    else:
        return cpm, unit


def get_unit_conversion_from_device():
    # make sure the cached config is up to date
    if m_config_data is None:
        get_config()

    cal1_sv = m_config['cal1_sv'] * 1000 / m_config['cal1_cpm']
    cal2_sv = m_config['cal2_sv'] * 1000 / m_config['cal2_cpm']
    cal3_sv = m_config['cal3_sv'] * 1000 / m_config['cal3_cpm']
    cal_sv = (cal1_sv + cal2_sv + cal3_sv) / 3

    if m_verbose == 2:
        print("calibration value 1 from device: {:d} CPM = {:.2f} uSievert/h"
              .format(m_config['cal1_cpm'], m_config['cal1_sv']))
        print("calibration value 2 from device: {:d} CPM = {:.2f} uSievert/h"
              .format(m_config['cal2_cpm'], m_config['cal2_sv']))
        print("calibration value 3 from device: {:d} CPM = {:.2f} uSievert/h"
              .format(m_config['cal3_cpm'], m_config['cal3_sv']))
        print("using the average of calibration values: {:d} CPM = {:.2f} uSievert/h"
              .format(1000, cal_sv))

    return 1000, cal_sv


def print_data(out_file, data_type, c_str, size=1, cpm_to_usievert=None):
    if size < 5:
        c_value = 0
        for i in range(size):
            c_value = c_value * 256 + ord(c_str[i])
        value = convert_cpm_to_usievert(c_value, data_type, cpm_to_usievert)

    else:
        return '(unsupported size: {})'.format(size)

    if value[1] is None or value[1] == '':
        return None
    elif value[1] == 'uSv/h':
        return '{:.4f},{:s}'.format(value[0], value[1])
    else:
        return '{:d},{:s}'.format(value[0], value[1])


def parse_data_file(in_file=DEFAULT_BIN_FILE, out_file=DEFAULT_CSV_FILE,
                    cpm_to_usievert=None):
    if in_file is None:
        in_file = DEFAULT_BIN_FILE
    if m_verbose >= 1:
        print("parsing file '" + in_file + "', and storing data to '" +
              out_file + "'")

    marker = 0
    eof_count = 0
    data_type = '*'
    f_in = open(in_file, 'rb')
    f_out = open(out_file, 'w')

    while True:
        c_str = f_in.read(1)
        if c_str == '':
            break
        c = ord(c_str)

        # handle commands and large values
        if marker == 0x55aa:
            # command: set count type
            if c == 0x00:
                data = f_in.read(9)
                if data == '' or len(data) < 9:
                    break

                save_mode = ord(data[8])
                if save_mode == 0:
                    data_type = ''
                    mode_str = 'off'
                elif save_mode == 1:
                    data_type = 'CPS'
                    mode_str = 'every second'
                elif save_mode == 2:
                    data_type = 'CPM'
                    mode_str = 'every minute'
                elif save_mode == 3:
                    data_type = 'CPM'
                    mode_str = 'every hour'
                elif save_mode == 4:
                    data_type = 'CPS'
                    mode_str = 'every second - threshold'
                elif save_mode == 5:
                    data_type = 'CPM'
                    mode_str = 'every minute - threshold'
                else:
                    data_type = ''
                    mode_str = '[UNKNOWN]'

                f_out.write(',,20%02d/%02d/%02d %02d:%02d:%02d,%s' %
                    (ord(data[0]), ord(data[1]), ord(data[2]), ord(data[3]),
                     ord(data[4]), ord(data[5]), mode_str) + EOL)

            # command: two byte value (large numbers)
            elif c == 0x01:
                data = f_in.read(2)
                if data == '' or len(data) < 2:
                    break

                value = print_data(f_out, data_type, data, size=2,
                                   cpm_to_usievert=cpm_to_usievert)
                f_out.write(value + EOL)

            # command: three byte value (very large numbers)
            elif c == 0x02:
                data = f_in.read(3)
                if data == '' or len(data) < 3:
                    break

                value = print_data(f_out, data_type, data, size=3,
                                   cpm_to_usievert=cpm_to_usievert)
                f_out.write(value + EOL)

            # command: four byte value (huge numbers)
            elif c == 0x03:  # TODO: test me ;)
                data = f_in.read(4)
                if data == '' or len(data) < 4:
                    break

                value = print_data(f_out, data_type, data, size=4,
                                   cpm_to_usievert=cpm_to_usievert)
                f_out.write(value + EOL)

            # command: note
            elif c == 0x04:
                data = f_in.read(1)
                if data == '':
                    break

                length = ord(data)
                data = f_in.read(length)
                f_out.write(',,,,' + data + EOL)

            # command: unknown/unsupported
            else:
                f_out.write(',,,,[%d?]' % c + EOL)

            marker = 0
            # end of command
            continue

        if marker == 0x55:
            # command detected
            if c == 0xaa:
                marker = 0x55aa
                # handle command in the next loop
                continue
            else:
                # possible command turns out to be a regular value
                f_out.write(print_data(f_out, data_type, chr(0x55), size=1,
                                       cpm_to_usievert=cpm_to_usievert) + EOL)
                marker = 0
        else:
            marker = 0

        # possible command detected (but it still could be a regular value)
        if c == 0x55:
            marker = 0x55
            continue

        value = print_data(f_out, data_type, c_str, size=1,
                           cpm_to_usievert=cpm_to_usievert)
        if value is not None:
            f_out.write(value + EOL)

        # detect end of file, this is needed if the device is still logging but
        # hasn't reached the end of the flash memory yet
        if ord(c_str[0]) == 0xff:
            eof_count += 1
            if eof_count == 100:
                break
        else:
            eof_count = 0

    f_in.close()
    f_out.close()


def exit_gracefully(signum, frame):
    global m_terminate
    m_terminate = True


def set_heartbeat(enable, cpm_to_usievert=None):
    if m_device is None:
        print('ERROR: no device connected')
        return -1

    if enable:
        m_device.write('<HEARTBEAT1>>')

        signal.signal(signal.SIGINT, exit_gracefully)
        signal.signal(signal.SIGTERM, exit_gracefully)

        try:
            while not m_terminate:
                cpm = m_device.read(2)
                if cpm == '':
                    continue
                value = struct.unpack(">H", cpm)[0] & 0x3fff

                unit_value = (value, 'CPS')
                if cpm_to_usievert is not None:
                    unit_value = convert_cpm_to_usievert(value, 'CPS', cpm_to_usievert)

                if unit_value[1] == 'uSv/h':
                    print('{:.4f} {:s}'.format(unit_value[0], unit_value[1]))
                else:
                    print('{:d} {:s}'.format(unit_value[0], unit_value[1]))

        except KeyboardInterrupt:
            print("")
        except serial.SerialException:
            pass
        finally:
            # make sure we stop the heartbeat
            m_device.write('<HEARTBEAT0>>')

    else:
        m_device.write('<HEARTBEAT0>>')
        while True:
            x = m_device.read(1)
            sys.stdout.write('.')
            if x == '':
                break
        if m_verbose == 2:
            print("ok")


def get_temperature():
    if m_device is None:
        print('ERROR: no device connected')
        return -1

    m_device.write('<GETTEMP>>')
    temp = m_device.read(4)

    if temp == '' or len(temp) < 4:
        print('WARNING: no valid temperature received')
        return ''

    sign = ''
    if ord(temp[2]) != 0:
        sign = '-'
    temp_str = u'{:s}{:d}.{:d} {:s}{:s}' \
               .format(sign, ord(temp[0]), ord(temp[1]), unichr(0x00B0), unichr(0x0043))
    return temp_str.encode('utf-8')


def get_gyro():
    if m_device is None:
        print('ERROR: no device connected')
        return -1

    m_device.write('<GETGYRO>>')
    gyro = m_device.read(7)

    if gyro == '' or len(gyro) < 7:
        print('WARNING: no valid gyro data received')
        return ''

    (x, y, z, dummy) = struct.unpack(">hhhB", gyro)
    return "x:{}, y:{}, z:{}".format(x, y, z)


def get_config():
    global m_config_data, m_config

    if m_device is None:
        print('ERROR: no device connected')
        return -1

    if m_device_name in CONFIGURATION_BUFFER_SIZE:
        size = CONFIGURATION_BUFFER_SIZE[m_device_name]
    else:
        size = DEFAULT_CONFIGURATION_SIZE

    m_device.write('<GETCFG>>')
    data = m_device.read(size)

    if data == '' or len(data) == 0:
        print("WARNING: reading device configuration failed")
        return -1

    m_config_data = ctypes.create_string_buffer(data)

    m_config = {}
    m_config['cal1_cpm'] = ord(m_config_data[ADDRESS_CALIBRATE1_CPM]) * 256 \
                           + ord(m_config_data[ADDRESS_CALIBRATE1_CPM + 1])
    m_config['cal1_sv'] = struct.unpack(">f",
                                        m_config_data[ADDRESS_CALIBRATE1_SV:ADDRESS_CALIBRATE1_SV + 4])[0]
    m_config['cal2_cpm'] = ord(m_config_data[ADDRESS_CALIBRATE2_CPM]) * 256 \
                           + ord(m_config_data[ADDRESS_CALIBRATE2_CPM + 1])
    m_config['cal2_sv'] = struct.unpack(">f",
                                        m_config_data[ADDRESS_CALIBRATE2_SV:ADDRESS_CALIBRATE2_SV + 4])[0]
    m_config['cal3_cpm'] = ord(m_config_data[ADDRESS_CALIBRATE3_CPM]) * 256 \
                           + ord(m_config_data[ADDRESS_CALIBRATE3_CPM + 1])
    m_config['cal3_sv'] = struct.unpack(">f",
                                        m_config_data[ADDRESS_CALIBRATE3_SV:ADDRESS_CALIBRATE3_SV + 4])[0]
    m_config['server_website'] = m_config_data[ADDRESS_SERVER_WEBSITE:ADDRESS_SERVER_WEBSITE + 32]
    m_config['server_url'] = m_config_data[ADDRESS_SERVER_URL:ADDRESS_SERVER_URL + 32]
    m_config['user_id'] = m_config_data[ADDRESS_USER_ID:ADDRESS_USER_ID + 16]
    m_config['counter_id'] = m_config_data[ADDRESS_COUNTER_ID:ADDRESS_COUNTER_ID + 16]
    if ord(m_config_data[ADDRESS_WIFI_ON_OFF]) == 255:
        m_config['wifi_active'] = True
    else:
        m_config['wifi_active'] = False
    m_config['wifi_ssid'] = m_config_data[ADDRESS_WIFI_SSID:ADDRESS_WIFI_SSID + 16]
    m_config['wifi_password'] = m_config_data[ADDRESS_WIFI_PASSWORD:ADDRESS_WIFI_PASSWORD + 16]
    # TODO: figure out the other configuration parameters...


def list_config():
    # make sure the cached config is up to date
    if m_config_data is None:
        get_config()

    dump_data(m_config_data)

    print("server website: {}".format(m_config['server_website']))
    print("server url: {}".format(m_config['server_url']))
    print("user id: {}".format(m_config['user_id']))
    print("counter id: {}".format(m_config['counter_id']))
    print("wifi active: {}".format(str(m_config['wifi_active'])))
    print("wifi ssid: {}".format(m_config['wifi_ssid']))
    print("wifi password: {}".format(m_config['wifi_password']))
    print("calibrate 1: {:d} cpm = {:.2f} sv"
          .format(m_config['cal1_cpm'], m_config['cal1_sv']))
    print("calibrate 2: {:d} cpm = {:.2f} sv"
          .format(m_config['cal2_cpm'], m_config['cal2_sv']))
    print("calibrate 3: {:d} cpm = {:.2f} sv"
          .format(m_config['cal3_cpm'], m_config['cal3_sv']))


def write_config(parameters):
    global m_config_data

    if m_device_name == 'GMC-280' or \
       m_device_name == 'GMC-300' or \
       m_device_name == 'GMC-320':
        address_size = 'B'  # 1 byte address
    elif m_device_name == 'GMC-500':
        address_size = 'H'  # 2 byte address
    else:
        print('ERROR: device not supported, feature not available')
        return

    # make sure the cached config is up to date
    if m_config_data is None:
        get_config()

    # update the cached configuration (in memory)
    for par in parameters:
        par_value = par.split('=')
        if len(par_value) != 2:
            print("WARNING: skipping parameter '{}', it doesn't seem to contain a 'parameter-name=value' pair."
                  .format(par))
            continue

        if par_value[0] == 'cal1-cpm':
            struct.pack_into('>H', m_config_data, ADDRESS_CALIBRATE1_CPM,
                             int(par_value[1]))
        elif par_value[0] == 'cal1-sv':
            struct.pack_into('>f', m_config_data, ADDRESS_CALIBRATE1_SV,
                             float(par_value[1]))
        elif par_value[0] == 'cal2-cpm':
            struct.pack_into('>H', m_config_data, ADDRESS_CALIBRATE2_CPM,
                             int(par_value[1]))
        elif par_value[0] == 'cal2-sv':
            struct.pack_into('>f', m_config_data, ADDRESS_CALIBRATE2_SV,
                             float(par_value[1]))
        elif par_value[0] == 'cal3-cpm':
            struct.pack_into('>H', m_config_data, ADDRESS_CALIBRATE3_CPM,
                             int(par_value[1]))
        elif par_value[0] == 'cal3-sv':
            struct.pack_into('>f', m_config_data, ADDRESS_CALIBRATE3_SV,
                             float(par_value[1]))
        else:
            print("WARNING: parameter with name '{}' not supported".format(par_value[0]))

    # erase all stored parameters in flash
    m_device.write('<ECFG>>')
    if not command_returned_ok():
        print("WARNING: erase operation failed, parameters not stored on device")
        return

    if m_device_name in CONFIGURATION_BUFFER_SIZE:
        size = CONFIGURATION_BUFFER_SIZE[m_device_name]
    else:
        size = DEFAULT_CONFIGURATION_SIZE

    # write all cached parameters (from memory) into the device
    for i in range(size):
        cmd = struct.pack('>' + address_size + 'B', i, ord(m_config_data[i]))
        m_device.write('<WCFG' + cmd + '>>')
        if not command_returned_ok():
            print("WARNING: write operation failed at address 0x%02X, (some) parameters not stored to device" % i)

    # make the change permanent (write flash)
    m_device.write('<CFGUPDATE>>')
    if not command_returned_ok():
        print("WARNING: update operation failed, parameters not stored on device")
        return


def get_date_and_time():
    if m_device is None:
        print('ERROR: no device connected')
        return -1

    m_device.write('<GETDATETIME>>')
    date = m_device.read(7)

    if date == '' or len(date) < 7:
        print('WARNING: no valid date received')
        return ''

    (year, month, day, hour, minute, second, dummy) = struct.unpack(">BBBBBBB", date)
    return "{}/{}/{} {}:{}:{}".format(year, month, day, hour, minute, second)


def set_date_and_time(date_time):
    if m_device is None:
        print('ERROR: no device connected')
        return -1

    cmd = struct.pack('>BBBBBB',
                      date_time.year - 2000,
                      date_time.month,
                      date_time.day,
                      date_time.hour,
                      date_time.minute,
                      date_time.second)
    m_device.write('<SETDATETIME' + cmd + '>>')

    if not command_returned_ok():
        print("WARNING: setting date and time not succeded")


def send_key(key):
    if m_device is None:
        print('ERROR: no device connected')
        return -1

    if key.lower() == 's1':
        m_device.write('<KEY0>>')

    elif key.lower() == 's2':
        m_device.write('<KEY1>>')

    elif key.lower() == 's3':
        m_device.write('<KEY2>>')

    elif key.lower() == 's4':
        m_device.write('<KEY3>>')


def firmware_update():
    print('ERROR: option not yet available')


def factory_reset():
    if m_device is None:
        print('ERROR: no device connected')
        return -1

    m_device.write('<FACTORYRESET>>')

    if not command_returned_ok():
        print("WARNING: factory reset not succeded")


def reboot():
    if m_device is None:
        print('ERROR: no device connected')
        return -1

    m_device.write('<REBOOT>>')


def dump_data(data):
    for d in range(len(data)):
        print("0x{:02x} 0x{:02x} ({:s})".format(d, ord(data[d]), data[d]))


def open_device(port=None, baud_rate=115200, skip_check=False, device_type=None,
                allow_fail=False):
    global m_device, m_device_name

    if port is None or port == '':
        port = DEFAULT_PORT

    try:
        m_device = serial.Serial(port, baudrate=baud_rate, timeout=1.0)
    except serial.serialutil.SerialException:
        if not allow_fail:
            if platform.system() == 'Windows':
                print("ERROR: No device found (use the '-p COM1' option and provide the correct port)")
            else:
                print("ERROR: No device found (use the '-p /dev/ttyUSB0' option and provide the correct port, or install the udev rule as described in the INSTALL file)")
        return -1

    clear_port()

    res = 0
    if not skip_check:
        res = check_device_type()

    if device_type is not None:
        if device_type == 'GMC-280' or \
           device_type == 'GMC-300' or \
           device_type == 'GMC-320' or \
           device_type == 'GMC-500':
            m_device_name = device_type
            if m_verbose == 2:
                print("using device-type: {}".format(m_device_name))
        else:
            print("WARNING: unsupported selected device type '{}', defaulting to '{}'"
                  .format(device_type, m_device_name))

    return res


def set_verbose_level(verbose):
    global m_verbose
    m_verbose = verbose
