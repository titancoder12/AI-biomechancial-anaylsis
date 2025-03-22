import serial
import time
import serial.tools.list_ports
import re
import pandas as pd
import glob
from bleak import BleakClient
import asyncio
import sys
import select
from copy import deepcopy

# Hardware settings
arduino_port = "/dev/cu.usbmodem14301" # Mac
#arduino_port = "/dev/ttyACM0" # Linux
#arduino_port = "/dev/COM3" # Windows
baud_rate = 115200  
ADDRESS = "BD78FA1F-370A-3A38-106C-4D7E34C4BA4C"  # Address of the BLE device
UUID_X = "180A"
UUIDS = ["0001", "0002"] 

# Initialize variables
files_created = []
pitches_created = 0
stop = False
stuck = False
imu_update_count = {"0001": 0, "0002": 0}
imu_data = {"0001": "", "0002": ""}  # Store latest BLE data

# BLE notification handler
def notification_handler(uuid):
    async def callback(sender, data):
        imu_data[uuid] = data.decode("utf-8")
        global imu_update_count
        imu_update_count[uuid] += 1
    return callback

# Check for enter keystroke
def check_for_enter():
    global stop
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:  # Check if input is available
        if sys.stdin.read(1) == "\n":  # Read 1 character (Enter key)
            stop = True  # Stop recording

# Extracts data from the serial
def extract(message):
    values = []
    for part in message.split():
        try:
            if ':' in part:
                values.append(float(part.split(':')[1]))
        except ValueError:
            pass
    return tuple(values) if len(values) == 12 else (0,) * 12

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

# Detects the pitch, saves it to a CSV file
async def detect_pitch():
    # Initialize variables
    pitch = []
    last_point = ()
    last2_point = ()
    last3_point = ()
    global pitches_created
    global stop
    global stuck
    stop=False
    stuck=False

    # Start collecting data
    async with BleakClient(ADDRESS) as client:
        tasks = [client.start_notify(uuid, notification_handler(uuid)) for uuid in UUIDS]
        await asyncio.gather(*tasks)

        while not stuck:
            input("Press enter to start recording pitch. ")    
            stop=False
            
            print("Recording pitch...")
            # Keep checking until enter pressed
            
            last_update_count = imu_update_count.copy()

            while not stop:
                check_for_enter()
                if imu_update_count == last_update_count:
                    await asyncio.sleep(0)  # Minimal yield only if no update
                    continue

                # Both updated — proceed
                last_update_count = {
                    "0001": imu_update_count["0001"],
                    "0002": imu_update_count["0002"]
                }

                message = f"{imu_data['0001']} {imu_data['0002']}"

                #print(".")

                datapoint_extract = extract(message)
                Acx0, Acy0, Acz0, Gyx0, Gyy0, Gyz0, Acx1, Acy1, Acz1, Gyx1, Gyy1, Gyz1 = datapoint_extract

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
                            }

                if datapoint_extract == last_point and last_point == last2_point:
                    print("Frozen IMU detected. Reconnecting...\n\n")
                    stop = True
                    stuck= True
                    pitch=[]
                    break

                pitch.append(datapoint)
                #last3_point = deepcopy(last2_point)
                last2_point = deepcopy(last_point)
                last_point = deepcopy(datapoint_extract)
            if not stuck:
                print("Total samples: "+str(len(pitch)))
                speed = input("Enter speed of pitch (mph) [OV to override]: ")
                if speed == "OV":
                    print("Pitch overrided. Not saving.")
                    print()
                elif speed.isdigit():
                    # Save pitch data to CSV file
                    pitch_df = pd.DataFrame(pitch)
                    pitch_df["speed_mph"] = speed

                    filename = create_file_name()
                    #df = pitch_df.drop_duplicates(subset=pitch_df.columns.difference(["Timestamp"]))
                    pitch_df.to_csv("./pitches/" + filename, index=False)
                    pitches_created += 1

                else:
                    print("Invalid speed. Not saving.")
                    print()
                pitch = []

# Initiate the pitch detection
try:
    print("Access recorded pitches at /pitches in the current directory.")
    print("Press Ctrl+C to exit.\n")
    while True:
        asyncio.run(detect_pitch())
except KeyboardInterrupt or TracebackError or pynput._util.AbstractListener.StopException:
    print(f"\n\nCreated {pitches_created} {'pitch' if pitches_created == 1 else 'pitches'}: {files_created}")
    print("Exiting...")