#!/usr/bin/env python
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
import os
import serial
import argparse
import struct
import platform
import tempfile
import ctypes
import datetime
import signal

DEFAULT_CONFIG = '~/.gq-gmc-control.conf'
DEFAULT_BIN_FILE = 'gq-gmc-log.bin'
DEFAULT_CSV_FILE = 'gq-gmc-log.csv'
if platform.system() == 'Windows':
    DEFAULT_PORT = 'COM3'
else:
    DEFAULT_PORT = '/dev/ttyUSB0'
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
VERSION = '1.1.0'

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

m_description = """
Control tool  for the GQ GMC  Geiger Counters.  This tool  provides a convenient
cross platform (Linux,  Windows & OS X)  command line user interface  to most of
the  device features  (which are  accessible  by USB).   Currently the  GMC-280,
GMC-300, GMC-320 and GMC-500 models are supported.

The    implementation     of    the     tool    is    based     on    GQ-RFC1201
(http://www.gqelectronicsllc.com/download/GQ-RFC1201.txt), and testing done on a
GQ GMC-500. It possible some incompatibilities exists with other GQ GMC devices.
Any help to test  and debug these devices is welcome, and  will only improve the
quality of this tool.  """

m_epilog = "Copyright (c) 2017, Chaim Zax <chaim.zax@gmail.com>"


def handle_arguments():
    parser = argparse.ArgumentParser(description=m_description, epilog=m_epilog)
    unit_group = parser.add_mutually_exclusive_group()
    group = parser.add_argument_group(
        title='commands',
        description='Device specific commands. Any of the following commands below can be send to the device. '
                    + 'Only one command can be used at a time.')
    command_group = group.add_mutually_exclusive_group(required=True)

    # device settings
    parser.add_argument('-b', '--baud-rate',
        action='store', default=DEFAULT_BAUD_RATE, type=int,
        help='set the baud-rate of the serial port (default {})'.format(DEFAULT_BAUD_RATE))
    parser.add_argument('-p', '--port',
        action='store', default='',
        help="set the serial port (default '{}')".format(DEFAULT_PORT))
    # command line configuration
    parser.add_argument('-n', '--no-parse',
        action='store_true', default=None,
        help="do not parse the history data into a csv file, only store the binary data. "
             + "use only in combination with the '--data' command option.")
    parser.add_argument('-c', '--config',
        action='store', default=None,
        help='load command line options from a configuration file')
    # unit_group.add_argument('-S', '--output-in-sievert', metavar='CPM,Sievert', nargs='?',
    # help='don\'t log data in CPM or CPS but in micro Sieverts. optionally
    # supply a tuple used as a conversion factor. e.g. \'1000,0.0000065\'
    # indicates 1000 CPM equals 6.50 uSievert.')
    unit_group.add_argument('-S', '--output-in-usievert',
        metavar='CPM,uSievert', nargs='?', dest='output_in_usievert', const='',
        help="don't log data in CPM or CPS but in micro Sievert/h. optionally supply a tuple used as a conversion "
             + "factor. e.g. \'1000,6.50\' indicates 1000 CPM equals 6.50 uSievert/h.")
    unit_group.add_argument('-M', '--output-in-cpm',
        action='store_true', default=None,
        help='log data in CPM or CPS')
    parser.add_argument('-K', '--skip-check',
        action='store_true', default=None,
        help="skip sanity/device checking on start-up. the tool will use it's default settings, if needed use in "
             + "combination with '--device-type' to override these defaults "
             + "(recommended when skipping device checking)")
    parser.add_argument('-Y', '--device-type',
        action='store', default='', nargs=1,
        help="don't use the auto-detect feature to select the device-type, but use the one provided "
             + "('CMG-280', 'CMG-300', 'CMG-320' or 'CMG-500')")
    parser.add_argument('output_file',
        metavar='OUTPUT_FILE', nargs='?',
        help='an output file')
    parser.add_argument('-u', '--unit-conversion-from-device',
        action='store_true', default=None,
        help="use the CPM to Sievert calibration values from the device to convert data to uSieverts.")
    parser.add_argument('-B', '--verbose',
        action='store', default=None, type=int, choices=[1, 2],
        help="in- or decrease verbosity")

    # device operations
    command_group.add_argument('-i', '--device-info',
        action='store_true', default=None,
        help='get the device type and revision')
    command_group.add_argument('-s', '--serial',
        action='store_true', default=None,
        help='get the serial number of the device')
    command_group.add_argument('-o', '--power-on',
        action='store_true', default=None,
        help='powers on the device')
    command_group.add_argument('-O', '--power-off',
        action='store_true', default=None,
        help='powers off the device')
    command_group.add_argument('-a', '--heartbeat',
        action='store_true', default=None,
        help='prints every second the CPS (or uSv/h) value until CTRL-C is pressed')
    command_group.add_argument('-A', '--heartbeat-off',
        action='store_true', default=None,
        help="disable the heartbeat (should normally not be needed when using the '--heartbeat' command)")
    command_group.add_argument('-V', '--voltage',
        action='store_true', default=None,
        help='get the current voltage of the battery (or power supply)')
    command_group.add_argument('-C', '--cpm',
        action='store_true', default=None,
        help="get the current CPM (or uSv/h). can be used in combination with the '--output-in-usievert',  "
             + "'--unit-conversion-from-device' and/or '--output-in-cpm' options")
    command_group.add_argument('-T', '--temperature',
        action='store_true', default=None,
        help='get the current temperature')
    command_group.add_argument('-G', '--gyro',
        action='store_true', default=None,
        help='get the current gyroscopic data')
    command_group.add_argument('-d', '--data',
        action='store_true', default=None,
        help="download all history data and store it to file (default '{}' or '{}'). can be used in combination with "
             + "the '--no-parse', '--output-in-usievert',  '--unit-conversion-from-device' and/or '--output-in-cpm' "
             + "options".format(DEFAULT_CSV_FILE, DEFAULT_BIN_FILE))
    command_group.add_argument('-P', '--only-parse',
        nargs='?', type=str, dest='bin_file', const='',
        help="do not download history data, only parse the already downloaded data to a csv file (default '{}'). "
             + "can be used in combination with the '--data' option to create a csv file with a different file-name, "
             + "and the '--output-in-usievert',  '--unit-conversion-from-device' and/or '--output-in-cpm' options"
             .format(DEFAULT_CSV_FILE))
    command_group.add_argument('-l', '--list-config',
        action='store_true', default=None,
        help='shows the current device configuration')
    command_group.add_argument('-w', '--write-config',
        action='store', default=None, nargs='+', metavar='PARAMETER=VALUE',
        dest='write_config',
        help="write a specific device configuration parameter. the following parameters are supported: 'cal1-cpm', "
             + "'cal1-sv', 'cal2-cpm', 'cal2-sv', 'cal3-cpm' and 'cal3-sv', the values depend on the type of argument "
             + "(e.g. '1000' for cpm, '6.45' for us, '0x123' for addresses). multiple configuration parameters can be "
             + "provided at once (space separated). note: this feature is only tested on a GQ GMC-500.")
    command_group.add_argument('-E', '--set-date-and-time',
                               action='store', default=None, type=valid_date_time,
                               metavar='"yy/mm/dd HH:MM:SS"',
                               help='set the local date and time')
    command_group.add_argument('-e', '--get-date-and-time',
        action='store_true', default=None,
        help='get the local date and time')
    command_group.add_argument('-k', '--send-key',
        action='store', default=None, choices=['S1', 'S2', 'S3', 'S4'],
        help='emulate a key-press of the device')
    command_group.add_argument('-F', '--firmware-update',
        action='store', default=None,
        help='update the firmware of the device (NOT IMPLEMENTED)')
    command_group.add_argument('-R', '--reset',
        action='store_true', default=None,
        help='reset the device to the default factory settings')
    command_group.add_argument('-r', '--reboot',
        action='store_true', default=None,
        help='reboot the device')
    command_group.add_argument('-L', '--list-tool-config',
        action='store_true', default=None,
        help='shows the currently used command line configuration options')
    command_group.add_argument('-v', '--version', action='version',
                               version='%(prog)s v{}'.format(VERSION))

    return parser.parse_args()


def valid_date_time(s):
    try:
        return datetime.datetime.strptime(s, '%y/%m/%d %H:%M:%S')
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


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
            print('ERROR: No device found')
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


if __name__ == "__main__":
    baud_rate = DEFAULT_BAUD_RATE
    port = DEFAULT_PORT
    bin_file = DEFAULT_BIN_FILE
    output_file = DEFAULT_CSV_FILE
    no_parse = DEFAULT_NO_PARSE
    output_in_usievert = DEFAULT_CPM_TO_SIEVERT
    output_in_cpm = DEFAULT_OUTPUT_IN_CPM
    skip_check = DEFAULT_SKIP_CHECK
    unit_conversion_from_device = DEFAULT_UNIT_CONVERSION_FROM_DEVICE
    device_type = DEFAULT_DEVICE_TYPE
    verbose = DEFAULT_VERBOSE_LEVEL

    # handle all command line options
    args = handle_arguments()

    # load configuration file(s)
    home = os.path.expanduser("~")
    default_config = DEFAULT_CONFIG.replace('~', home)
    if os.path.isfile(default_config):
        exec(open(default_config).read())

    if args.config is not None and os.path.isfile(args.config):
        exec(open(args.config).read())

    if args.baud_rate != '':
        baud_rate = args.baud_rate
    if args.port != '':
        port = args.port
    if args.bin_file is not None and args.bin_file != '':
        bin_file = args.bin_file
    if args.output_file is not None:
        output_file = args.output_file
    if args.no_parse is not None:
        no_parse = args.no_parse
    if args.output_in_usievert is not None and args.output_in_usievert != '':
        output_in_usievert = args.output_in_usievert
    if args.output_in_cpm is not None:
        output_in_cpm = args.output_in_cpm
    if args.skip_check is not None:
        skip_check = args.skip_check
    if args.unit_conversion_from_device is not None:
        unit_conversion_from_device = args.unit_conversion_from_device
    if args.device_type is not None and len(args.device_type) > 0:
        device_type = args.device_type[0]
    if args.verbose is not None:
        verbose = args.verbose

    m_verbose = verbose

    # additional checks for conflicting command line parameters
    if args.unit_conversion_from_device is not None and args.output_in_cpm is not None:
        print("ERROR: the options '--output-in-cpm' and '--unit-conversion-from-device' can not be combined")
        sys.exit(-1)

    if args.output_in_usievert is not None and args.output_in_usievert != '' \
            and args.unit_conversion_from_device is not None:
        print("ERROR: providing '--output-in-usievert' with a conversion factor can not be combined with the "
              + "'--unit-conversion-from-device' option")
        sys.exit(-1)

    if no_parse and not args.data:
        print("ERROR: the '--no-parse' option can only be used with the '--data' option.")
        sys.exit(-1)

    # show existing configuration
    if args.list_tool_config:
        print("baud_rate                    = {}".format(baud_rate))
        print("port                        = '{}'".format(port))
        print("bin_file                    = '{}'".format(bin_file))
        print("output_file                 = '{}'".format(output_file))
        print("no_parse                    = {}".format(no_parse))
        print("output_in_usievert          = '{}'".format(output_in_usievert))
        print("output_in_cpm               = {}".format(output_in_cpm))
        print("skip_check                  = {}".format(skip_check))
        print("unit_conversion_from_device = {}".format(unit_conversion_from_device))
        if device_type is None:
            print("device_type                 = None")
        else:
            print("device_type                 = '{}'".format(device_type))
        print("verbose                     = {}".format(verbose))
        sys.exit(0)

    # prefix the comport to support ports above COM9
    if platform.system() == 'Windows':
        port = '\\\\.\\' + port

    # determine CPM to uSievert conversion factor
    cpm_to_usievert = None
    if not output_in_cpm or args.output_in_usievert is not None:
        conversion = output_in_usievert.split(',')
        if len(conversion) != 2:
            print("WARNING: conversion to Sieverts not valid, defaulting to CPM/CPS")
        else:
            cpm_to_usievert = (int(conversion[0]), float(conversion[1]))

    # only parse a binary file, if needed
    if args.bin_file is not None:
        if unit_conversion_from_device:
            res = open_device(port=port, baud_rate=baud_rate, skip_check=skip_check,
                              device_type=device_type, allow_fail=True)
            if res != 0:
                print('WARNING: no connection to device, defaulting to known unit '
                      + 'conversion ({:d} CPM = {:.2f} uSv/h)'
                        .format(cpm_to_usievert[0], cpm_to_usievert[1]))
            else:
                cpm_to_usievert = get_unit_conversion_from_device()

        parse_data_file(bin_file, output_file, cpm_to_usievert=cpm_to_usievert)
        sys.exit(0)

    if args.device_info:
        skip_check = True

    # all commands below require a connected device
    res = open_device(port=port, baud_rate=baud_rate, skip_check=skip_check,
                      device_type=device_type)
    if res != 0:
        sys.exit(-res)

    # determine CPM to uSievert conversion factor by using the calibration
    # values from the device
    if unit_conversion_from_device:
        cpm_to_usievert = get_unit_conversion_from_device()

    # parse all history data, and get it from the device if needed
    if args.data:
        tmp_file = None
        bin_output_file = ''
        if no_parse:
            if args.output_file is not None:
                bin_output_file = output_file
            else:
                bin_output_file = bin_file
        else:
            tmp_file = tempfile.mktemp('.bin')
            bin_output_file = tmp_file

        get_data(out_file=bin_output_file)

        if not no_parse:
            parse_data_file(bin_output_file, output_file,
                            cpm_to_usievert=cpm_to_usievert)

        if tmp_file is not None and os.path.exists(tmp_file):
            os.remove(tmp_file)

    # handle the rest of the commands

    elif args.device_info:
        print(get_device_type())

    elif args.serial:
        print(get_serial_number())

    elif args.power_on:
        set_power(True)

    elif args.power_off:
        set_power(False)

    elif args.heartbeat:
        set_heartbeat(True, cpm_to_usievert=cpm_to_usievert)

    elif args.heartbeat_off:
        set_heartbeat(False)

    elif args.voltage:
        print(get_voltage())

    elif args.cpm:
        print(get_cpm(cpm_to_usievert=cpm_to_usievert))

    elif args.temperature:
        print(get_temperature())

    elif args.gyro:
        print(get_gyro())

    elif args.list_config:
        list_config()

    elif args.write_config is not None:
        write_config(args.write_config)

    elif args.get_date_and_time:
        print(get_date_and_time())

    elif args.set_date_and_time is not None:
        set_date_and_time(args.set_date_and_time)

    elif args.send_key is not None:
        send_key(args.send_key)

    elif args.firmware_update is not None:
        firmware_update()

    elif args.reset:
        factory_reset()

    elif args.reboot:
        reboot()
