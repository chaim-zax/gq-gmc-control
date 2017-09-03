# gq-gmc-control

Control tool  for the  GQ GMC  Geiger Counters.  This tool  provices a
convenient command line user interface  to most of the device features
(which are accessable by usb). Currently the GMC-280, GMC-300, GMC-320
and GMC-500 models are supported.


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
    parmeters  are   supported:  'cal1-cpm',   'cal1-sv',  'cal2-cpm',
    'cal2-sv', 'cal3-cpm' and 'cal3-sv', the values depend on the type
    of  argument (e.g.  '1000' for  cpm,  '6.45' for  us, '0x123'  for
    addresses). Multiple  configuration parameters can be  provided at
    once (space separated). Note: this feature  is only tested on a GQ
    GMC-500.

--set-date-and-time
    Set the local date and time.

--get-date-and-time
    Get the local date and time.

--send-key
    Emulate a keypress of the device.

--reset
    Reset the device to the default factory settings.

--reboot
    Reboot the device.


## The following aditional options are provided:

--baudrate BAUDRATE
    Set the baudrate of the serial port (default 115200).

--port PORT
    Set the serial port (default '/dev/ttyUSB0').

--no-parse
    Do not  parse the  history data  into a csv  file, only  store the
    binary data.  use only  in combination  with the  '--data' command
    option.

--config CONFIG
    Load command line options from a configuration file.

--output-in-usievert [CPM,uSievert]
    Don't log data  in CPM or CPS but in  micro Sievert/h.  Optionally
    supply  a tuple  used as  a conversion  factor.  e.g.  '1000,6.50'
    indicates 1000 CPM equals 6.50 uSievert/h.

--output-in-cpm
    Log data in CPM or CPS.

--skip-check
    Skip sanity/device  checking on  startup. The  tool will  use it's
    default   settings,   if   needed    use   in   combination   with
    '--device-type'  to  overide   these  defaults  (recommended  when
    skipping device checking).

--device-type DEVICE_TYPE
    Don't use the  autodetect feature to select the  device- type, but
    use  the   one  provided   ('CMG-280',  'CMG-300',   'CMG-320'  or
    'CMG-500').

--unit-conversion-from-device
    Use  the CPM  to Sievert  calibration  values from  the device  to
    convert data to uSieverts.

--verbose {1,2}
    In- or decrease verbosity.

--list-tool-config
    Shows the currently used command line configuration options.

--version
    Show program's version number and exit.

--help
    Show a help message describing the usage and options of the tool.


## Usage Windows

Once the device is connected using usb a virtual com port should be available.
Check the 'devices' in the control panel and look for COM & LPT ports. The
one you are looking for is called like "USB Serial (COMx)" or "USB CDC (COMx)".
Try disconnecting and reconnecting your GM GMC device and check which device
dis- and re-appears. In the examples below we assume the device was connected
to COM3.

To get the device information the following command could be used:

    C:\gq-gmc-control> C:\Python27\python gq-gmc-control.py -p COM3 -i

Which should result (in the case of the GQ GMC-500 device) in:	GMC-500Re 1.03

To get all history data in a CSV file:

    C:\gq-gmc-control> C:\Python27\python gq-gmc-control.py -p COM3 -d

Which should create a file called 'gq-gmc-log.csv'. The file can be opened in
MS Excel, Matlab or any other tool which handles comma separated data.
