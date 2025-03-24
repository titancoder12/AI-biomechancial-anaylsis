import time
import serial.tools.list_ports
import re
import pandas as pd
import glob
from bleak import BleakClient
import asyncio
import sys
import select
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.layers import Bidirectional
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import Input, LSTM, Dense, Bidirectional, Dropout, Masking
from sklearn.preprocessing import StandardScaler
import numpy as np

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
imu_data = {"0001": "", "0002": ""}  # Store latest BLE data

"""def load_model():
    input_layer = Input(shape=(414, 13))
    x = Masking(mask_value=0.)(input_layer)
    x = Bidirectional(LSTM(128, return_sequences=True))(x)
    x = Dropout(0.3)(x)
    x = Bidirectional(LSTM(64, return_sequences=False))(x)
    x = Dropout(0.3)(x)
    x = Dense(32, activation='relu')(x)
    output = Dense(1)(x)

    model = Model(inputs=input_layer, outputs=output)
    model = lm("speed_prediction/model.weights.h5")
    return model"""
model = load_model("pitchprediction.keras")

# BLE notification handler
def notification_handler(uuid):
    async def callback(sender, data):
        imu_data[uuid] = data.decode("utf-8")
    return callback

# Check for enter keystroke
def check_for_enter():
    global stop
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:  # Check if input is available
        if sys.stdin.read(1) == "\n":  # Read 1 character (Enter key)
            stop = True  # Stop recording
            return
        elif sys.stdin.read(1) == "command":
            stop = True
            return
        
# Extracts data from the serial
def extract(message):
    l = []
    for t in message.split():
        try:
            n = re.sub(r"[01](AcX|AcY|AcZ|GyX|GyY|GyZ|):", "", t)
            l.append(float(n))
        except ValueError:
            pass
    return tuple(l) if len(l) == 12 else (0,) * 12  # Ensure all values exist

# Runs model with preprocessing of data
def run_model(data):
    # Data to Dataframe
    df = pd.DataFrame(data)

    # Normalize
    scaler = StandardScaler()
    scaler.fit(df)
    imu_scaled = scaler.transform(df)
    
    # Pad
    imu_scaled_pad = pad_sequences([imu_scaled], maxlen=414, padding="post", dtype='float32')

    # Predict
    prediction = model.predict(imu_scaled_pad)
    return prediction[0][0]



# Detects the pitch, saves it to a CSV file
async def detect_pitch():

    # Initialize variables
    pitch = []
    last_pitch = {}
    past_samples = []
    not_updated = 0
    global pitches_created
    global stop
    global stuck
    stuck = False

    # Start collecting data
    async with BleakClient(ADDRESS) as client:
        tasks = [client.start_notify(uuid, notification_handler(uuid)) for uuid in UUIDS]
        await asyncio.gather(*tasks)

        while True:
            if stuck:
                stuck=False
                break

            print("Connected.")
            input("Press enter to start recording pitch. ")    
            stop=False
            
            print("Recording pitch...")
            # Keep checking until enter pressed
            while not stop and not stuck:
                #print(".")
                check_for_enter()
                await asyncio.sleep(0.001)
                message = f"{imu_data['0001']} {imu_data['0002']}"

                extracted = extract(message)

                Acx0, Acy0, Acz0, Gyx0, Gyy0, Gyz0, Acx1, Acy1, Acz1, Gyx1, Gyy1, Gyz1 = extracted

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
                if extracted != last_pitch:
                    pitch.append(datapoint)
                    print(message)
                    not_updated = 0
                else:
                    not_updated+=1
                #print(not_updated)

                if not_updated > 70:
                    print("\nIMUs stuck. Restarting BLE...\n")
                    stuck=True
                    not_updated = 0
                    break
                last_pitch = extracted

            if not stuck:
                print("Processing pitch...")
                print("Predicted speed: " + str(run_model(pitch)))
            pitch = []

# Initiate the pitch detection
try:
    print("Access recorded pitches at /pitches in the current directory.")
    print("Press Ctrl+C to exit.\n")
    print("Connecting to BLE device...")
    while True:
        asyncio.run(detect_pitch())
except KeyboardInterrupt or TracebackError or pynput._util.AbstractListener.StopException:
    print("Exiting...")