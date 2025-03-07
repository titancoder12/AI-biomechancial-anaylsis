import serial
import time
import serial.tools.list_ports
import re
import pandas as pd
import glob
from bleak import BleakClient
import asyncio
import struct

# Hardware settings

#arduino_port = "/dev/ttyACM0" # Linux
arduino_port = "/dev/cu.usbmodem14301" # Mac
#arduino_port = "/dev/COM3" # Windows

baud_rate = 115200  
ADDRESS = "F63F8735-29EA-2F5E-8653-DF2C1463A90B"  # Address of the BLE device
UUID_X = "180A"
UUIDS = ["0001", "0002", "0003"] 

files_created = []
pitches_created = 0

# Data collection settings
acc_start_threshold = 14
acc_stop_threshold = 4
#ser = serial.Serial(arduino_port, baud_rate, timeout=1)
motionless_threshold = 25
sliding_window_length = 100

imu_data = {"0001": "", "0002": "", "0003": ""}  # Store latest BLE data

# BLE notification handler
def notification_handler(uuid):
    async def callback(sender, data):
        imu_data[uuid] = data.decode("utf-8")
    return callback

# Detects the pitch, saves it to a CSV file
async def detect_pitch():

    print("Access recorded pitches at /pitches in the current directory.")
    print("Press Ctrl+C to exit.\n")

    #time.sleep(2)

    # Initialize variables
    pitch = []
    sliding_window = []
    recording_pitch = False
    motionless_period = 0

    global pitches_created

    # Start collecting data
    async with BleakClient(ADDRESS) as client:

        tasks = [client.start_notify(uuid, notification_handler(uuid)) for uuid in UUIDS]
        await asyncio.gather(*tasks)
        
        while True:
            await client.connect()
            message = f"{imu_data['0001']} {imu_data['0002']} {imu_data['0003']}"

            #print(extract(message))

            Acx0, Acy0, Acz0, Gyx0, Gyy0, Gyz0, Acx1, Acy1, Acz1, Gyx1, Gyy1, Gyz1, Acx2, Acy2, Acz2, Gyx2, Gyy2, Gyz2 = extract(message)
            
            print(message)

            datapoint = {"Timestamp": time.time(),
                        "Acx0": Acx0,
                        "Acy0": Acy0,
                        "Acz0": Acz0,
                        "Gyx0": Gyx0,
                        "Gyy0": Gyy0,
                        "Gyz0": Gyz0,
                        "Acx1": Acx1,
                        "Acy1": Acy1,
                        "Acz1": Acz1,
                        "Gyx1": Gyx1,
                        "Gyy1": Gyy1,
                        "Gyz1": Gyz1,
                        "Acx2": Acx2,
                        "Acy2": Acy2,
                        "Acz2": Acz2,
                        "Gyx2": Gyx2,
                        "Gyy2": Gyy2,
                        "Gyz2": Gyz2
                        }

            # Sliding window is used to store the data before the pitch is detected to get complete pitch data.
            
            # Variable makes sure the data is not recorded in duplicate.
            rcbsliding = False

            if recording_pitch == False:
                rcbsliding = True
                sliding_window.append(datapoint)
                    
            # If the sliding window is full, remove the first element and add the new element.
            if len(sliding_window) == sliding_window_length+1:
                sliding_window.pop(0)
            
            # Pitch recording
            # If the acceleration is greater than the threshold, start recording the pitch.
            if any(abs(val) >= acc_start_threshold for val in (datapoint["Acx0"], datapoint["Acy0"], datapoint["Acz0"], datapoint["Acx1"], datapoint["Acy1"], datapoint["Acz1"], datapoint["Acx2"], datapoint["Acy2"], datapoint["Acz2"],)) and recording_pitch==False:
                print("-------- Pitch detected --------")
                recording_pitch = True
            
            # Only record the pitch if the sliding window has not already recorded the data.
            if recording_pitch and not rcbsliding:
                pitch.append(datapoint)

                # If the acceleration is less than the stop threshold, stop recording the pitch.
                if all(abs(val) <= acc_stop_threshold for val in (Acx0-sliding_window[-1]["Acx0"], Acy0-sliding_window[-1]["Acy0"], Acz0-sliding_window[-1]["Acz0"], Acx1-sliding_window[-1]["Acx1"], Acy1-sliding_window[-1]["Acy1"], Acz1-sliding_window[-1]["Acz1"], Acx2-sliding_window[-1]["Acx2"], Acy2-sliding_window[-1]["Acy2"], Acz2-sliding_window[-1]["Acz2"],)):
                    motionless_period += 1
                else:
                    motionless_period = 0  # Reset when motion resumes

                savefile = True

                # Save pitch data after pitch finish detected
                if motionless_period >= motionless_threshold:
                    print("Sliding window samples:"+str(len(sliding_window)))
                    print("Pitch motion samples:"+str(len(pitch)))
                    print("Total samples:"+str(len(sliding_window)+len(pitch)))

                    complete_pitch = sliding_window + pitch
                    speed = input("Enter speed of pitch (mph) [OV to override]: ")
                    if speed == "OV":
                        print("Pitch overrided. Not saving.")
                        print()
                        savefile = False

                    if savefile == True:
                        # Save pitch data to CSV file
                        pitch_df = pd.DataFrame(complete_pitch)
                        pitch_df["speed_mph"] = speed
                        filename = create_file_name()
                        pitch_df.to_csv("./pitches/" + filename)

                        pitches_created += 1

                    # Reset variables
                    pitch = []
                    rcbsliding = False
                    recording_pitch = False
                    motionless_period = 0
                    sliding_window = []


# Extracts data from the serial
def extract(message):
    l = []
    for t in message.split():
        try:
            n = re.sub(r"[012](AcX|AcY|AcZ|GyX|GyY|GyZ|):", "", t)
            l.append(float(n))
        except ValueError:
            pass
    return tuple(l) if len(l) == 18 else (0,) * 18  # Ensure all values exist

# Creates a file name based on existing files in the directory
def create_file_name():
    #print("Creating file...")
    filenamenumbers = []
    for file in glob.glob("./pitches/*.csv"):  # Corrected path to CSV files
        #print(file)
        filenamenumbers.append(int(re.findall(r'\d+', file)[0]))  # Safely extract numbers from filenames
    if filenamenumbers == []:
        num = 0
    else:
        max_num = max(filenamenumbers)
        num = max_num + 1
    
    print("Created file pitch_"+str(num)+".csv" + "\n\n")
    files_created.append(f"{num}.csv")
    return "pitch_" + str(num) + ".csv"  # Adding .csv extension

# Initiate the pitch detection
try:
    asyncio.run(detect_pitch())
except KeyboardInterrupt or TracebackError:
    print(f"\n\nCreated {pitches_created} {'pitch' if pitches_created == 1 else 'pitches'}: {files_created}")
    print("Exiting...")