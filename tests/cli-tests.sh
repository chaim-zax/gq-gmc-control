#!/bin/sh

TOOL=../gq-gmc-control.py
LOG=cli-tests.log

date > ${LOG}

verify_pass()
{
    ARGS="$@"
    echo -n "testing '${ARGS}': "

    echo "\$ ${TOOL} ${ARGS}" >> ${LOG}
    ${TOOL} ${ARGS} >> ${LOG} 2>> ${LOG}

    if [ $? -eq 0 ]; then
        echo 'OK'
    else
        echo 'FAILED'
        echo 'FAILED' >> ${LOG}
    fi
}

verify_fail()
{
    ARGS="$@"
    echo -n "testing '${ARGS}': "

    echo "\$ ${TOOL} ${ARGS}" >> ${LOG}
    ${TOOL} ${ARGS} >> ${LOG} 2>> ${LOG}

    if [ $? -eq 0 ]; then
        echo 'FAILED'
        echo 'FAILED' >> ${LOG}
    else
        echo 'OK'
    fi
}

verify_only_parse()
{
    verify_pass "--only-parse test-data.bin test-data.csv"

    echo "diff -q test-data.csv test-compare-data.csv" >> ${LOG}
    diff -q test-data.csv test-compare-data.csv >> ${LOG} 2>> ${LOG}

    if [ ! $? -eq 0 ]; then
        echo 'generated and comparison CSV files differ: FAILED'
        echo 'FAILED' >> ${LOG}
    fi
}

verify_pass_background()
{
    ARGS="$@"
    echo -n "testing '${ARGS}': "

    echo "\$ ${TOOL} ${ARGS}" >> ${LOG}
    ${TOOL} ${ARGS} >> ${LOG} 2>> ${LOG} &
    PID=$!

    if [ $? -eq 0 ]; then
        echo 'OK'
    else
        echo 'FAILED'
        echo 'FAILED' >> ${LOG}
    fi
}

verify_pass_data_with_file()
{
    TEST_CSV=$1
    ARG=$2

    rm -f ${TEST_CSV}
    verify_pass "${ARG} --data ${TEST_CSV}"

    if [ ! -s "${TEST_CSV}" ]; then
        echo 'generated CSV file missing or empty: FAILED'
        echo 'generated CSV file missing or empty: FAILED' >> ${LOG}
    fi
}

cat <<EOF
These test expect a GQ GMC-500 device to be connected (or compatible),
at the end of  the test the device will be  reset to factory settings,
other changes might  be made between testing. This  test will continue
in 20 seconds. If you do not want to continue, press CTRL-C now.

EOF

sleep 20

verify_pass "--help"

verify_fail "--cpm --output-in-usievert 1000,6.50 --output-in-cpm"
verify_fail "--cpm --unit-conversion-from-device --output-in-cpm"
verify_fail "--cpm --output-in-usievert 1000,6.50 --unit-conversion-from-device"
verify_fail "--output-in-cpm"
verify_fail "--cpm --voltage"
verify_fail "--temperature --gyro"
verify_fail "--serial --device-info"
verify_fail "--power-on --power-off"
verify_fail "--heartbeat --heartbeat-off"
verify_fail ""

verify_pass "--device-info"
verify_pass "--device-info --baudrate 115200"
verify_pass "--device-info --port /dev/ttyUSB0"
verify_pass "--device-info --config ~/.gq-gmc-control.conf"
verify_pass "--device-info --skip-check"
verify_pass "--device-info --device-type GMC-500"
verify_pass "--device-info --skip-check --device-type GMC-500"
verify_pass "--device-info --verbose 2"

verify_pass "--cpm"
verify_pass "--cpm --output-in-usievert 1000,6.50"
verify_pass "--cpm --output-in-cpm"
verify_pass "--cpm --unit-conversion-from-device"
verify_pass "--cpm --output-in-usievert --unit-conversion-from-device"

verify_pass "--serial"
verify_pass "--power-off"
sleep 5

verify_pass "--power-on"
sleep 5

verify_pass_background "--heartbeat"
sleep 5
kill -2 ${PID}
verify_pass "--cpm"  # should fail if the heartbeat is still active

verify_pass "--heartbeat-off"
verify_pass "--voltage"
verify_pass "--temperature"
verify_pass "--gyro"

verify_pass_data_with_file "gq-gmc-test.csv"
verify_pass_data_with_file "gq-gmc-test.bin" "--no-parse"

verify_only_parse

verify_pass "--list-config"
#verify_pass "--write-config"
#DATE=`date +'%g/%m/%d %H:%M:%S'`
#verify_pass "--set-date-and-time '${DATE}'"
verify_pass "--get-date-and-time"
verify_pass "--send-key S1"
verify_pass "--reboot"
sleep 5

verify_pass "--list-tool-config"
verify_pass "--version"
verify_pass "--reset"
sleep 5
