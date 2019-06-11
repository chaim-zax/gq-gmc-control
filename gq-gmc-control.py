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
import argparse
import platform
import tempfile
import datetime
import gq_gmc

VERSION = '1.1.0'

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

m_epilog = "Copyright (c) 2019, Chaim Zax <chaim.zax@gmail.com>"


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
        action='store', default=gq_gmc.DEFAULT_BAUD_RATE, type=int,
        help='set the baud-rate of the serial port (default {})'.format(gq_gmc.DEFAULT_BAUD_RATE))
    parser.add_argument('-p', '--port',
        action='store', default='',
        help="set the serial port (default '{}')".format(gq_gmc.DEFAULT_PORT))
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
             + "options".format(gq_gmc.DEFAULT_CSV_FILE, gq_gmc.DEFAULT_BIN_FILE))
    command_group.add_argument('-P', '--only-parse',
        nargs='?', type=str, dest='bin_file', const='',
        help="do not download history data, only parse the already downloaded data to a csv file (default '{}'). "
             + "can be used in combination with the '--data' option to create a csv file with a different file-name, "
             + "and the '--output-in-usievert',  '--unit-conversion-from-device' and/or '--output-in-cpm' options"
             .format(gq_gmc.DEFAULT_CSV_FILE))
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


def main():
    baud_rate = gq_gmc.DEFAULT_BAUD_RATE
    port = gq_gmc.DEFAULT_PORT
    bin_file = gq_gmc.DEFAULT_BIN_FILE
    output_file = gq_gmc.DEFAULT_CSV_FILE
    no_parse = gq_gmc.DEFAULT_NO_PARSE
    output_in_usievert = gq_gmc.DEFAULT_CPM_TO_SIEVERT
    output_in_cpm = gq_gmc.DEFAULT_OUTPUT_IN_CPM
    skip_check = gq_gmc.DEFAULT_SKIP_CHECK
    unit_conversion_from_device = gq_gmc.DEFAULT_UNIT_CONVERSION_FROM_DEVICE
    device_type = gq_gmc.DEFAULT_DEVICE_TYPE
    verbose = gq_gmc.DEFAULT_VERBOSE_LEVEL

    # handle all command line options
    args = handle_arguments()

    # load configuration file(s)
    home = os.path.expanduser("~")
    default_config = gq_gmc.DEFAULT_CONFIG.replace('~', home)
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

    gq_gmc.set_verbose_level(verbose)

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
            res = gq_gmc.open_device(port=port, baud_rate=baud_rate, skip_check=skip_check,
                              device_type=device_type, allow_fail=True)
            if res != 0:
                print('WARNING: no connection to device, defaulting to known unit '
                      + 'conversion ({:d} CPM = {:.2f} uSv/h)'
                        .format(cpm_to_usievert[0], cpm_to_usievert[1]))
            else:
                cpm_to_usievert = gq_gmc.get_unit_conversion_from_device()

        gq_gmc.parse_data_file(bin_file, output_file, cpm_to_usievert=cpm_to_usievert)
        sys.exit(0)

    if args.device_info:
        skip_check = True

    # all commands below require a connected device
    res = gq_gmc.open_device(port=port, baud_rate=baud_rate, skip_check=skip_check,
                      device_type=device_type)
    if res != 0:
        sys.exit(-res)

    # determine CPM to uSievert conversion factor by using the calibration
    # values from the device
    if unit_conversion_from_device:
        cpm_to_usievert = gq_gmc.get_unit_conversion_from_device()

    # parse all history data, and get it from the device if needed
    if args.data:
        tmp_file = None
        if no_parse:
            if args.output_file is not None:
                bin_output_file = output_file
            else:
                bin_output_file = bin_file
        else:
            tmp_file = tempfile.mktemp('.bin')
            bin_output_file = tmp_file

        gq_gmc.get_data(out_file=bin_output_file)

        if not no_parse:
            gq_gmc.parse_data_file(bin_output_file, output_file,
                            cpm_to_usievert=cpm_to_usievert)

        if tmp_file is not None and os.path.exists(tmp_file):
            os.remove(tmp_file)

    # handle the rest of the commands

    elif args.device_info:
        print(gq_gmc.get_device_type())

    elif args.serial:
        print(gq_gmc.get_serial_number())

    elif args.power_on:
        gq_gmc.set_power(True)

    elif args.power_off:
        gq_gmc.set_power(False)

    elif args.heartbeat:
        gq_gmc.set_heartbeat(True, cpm_to_usievert=cpm_to_usievert)

    elif args.heartbeat_off:
        gq_gmc.set_heartbeat(False)

    elif args.voltage:
        print(gq_gmc.get_voltage())

    elif args.cpm:
        print(gq_gmc.get_cpm(cpm_to_usievert=cpm_to_usievert))

    elif args.temperature:
        print(gq_gmc.get_temperature())

    elif args.gyro:
        print(gq_gmc.get_gyro())

    elif args.list_config:
        gq_gmc.list_config()

    elif args.write_config is not None:
        gq_gmc.write_config(args.write_config)

    elif args.get_date_and_time:
        print(gq_gmc.get_date_and_time())

    elif args.set_date_and_time is not None:
        gq_gmc.set_date_and_time(args.set_date_and_time)

    elif args.send_key is not None:
        gq_gmc.send_key(args.send_key)

    elif args.firmware_update is not None:
        gq_gmc.firmware_update()

    elif args.reset:
        gq_gmc.factory_reset()

    elif args.reboot:
        gq_gmc.reboot()


main()
