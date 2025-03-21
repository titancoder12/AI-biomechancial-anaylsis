#include <ArduinoBLE.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <iostream>

using namespace std;

#define SERVICE_UUID        "12345678-1234-5678-1234-56789abcdef0"
#define CHARACTERISTIC_UUID "12345678-1234-5678-1234-56789abcdef1"

BLEService imuService("180A");
BLEStringCharacteristic S0("0001", BLERead | BLENotify, 150);  // X0-axis acc characteristic
BLEStringCharacteristic S1("0002", BLERead | BLENotify, 150);  // Y0-axis acc characteristic

// Create MPU6050 objects for each sensor
Adafruit_MPU6050 mpu1, mpu2;

bool computer_connected = false;

void setup() {
    delay(2000);
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

    imuService.addCharacteristic(S0);
    imuService.addCharacteristic(S1);

    BLE.addService(imuService);
    
    BLE.advertise();
    //Wire.setClock(400000);
    Wire.begin();

    // Initialize MPU6050 on Channel 0
    if (!mpu1.begin(0x68)) {
        Serial.println("Failed to find MPU6050-1");
    } else {
        Serial.println("MPU6050-1 found");
        mpu1.setAccelerometerRange(MPU6050_RANGE_16_G);
        mpu1.setGyroRange(MPU6050_RANGE_2000_DEG);
        mpu1.setFilterBandwidth(MPU6050_BAND_260_HZ);
    }
  
    // Initialize MPU6050 on Channel 1
    if (!mpu2.begin(0x69)) {
        Serial.println("Failed to find MPU6050-2");
    } else {
        Serial.println("MPU6050-2 found");
        mpu2.setAccelerometerRange(MPU6050_RANGE_16_G);
        mpu2.setGyroRange(MPU6050_RANGE_2000_DEG);
        mpu2.setFilterBandwidth(MPU6050_BAND_260_HZ);
    }
}

void loop() {
    // Listen for BLE connections
    BLEDevice central = BLE.central();
    if (central) {
        Serial.print("Connected to: ");
        Serial.println(central.address());
        
        while (central.connected()) {
            // Read IMU Data
            sensors_event_t a, g, temp;

            mpu1.getEvent(&a, &g, &temp);
            double AX0 = a.acceleration.x;
            double AY0 = a.acceleration.y;
            double AZ0 = a.acceleration.z;
            double GX0 = g.gyro.x;
            double GY0 = g.gyro.y;
            double GZ0 = g.gyro.z;

            //Write values to BLE
            char buffer0[250];
            sprintf(buffer0, "0AcX:%.4f 0AcY:%.4f 0AcZ:%.4f 0GyX:%.4f 0GyY:%.4f 0GyZ:%.4f", AX0, AY0, AZ0, GX0, GY0, GZ0);
            S0.writeValue(buffer0);
 
            mpu2.getEvent(&a, &g, &temp);
            double AX1 = a.acceleration.x;
            double AY1 = a.acceleration.y;
            double AZ1 = a.acceleration.z;
            double GX1 = g.gyro.x;
            double GY1 = g.gyro.y;
            double GZ1 = g.gyro.z;

            //Write values to BLE
            char buffer1[250];
            sprintf(buffer1, "1AcX:%.4f 1AcY:%.4f 1AcZ:%.4f 1GyX:%.4f 1GyY:%.4f 1GyZ:%.4f", AX1, AY1, AZ1, GX1, GY1, GZ1);
            S1.writeValue(buffer1);

            Serial.print(buffer0);
            Serial.print(" ");
            Serial.println(buffer1);
        }
        Serial.println("Disconnected from central");
    }
}
