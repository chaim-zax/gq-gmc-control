# gq-gmc-control

Control tool  for the GQ GMC  Geiger Counters.  This tool  provides a convenient
cross platform (Linux,  Windows & OS X)  command line user interface  to most of
the  device features  (which are  accessible  by USB).   Currently the  GMC-280,
GMC-300, GMC-320 and GMC-500 models are supported.

The    implementation     of    the     tool    is    based     on    GQ-RFC1201
(http://www.gqelectronicsllc.com/download/GQ-RFC1201.txt), and testing done on a
GQ GMC-500. It possible some incompatibilities exists with other GQ GMC devices.
Any help to test  and debug these devices is welcome, and  will only improve the
quality of this tool.


## The following (device) commands are supported:

--device-info
    Get the device type and revision.

--serial
    Get the serial number of the device.

--power-on
    Powers on the device.

--power-off
    Powers off the device.

--heartbeat
    Prints  every second  the CPS  (or  uSv/h) value  until CTRL-C  is
    pressed.

--voltage
    Get the current voltage of the battery (or power supply).

--cpm
    Get the  current CPM (or uSv/h).  can be used in  combination with
    the '--output-in-usievert', '--unit-conversion-from-device' and/or
    '--output-in-cpm' options.

--temperature
    Get the current temperature.

--gyro
    Get the current gyroscopic data.

--data
    Download all  history data and  store it to  file. Can be  used in
    combination   with   the   '--no-parse',   '--output-in-usievert',
    '--unit-conversion-from-device' and/or '--output-in-cpm' options.

--only-parse
    Do not  download history data,  only parse the  already downloaded
    data to a  csv file. can be used in  combination with the '--data'
    option to  create a csv file  with a different file-name,  and the
    '--output-in-usievert',   '--unit-conversion-from-device'   and/or
    '--output-in-cpm' options.

--list-config
    Shows the current device configuration.

--write-config
    Write  a specific  device configuration  parameter. The  following
    parameters  are  supported:   'cal1-cpm',  'cal1-sv',  'cal2-cpm',
    'cal2-sv', 'cal3-cpm' and 'cal3-sv', the values depend on the type
    of  argument (e.g.   '1000' for  cpm, '6.45'  for us,  '0x123' for
    addresses). Multiple  configuration parameters can be  provided at
    once (space separated). Note: this feature  is only tested on a GQ
    GMC-500.

--set-date-and-time
    Set the local date and time.

--get-date-and-time
    Get the local date and time.

--send-key
    Emulate a key-press of the device.

--reset
    Reset the device to the default factory settings.

--reboot
    Reboot the device.


## The following additional options are provided:

--baud-rate
    Set the baud-rate of the serial port (default 115200).

--port
    Set the serial port (default '/dev/ttyUSB0').

--no-parse
    Do not  parse the  history data  into a csv  file, only  store the
    binary data.  use only  in combination  with the  '--data' command
    option.

--config
    Load command line options from a configuration file.

--output-in-usievert
    Don't log data  in CPM or CPS but in  micro Sievert/h.  Optionally
    supply  a tuple  used as  a conversion  factor.  e.g.  '1000,6.50'
    indicates 1000 CPM equals 6.50 uSievert/h.

--output-in-cpm
    Log data in CPM or CPS.

--skip-check
    Skip sanity/device  checking on start  up. The tool will  use it's
    default   settings,   if   needed    use   in   combination   with
    '--device-type'  to  override  these  defaults  (recommended  when
    skipping device checking).

--device-type
    Don't use the auto detect feature  to select the device- type, but
    use  the   one  provided   ('CMG-280',  'CMG-300',   'CMG-320'  or
    'CMG-500').

--unit-conversion-from-device
    Use  the CPM  to Sievert  calibration  values from  the device  to
    convert data to uSieverts.

--verbose
    In- or decrease verbosity.

--list-tool-config
    Shows the currently used command line configuration options.

--version
    Show program's version number and exit.

--help
    Show a help message describing the usage and options of the tool.


## Usage Linux

To get the device information the following command could be used:

    ~/gq-gmc-control$ ./gq-gmc-control.py -i

Which should result (in the case of the GQ GMC-500 device) in:	GMC-500Re 1.03

To get all history data in a CSV file:

    ~/gq-gmc-control$ ./gq-gmc-control.py -d

Which should  create a file called  'gq-gmc-log.csv'. The file can  be opened in
LibreOffice  Calc, MS  Excel,  Matlab  or any  other  tool  which handles  comma
separated data.

Normally  no additional  option are  required to  run this  tool in  Linux. When
multiple USB devices are connected the tool  might not find the (correct) GQ GMC
device.   In  this  case  look  for  an tty  USB  device  by  disconnecting  and
reconnecting your  GM GMC device  while checking which  tty USB device  dis- and
re-appears:

    $ ls /dev/ttyUSB*

Provide the correct device using the '-p' option:

    ~/gq-gmc-control$ ./gq-gmc-control.py -p /dev/ttyUSB0 -i

When you get  access denied errors running this tool,  please refer to
the INSTALL  file and correct  group permissions. If  problems persist
there is always the option  to prepend the gq-gmc-control command with
the 'sudo' command (not advisable).


## Usage Windows

Once the device is  connected using USB a virtual com  port should be available.
Check the 'devices' in the control panel and  look for COM & LPT ports.  The one
you are looking for is called like "USB Serial (COMx)" or "USB CDC (COMx)".  Try
disconnecting and  reconnecting your GM  GMC device while checking  which device
dis- and re-appears. In the examples below we assume the device was connected to
COM3.

To get the device information the following command could be used:

    C:\gq-gmc-control> C:\Python27\python gq-gmc-control.py -p COM3 -i

Which should result (in the case of the GQ GMC-500 device) in:	GMC-500Re 1.03

To get all history data in a CSV file:

    C:\gq-gmc-control> C:\Python27\python gq-gmc-control.py -p COM3 -d

Which should create a file called 'gq-gmc-log.csv'. The file can be opened in MS
Excel, Matlab or any other tool which handles comma separated data.
