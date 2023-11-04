import utils as f

def app():
    '''
    Main script
    '''
    # Set up connection with the arduino and V4 Board
    fmcd_ser = f.fmcd_ser_setup()
    ard_ser = f.arduino_ser_setup()

    # Get variable values and other setups
    f.create_directory() # Creates directory to save test results
    timestamp, curr_date=f.get_time()
    test_type, sub_type, db, fr1, fr2, leak_test, ef_test, afc_pot, ser_val, pthresh, cmvalve = f.get_config()
    enable = 'enable'
    f.get_var()

    # Begining
    # print('-' *50)
    print(f.bcolors['HEADER'] + "SOUNDNESS & EXCESS FLOW INLINE TEST" + f.bcolors['ENDC'])
    print('-' *50)
    
   # Change v4 board mode to TEST mode
    f.switch_to_test_mode(fmcd_ser)

    # Get Tester's Name
    user_name = input("Enter Tester's Name: ")

    # Scan regulator and afc serial number
    if ser_val.lower() == 'enable':
        reg_ser = input("Scan REGULATOR Serial Number: ")
        lock_ser = input("Scan LOCK Serial Number: ")
        valve_ser = input("Scan VALVE Serial Number: ")
        afc_ser = input("Scan AFC Serial Number: ")
        
        # Validate that the afc passed leak test(WHAT OF REGULATOR??)
        f.validate_ser_no(reg_ser, lock_ser, valve_ser, afc_ser)
    else:
        print("Serial Number Entry and Validation DISABLED!")

    # Get AFC Potting Config used
    print('-'*50)
    if afc_pot.lower() == enable:
        pott_config = f.get_afc_pot()
    else:
        print("AFC Potting Selection DISABLED!")

    # Run soundness test
    print('-'*50)
    if leak_test.lower() == enable:
        soundnessTestResult, firstPressureReading, secondPresureReading = f.run_soundness_test(fmcd_ser, ard_ser, pthresh)
    else:
        print("Soundness Test DISABLED!")
        soundnessTestResult = 'PASS'

    # Run excess flow test only if soundness test
    print('-'*50)
    if ef_test.lower() == enable:
        excessFlowrate_th1, flowrate_th1, excessFlowrate_th2, flowrate_th2 = f.run_excessflow_test(fmcd_ser, ard_ser, fr1, fr2, pthresh, soundnessTestResult, cmvalve)
    else:
        print('Excess Flow Test DISABLED!')
    print('-'*50)

    if ser_val.lower() == enable and afc_pot.lower() == enable and leak_test.lower() == enable and ef_test.lower() == enable:
        # Post data to server and also save them locally.
        try:
            print(f.bcolors['OKBLUE']+"Posting Data to "+db+" database..."+f.bcolors['ENDC'])
            # Append SEF(Soundness Excess Flow) to regulator serial number
            base_ser = reg_ser + "SEF"
            # Define dictionary with the test results
            summary = {
                "timestamp_UTC" : timestamp,
                "date": curr_date.strftime("%x"),
                "time": curr_date.strftime("%X"),
                "type": test_type,
                "subtype":sub_type,
                "serial_number": base_ser,
                "afc_serial_number": afc_ser,
                "potting_config": pott_config,
                "soundness_test": soundnessTestResult,
                "initial_pressure(mbar)": firstPressureReading,
                "final_pressure(mbar)":secondPresureReading,
                "excessflow_test_1": excessFlowrate_th1,
                "flowrate_1": flowrate_th1,
                "excessflow_test_2": excessFlowrate_th2, 
                "flowrate_2": flowrate_th2,
                "tester": user_name        
            }

            #Logfile name format: UNIXTIMESTAMP_ID_PASS/FAIL
            if 'FAIL' in summary.values():
                filename = "BASE_SEF_Results\\" + str(timestamp)+'_' + base_ser + '_FAIL''.json'
                summary["overall_result"]='FAIL'
                #Write and save output file
                with open(filename, "w") as outfile:
                    f.json.dump(summary, outfile)
                #Determine test duration
                timestamp_end, curr_date_end=f.get_time()
                print('Test time(sec): '+str(timestamp_end-timestamp))
                summary["test_duration(secs)"]=str(timestamp_end-timestamp)
                #Post result to mognodb
                f.post_db(summary,db)
                print(f.bcolors['FAIL']+'Overall Result FAIL'+f.bcolors['ENDC'])
                print('-'*50)
                f.sys.exit(0)
            else:                      
                filename = "BASE_SEF_Results\\" + str(timestamp)+'_' + base_ser + '_PASS''.json'
                summary["overall_result"]='PASS'
                #Write and save output file
                with open(filename, "w") as outfile:
                    f.json.dump(summary, outfile)
                #Determine test duration
                timestamp_end, curr_date_end=f.get_time()
                print('Test time(sec): '+str(timestamp_end-timestamp))
                summary["test_duration(secs)"]=str(timestamp_end-timestamp)
                #Post result to mognodb
                f.post_db(summary,db)
                print(f.bcolors['OKGREEN']+'Overall Result PASS'+f.bcolors['ENDC'])
                print('-'*50)
                f.sys.exit(1)
            fmcd_ser.close()
            ard_ser.close()
        except Exception as e:
            fmcd_ser.close()
            ard_ser.close()
            print(e)
            exit()

if __name__ == '__main__':
    f.os.system('color')
    app()
