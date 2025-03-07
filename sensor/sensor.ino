#include <ArduinoBLE.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <iostream>
using namespace std;

#define SERVICE_UUID        "12345678-1234-5678-1234-56789abcdef0"
#define CHARACTERISTIC_UUID "12345678-1234-5678-1234-56789abcdef1"

#define TCA_ADDRESS 0x70  // I2C address for the TCA9548A

BLEService imuService("180A");
/*BLEFloatCharacteristic AcX0("2A19", BLERead | BLENotify);  // X0-axis acc characteristic
BLEFloatCharacteristic AcY0("2A1A", BLERead | BLENotify);  // Y0-axis acc characteristic
BLEFloatCharacteristic AcZ0("2A1B", BLERead | BLENotify);  // Z0-axis acc characteristi
*/
BLEFloatCharacteristic AcX0("1", BLERead | BLENotify);  // X0-axis acc characteristic
BLEFloatCharacteristic AcY0("2", BLERead | BLENotify);  // Y0-axis acc characteristic
BLEFloatCharacteristic AcZ0("3", BLERead | BLENotify);  // Z0-axis acc characteristi

BLEStringCharacteristic Data("4", BLERead | BLENotify, 150);
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
    while (!Serial);

    //BLE
    if (!BLE.begin()) {
        Serial.println("Starting BLE failed!");
        while (1);
    }

    Serial.print("Arduino BLE Address: ");
    Serial.println(BLE.address());  // Print BLE address
    BLE.setLocalName("IMU_Sensor");
    BLE.setAdvertisedService(imuService);

    imuService.addCharacteristic(AcX0);
    imuService.addCharacteristic(AcY0);
    imuService.addCharacteristic(AcZ0);

    imuService.addCharacteristic(Data);

    BLE.addService(imuService);
    
    BLE.advertise();
    //Serial.println("BLE IMU Sensor is ready...");
  

    Wire.begin();
    
    // Initialize MPU6050 on Channel 0
    selectChannel(0);
    if (!mpu1.begin()) {
        Serial.println("Failed to find MPU6050 on Channel 0");
    } else {
        Serial.println("MPU6050 found on Channel 0");
        //mpu1.setFilterBandwidth(MPU6050_BAND_260_HZ);
    }
  
    // Initialize MPU6050 on Channel 1
    selectChannel(1);
    if (!mpu2.begin()) {
        Serial.println("Failed to find MPU6050 on Channel 1");
    } else {
        Serial.println("MPU6050 found on Channel 1");
        //mpu2.setFilterBandwidth(MPU6050_BAND_260_HZ);
    }
  
    // Initialize MPU6050 on Channel 2
    selectChannel(2);
    if (!mpu3.begin()) {
        Serial.println("Failed to find MPU6050 on Channel 2");
    } else {
        Serial.println("MPU6050 found on Channel 2");
        //mpu3.setFilterBandwidth(MPU6050_BAND_260_HZ);
        delay(2000);
    }
    //Serial.println(BLE.address());
}

void loop() {
    //Serial.println(BLE.address());
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

    // Listen for BLE connections
    BLEDevice central = BLE.central();
    if (central) {
        Serial.print("Connected to: ");
        Serial.println(central.address());

        while (central.connected()) {
            // Read IMU Data
            sensors_event_t a, g, temp;

            selectChannel(0); 
            mpu1.getEvent(&a, &g, &temp);
            double AX0 = a.acceleration.x;
            double AY0 = a.acceleration.y;
            double AZ0 = a.acceleration.z;
            double GX0 = g.gyro.x;
            double GY0 = g.gyro.y;
            double GZ0 = g.gyro.z;

            selectChannel(1);  
            mpu2.getEvent(&a, &g, &temp);
            double AX1 = a.acceleration.x;
            double AY1 = a.acceleration.y;
            double AZ1 = a.acceleration.z;
            double GX1 = g.gyro.x;
            double GY1 = g.gyro.y;
            double GZ1 = g.gyro.z;

            selectChannel(2);  
            mpu3.getEvent(&a, &g, &temp);
            double AX2 = a.acceleration.x;
            double AY2 = a.acceleration.y;
            double AZ2 = a.acceleration.z;
            double GX2 = g.gyro.x;
            double GY2 = g.gyro.y;
            double GZ2 = g.gyro.z;

            char buffer[250];
            sprintf(buffer, "0AcX:%.4f 0AcY:%.4f 0AcZ:%.4f 0GyX:%.4f 0GyY:%.4f 0GyZ:%.4f 1AcX:%.4f 1AcY:%.4f 1AcZ:%.4f 1GyX:%.4f 1GyY:%.4f 1GyZ:%.4f 2AcX:%.4f 2AcY:%.4f 2AcZ:%.4f 2GyX:%.4f 2GyY:%.4f 2GyZ:%.4f", AX0, AY0, AZ0, GX0, GY0, GZ0, AX1, AY1, AZ1, GX1, GY1, GZ1, AX2, AY2, AZ2, GX2, GY2, GZ2);

            Data.writeValue(buffer);

            //Serial.print("0AcX:"); Serial.print(a.acceleration.x);
            //Serial.print("0AcY"); Serial.print(a.acceleration.y);
            //Serial.print("0AcZ"); Serial.println(a.acceleration.z);

            delay(100); // Small delay before sending next data
        }
        Serial.println("Disconnected from central");
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
