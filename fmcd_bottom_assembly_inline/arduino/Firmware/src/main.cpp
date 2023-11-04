#include <Arduino.h>
#include "config.h"
 

// put function declarations here:
void readSerial();
void relayControl(int, int);

// Global Variables
const char relay[] = {'0','1','2','3','4','7','8','5','6','A'};

void setup() {
  Serial.begin(9600); // Initialize serial communication with a baudrate of 9600

  for(int pin = RELAY_MIN; pin<=RELAY_MAX;pin++){
    pinMode(pin, OUTPUT); // Set relay pin controlling solenoid valve as an output
    digitalWrite(pin, RELAY_OFF); // Close SV1 initially (Relay is Active LOW)
  }
}

void loop() {
  // put your main code here, to run repeatedly:
  readSerial();
}

/**
 * @brief Reads data from the serial
 * 
 */
void readSerial(){
  if(Serial.available()){
    String cmd = Serial.readStringUntil('\n'); // Read the line terminated by '\n'
    #if MAIN_DEBUG_EN
      Serial.print("Received Line: ");Serial.println(cmd);
      Serial.print("Length: ");Serial.println(cmd.length());
      Serial.print("Command Prefix: ");Serial.println(cmd.substring(0,3));
    #endif //MAIN_DEBUG
    // Check that the data is valid
    if(cmd.substring(0,3) == STRING_CMD && cmd.length() == STRING_LENGTH && cmd[3] == '=' && cmd[5] == ','){
      char relay_pin = cmd[4];
      char action = cmd[6];
      int arr_length = sizeof(relay)/sizeof(relay[0]);
      uint16_t selected_relay = 0;
      bool isValidRelay = false;
      #if MAIN_DEBUG_EN
        Serial.print("Relay pin: ");
        Serial.println(relay_pin);
        Serial.print("Action: ");
        Serial.println(action);
      #endif //DEBUG_EN
      for(int i=0; i<arr_length;i++){ 
        // Check which relay pin has been selected
        if(relay_pin == relay[i]){
          // Check which action has been selected
          selected_relay = i + 1;
          isValidRelay = true;
          if (action == TURN_OFF){
            // Send command to close selected relay
            relayControl(selected_relay, RELAY_OFF);
            Serial.println("OK");
            break;
          }
          else if (action == TURN_ON){
            // Send command to open the selected relay
            relayControl(selected_relay, RELAY_ON);
            Serial.println("OK");
            break;
          }
          else{
            Serial.println("ERROR");
            break;
          }
        }
        if(!isValidRelay && i == arr_length-1){
          Serial.println("ERROR");
        }
      }
    }
    else{
      Serial.println("ERROR");
    }
  }
}

/**
 * @brief Turns on the selected relay
 * @param  relaypin: relay to turn on or off
 * @param action: action to do(either ON or OFF)
 */
void relayControl(int relaypin, int action) {
  if (relaypin == ALL_OFF){
    for (int pin=RELAY_MIN; pin<=RELAY_MAX; pin++){
      digitalWrite(pin, RELAY_OFF);
    }
  }
  else if (relaypin == ALL_ON){
    for (int pin=RELAY_MIN; pin<=RELAY_MAX; pin++){
      digitalWrite(pin, RELAY_ON);
    }
  }
  else{
    // Serial.print("Relay Pin: ");Serial.println(relaypin);Serial.print("Action: ");Serial.println(action);
    digitalWrite(relaypin, action);
  }
}