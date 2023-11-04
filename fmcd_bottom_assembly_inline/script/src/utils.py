import os
import sys
import json # this is a built-in module in python
import datetime # this is a built in module
import time
# import numpy as np
from datetime import timezone
import requests
import serial
import serial.tools.list_ports
import ast

# Variable Declaration
staging= ''
prod= '' 
ser_frmt = ''
valve_ctrl = ''
bcolors = ''
pot_config = ''
head = "\033["

def get_config():
    '''
     Read COM port settings from config.txt where this python file resides
    '''
    try:
        config = open(os.path.join(sys.path[0], "config.txt"), "r") #configure for each unique test setup
        test_type = config.readline().replace('\n','').split(':')[1].strip()
        sub_type =  config.readline().replace('\n','').split(':')[1].strip()
        db = config.readline().replace('\n','').split(':')[1].strip()
        fr1 = config.readline().replace('\n','').split(':')[1].strip()
        fr2 = config.readline().replace('\n','').split(':')[1].strip()
        ltest = config.readline().replace('\n','').split(':')[1].strip()
        eftest = config.readline().replace('\n','').split(':')[1].strip()
        afc_pot = config.readline().replace('\n','').split(':')[1].strip()
        ser_val = config.readline().replace('\n','').split(':')[1].strip()
        pthresh = config.readline().replace('\n','').split(':')[1].strip()
        cmvalve = int(config.readline().replace('\n','').split(':')[1].strip())
        config.close()
        if (fr1==0 and fr2==0):
            print('Expected flow rate for the AFC functional test not defined \nProgram terminated"')
            exit()
        if (cmvalve != 3 and cmvalve != 4):
            print('Expected common valve selected to be either 3 or 4.\nProgram Terminated!')
            exit()
        else:
            return test_type, sub_type, db, fr1, fr2, ltest, eftest, afc_pot, ser_val, pthresh, cmvalve
    except:
        print("Config file not found or config file missing critical information \nProgram terminated")
        exit()

def fmcd_ser_setup():
    '''
        Connect to the V4 board
    '''
    uart_type='USB'
    try:
        #input("Insert UART cable and press enter/return to continue...")
        time.sleep(0.2)
        if uart_type == 'USB':
            device_name = "VID:PID=1915:520F" #Should be static for nRF52840 devices
            ports = serial.tools.list_ports.comports()
            for port in ports:
                if port.hwid.find(device_name) != -1:
                    srport = port.name
                    break
            flowcontrol = True
        else:
            flowcontrol = False
        ser = serial.Serial(
            port=srport, # replace with the name of your serial port
            baudrate=115200,
            timeout=1,
            rtscts= flowcontrol
        )
        return ser
    except:
        print("V4 PCBA Serial port error. Please confirm correct connection and COM port. \nProgram terminated")
        exit()

def arduino_ser_setup():
    '''
    Connect to the arduino board
    '''
    try:
        #input("Insert UART cable and press enter/return to continue...")
        time.sleep(1)
        
        device_name = "VID:PID=2341:0042" #Should be static for Arduino devices
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.hwid.find(device_name) != -1:
                srport = port.name
                break
            
        ser = serial.Serial(
            port=srport, # replace with the name of your serial port
            baudrate=9600,
            timeout=1
        )
        return ser
    except Exception as e:
        print("ARDUINO Serial port error. Please confirm correct connection and COM port. \nProgram terminated")
        exit()

def get_time():
    '''
    Get the test date
    '''
    curr_date = datetime.datetime.now(timezone.utc)
    # convert current date/time into unixtime stamp to be used in filename
    timestamp = int(curr_date.timestamp())
    # Test time
    return timestamp, curr_date

def create_directory():
    '''
    Creates directories to save test results
    '''
    # Create test-results folder
    try:
        os.mkdir('BASE_SEF_Results')
        time.sleep(0.1)
    except Exception as e:
        # print(e)
        pass

def get_var():
    '''
    Gets variables to use
    '''
    try:
        global staging, prod # URLs to use
        global ser_frmt # Serial number validation values
        global valve_ctrl # Valve control commands
        global pot_config # AFC potting configurations
        global bcolors,head
  
        with open(os.path.join(sys.path[0], "setup.json"), 'r') as f:
            var = json.load(f)
        staging= var['staging']
        prod = var['production']
        ser_frmt = var['ser_frmt']
        valve_ctrl = var['valve_ctrl']
        pot_config = var['pott_config']
        bcolors = var['bcolors']
        for key in bcolors.keys():
            bcolors[key] = head + bcolors[key]

    except Exception as e:
        print(e)
        print("setup.json file missing/corrupted\nProgram terminated")
        exit()

def validate_ser_no(reg_ser, lock_ser, valve_ser, afc_ser):
    '''
    Validates that the regulator and afc serial numbers are:
        - the correct format
        - afc passed afc leak test
    '''
    try:
        # Inform tester what is going on:
        print("Validating Serial Numbers...")
        # Check that the correct format is used for both 
        isRegSerValid = (reg_ser.startswith(ser_frmt["reg_pref"]) and len(reg_ser) == len(ser_frmt["reg_pref"]+ser_frmt["reg_suff"]))
        isLockSerValid = (lock_ser.startswith(ser_frmt["lock_pref"]) and len(lock_ser) == len(ser_frmt["lock_pref"]+ser_frmt["lock_suff"]))
        isValveSerValid = (valve_ser.startswith(ser_frmt["valve_pref"]) and len(valve_ser) == len(ser_frmt["valve_pref"]+ser_frmt["valve_suff"]))        
        isAfcSerValid = (afc_ser.startswith(ser_frmt["afc_pref"]) and len(afc_ser) == len(ser_frmt["afc_pref"]+ser_frmt["afc_suff"]))
        if not isRegSerValid or not isAfcSerValid or not isValveSerValid or not isLockSerValid:
            if not isRegSerValid :
                print(bcolors['FAIL'] + "Incorrect format for REGULATOR Serial Number!"+bcolors['ENDC'])
            if not isAfcSerValid :
                print(bcolors['FAIL'] + "Incorrect format for AFC Serial Number!"+bcolors['ENDC'])
            if not isLockSerValid :
                print(bcolors['FAIL'] + "Incorrect format for LOCK Serial Number!"+bcolors['ENDC'])
            if not isValveSerValid :
                print(bcolors['FAIL'] + "Incorrect format for VALVE Serial Number!"+bcolors['ENDC'])
            print(bcolors['FAIL']+"Program Terminated!"+bcolors['ENDC'])
            exit()
        # Check that the AFC, LOCK, VALVE passed the previous tests
        ## Append 'A' to get AFC Leak test result
        afc_ser_leak = afc_ser + 'A'
        ## Append 'ASLB' to get Lock inline results
        reg_ser_l = reg_ser + 'ASLBO'
        ## Save the serial numbers in a list
        serial_list = [afc_ser_leak, reg_ser_l]
        failedParts = []
        ## Fetch the results
        for ser in serial_list:
            ## Define url to use
            url = prod['get'] + ser
            ## Fetch AFC Leak test results
            # print(url)
            res = requests.get(url)
            ## Confirm that data was fetched successfully
            if res.status_code != 200:
                print(f'Failed to fetch {ser} Leak Test Results. Status Code: {res.status_code}.\nProgram Terminated!')
                exit()
            ## Extract data from json file
            data = res.json()
            ## Get the overall result
            # print(data)
            result = data['overall_result']
            ## Check if leak test result was PASS or FAIL
            if (result != 'PASS'):
                failedParts.append(ser)
                print(bcolors['FAIL']+f'{ser} FAILED Previous IQC/INLINE Test.'+bcolors['ENDC'])
            else:
                print(bcolors['OKBLUE']+ser+' PASSED Previous IQC/INLINE Test.'+bcolors['ENDC'])
            ## Check if the lock and valve serials provided are correct()
            if ser == reg_ser_l:
                if lock_ser != data['latest_event']['lock_serial'] or valve_ser != data['latest_event']['valve_serial']:
                    print(bcolors['FAIL']+"Expected LOCK Serial: "+data['latest_event']['lock_serial'] +", Provided LOCK Serial: "+ lock_ser+bcolors['ENDC'])
                    print(bcolors['FAIL']+"Expected VALVE Serial: "+data['latest_event']['valve_serial']+", Provided VALVE Serial: "+ valve_ser+bcolors['ENDC'])
                    print(bcolors['FAIL']+"Program Terminated!"+bcolors['ENDC'])
                    exit()

        if len(failedParts) > 0:
            print(bcolors['FAIL']+"Program Terminated!"+bcolors['ENDC'])  
            exit()

        # If all validations PASS:
        print(bcolors['OKGREEN'] + "All Validations PASSED." + bcolors['ENDC'])


    except Exception as e:
        print(e)
        print(bcolors['FAIL']+'Error encountered validating serial numbers.\nProgram Terminated!'+bcolors['ENDC'])
        exit()


def send_cmd(ser, cmd):
    '''
    sends commands to the arduino/v4 board
    '''
    try:
        cmd = cmd +'\r\n'
        if ser.in_waiting == 0:
            ser.write(cmd.encode('utf-8'))
        time.sleep(0.5)
        res = ser.read(1024) # read unicode strings are not supported, please encode to bytes: 'AT+RBT'up to 1024 bytes
        return res
    except Exception as e:
        print(f'Error sending {cmd} command to arduino/v4 board')
        ser.close()
        return 'ERR'

def switch_to_test_mode(fmcd_ser):
    '''
    Switches the SR Board to Test Mode
    '''
    try:
        cmd = "AT+CMOD=0" # Command used to set v4 board to test mode
        # Send command to board
        res = send_cmd(fmcd_ser, cmd)
        # check if command was sent successfully
        res = res.split()
        if res==[]:
            # print('Test mode switch failed.\nProgram Terminated!')
            fmcd_ser.close()
            exit()
        # print('Test mode switch successful')    
        fmcd_ser.flushOutput()        

    except:
        print("Error encountered while switching V4 board to test mode.\nProgram Terminated!")
        exit()

def get_afc_pot():
    '''
    Gets the type of potting configuration applied to the 
    '''
    # mydict = ast.literal_eval(pot_config)
    print(bcolors['OKBLUE']+"AFC Potting Config..."+bcolors['ENDC'])
    potting_configs = """
    ------------------------------------
     Type      : Potting Configuration
    ------------------------------------
     1         : FULLY_POTTED\n
     2         : MOLDED_POTTED\n
     3         : DRIP_POTTED\n
     4         : NO_POT\n
    ------------------------------------
    """
    try:
        print(potting_configs)
        while True:
            opt = [int(x) for x in pot_config.keys()]
            pot_opt = input("Select type "+str(opt)+" of potting applied: ")
            if pot_opt in pot_config.keys():
                return pot_config[pot_opt]
            else:
                print(bcolors['WARNING']+"Wrong Input!"+bcolors['ENDC'])
    except Exception as e:
        print(e)
        print(bcolors["FAIL"]+"Error getting Potting Config Applied.\nProgram Terminated!"+bcolors["ENDC"])
        exit()


def get_flow_meas(fmcd_ser):
    '''
    Gets the flow rate value from the v4 board
    '''
    # Send command
    # cmd = "AT+TPSDF=1,0,1000,50,2800"
    # res = send_cmd(fmcd_ser, cmd)
    i = 0
    tries = 3
    # Attempt at most three times to get the flow rate
    while i< tries:
        # Send command
        cmd = "AT+TPSDF=1,0,1000,50,2800"
        res = send_cmd(fmcd_ser, cmd)
        # Checks that the response is not empty
        if res != b'':
            # Response is: b'\r\nOK\r\n\r\n+TPSDF:1,179,2796.875,1.938723E-10,-94.11,0.000000\r\n'
            res = res.split()
            # Response is: [b'OK', b'+TPSDF:1,179,2796.875,1.938723E-10,-94.11,0.000000']
            # print(res)
            # Isolate the TPSDF response
            _tpsdf = str(res[0].decode('utf-8') )
            # Split string to array
            print(_tpsdf)
            _tpsdf = _tpsdf.split(',')
            # print(_tpsdf)
            # Get the flow rate value. It is the last value of the array
            _flowrate = float(_tpsdf[-1])

            # Disable polling of flow sesnor
            cmd = "AT+TPSDF=0"
            res = send_cmd(fmcd_ser, cmd)

            return _flowrate
        else:
            i = i + 1
            time.sleep(1)
    return ''

def run_soundness_test(fmcd_ser, ard_ser, pthresh):
    '''
    Test the system soundness(checks for leaks in the base enclosure)
    '''
    try:
        # Declare local variables
        soundnessTestResult = ''
        firstPressReading = '' 
        secondPressureReading = ''

        print(bcolors['OKBLUE'] + 'Soundness Test in progress...' + bcolors['ENDC'])
        # Prompt user to close the ball valve:
        input(bcolors['WARNING']+"MAKE SURE THAT THE BALL VALVE IS CLOSED BEFORE PROCEEDING WITH THE TEST!\nPress Enter/Return"+bcolors['ENDC'])
        # Prompt the tester to turn regulator to 9 o'clock position
        input("Turn gas regulator to 9 O'CLOCK position and press enter/return to continue.")

        # TO ADD: Open devkit valve()

        # Close all valves
        res = send_cmd(ard_ser, valve_ctrl['AV_CLOSE'])
        # print(res)

        # Open valve 8. This supplies air to the DUT through the outlet connection, creating a back pressure
        print("Solenoid Valve 8: OPEN.\n5 Second delay...")
        res = send_cmd(ard_ser, valve_ctrl['SV_OPEN'])
        # print(res)

        # Wait for 5 seconds
        time.sleep(5)

        # Close valve 8
        print("Solenoid Valve 8: CLOSED")
        res = send_cmd(ard_ser, valve_ctrl['SV_CLOSE'])
        # print(res)

        # Get first pressure reading from tester
        firstPressReading = input("Enter Initial Pressure Reading and press enter/return to continue: ")

        # Check if initial pressure is greater than 150mbar
        if float(firstPressReading) < float(pthresh):
            print(bcolors['FAIL'] + "Pressure is below "+pthresh + " mbar.\nTest ABORTED!"+bcolors['ENDC'])
            soundnessTestResult = "FAIL"
            return soundnessTestResult, firstPressReading, secondPressureReading

        # Wait for 30 seconds
        delay = 30
        print(f"{delay} second delay...")
        time.sleep(delay)

        # Get second pressure reading from tester
        secondPressureReading = input("Enter Final Pressure Reading and press enter/return to continue: ")

        # Check if leak test has passed
        if secondPressureReading >=firstPressReading:
            soundnessTestResult = "PASS"
            print(bcolors['OKGREEN'] + "Soundness Test: PASSED" + bcolors['ENDC'])
        else:
            soundnessTestResult = "FAIL"
            print(bcolors['FAIL'] + "Soundness Test: FAILED." + bcolors['ENDC'])

        return soundnessTestResult, firstPressReading, secondPressureReading

    except:
        print("Error encountered while running Soundness Test.\nProgram Terminated!")
        exit()

def run_pressure_release(ard_ser):
    '''
    Releases pressure from the system
    '''
    try:
        # Close all valves
        res = send_cmd(ard_ser, valve_ctrl['AV_CLOSE'])

        # Open flow rate valve 2(8.3LPM) to release the pressure
        print("Solenoid Valve 4(8.0LPM): OPEN")
        res = send_cmd(ard_ser, valve_ctrl['FRV2_OPEN'])

        # Wait for 5 seconds
        time.sleep(5)

        # Close flow rate valve 2(8.3LPM)
        print("Solenoid Valve 4(8.0LPM): CLOSED")
        res = send_cmd(ard_ser, valve_ctrl['FRV2_CLOSE'])

        # Inform the tester
        print("Pressure Released!")

    except Exception as e:
        print(e)
        print(bcolors['FAIL']+"Error while releasing pressure from the system"+bcolors['ENDC'])
        exit()

def check_valve_selected(cmvalve):
    '''
    Returns the key of the valve selected as common for the excess flow shut off
    '''
    if cmvalve == 3:
        return 'FRV1_CLOSE', 'FRV1_OPEN'
    elif cmvalve == 4:
        return 'FRV2_CLOSE', 'FRV2_OPEN'
    else:
        print(bcolors['FAIL']+'Check valve selected as common in config file(should be 3/4).\nProgram Terminated!'+bcolors['ENDC'])
        exit()

def run_excessflow_test(fmcd_ser, ard_ser, fr1, fr2, leak_test, soundnessTestResult, cmvalve):
    '''
    Runs the excess flow test(The excess flow shut off ball valve should be engaged at 19.333lpm)
    '''
    try:
        # Declare Variables
        excessFlowrateTest_th1 = ''
        flowrate_th1 = ''
        excessFlowrateTest_th2 = ''
        flowrate_th2 = ''
        cmvalve2 = 7
        cmvalve2_open = valve_ctrl['V7_OPEN']
        cmvalve2_close = valve_ctrl['V7_CLOSE']

        if soundnessTestResult != "PASS":
            print(bcolors['WARNING']+"Excess Flow test ABORTED because Soundness Test FAILED"+ bcolors['ENDC'])
            return excessFlowrateTest_th1, flowrate_th1, excessFlowrateTest_th2, flowrate_th2

        print(bcolors['OKBLUE'] + "Excess flow test in progress..." + bcolors['ENDC'])

        # Prompt the tester to open the BALL VALVE
        input(bcolors['WARNING']+"MAKE SURE THAT THE BALL VALVE IS "+bcolors['BOLD']+ "OPENED" +bcolors['ENDC'] + bcolors['WARNING']+ " BEFORE PROCEEDING WITH THE TEST!\nPress Enter/Return"+bcolors['ENDC'])

        # Close all valves
        res = send_cmd(ard_ser, valve_ctrl['AV_CLOSE'])
        # print(res)

        # Open valve 9. This allows for flow of air to the DIT through the regulator (REMOVED)
        # res = send_cmd(ard_ser, valve_ctrl['EFV_OPEN'])
        # print(res)

        # Get commands to use to control the common valve(this is the valve that will be opened together
        # with the excess flow shut off test valves so as to prevent etriggering of the shut off ball valve
        # because of the intantaneous change in flow)
        CLOSE, OPEN = check_valve_selected(cmvalve)

        # Release pressure from the system
        print("Releasing pressure from the system...")
        run_pressure_release(ard_ser)

        # Prompt user to turn the regulator to the 12 O'clock position
        input("Turn regulator to 12 O'CLOCK position and press enter/return to continue.")

        # Open DUT Valve
        res = send_cmd(fmcd_ser, "AT+TVALVE=1")

        # Open valve set to 8.0LPM
        ## This will prevent the shut off ball valve from being engaged due to the instantaneous increase of the flow rate from 0 to 17.33LPM
        print("Solenoid Valve " + str(cmvalve) + ": OPEN")
        res = send_cmd(ard_ser, valve_ctrl[OPEN])

        for i in range(0,5):
            flow_rate = get_flow_meas(fmcd_ser)
        
        time.sleep(1)

        print("Solenoid Valve " + str(cmvalve2) + ": OPEN")
        res = send_cmd(ard_ser, cmvalve2_open)

        for i in range(0,5):
            flow_rate = get_flow_meas(fmcd_ser)

        time.sleep(1)

        # Open valve set to 17.33LPM
        print("Solenoid Valve 1(17.33LPM): OPEN")
        res = send_cmd(ard_ser, valve_ctrl['EFV1_OPEN'])
        # print(res)

        # Read flow sensor. Take 5 measurements to get an average
        print("Flow sensor polling...")
        flowrate = []
        for i in range(0,5):
            flow_rate = get_flow_meas(fmcd_ser)
            if flow_rate != '':
                flowrate.append(flow_rate)
            else:
                # Close alll valves
                res = send_cmd(ard_ser, valve_ctrl['AV_CLOSE'])
                print(bcolors['FAIL']+"Failed to get the flow sensor readings. Rerun the test.\nProgram Terminated!"+bcolors['ENDC'])
                exit()

        flowrate_th1 = sum(flowrate)/len(flowrate)
        print(f"Flow rate at 17.33LPM setting: {flowrate_th1}")

        # Check if the flow rate is >=17.33LPM. It should be because the excess flow shut off ball valve should not
        # be engaged at this flow rate, otherwise the 
        if flowrate_th1 < float(fr1):
            # Close all valves
            res=send_cmd(ard_ser, valve_ctrl['AV_CLOSE'])
            excessFlowrateTest_th1 = "FAIL"
            print(bcolors['FAIL']+"Excess Flow Test at 17.33LPM FAILED.\nTest ABORTED!"+bcolors['ENDC'])
            return excessFlowrateTest_th1, flowrate_th1, excessFlowrateTest_th2, flowrate_th1
        else:
            print(bcolors['OKGREEN']+"Excess Flow Test at 17.33LPM PASSED.!"+bcolors['ENDC'])
            excessFlowrateTest_th1 = "PASS"

        # Close valve set to 17.33LPM
        print("Solenoid Valve 1(17.33LPM): CLOSE")
        res = send_cmd(ard_ser, valve_ctrl['EFV1_CLOSE'])
    
        # Close valve set at 8.0
        print("Solenoid Valve " + str(cmvalve) + ": CLOSE")
        res = send_cmd(ard_ser, valve_ctrl[CLOSE])

        print("Solenoid Valve " + str(cmvalve2) + ": CLOSE")
        res = send_cmd(ard_ser, cmvalve2_close)

        time.sleep(2)

        # Open valve set to 8.0LPM
        ## This will prevent the shut off ball valve from being engaged due to the instantaneous increase of the flow rate from 0 to 17.33LPM
        print("Solenoid Valve " + str(cmvalve) + ": OPEN")
        res = send_cmd(ard_ser, valve_ctrl[OPEN])
        
        time.sleep(1.5)

        print("Solenoid Valve " + str(cmvalve2) + ": OPEN")
        res = send_cmd(ard_ser, cmvalve2_open)
        
        time.sleep(1.5)

        # Open valve set to 19.33LPM
        print("Solenoid Valve 2(19.33LPM): OPEN")
        res = send_cmd(ard_ser, valve_ctrl['EFV2_OPEN'])

        # Read flow sensor. Take 5 measurements to get an average
        print("Flow sensor polling...")
        flowrate = []
        for i in range(0,5):
            flow_rate = get_flow_meas(fmcd_ser)
            if flow_rate != '':
                flowrate.append(flow_rate)
            else:
                # Close alll valves
                res = send_cmd(ard_ser, valve_ctrl['AV_CLOSE'])
                print(bcolors['FAIL']+"Failed to get the flow sensor readings. Rerun the test.\nProgram Terminated!"+bcolors['ENDC'])
                exit()
        flowrate_th2 = sum(flowrate)/len(flowrate)
        print(f"Flow rate at 19.33LPM setting: {flowrate_th2}")

        # Check if flow rate is < 1.0LPM. At 19.33LPM, the shutoff ball valve should be engaged, otherwise the test fails
        if flowrate_th2 < float(fr2):
            print(bcolors['OKGREEN']+"Excess Flow Test PASSED"+bcolors['ENDC'])
            excessFlowrateTest_th2 = "PASS"
        else:
            print(bcolors['FAIL']+"Excess Flow Test FAILED"+bcolors['ENDC'])
            excessFlowrateTest_th2 = "FAIL"

        # Close valve set at 19.33
        print("Solenoid Valve 2(19.33LPM): CLOSE")
        res = send_cmd(ard_ser, valve_ctrl['EFV2_CLOSE'])

        # Close valve set at 8.0
        print("Solenoid Valve " + str(cmvalve) + ": CLOSE")
        res = send_cmd(ard_ser, valve_ctrl[CLOSE])

        print("Solenoid Valve " + str(cmvalve2) + ": CLOSE")
        res = send_cmd(ard_ser, cmvalve2_close)

        # Release pressure from the system
        print("Releasing pressure from the system...")
        run_pressure_release(ard_ser)

        return excessFlowrateTest_th1, flowrate_th1, excessFlowrateTest_th2, flowrate_th2


    except Exception as e:
        print(e)
        print("Error encountered while running excess flow test.\nProgram Terminated!")
        exit()

def post_db(summary, db):
    try:
        text = 'Event for part ' + summary['serial_number'] + ' created.'
        if db == 'STAGING':
        #Database post (staging)
            r= requests.post(staging['post'], summary)
            # print(r.json())
            if r.json()['message'] == text:
                print(bcolors["OKGREEN"]+"Posting to STAGING DB PASS"+bcolors["ENDC"])
            return True
        elif db == 'PROD':
        #Database post (production)
            r= requests.post(prod['post'], summary)
            # print(r.json())
            if r.json()['message'] == text:
                print(bcolors["OKGREEN"]+"Posting to PRODUCTION DB PASS"+bcolors["ENDC"])
            return True
        else:
            print(bcolors["FAIL"]+"No database defined so posting failed"+bcolors["ENDC"])
            return False
    except Exception as e:
        print(e)
        return False
