/**
 * Config Header File
 * 
 * Copyright 2023 Eugene Mwangi <eugene.mwangi@paygoenergy.co>
 * 
 * Contains MACROS for pin definition and debug enabling/disabling
*/

// Define the relay pins
#define RELAYPIN1 2     // 17.33LPM Solenoid
#define RELAYPIN2 3     // 19.33LPM Solenoid
#define RELAYPIN3 4     // 1.25LPM Solenoid
#define RELAYPIN4 5     // 8.0LPM Solenoid
#define RELAYPIN5 6     // spare valve 5
#define RELAYPIN6 7     // spare valve 6
#define RELAYPIN7 8     // spare valve 7
#define RELAYPIN8 9     // Soundness Flow Solenoid

#define RELAY_MIN   2
#define RELAY_MAX   9 

// Define MACROS to turn all relays ON or OFF 
#define TURN_ON   '1'
#define TURN_OFF  '0'

// Define the states of the relay. Pins are ACTIVE LOW
#define RELAY_ON    0
#define RELAY_OFF   1
#define ALL_ON      RELAY_MAX+1
#define ALL_OFF     1

// Define Enable MACROS
#define MAIN_DEBUG_EN 0

// Other MACROS
#define STRING_LENGTH     8 // Expected length of string sent via serial
#define STRING_CMD        "CMD"// Expected command prefix