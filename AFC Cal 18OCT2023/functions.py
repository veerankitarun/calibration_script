import os
import sys
import json # this is a built-in module in python
import csv # this is included in the Python installation
import datetime # this is a built in module
import time
import serial
import serial.tools.list_ports
import numpy as np
from datetime import timezone
import requests
import re

def get_config():
    # Read COM port settings from config.txt where this python file resides
    try:
        config = open(os.path.join(sys.path[0], "config.txt"), "r") #configure for each unique test setup
        test_type = config.readline().replace('\n','').split(':')[1].strip()
        sub_type =  config.readline().replace('\n','').split(':')[1].strip()
        db = config.readline().replace('\n','').split(':')[1].strip()
        air2lpg = config.readline().replace('\n','').split(':')[1].strip()
        fr1 = config.readline().replace('\n','').split(':')[1].strip()
        fr2 = config.readline().replace('\n','').split(':')[1].strip()
        psd1 = config.readline().replace('\n','').split(':')[1].strip()
        fr1_var = config.readline().replace('\n','').split(':')[1].strip()
        psd1_var = config.readline().replace('\n','').split(':')[1].strip()
        psd_range = config.readline().replace('\n','').split(':')[1].strip()

        return test_type, sub_type, db, air2lpg, fr1, fr2, psd1, fr1_var, psd1_var, psd_range
    except:
        print("Config file not found \nProgram terminated")
        exit()

def fmcd_ser_setup():
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


def get_pres_inlet():
    while True:
        try:
            input_inlet = input("Enter INLET pressure in BAR and press enter/ return to continue: ")
            if len(input_inlet) == 0:
                print("No pressure entered \nProgram terminated")
                exit()
            else:
                input_inlet = input_inlet.replace(" ", "")

            if 5 < int(input_inlet) <9:
                #add check for DB (staging and prod)
                return input_inlet
            else:
                print("Invalid inlet pressure. Please try again.")
        except Exception as e:
            print(e)
            exit()

def get_pres_outlet():
    while True:
        try:
            outlet = input("Enter OUTLET pressure in mBAR and press enter/ return to continue: ")
            if len(outlet) == 0:
                print("No pressure entered \nProgram terminated")
                exit()
            else:
                outlet = outlet.replace(" ", "")

            if 21 < int(outlet) <46:
                #add check for DB (staging and prod)
                return outlet
            else:
                print("Invalid outlet pressure. Please try again.")
        except Exception as e:
            print(e)
            exit()

def get_time():
    # Test date
    curr_date = datetime.datetime.now(timezone.utc)
    # convert current date/time into unixtime stamp to be used in filename
    timestamp = int(curr_date.timestamp())
    # Test time
    return timestamp, curr_date

def get_afc_sn(db):
    pattern = r'^EF[A-Z]\d{9}$'
    while True:
        try:
            sn = input("Enter/Scan AFC PCBA serial number and press enter/return to continue: ")
            if len(sn) == 0:
                print("No AFC PCBA serial number entered \nProgram terminated")
                exit()
            else:
                sn = sn.replace(" ", "")

            if re.match(pattern, sn):
                sn = sn + 'A'
                #add check for DB (staging and prod)
                if db == 'STAGING':
                    x = requests.get('https://fusion.staging.paygoenergy.io/api/v1/assembly-parts/'+str(sn))
                    x=x.json()
                    if x['overall_result']=='PASS':
                        return sn
                    else:
                        print("FAIL record for AFC module inline test found\nProgram Exiting!")
                        exit()
                elif db == 'PROD':
                    x = requests.get('https://fusion.paygoenergy.io/api/v1/assembly-parts/'+str(sn))
                    x=x.json()
                    if x['overall_result']=='PASS':
                        return sn
                    else:
                        print("FAIL record for AFC module inline test found\nProgram terminated")
                        exit()
                else:
                    print("No database defined \nProgram terminated")
                    exit()
            else:
                print("Invalid serial number. Please try again.")
        except Exception as e:
            print('Database error or record not found \nProgram Exiting!')
            exit()


def get_besasn():
    pattern = r'^[A-Z]{3}\d{2}[A-Z]{2}\d{5}[A-Z]{2}$'
    while True:
        try:
            mn = input("Enter/Scan Regulator serial number and press enter/return to continue: ")
            if len(mn) == 0:
                print("No regulator serial number entered \nProgram terminated")
                exit()
            else:
                mn = mn.replace(" ", "")
            if re.match(pattern, mn):
                mn = mn + 'ASLBOAFCC'
                return mn
            else:
                print("Invalid serial number. Please try again.")
        except Exception as e:
            print(e)
            exit()

def get_db(meter, db):
    try:
        if db == 'STAGING':
            x = requests.get('https://fusion.staging.paygoenergy.io/api/v1/assembly-parts/'+str(meter))
            x=x.json()
            if x['latest_event']['type']!='IQC':
                print("IQC record for "+str(meter)+" not found. Program exiting!")
                exit() 
            result = x['overall_result']
            if result == 'PASS':
                print(str(meter) +' passed IQC. Continuing test!')
                sn=meter+'TKDZ'
                return sn
            else:
                print(str(meter)+' failed IQC test. Program exiting!')
                exit() 
        elif db == 'PROD':
            x = requests.get('https://fusion.paygoenergy.io/api/v1/assembly-parts/'+str(meter))
            x=x.json()
            if x['latest_event']['type']!='IQC':
                print("IQC record for "+str(meter)+" not found. Program exiting!")
                exit() 
            result = x['overall_result']
            if result == 'PASS':
                print(str(meter) +' passed IQC. Continuing test!')
                sn=meter+'TKDZ'
                return sn
            else:
                print(str(meter)+' failed IQC test. Program exiting!')
                exit()             
        else:
            print('No database defined so terminating')
            exit()

    except Exception as e:
        print("Log for device "+meter+" not found or network error has ocurred. "+str(e))
        print("Program exiting!")
        exit() 

def post_db(summary, db):
    try:
        if db == 'STAGING':
        #Database post (staging)
            r= requests.post('https://fusion.staging.paygoenergy.io/api/v1/assembly-events', summary)
            print(r.json())
            return True
        elif db == 'PROD':
        #Database post (production)
            r= requests.post('https://fusion.paygoenergy.io/api/v1/assembly-events', summary)
            print(r.json())
            return True
        else:
            print('No database defined so posting failed')
            return False
    except Exception as e:
        print(e)
        return False
