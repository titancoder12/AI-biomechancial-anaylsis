#include <Wire.h>
#include <ArduinoBLE.h>

//BLEService imuService("180A");
//BLEFloatCharacteristic AcX0_t("2A19", BLERead | BLENotify);  // X0-axis acc characteristic
//BLEFloatCharacteristic AcY0_t("2A1A", BLERead | BLENotify);  // Y0-axis acc characteristic
//BLEFloatCharacteristic AcZ0_t("2A1B", BLERead | BLENotify);  // Z0-axis acc characteristic

const int MPU_addrs[] = { 0x68, 0x69 }; // Addresses of the MPU6050 sensors

int16_t rawAcX[2], rawAcY[2], rawAcZ[2], rawTmp[2];
int16_t rawGyX[2], rawGyY[2], rawGyZ[2];

float AcX[2], AcY[2], AcZ[2], Tmp[2];
float GyX[2], GyY[2], GyZ[2];

bool sensor_connected=false;
int i = 0;

void setup() {
    Wire.begin();
    Serial.begin(115200);

    while (!Serial);

    //if (!BLE.begin()) {
    //    Serial.println("Starting BLE failed!");
    //    while (1);
    //}
    /*Serial.print("Arduino BLE Address: ");
    Serial.println(BLE.address());  // Print BLE address
    BLE.setLocalName("IMU_Sensor");
    BLE.setAdvertisedService(imuService);

    imuService.addCharacteristic(AcX0_t);
    imuService.addCharacteristic(AcY0_t);
    imuService.addCharacteristic(AcZ0_t);
    BLE.addService(imuService);*/
    
    //BLE.advertise();
    //Serial.println("BLE IMU Sensor is ready...");
  
    for (byte b = 0; b < 2; b++) {
        Wire.beginTransmission(MPU_addrs[b]);
        Wire.write(0x6B);  // PWR_MGMT_1 register
        Wire.write(0x00);     // Wake up MPU6050
        Wire.endTransmission(true);
    }
  
    Serial.println("Waiting for connections...");
}

void loop() {
    //Serial.println(sensor_connected);
    //Serial.println(i);
    //BLEDevice central = BLE.central();
    
    if (Serial.available()) {
        String command = Serial.readStringUntil('\n'); // Read the incoming string
        bool readingData;
        command.trim();
        Serial.println(command);
        Serial.println(command=="connect");
        if (command == "connect") {
            sensor_connected = true;
            Serial.println("connected");
        }
        else if (command == "disconnect"){
            sensor_connected=false;
            Serial.println("disconnected");
        }
    }
        if (sensor_connected == true) {
            //Serial.println("READING DATA");
            // Iterate over both sensors
            for (byte b = 0; b < 2; b++) {
                Wire.beginTransmission(MPU_addrs[b]);
                Wire.write(0x3B);  // Start reading from ACCEL_XOUT_H
                //Wire.write(0x00);
                Wire.endTransmission(false);
                Wire.requestFrom(MPU_addrs[b], 14, true); // Read 14 bytes (Accel, Temp, Gyro)

                if (Wire.available() == 14) {  // Ensure we received 14 bytes
                    // Read the accelerometer and gyroscope data
                    rawAcX[b] = Wire.read() << 8 | Wire.read();
                    rawAcY[b] = Wire.read() << 8 | Wire.read();
                    rawAcZ[b] = Wire.read() << 8 | Wire.read();
                    rawTmp[b] = Wire.read() << 8 | Wire.read(); // Temperature

                    rawGyX[b] = Wire.read() << 8 | Wire.read();
                    rawGyY[b] = Wire.read() << 8 | Wire.read();
                    rawGyZ[b] = Wire.read() << 8 | Wire.read();

                    // Convert raw values to actual units
                    AcX[b] = rawAcX[b] / 16384.0;
                    AcY[b] = rawAcY[b] / 16384.0;
                    AcZ[b] = rawAcZ[b] / 16384.0;
                    Tmp[b] = rawTmp[b] / 340.0 + 36.53;

                    GyX[b] = rawGyX[b] / 131.0;
                    GyY[b] = rawGyY[b] / 131.0;
                    GyZ[b] = rawGyZ[b] / 131.0;

                    // Print sensor values
                    Serial.print(b);
                    Serial.print("AcX:");
                    Serial.print(AcX[b]);
                    Serial.print(" ");
                    Serial.print(b);
                    Serial.print("AcY:");
                    Serial.print(AcY[b]);
                    Serial.print(" ");
                    Serial.print(b);
                    Serial.print("AcZ:");
                    Serial.print(AcZ[b]);
                    Serial.print(" ");
                    Serial.print(b);
                    Serial.print("GyX:");
                    Serial.print(GyX[b]);
                    Serial.print(" ");
                    Serial.print(b);
                    Serial.print("GyY:");
                    Serial.print(GyY[b]);
                    Serial.print(" ");
                    Serial.print(b);
                    Serial.print("GyZ:");
                    Serial.print(GyZ[b]);
                    Serial.print(" ");

                    //Wire.endTransmission(true);
                    //if (central) {
                        //Serial.print("Connected to: "); Serial.println(central.address());
                        //AcX0_t.writeValue(AcX[b]);
                        //AcY0_t.writeValue(AcY[b]);
                        //AcZ0_t.writeValue(AcZ[b]);
                    //}
                    
                } else {
                    // Handle I2C error
                    Serial.println("Error: Sensor data read failed!");
                }
                delay(10);  // Small delay between sensor reads
            }
            Serial.println();  // Newline after printing data for both sensors
            //readingData = false;  // Reset flag after data read
        }
    //i+=1;
}