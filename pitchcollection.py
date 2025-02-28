import serial
import time
import serial.tools.list_ports
import re
import pandas as pd
import glob
from bleak import BleakClient
import asyncio

# Hardware settings
arduino_port = "/dev/ttyACM0"
baud_rate = 115200  
"""ADDRESS = "f4:12:fa:6f:7c:c1"  # Address of the BLE device
UUID_X = "00002A19-0000-1000-8000-00805F9B34FB"

async def read_imu():
    async with BleakClient(ADDRESS) as client:
        x = await client.read_gatt_char(UUID_X)
        print(x)"""

pitches_created = 0

# Data collection settings
acc_start_threshold = 1
acc_stop_threshold = 1
ser = serial.Serial(arduino_port, baud_rate, timeout=1)
motionless_threshold = 25
sliding_window_length = 100

# Detects the pitch, saves it to a CSV file
def detect_pitch():
    print("Connecting...")
    
    # Connect to Arduino
    ser.write("connect".encode('utf-8'))

    # Confirm connectioon
    if ser.readline().decode('utf-8') == "connected":
        print("connected")

    # Initialize variables
    pitch = []
    sliding_window = []
    recording_pitch = False
    motionless_period = 0

    try:
        # Start collecting data
        while True:
            # Only enter if there is data in the buffer
            if ser.in_waiting > 0:
                
                # Read the data from the buffer
                message = ser.readline().decode('utf-8') #.strip() 
                print(message) 
                Acx0, Acy0, Acz0, Gcx0, Gcy0, Gcz0, Acx1, Acy1, Acz1, Gcx1, Gcy1, Gcz1 = extract(message)
                
                # Sliding window is used to store the data before the pitch is detected to get complete pitch data.
                
                # Variable makes sure the data is not recorded in duplicate.
                rcbsliding = False

                if len(sliding_window) < sliding_window_length and recording_pitch == False:
                    rcbsliding = True
                    sliding_window.append({"Timestamp": time.time(),
                                  "Acx0": Acx0,
                                  "Acy0": Acy0,
                                  "Acz0": Acz0,
                                  "Gcx0": Gcx0,
                                  "Gcy0": Gcy0,
                                  "Gcz0": Gcz0,
                                  "Acx1": Acx1,
                                  "Acy1": Acy1,
                                  "Acz1": Acz1,
                                  "Gcx1": Gcx1,
                                  "Gcy1": Gcy1,
                                  "Gcz1": Gcz1})
                
                # If the sliding window is full, remove the first element and add the new element.
                if len(sliding_window) == sliding_window_length+1:
                    sliding_window.pop(0)

                
                # Pitch recording
                # If the acceleration is greater than the threshold, start recording the pitch.
                if abs(Acx0) >= acc_start_threshold or Acy0 >= abs(acc_start_threshold) or Acz0 >= abs(acc_start_threshold) or Acx1 >= abs(acc_start_threshold) or Acy1 >= abs(acc_start_threshold) or Acz1 >= abs(acc_start_threshold):
                    recording_pitch = True
                    #start_time = time.time()
                
                # Only record the pitch if the sliding window has not already recorded the data.
                if recording_pitch and not rcbsliding:
                    pitch.append({"Timestamp": time.time(),
                                  "Acx0": Acx0,
                                  "Acy0": Acy0,
                                  "Acz0": Acz0,
                                  "Gcx0": Gcx0,
                                  "Gcy0": Gcy0,
                                  "Gcz0": Gcz0,
                                  "Acx1": Acx1,
                                  "Acy1": Acy1,
                                  "Acz1": Acz1,
                                  "Gcx1": Gcx1,
                                  "Gcy1": Gcy1,
                                  "Gcz1": Gcz1})

                    # If the acceleration is less than the stop threshold, stop recording the pitch.
                    if all(abs(val) <= acc_stop_threshold for val in (Acx0, Acy0, Acz0, Acx1, Acy1, Acz1)):
                        motionless_period += 1
                    else:
                        motionless_period = 0  # Reset when motion resumes

                    # Save pitch data after pitch finish detected
                    if motionless_period >= motionless_threshold:
                        print("Sliding window samples:"+str(len(sliding_window)))
                        print("Pitch motion samples:"+str(len(pitch)))
                        print("Total samples:"+str(len(sliding_window)+len(pitch)))

                        complete_pitch = sliding_window + pitch

                        # Save pitch data to CSV file
                        pitch_df = pd.DataFrame(complete_pitch)
                        filename = create_file_name()
                        pitch_df.to_csv("./pitches/" + filename)

                        pitches_created += 1

                        # Reset variables
                        pitch = []
                        recording_pitch = False
                        motionless_period = 0
    
    # Safely exit the program
    except KeyboardInterrupt:
        print("exiting...")
        print("Total pitches created: " + str(pitches_created))

    finally:
        # Safely disconnect from the Arduino
        ser.write("disconnect".encode('utf-8'))
        ser.close()

# Extracts data from the serial
def extract(message):
    l = []
    for t in message.split():
        try:
            n = re.sub(r"[01](AcX|AcY|AcZ|GyX|GyY|GyZ):", "", t)
            l.append(float(n))
        except ValueError:
            pass
    return tuple(l) if len(l) == 12 else (0,) * 12  # Ensure all values exist

# Creates a file name based on existing files in the directory
def create_file_name():
    print("Creating file.")
    filenamenumbers = []
    for file in glob.glob("./pitches/*.csv"):  # Corrected path to CSV files
        #print(file)
        filenamenumbers.append(int(re.findall(r'\d+', file)[0]))  # Safely extract numbers from filenames
    if filenamenumbers == []:
        num = 0
    else:
        max_num = max(filenamenumbers)
        num = max_num + 1
    
    print(str(num) + "\n\n\n\n")
    return "pitch_" + str(num) + ".csv"  # Adding .csv extension

# Initiate the pitch detection
detect_pitch()