#!/usr/bin/env python

import sys
import serial
import argparse
import struct

DEFAULT_BIN_FILE = 'gq-gmc-log.bin'

def handleArguments():
    parser = argparse.ArgumentParser(description='Control tool for the GQ GMC-500 series.')
    parser.add_argument('-y', '--device-type', action='store_true', default=None,
                       help='Get the device type and revision.')
    parser.add_argument('-b', '--baudrate', action='store', default=115200,
                       help='')
    parser.add_argument('-p', '--port', action='store', default=None,
                       help='')
    parser.add_argument('-s', '--serial', action='store_true', default=None,
                       help='Get the serial number of the device.')
    parser.add_argument('-o', '--power-on', action='store_true', default=None,
                       help='')
    parser.add_argument('-O', '--power-off', action='store_true', default=None,
                       help='')
    parser.add_argument('-h0', '--hearbeat0', action='store_true', default=None,
                       help='')
    parser.add_argument('-h1', '--hearbeat1', action='store_true', default=None,
                       help='')
    parser.add_argument('-V', '--voltage', action='store_true', default=None,
                       help='')
    parser.add_argument('-c', '--cpm', action='store_true', default=None,
                       help='Get the current CPM.')
    parser.add_argument('-t', '--temperature', action='store_true', default=None,
                       help='')
    parser.add_argument('-g', '--gyro', action='store_true', default=None,
                       help='')
    parser.add_argument('-d', '--data', action='store', default=None,
                       help='')
    parser.add_argument('-f', '--data-file', action='store', default=None,
                       help='')
    parser.add_argument('-P', '--parse', action='store_true', default=None,
                       help='')
    parser.add_argument('-l', '--list-config', action='store_true', default=None,
                       help='')
    parser.add_argument('-e', '--erase-config', action='store_true', default=None,
                       help='')
    parser.add_argument('-w', '--write-config', action='store_true', default=None,
                       help='')
    parser.add_argument('-u', '--update-config', action='store_true', default=None,
                       help='')
    parser.add_argument('-T', '--set-time', action='store', default=None,
                       help='')
    parser.add_argument('-D', '--set-date', action='store', default=None,
                       help='')
    parser.add_argument('-k', '--send-key', action='store', default=None,
                       help='')
    parser.add_argument('-F', '--firmware-update', action='store', default=None,
                       help='')
    parser.add_argument('-R', '--reset', action='store_true', default=None,
                       help='')
    parser.add_argument('-r', '--reboot', action='store_true', default=None,
                       help='')

    return parser.parse_args()

GET_CPM_CMD           = "GETCPM"
GET_CPS_CMD           = "GETCPS"
GET_CFG_CMD           = "GETCFG"
ERASE_CFG_CMD         = "ECFG"
UPDATE_CFG_CMD        = "CFGUPDATE"
TURN_ON_CPS_CMD       = "HEARTBEAT1"
TURN_OFF_CPS_CMD      = "HEARTBEAT0"
WRITE_CFG_CMD         = "WCFGAD"

SET_MONTH_CMD  = "SETDATEMM"
SET_DAY_CMD  = "SETDATEDD"
SET_YEAR_CMD  = "SETDATEYY"
SET_HOUR_CMD  = "SETTIMEHH"
SET_MINUTE_CMD  = "SETTIMEMM"
SET_SECOND_CMD  = "SETTIMESS"
KEY_CMD = "KEY"
GET_HISTORY_DATA_CMD = "SPIR"

FLASH_SIZE_GMC500 = 1048576  # 1Mbyte


m_deviceType = None

def clearPort():
    # close any pending previous command
    port.write(">>")

    # get rid off all buffered data still in the queue
    while True:
        x = port.read(1)
        if x == '':
            break

def checkDeviceType():
    m_deviceType = getDeviceType()
    if m_deviceType[:7] == 'GMC-500':
        print("device found: %s" % m_deviceType)
        
    else:
        print("device '%s' not supported" % m_deviceType)
        return -1
    
    return 0
        
def getDeviceType():
    port.write('<GETVER>>')
    deviceType = port.read(14)
    return deviceType

def getSerialNumber():
    port.write('<GETSERIAL>>')
    serialNumber = port.read(7)
    ser = ''
    for x in range(7):
        ser += "%02X" % ord(serialNumber[x])
    return ser

def setPower(on=True):
    if on:
        port.write('<' + TURN_ON_PWR_CMD + '>>')
    else:
        port.write('<' + TURN_OFF_PWR_CMD + '>>')

def getVoltage():
    port.write('<GETVOLT>>')
    voltage = port.read(3)
    return voltage

def getCPM():
    port.write('<GETCPM>>')
    cpm = port.read(2)
    value = struct.unpack(">H", cpm)[0]
    return value

def getData(address=0x000000, length=0x00100000, file=DEFAULT_BIN_FILE):
    if address == None:
        address = 0x000000
    if length == None:
        length = 0x00100000
    if file == None:
        file = DEFAULT_BIN_FILE
        
    #length = 0x00200000 # 2Mbyte
    total_len = 0
    sub_addr = address
    sub_len = 4096
    
    f = open(file, 'w')
    
    while True:
        cmd = struct.pack('>sssssBBBHss', '<', 'S', 'P', 'I', 'R', (sub_addr >> 16) & 0xff, (sub_addr >> 8) & 0xff, (sub_addr) & 0xff, sub_len, '>', '>')
        port.write(cmd)
        
        data = port.read(sub_len)        
        if data == '' or total_len >= length:
            break
        
        f.write(data)
        total_len += len(data)
        print("address: 0x%06x, size: %s, total size: %d bytes (%d%%)" % (sub_addr, sub_len, total_len, int(total_len*100/length)))
        sub_addr += sub_len
        
    f.close

def printData(data_type, c_str, size=1):
    c0 = ord(c_str[0])
    
    if size == 1:
        if c0 != 0xff:
            print('%d,%s' % (c0, data_type))
            
    elif size == 2:
        c1 = ord(c_str[1])
        if c0 != 0xff:
            print('%d,%s' % (c0 * 256 + c1, data_type))
            
    elif size == 3:
        c1 = ord(c_str[1])
        c2 = ord(c_str[2])
        if c0 != 0xff:
            print('%d,%s' % (c0 * 256 * 256 + c1 * 256 + c2, data_type))
            
    else:
        print('(unsupported size: %d)' % (size))
        
    
def parseDataFile(file=DEFAULT_BIN_FILE):
    if file == None:
        file = DEFAULT_BIN_FILE
    print("parsing file " + file)

    marker = 0
    cmd = ''
    data_type = '*'
    f = open(file, 'r')
    while True:
        c_str = f.read(1)
        if c_str == '':
            break
        c = ord(c_str)
        
        if marker == 0x55aa:
            if c == 0x00:
                cmd = 'date-time'
                date = f.read(9)
                
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
                    
                print(',,20%02d/%02d/%02d %02d:%02d:%02d,%s' % (ord(date[0]), ord(date[1]), ord(date[2]), ord(date[3]), ord(date[4]), ord(date[5]), mode_str))
            elif c == 0x01:
                data = f.read(2)
                printData(data_type, data, size=2)
                
            elif c == 0x02:
                data = f.read(3)
                printData(data_type, data, size=3)
                
            elif c == 0x03:
                cmd = '3?'
                print cmd
                
            elif c == 0x04:
                cmd = '4?'
                date = f.read(6)
                print('[4] 0x%02x 0x%02x 0x%02x 0x%02x 0x%02x 0x%02x ' % (ord(date[0]), ord(date[1]), ord(date[2]), ord(date[3]), ord(date[4]), ord(date[5])))
            else:
                cmd = '?'
                print cmd
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
        
        printData(data_type, c_str, size=1)
        
    f.close()
    
def dumpData(data):
    for d in range(len(data)):
        print "0x%02x (%s)" % (ord(data[d]), data[d])

def openDevice():
    global port
    port = serial.Serial("/dev/ttyUSB0", baudrate=115200, timeout=1.0)

    clearPort()
    checkDeviceType()

    
arg = handleArguments()

if arg.parse == True:
    parseDataFile(arg.data_file)
    sys.exit(0)
        
openDevice()

if arg.device_type == True:
    print getDeviceType()
    
if arg.serial == True:
    print getSerialNumber()
    
if arg.power_on == True:
    setPower(True)

if arg.power_off == True:
    setPower(False)

if arg.hearbeat0 == True:
    print ''
if arg.hearbeat1 == True:
    print ''
    
if arg.voltage == True:
    print getVoltage()
    
if arg.cpm == True:
    print getCPM()
    
if arg.temperature == True:
    print ''
if arg.gyro == True:
    print ''
if arg.data != None:
    getData(file=arg.data_file)
    
if arg.list_config == True:
    print ''
if arg.erase_config == True:
    print ''
if arg.write_config == True:
    print ''
if arg.update_config == True:
    print ''
if arg.set_time == True:
    print ''
if arg.set_date == True:
    print ''
if arg.send_key == True:
    print ''
if arg.firmware_update == True:
    print ''
if arg.reset == True:
    print ''
if arg.reboot == True:
    print ''
