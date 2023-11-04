import os
import sys
import json # this is a built-in module in python
import csv # this is included in the Python installation
import datetime # this is a built in module
import time
import serial
import numpy as np
from datetime import timezone
import requests
import functions as f
import tests as t
import asyncio

def main():
    timestamp, curr_date=f.get_time()
    test_type, sub_type, db, air2lpg, fr1, fr2, psd1, fr1_var, psd1_var, psd_range = f.get_config()
    fmcd_ser = f.fmcd_ser_setup()
    ard_ser = f.arduino_ser_setup()  
    regsn = f.get_besasn()
    afcsn = f.get_afc_sn(db)

    #Enable appropriate inlet relay(s)
    

    #Enter inlet pressure:
    inlet_p = f.get_pres_inlet()

    #Enter outlet pressure
    outlet_p = f.get_pres_outlet()

    #Check control board is active and set to test
    fv= t.ati(fmcd_ser)
    t.testmode(fmcd_ser)
    
    #Execute AFC calibration and get 'gain'
    #GET GAIN VALUE, FR etc. 
    cal_test,gain,avg_psd_lfr_corr,cal_fr= t.afc_calibration(ard_ser, fmcd_ser, fr1, psd1, fr1_var, psd1_var, air2lpg)
    #avg_psd_lfr_corr = -48.21
    #Check AFC PSD range from lowest flow rate (1.25LPM) to highest (8LPM)
    psd_range_test,range,high_fr,high_psd_corr=t.afc_range(ard_ser, fmcd_ser, fr2, fr1_var, air2lpg, avg_psd_lfr_corr, psd_range)
    
    #Results dictionary
    summary = {
        "timestamp_UTC": timestamp,
        "date": curr_date.strftime("%x"),
        "time": curr_date.strftime("%X"),
        "type": test_type,
        "subtype": sub_type,
        "serial_number": regsn,
        "afcm_number": afcsn,
        "fv": fv.decode('utf-8'),
        "cal_test":cal_test,
        "afcgain": gain, 
        "inlet_pres_bar": inlet_p, 
        "outlet_pres_mbar": outlet_p,
        "flowRate_low": cal_fr,
        "flowRate_high": high_fr,
        "psd_low": avg_psd_lfr_corr,
        "psd_high": high_psd_corr,
        "range_test":psd_range_test,
        "range": range,
        "lpg_air_scale":air2lpg,
    }
    

    #save log
    #Logfile name format: UNIXTIMESTAMP_ID_PASS/FAIL
    try:
        if 'FAIL' in summary.values():
            filename = str(timestamp)+'_' + regsn + '_FAIL''.json'
            summary["overall_result"]='FAIL'
            print('Overall Result FAIL')
            #Write and save output file
            with open(filename, "w") as outfile:
                json.dump(summary, outfile)
        else:                    
            filename = str(timestamp)+'_' + regsn + '_PASS''.json'
            summary["overall_result"]='PASS'
            print('Overall Result PASS')
            #Write and save output file
            with open(filename, "w") as outfile:
                json.dump(summary, outfile)
        f.post_db(summary,db)
         #close serial
        fmcd_ser.close()
        ard_ser.close()
    except Exception as e:
        print(e)

if __name__ == '__main__':
    main()

