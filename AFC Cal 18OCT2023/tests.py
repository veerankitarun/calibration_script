import serial
import time
import numpy as np
import platform
import logging
import asyncio
from bleak import BleakScanner
from bleak import BleakClient
from bleak import _logger as logger
from bleak.uuids import uuid16_dict
import functions as f
import re

def ati(ser):
    try:
        time.sleep(0.5)
        cmd = "ATI"
        cmd = cmd +'\r\n'
        time.sleep(0.5)
        if ser.in_waiting == 0:
            ser.write(cmd.encode('utf-8'))
            time.sleep(0.5)
        temp = ser.read(1024) # read unicode strings are not supported, please encode to bytes: 'AT+RBT'up to 1024 bytes
        temp = temp.split()
        if temp==[]:
            print('AT PROTOCOL FAIL CHECK CONNECTIONS')
            ser.close()
            exit()
        else:
            print('AT PROTOCOL PASS')
            fv = temp[5]
            ser.flushOutput()
            return fv
    except Exception as e:
        print('Failed to connect to device\nProgram Exiting!')
        ser.close()
        exit()

def testmode(ser):
    # Test: Switch to test mode
    try:
        cmd = "AT+CMOD=0"
        cmd = cmd +'\r\n'
        if ser.in_waiting == 0:
            ser.write(cmd.encode('utf-8'))
        time.sleep(1.5)
        temp = ser.read(1024) # read unicode strings are not supported, please encode to bytes: 'AT+RBT'up to 1024 bytes
        temp = temp.split()
        if temp==[]:
            print('Test mode switch failed\nProgram Exiting!')
            ser.close()
            exit()
        ser.flushOutput()
    except Exception as e:
        print('Test mode switch failed')
        ser.close()
        exit()
    
def afc_calibration(ser_ard, ser_fmcd, fr1, psd1, fr_var, psd_var, air_to_lpg):
    try:
    #Check for number of flow rates
        #AFC being tested at single flow rate
        input('Please set regulator to gas OFF position and press Enter/Return! ')
        print('Single flow rate calibration!')
        #Initialize PSD result dictionary
        psd_res = {}
        """ #Force vale to close to set starting condition
        print('Initializing valve position to closed!')
        cmd = "AT+TVALVE=0"
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        time.sleep(3)
        #input('1. Connect hose to DUT\n2. Set regulator to GAS ON position\n3. Press enter!')
        #Open valve (tvalve=1)
        print('Opening valve!')
        cmd = "AT+TVALVE=1"
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        time.sleep(2) """
        #Enable solenoid valve
        cmd = 'CMD=0,1'
        cmd = cmd +'\r\n'
        ser_ard.write(cmd.encode('utf-8'))
        time.sleep(0.5)
        cmd = 'CMD=6,1'
        cmd = cmd +'\r\n'
        ser_ard.write(cmd.encode('utf-8'))
        time.sleep(5)
        input('Please set regulator to GAS ON position! and press Enter/ Return!')
        cmd = 'CMD=3,1'
        cmd = cmd +'\r\n'
        ser_ard.write(cmd.encode('utf-8'))
        time.sleep(0.5)
        #Force vale to close to set starting condition
        print('Initializing valve position to closed!')
        cmd = "AT+TVALVE=0"
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        time.sleep(3)
        #input('1. Connect hose to DUT\n2. Set regulator to GAS ON position\n3. Press enter!')
        #Open valve (tvalve=1)
        print('Opening valve!')
        cmd = "AT+TVALVE=1"
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        time.sleep(3)
        #start polling flow rate on FMCD PCBA wait for flow rate to settle
        print('Starting flow sensor polling for AFC calibration...')
        cmd = "AT+TPSDF=1,1,500,50,2800" #3000ms ssaple size and 2895hz
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        time.sleep(1)
        ser_fmcd.reset_input_buffer()
        time.sleep(20)
        self = ser_fmcd.read(1024)
        # Decode the byte string
        decoded_data = self.decode('utf-8')
        # Put decoded data into list
        tpsdf_list = [line for line in decoded_data.split('\r\n') if line.startswith('+TPSDF')]
        # Extract only flow rate frm output (last item in each line of the list)
        fr_float= [float(line.split(',')[-1]) for line in tpsdf_list]
        # Average the flow rate
        avg_fr = sum(fr_float)/len(fr_float)
        print('Average flow rate measured(LPM): '+str(round(avg_fr,4))) #round(avg_psd,2)
        # Set allowable flowrate variation for test
        fr_variation = int(fr_var)/100 * float(fr1)
        cmd = "AT+TPSDF=0" #3000ms ssaple size and 2895hz
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        time.sleep(1)
        #Check for stable flowrate
        if float(fr1) - fr_variation <= avg_fr <= float(fr1) + fr_variation:
            print('Stable flowrate achieved!')
            psd_attempt=1
            while psd_attempt<4:
                print('PSD calibration - attempt '+str(psd_attempt))
                #Reset received data buffer
                ser_fmcd.reset_input_buffer()
                #Wait for enough data
                time.sleep(20)
                #Get data
                decoded_data = self.decode('utf-8')
                #Find all instances of TPSD lines
                tpsdf_list = [line for line in decoded_data.split('\r\n') if line.startswith('+TPSDF')]
                cal_fr_data = [float(line.split(',')[-1]) for line in tpsdf_list]
                cal_fr_data_avg = sum(cal_fr_data)/len(cal_fr_data)
                #Put all TPSD lines in a list and get PSD data (second last item in list)
                psd_data = [float(line.split(',')[-2]) for line in tpsdf_list]
                avg_psd_lfr = sum(psd_data)/len(psd_data)
                avg_psd_lfr_corr = avg_psd_lfr + float(air_to_lpg)
                psd_variation = int(psd_var)/100 * float(psd1)
                if float(psd1) + psd_variation <= avg_psd_lfr_corr <= float(psd1) - psd_variation:
                    gain = avg_psd_lfr_corr - float(psd1)
                    psd_res['0']= 'AVG_FR_LPM:'+str(round(cal_fr_data_avg,2))
                    psd_res['1']= 'CAL_PSD:'+str(psd1)
                    psd_res['2']= 'ALLOWED_PSD_VAR(%):'+str(psd_var)
                    psd_res['3']= 'PSD_READINGS:'+str(len(psd_data))
                    psd_res['4']='AVG_PSD_LFR_CORR_dB:'+str(round(avg_psd_lfr_corr,2))
                    psd_res['5']='AFC_GAIN:'+str(round(gain,2))
                    psd_res = ','.join(psd_res.values())
                    psd_test = 'PASS'
                    print('PSD calibration complete!')
                    print(psd_res)
                    break
                else:
                    avg_psd_lfr_corr = avg_psd_lfr + air_to_lpg
                    gain = avg_psd_lfr_corr - psd1
                    psd_res['0']= 'AVG_FR_LPM:'+str(round(cal_fr_data_avg,2))
                    psd_res['1']= 'CAL_PSD:'+str(psd1)
                    psd_res['2']= 'ALLOWED_PSD_VAR(%):'+str(psd_var)
                    psd_res['3']= 'PSD_READINGS:'+str(len(psd_data))
                    psd_res['4']='AVG_PSD_LFR_CORR_dB:'+str(round(avg_psd_lfr_corr,2))
                    psd_res['5']='AFC_GAIN:'+str(round(gain,2))
                    psd_res = ','.join(psd_res.values())
                    print(psd_res)
                    print('PSD NOT STABLE RETRYING CALIBRATION!')
                    psd_test = 'FAIL'
                    psd_res = {}
                    psd_attempt+=1
            else:
                print('PSD calibration test failed')
                psd_test = 'FAIL'
                avg_psd_lfr_corr = avg_psd_lfr + float(air_to_lpg)
                gain = avg_psd_lfr_corr - psd1
                psd_res['0']= 'AVG_FR_LPM:'+str(round(avg_fr,2))
                psd_res['1']= 'CAL_PSD:'+str(psd1)
                psd_res['2']= 'ALLOWED_PSD_VAR(%):'+str(psd_var)
                psd_res['3']= 'PSD_READINGS:'+str(len(psd_data))
                psd_res['4']='AVG_PSD_LFR_CORR_dB:'+str(round(avg_psd_lfr_corr,2))
                psd_res['5']='AFC_GAIN:'+str(gain)
                psd_res = ','.join(psd_res.values())
                print(psd_res)
        else:
            psd_test = 'FAIL'
            psd_res = {}
            print("Stable flowrate not achieved")
        #Stop polling flow sensor
        cmd = "AT+TPSDF=0"
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        time.sleep(2)
        ser_fmcd.reset_input_buffer()
        #Close valvein preparation of leak test
        print('Closing valve!')
        cmd = "AT+TVALVE=0"
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        time.sleep(2) 
        #Ask tester to set device back to gas off position
        #Set time
        #Unlock and remove - end test
        cmd = 'CMD=3,0'
        cmd = cmd +'\r\n'
        ser_ard.write(cmd.encode('utf-8'))
        return psd_test, round(gain,2), round(avg_psd_lfr_corr,2), round(cal_fr_data_avg,2)

    except Exception as e:
        psd_test ='FAIL'
        gain = 99
        avg_psd_lfr_corr = 99
        cal_fr_data_avg = 99
        #close valve
        cmd = "AT+TVALVE=0"
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        time.sleep(2) 
        # Ensure solenoid valve is closed
        cmd = 'CMD=3,0'
        cmd = cmd +'\r\n'
        ser_ard.write(cmd.encode('utf-8'))
        #Stop polling flow sensor
        cmd = "AT+TPSDF=0"
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        time.sleep(2) 
        ser_fmcd.reset_input_buffer()
        print(f"AFC Test error: {e}")
        return psd_test, gain, avg_psd_lfr_corr, cal_fr_data_avg
    

def afc_range(ser_ard, ser_fmcd, fr2, fr_var, air_to_lpg, psd_lfr_corr, pass_range):
    try:
    #Check for number of flow rates
        #AFC being tested at single flow rate
        print('AFC range test!')
        #Force vale to close to set starting condition
        print('Initializing valve position to closed!')
        cmd = "AT+TVALVE=0"
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        time.sleep(2)
        #Open valve (tvalve=1)
        print('Opening valve!')
        cmd = "AT+TVALVE=1"
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        time.sleep(2)
        #Enable solenoid valve for high flow rate (LPM)
        cmd = 'CMD=4,1'
        cmd = cmd +'\r\n'
        ser_ard.write(cmd.encode('utf-8'))
        #start polling flow rate on FMCD PCBA wait for flow rate to settle
        print('Starting flow sensor polling for AFC range test...')
        cmd = "AT+TPSDF=1,1,500,50,2800"
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        time.sleep(1)
        ser_fmcd.reset_input_buffer()
        time.sleep(20)
        self = ser_fmcd.read(1024)
        # Decode the byte string
        decoded_data = self.decode('utf-8')
        # Put decoded data into list
        tpsdf_list = [line for line in decoded_data.split('\r\n') if line.startswith('+TPSDF')]
        # Extract only flow rate frm output (last item in each line of the list)
        fr_float= [float(line.split(',')[-1]) for line in tpsdf_list]
        # Average the flow rate
        avg_fr = sum(fr_float)/len(fr_float)
        print('Average flow rate measured(LPM): '+str(round(avg_fr,4))) #round(avg_psd,2)
        # Set allowable flowrate variation for test
        fr_variation = int(fr_var)/100 * float(fr2)
        #Check for stable flowrate
        if float(fr2) - fr_variation <= avg_fr <= float(fr2) + fr_variation:
            print('Stable flowrate achieved')
            psd_attempt=1
            while psd_attempt<4:
                print('PSD range check - attempt '+str(psd_attempt))
                #Reset received data buffer
                ser_fmcd.reset_input_buffer()
                #Wait for enough data
                time.sleep(20)
                #Get data
                decoded_data = self.decode('utf-8')
                #Find all instances of TPSD lines
                tpsdf_list = [line for line in decoded_data.split('\r\n') if line.startswith('+TPSDF')]
                #Put all TPSD lines in a list - second last item in each row
                psd_data = [float(line.split(',')[-2]) for line in tpsdf_list]
                avg_psd_hfr = sum(psd_data)/len(psd_data)
                avg_psd_hfr_corr = avg_psd_hfr + float(air_to_lpg)
                range = avg_psd_hfr_corr - psd_lfr_corr
                if range > int(pass_range):
                    print('Range: '+str(round(range,2))+'dB: PASS')
                    psd_range_test = 'PASS'
                    break
                else:
                    print('Range: '+str(round(range,2))+'dB: FAIL - attempt: '+str(psd_attempt))
                    psd_range_test = 'FAIL'
                    psd_attempt+=1
            else:
                print('PSD range test failed!')
                psd_range_test = 'FAIL'

        else:
            #range = avg_psd_hfr_corr - psd_lfr_corr
            print("Stable flowrate not achieved")
            psd_range_test = 'FAIL'
            range = 0
        #Stop polling flow sensor
        cmd = "AT+TPSDF=0"
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        time.sleep(2)
        ser_fmcd.reset_input_buffer() 
        instruction = 'Closing valve!'
        print(instruction)
        cmd = "AT+TVALVE=0"
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        ser_fmcd.reset_input_buffer()
        cmd = 'CMD=4,0'
        cmd = cmd +'\r\n'
        ser_ard.write(cmd.encode('utf-8'))
        
        return psd_range_test, round(range,2), round(avg_fr,2), round(avg_psd_hfr_corr,2)

    except Exception as e:
        psd_range_test = 'FAIL'
        range = 0
        avg_fr = 0
        avg_psd_hfr_corr = 0
        #close valve
        cmd = "AT+TVALVE=0"
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        # Ensure solenoid valve is closed
        cmd = 'CMD=4,0'
        cmd = cmd +'\r\n'
        ser_ard.write(cmd.encode('utf-8'))
        #Stop polling flow sensor
        cmd = "AT+TPSDF=0"
        cmd = cmd +'\r\n'
        ser_fmcd.write(cmd.encode('utf-8'))
        ser_fmcd.reset_input_buffer()
        print(f"AFC Test error: {e}")
        return psd_range_test, range, round(avg_fr,2), avg_psd_hfr_corr