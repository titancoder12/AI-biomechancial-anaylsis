//#include <ArduinoBLE.h>

#include <Wire.h>
#include <Adafruit_MPU6050.h>
//#include <Adafruit_Sensor.h>
#include <iostream>

using namespace std;

#define SERVICE_UUID        "12345678-1234-5678-1234-56789abcdef0"
#define CHARACTERISTIC_UUID "12345678-1234-5678-1234-56789abcdef1"

#define TCA_ADDRESS 0x70  // I2C address for the TCA9548A

// Create MPU6050 objects for each sensor
Adafruit_MPU6050 mpu1, mpu2, mpu3;

bool computer_connected = false;

// Function to select a channel on the TCA9548A
void selectChannel(uint8_t channel) {
    if (channel > 7) return; // There are only 8 channels (0-7)
    Wire.beginTransmission(TCA_ADDRESS);
    Wire.write(1 << channel);  // This enables only the desired channel
    Wire.endTransmission();
}

void setup() {
    Serial.begin(115200);
    
    Wire.begin();
    
    // Initialize MPU6050 on Channel 0
    selectChannel(0);
    if (!mpu1.begin()) {
        Serial.println("Failed to find MPU6050 on Channel 0");
    } else {
        Serial.println("MPU6050 found on Channel 0");
        mpu1.setFilterBandwidth(MPU6050_BAND_260_HZ);
    }
  
    // Initialize MPU6050 on Channel 1
    selectChannel(1);
    if (!mpu2.begin()) {
        Serial.println("Failed to find MPU6050 on Channel 1");
    } else {
        Serial.println("MPU6050 found on Channel 1");
        mpu2.setFilterBandwidth(MPU6050_BAND_260_HZ);
    }
  
    // Initialize MPU6050 on Channel 2
    selectChannel(2);
    if (!mpu3.begin()) {
        Serial.println("Failed to find MPU6050 on Channel 2");
    } else {
        Serial.println("MPU6050 found on Channel 2");
        mpu3.setFilterBandwidth(MPU6050_BAND_260_HZ);
        delay(2000);
    }
}

void loop() {
    if (Serial.available()) {
        String command = Serial.readStringUntil('\n');
        command.trim();
        Serial.println("Command: " + command);
        if (command == "connect") {
            computer_connected = true;
            Serial.println("Connected");
        } else if (command == "disconnect") {
            computer_connected = false;
            Serial.println("Disconnected");
        }
    }

    sensors_event_t a, g, temp;
    
    if (computer_connected) {
    
        // --- Read from MPU6050 on Channel 0 ---
        selectChannel(0);         // Switch to channel 0
        mpu1.getEvent(&a, &g, &temp);  // Get sensor event data
        //Serial.print("Channel 0 - Accel X: "); Serial.println(a.acceleration.x);

        Serial.print("0AcX:"); Serial.print(a.acceleration.x);
        Serial.print(" 0AcY:"); Serial.print(a.acceleration.y);
        Serial.print(" 0AcZ:"); Serial.print(a.acceleration.z);
        Serial.print(" 0GyX:"); Serial.print(g.gyro.x);
        Serial.print(" 0GyY:"); Serial.print(g.gyro.y);
        Serial.print(" 0GyZ:"); Serial.print(g.gyro.z);
        // --- Read from MPU6050 on Channel 1 ---
        selectChannel(1);         // Switch to channel 1
        mpu2.getEvent(&a, &g, &temp);
        //Serial.print("Channel 1 - Accel X: "); Serial.println(a.acceleration.x);

        Serial.print(" 1AcX:"); Serial.print(a.acceleration.x);
        Serial.print(" 1AcY:"); Serial.print(a.acceleration.y);
        Serial.print(" 1AcZ:"); Serial.print(a.acceleration.z);
        Serial.print(" 1GyX:"); Serial.print(g.gyro.x);
        Serial.print(" 1GyY:"); Serial.print(g.gyro.y);
        Serial.print(" 1GyZ:"); Serial.print(g.gyro.z);

        // --- Read from MPU6050 on Channel 2 ---
        selectChannel(2);         // Switch to channel 2
        mpu3.getEvent(&a, &g, &temp);
        //Serial.print("Channel 2 - Accel X: "); Serial.println(a.acceleration.x);

        Serial.print(" 2AcX:"); Serial.print(a.acceleration.x);
        Serial.print(" 2AcY:"); Serial.print(a.acceleration.y);
        Serial.print(" 2AcZ:"); Serial.print(a.acceleration.z);
        Serial.print(" 2GyX:"); Serial.print(g.gyro.x);
        Serial.print(" 2GyY:"); Serial.print(g.gyro.y);
        Serial.print(" 2GyZ:"); Serial.print(g.gyro.z);

        Serial.println();
        //delay(5); // Short delay before next cycle
    }
}
