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
#  Copyright (c) 2017, Chaim Zax <chaim.zax@gmail.com>

import sys
import os
import serial
import argparse
import struct
import platform
import tempfile

DEFAULT_CONFIG = '~/.gq-gmc-control.conf'
DEFAULT_BIN_FILE = 'gq-gmc-log.bin'
DEFAULT_CSV_FILE = 'gq-gmc-log.csv'
if platform.system() == 'Windows':
    DEFAULT_PORT = '\\.\COM4'
else:
    DEFAULT_PORT = '/dev/ttyUSB0'
DEFAULT_BAUDRATE = 115200
DEFAULT_CPM_TO_SIEVERT = '1000,6.50'
DEFAULT_OUTPUT_IN_CPM = False
DEFAULT_NO_PARSE = False

EOL = '\n'
VERSION = '1.0.0'

def handleArguments():
    parser = argparse.ArgumentParser(description='Control tool for the GQ GMC-500 series.',
                                     epilog="Copyright (c) 2017, Chaim Zax <chaim.zax@gmail.com>")
    unit_group = parser.add_mutually_exclusive_group()
    group = parser.add_argument_group(title='commands', description='Device specific commands. Any of the following commands below can be send to de device. Only one command can be used at a time.')
    command_group = group.add_mutually_exclusive_group(required=True)

    # device settings
    parser.add_argument('-b', '--baudrate', action='store', default=DEFAULT_BAUDRATE, type=int,
                       help='set the baudrate of the serial port (default %d)' % (DEFAULT_BAUDRATE))
    parser.add_argument('-p', '--port', action='store', default='',
                       help='set the serial port (default \'%s\')' % (DEFAULT_PORT))
    # command line configuration
    parser.add_argument('-n', '--no-parse', action='store_true', default=None,
                       help='do not parse the history data into a csv file, only store the binary data. use only in combination with the \'--data\' command option.')
    parser.add_argument('-c', '--config', action='store', default=None,
                       help='load command line options from a configuration file')
    #unit_group.add_argument('-S', '--output-in-sievert', metavar='CPM,Sievert', nargs='?',
    #                    help='don\'t log data in CPM or CPS but in micro Sieverts. optionally supply a tuple used as a conversion factor. e.g. \'1000,0.0000065\' indicates 1000 CPM equals 6.50 uSievert.')
    unit_group.add_argument('-S', '--output-in-usievert', metavar='CPM,uSievert', nargs='?', dest='output_in_usievert', const='',
                            help='don\'t log data in CPM or CPS but in micro Sieverts. optionally supply a tuple used as a conversion factor. e.g. \'1000,6.50\' indicates 1000 CPM equals 6.50 uSievert.')
    unit_group.add_argument('-M', '--output-in-cpm', action='store_true', default=None,
                            help='log data in CPM or CPS')
    parser.add_argument('output_file', metavar='OUTPUT_FILE', nargs='?',
                        help='an output file')

    # device operations
    command_group.add_argument('-i', '--device-info', action='store_true', default=None,
                       help='get the device type and revision')
    command_group.add_argument('-s', '--serial', action='store_true', default=None,
                       help='get the serial number of the device')
    command_group.add_argument('-o', '--power-on', action='store_true', default=None,
                       help='powers on the device')
    command_group.add_argument('-O', '--power-off', action='store_true', default=None,
                       help='powers off the device')
    command_group.add_argument('-h0', '--hearbeat0', action='store_true', default=None,
                       help='')
    command_group.add_argument('-h1', '--hearbeat1', action='store_true', default=None,
                       help='')
    command_group.add_argument('-V', '--voltage', action='store_true', default=None,
                       help='get the current voltage of the battery (or power supply)')
    command_group.add_argument('-C', '--cpm', action='store_true', default=None,
                       help='get the current CPM')
    command_group.add_argument('-T', '--temperature', action='store_true', default=None,
                       help='get the current temperature')
    command_group.add_argument('-G', '--gyro', action='store_true', default=None,
                       help='get the current gyroscopic data')
    command_group.add_argument('-d', '--data', action='store_true', default=None,
                       help='download all history data and store it to file (default \'%s\' or \'%s\'). can be used in combination with the \'--no-parse\' option' % (DEFAULT_CSV_FILE, DEFAULT_BIN_FILE))
    command_group.add_argument('-P', '--only-parse', nargs='?', type=str, dest='bin_file', const='',
                       help='do not download history data, only parse the already downloaded data to a csv file (default \'%s\'). can be used in combination with the \'--data\' option to create a csv file with a different file-name' % (DEFAULT_CSV_FILE))
    command_group.add_argument('-l', '--list-config', action='store_true', default=None,
                       help='shows the current device configuration')
    command_group.add_argument('-e', '--erase-config', action='store_true', default=None,
                       help='erase the current device configuration')
    command_group.add_argument('-w', '--write-config', action='store_true', default=None,
                       help='write the device configuration')
    command_group.add_argument('-u', '--update-config', action='store_true', default=None,
                       help='update the current device configuration')
    command_group.add_argument('-t', '--set-time', action='store', default=None,
                       help='set the local time')
    command_group.add_argument('-D', '--set-date', action='store', default=None,
                       help='set the local date')
    command_group.add_argument('-k', '--send-key', action='store', default=None,
                       help='emulate a keypress of the device')
    command_group.add_argument('-F', '--firmware-update', action='store', default=None,
                       help='update the firmware of the device')
    command_group.add_argument('-R', '--reset', action='store_true', default=None,
                       help='reset the device to the default factory settings')
    command_group.add_argument('-r', '--reboot', action='store_true', default=None,
                       help='reboot the device')

    command_group.add_argument('-L', '--list-tool-config', action='store_true', default=None,
                       help='shows the currently used command line configuration options')
    command_group.add_argument('-v', '--version', action='version', version='%(prog)s ' + VERSION)

    return parser.parse_args()

# "GETCPM"
# "GETCPS"
# "GETCFG"
# "ECFG"
# "CFGUPDATE"
# "HEARTBEAT1"
# "HEARTBEAT0"
# "WCFGAD"
#
# "SETDATEMM"...
# "SETDATEDD"...
# "SETDATEYY"...
# "SETTIMEHH"...
# "SETTIMEMM"...
# "SETTIMESS"...
# "KEY"...
# "SPIR"...

FLASH_SIZE = {}
FLASH_SIZE['default'] = 0x00100000
FLASH_SIZE['GMC-500'] = 0x00100000

m_deviceType = None
m_deviceName = 'default'
m_port = None

def clearPort():
    # close any pending previous command
    m_port.write(">>")

    # get rid off all buffered data still in the queue
    while True:
        x = m_port.read(1)
        if x == '':
            break

def checkDeviceType():
    global m_deviceType, m_deviceName

    m_deviceType = getDeviceType()
    m_deviceName = m_deviceType[:7]

    if m_deviceName == 'GMC-500':
        print("device found: %s" % m_deviceType)

    else:
        print("device '%s' not supported" % m_deviceType)
        return -1

    return 0

def getDeviceType():
    if m_port == None:
        print('ERROR: no device connected')
        return -1

    m_port.write('<GETVER>>')
    deviceType = m_port.read(14)
    return deviceType

def getSerialNumber():
    if m_port == None:
        print('ERROR: no device connected')
        return -1

    m_port.write('<GETSERIAL>>')
    serialNumber = m_port.read(7)
    ser = ''
    for x in range(7):
        ser += "%02X" % ord(serialNumber[x])
    return ser

def setPower(on=True):
    if m_port == None:
        print('ERROR: no device connected')
        return -1

    if on:
        m_port.write('<' + TURN_ON_PWR_CMD + '>>')
    else:
        m_port.write('<' + TURN_OFF_PWR_CMD + '>>')

def getVoltage():
    if m_port == None:
        print('ERROR: no device connected')
        return -1

    m_port.write('<GETVOLT>>')
    voltage = m_port.read(3)
    return voltage

def getCPM():
    if m_port == None:
        print('ERROR: no device connected')
        return -1

    m_port.write('<GETCPM>>')
    cpm = m_port.read(2)
    value = struct.unpack(">H", cpm)[0]
    return value

def getData(address=0x000000, length=None, out_file=DEFAULT_BIN_FILE):
    if m_port == None:
        print('ERROR: no device connected')
        return -1

    if address == None:
        address = 0x000000
    if length == None:
        length = FLASH_SIZE[m_deviceName]
    if out_file == None or out_file == '':
        out_file = DEFAULT_BIN_FILE

    total_len = 0
    sub_addr = address
    sub_len = 4096

    print("storing data to '" + out_file + "'")
    f_out = open(out_file, 'w')

    while True:
        cmd = struct.pack('>sssssBBBHss', '<', 'S', 'P', 'I', 'R', (sub_addr >> 16) & 0xff, (sub_addr >> 8) & 0xff, (sub_addr) & 0xff, sub_len, '>', '>')
        m_port.write(cmd)

        data = m_port.read(sub_len)
        if data == '' or total_len >= length:
            break

        f_out.write(data)
        total_len += len(data)
        print("address: 0x%06x, size: %s, total size: %d bytes (%d%%)" % (sub_addr, sub_len, total_len, int(total_len*100/length)))
        sub_addr += sub_len

    f_out.close

def cpmToUSievert(cpm, unit, cpm_to_usievert):
    if cpm_to_usievert == None:
        return (cpm, unit)

    if unit == 'CPS':
        return (cpm * cpm_to_usievert[1] / cpm_to_usievert[0] * 60, 'uSv/h')
    elif unit == 'CPM':
        return (cpm * cpm_to_usievert[1] / cpm_to_usievert[0], 'uSv/h')
    elif unit == 'CPH':
        return (cpm * cpm_to_usievert[1] / cpm_to_usievert[0] / 60, 'uSv/h')
    else:
        return (cpm, unit)


def printData(out_file, data_type, c_str, size=1, cpm_to_usievert=None):
    value = (None, None)

    if size < 5:
        c_value = 0
        for i in range(size):
            c_value = c_value * 256 + ord(c_str[i])
        value = cpmToUSievert(c_value, data_type, cpm_to_usievert)

    else:
        return('(unsupported size: %d)' % (size))

    if value[1] == None or value[1] == '':
        return(None)
    elif value[1] == 'uSv/h':
        return('%.4f,%s' % value)
    else:
        return('%d,%s' % value)

def parseDataFile(in_file=DEFAULT_BIN_FILE, out_file=DEFAULT_CSV_FILE, cpm_to_usievert=None):
    if in_file == None:
        in_file = DEFAULT_BIN_FILE
    print("parsing file '" + in_file + "', and storing data to '" + out_file + "'")

    marker = 0
    #eof_count = 0
    data_type = '*'
    f_in = open(in_file, 'r')
    f_out = open(out_file, 'w')
    while True:
        c_str = f_in.read(1)
        if c_str == '':
            break
        c = ord(c_str)

        if marker == 0x55aa:
            if c == 0x00:
                date = f_in.read(9)

                save_mode = ord(date[8])
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
                    data_type = 'CPH'
                    mode_str = 'every hour'
                elif save_mode == 4:
                    data_type = 'CPS'
                    mode_str = 'every second - threshold'
                elif save_mode == 5:
                    data_type = 'CPM'
                    mode_str = 'every minute - threshold'

                f_out.write(',,20%02d/%02d/%02d %02d:%02d:%02d,%s' % (ord(date[0]), ord(date[1]), ord(date[2]), ord(date[3]), ord(date[4]), ord(date[5]), mode_str) + EOL)
            elif c == 0x01:
                data = f_in.read(2)
                value = printData(f_out, data_type, data, size=2, cpm_to_usievert=cpm_to_usievert)
                f_out.write(value + EOL)

            elif c == 0x02:
                data = f_in.read(3)
                value = printData(f_out, data_type, data, size=3, cpm_to_usievert=cpm_to_usievert)
                f_out.write(value + EOL)

            elif c == 0x03:  # TODO: test me ;)
                data = f_in.read(4)
                value = printData(f_out, data_type, data, size=4, cpm_to_usievert=cpm_to_usievert)
                f_out.write(value + EOL)

            elif c == 0x04:  # note
                length = ord(f_in.read(1))
                data = f_in.read(length)
                f_out.write(',,,,' + data + EOL)

            else:
                f_out.write(',,,,[%d?]' % (c) + EOL)
            marker = 0
            continue

        if marker == 0x55 and c == 0xaa:
            marker = 0x55aa
            continue
        else:
            marker = 0

        if c == 0x55:
            marker = 0x55
            continue

        value = printData(f_out, data_type, c_str, size=1, cpm_to_usievert=cpm_to_usievert)
        if value != None:
            f_out.write(value + EOL)

        # detect end of file
        #if ord(c_str[0]) == 0xff:
        #    eof_count += 1
        #    if eof_count == 100:
        #        break
        #else:
        #    eof_count = 0

    f_in.close()
    f_out.close()

def dumpData(data):
    for d in range(len(data)):
        print "0x%02x (%s)" % (ord(data[d]), data[d])

def openDevice(port=None, baudrate=115200):
    global m_port

    if port == None or port == '':
        port = DEFAULT_PORT

    try:
        m_port = serial.Serial(port, baudrate=baudrate, timeout=1.0)
    except serial.serialutil.SerialException:
        print('No device found')
        return -1

    clearPort()
    res = checkDeviceType()
    return res


if __name__ == "__main__":
    args = handleArguments()

    baudrate = DEFAULT_BAUDRATE
    port = DEFAULT_PORT
    bin_file = DEFAULT_BIN_FILE
    output_file = DEFAULT_CSV_FILE
    no_parse = DEFAULT_NO_PARSE
    output_in_usievert = DEFAULT_CPM_TO_SIEVERT
    output_in_cpm = DEFAULT_OUTPUT_IN_CPM

    home = os.path.expanduser("~")
    default_config = DEFAULT_CONFIG.replace('~', home)
    if os.path.isfile(default_config):
        exec (open(default_config).read())

    if args.config != None and os.path.isfile(args.config):
        exec (open(args.config).read())

    if args.baudrate != '':
        baudrate = args.baudrate
    if args.port != '':
        port = args.port
    if args.bin_file != None and args.bin_file != '':
        bin_file = args.bin_file
    if args.no_parse != None:
        no_parse = args.no_parse
    if args.output_file != None:
        output_file = args.output_file
    if args.output_in_usievert != None and args.output_in_usievert != '':
        output_in_usievert = args.output_in_usievert
    if args.output_in_cpm != None:
        output_in_cpm = args.output_in_cpm

    if args.list_tool_config == True:
        print("baudrate           = %s" % (baudrate))
        print("port               = '%s'" % (port))
        print("bin_file           = '%s'" % (bin_file))
        print("output_file        = '%s'" % (output_file))
        print("no_parse           = %s" % (no_parse))
        print("output_in_usievert = '%s'" % (output_in_usievert))
        print("output_in_cpm      = %s" % (output_in_cpm))
        sys.exit(0)


    cpm_to_usievert = None
    if output_in_cpm == False or args.output_in_usievert != None:
        conversion = output_in_usievert.split(',')
        if len(conversion) != 2:
            print("WARNING: conversion to Sieverts not valid, defaulting to CPM/CPS")
        else:
            cpm_to_usievert = (int(conversion[0]), float(conversion[1]))

    # handle all operations
    if no_parse == True and args.data != True:
        print("ERROR: the '--no-parse' option can only be used with the '--data' option.")
        sys.exit(-1)

    if args.bin_file != None:
        parseDataFile(bin_file, output_file, cpm_to_usievert=cpm_to_usievert)
        sys.exit(0)

    res = openDevice(port=port, baudrate=baudrate)
    if res != 0:
        sys.exit(-res)

    if args.data == True:
        tmp_file = None
        bin_output_file = ''
        if no_parse == True:
            if args.output_file != None:
                bin_output_file = output_file
            else:
                bin_output_file = bin_file
        else:
            tmp_file = tempfile.mktemp('.bin')
            bin_output_file = tmp_file

        getData(out_file=bin_output_file)

        if no_parse == False:
            parseDataFile(bin_output_file, output_file, cpm_to_usievert=cpm_to_usievert)

        if tmp_file != None and os.path.exists(tmp_file):
            os.remove(tmp_file)

    elif args.device_info == True:
        print getDeviceType()

    elif args.serial == True:
        print getSerialNumber()

    elif args.power_on == True:
        setPower(True)

    elif args.power_off == True:
        setPower(False)

    elif args.hearbeat0 == True:
        print 'option not yet available'
    elif args.hearbeat1 == True:
        print 'option not yet available'

    elif args.voltage == True:
        print getVoltage()

    elif args.cpm == True:
        print getCPM()

    elif args.temperature == True:
        print 'option not yet available'
    elif args.gyro == True:
        print 'option not yet available'
    elif args.list_config == True:
        print 'option not yet available'
    elif args.erase_config == True:
        print 'option not yet available'
    elif args.write_config == True:
        print 'option not yet available'
    elif args.update_config == True:
        print 'option not yet available'
    elif args.set_time == True:
        print 'option not yet available'
    elif args.set_date == True:
        print 'option not yet available'
    elif args.send_key == True:
        print 'option not yet available'
    elif args.firmware_update == True:
        print 'option not yet available'
    elif args.reset == True:
        print 'option not yet available'
    elif args.reboot == True:
        print 'option not yet available'
