#include <Wire.h>
#include <ArduinoBLE.h>  // BLE code remains commented as needed

// Sensor addresses on the default I²C bus (Wire)
const int MPU_addrs_hw[2] = { 0x68, 0x69 };
// Sensor address on the second I²C bus (Wire1)
const int MPU_addr_wire1 = 0x68;  // Sensor 3

// Arrays for sensor data (indices 0 and 1 for hardware I²C, index 2 for Wire1 sensor)
int16_t rawAcX[3], rawAcY[3], rawAcZ[3], rawTmp[3];
int16_t rawGyX[3], rawGyY[3], rawGyZ[3];
float AcX[3], AcY[3], AcZ[3], Tmp[3];
float GyX[3], GyY[3], GyZ[3];

bool sensor_connected = false;

void setup() {
  // Initialize the default hardware I²C bus (Wire) 
  Wire.begin();  // Typically on A4 (SDA) and A5 (SCL)

  // Initialize the second hardware I²C bus (Wire1)
  // Refer to your UNO R4 WiFi documentation for the correct SDA1/SCL1 pins.
  Wire1.begin();

  Serial.begin(115200);
  while (!Serial);  // Wait for Serial Monitor to open

  // Uncomment and adjust BLE initialization if needed:
  /*
  if (!BLE.begin()) {
    Serial.println("Starting BLE failed!");
    while (1);
  }
  Serial.print("Arduino BLE Address: ");
  Serial.println(BLE.address());
  BLE.setLocalName("IMU_Sensor");
  BLE.advertise();
  Serial.println("BLE IMU Sensor is ready...");
  */

  // Initialize sensors on the default I²C bus (Sensors 1 and 2)
  for (byte b = 0; b < 2; b++) {
    Wire.beginTransmission(MPU_addrs_hw[b]);
    Wire.write(0x6B);  // PWR_MGMT_1 register
    Wire.write(0x00);  // Wake up MPU6050
    Wire.endTransmission(true);
  }

  // Initialize sensor on the second I²C bus (Sensor 3)
  Wire1.beginTransmission(MPU_addr_wire1);
  Wire1.write(0x6B);  // PWR_MGMT_1 register
  Wire1.write(0x00);  // Wake up MPU6050
  Wire1.endTransmission(true);

  Serial.println("Sensors initialized. Waiting for connection command...");
}

void loop() {
  // Process serial commands ("connect" / "disconnect")
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    Serial.println("Command: " + command);
    if (command == "connect") {
      sensor_connected = true;
      Serial.println("Connected");
    } else if (command == "disconnect") {
      sensor_connected = false;
      Serial.println("Disconnected");
    }
  }

  // When connected, read data from all sensors
  if (sensor_connected) {
    // --- Read from Sensors 1 and 2 on the default I²C bus (Wire) ---
    for (byte b = 0; b < 2; b++) {
      Wire.beginTransmission(MPU_addrs_hw[b]);
      Wire.write(0x3B);  // Starting register for ACCEL_XOUT_H
      Wire.endTransmission(false);
      Wire.requestFrom(MPU_addrs_hw[b], 14, true);  // Read 14 bytes

      if (Wire.available() == 14) {  // If 14 bytes were received
        rawAcX[b] = Wire.read() << 8 | Wire.read();
        rawAcY[b] = Wire.read() << 8 | Wire.read();
        rawAcZ[b] = Wire.read() << 8 | Wire.read();
        rawTmp[b] = Wire.read() << 8 | Wire.read();
        rawGyX[b] = Wire.read() << 8 | Wire.read();
        rawGyY[b] = Wire.read() << 8 | Wire.read();
        rawGyZ[b] = Wire.read() << 8 | Wire.read();

        AcX[b] = rawAcX[b] / 16384.0;
        AcY[b] = rawAcY[b] / 16384.0;
        AcZ[b] = rawAcZ[b] / 16384.0;
        Tmp[b] = rawTmp[b] / 340.0 + 36.53;
        GyX[b] = rawGyX[b] / 131.0;
        GyY[b] = rawGyY[b] / 131.0;
        GyZ[b] = rawGyZ[b] / 131.0;

        Serial.print("Sensor ");
        Serial.print(b+1);
        Serial.print(" -> AcX: ");
        Serial.print(AcX[b]);
        Serial.print(" AcY: ");
        Serial.print(AcY[b]);
        Serial.print(" AcZ: ");
        Serial.print(AcZ[b]);
        Serial.print(" | ");
      } else {
        Serial.print("Error: Read failed for sensor at address 0x");
        Serial.println(MPU_addrs_hw[b], HEX);
      }
      delay(10);  // Small delay between sensor reads
    }

    // --- Read from Sensor 3 on the second I²C bus (Wire1) ---
    Wire1.beginTransmission(MPU_addr_wire1);
    Wire1.write(0x3B);  // Starting register for ACCEL_XOUT_H
    Wire1.endTransmission(false);
    Wire1.requestFrom(MPU_addr_wire1, 14, true);  // Read 14 bytes

    if (Wire1.available() == 14) {
      rawAcX[2] = Wire1.read() << 8 | Wire1.read();
      rawAcY[2] = Wire1.read() << 8 | Wire1.read();
      rawAcZ[2] = Wire1.read() << 8 | Wire1.read();
      rawTmp[2] = Wire1.read() << 8 | Wire1.read();
      rawGyX[2] = Wire1.read() << 8 | Wire1.read();
      rawGyY[2] = Wire1.read() << 8 | Wire1.read();
      rawGyZ[2] = Wire1.read() << 8 | Wire1.read();

      AcX[2] = rawAcX[2] / 16384.0;
      AcY[2] = rawAcY[2] / 16384.0;
      AcZ[2] = rawAcZ[2] / 16384.0;
      Tmp[2] = rawTmp[2] / 340.0 + 36.53;
      GyX[2] = rawGyX[2] / 131.0;
      GyY[2] = rawGyY[2] / 131.0;
      GyZ[2] = rawGyZ[2] / 131.0;

      Serial.print("Sensor 3 -> AcX: ");
      Serial.print(AcX[2]);
      Serial.print(" AcY: ");
      Serial.print(AcY[2]);
      Serial.print(" AcZ: ");
      Serial.print(AcZ[2]);
      Serial.print(" | ");
    } else {
      Serial.print("Error: Read failed for sensor on Wire1 at address 0x");
      Serial.println(MPU_addr_wire1, HEX);
    }
    
    Serial.println();
    delay(500);
  }
}
