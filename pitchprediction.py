import time
import re
import pandas as pd
from bleak import BleakClient
import asyncio
import sys
import select
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import get_custom_objects
from tensorflow.keras.layers import (
    Input, Bidirectional, LSTM, Dense, Dropout, Masking, Flatten,
    RepeatVector, Multiply, Permute, Activation, Lambda
)
from sklearn.preprocessing import StandardScaler
import numpy as np
from ahrs.filters import Complementary
import tensorflow as tf
import keras

# Hardware settings
arduino_port = "/dev/cu.usbmodem14301" # Mac
#arduino_port = "/dev/ttyACM0" # Linux
#arduino_port = "/dev/COM3" # Windows
baud_rate = 115200  
ADDRESS = "FF09F8C5-BEAA-C5D6-CE44-82876D5CB88B"  # Address of the BLE device
UUID_X = "180A"
UUIDS = ["0001", "0002"] 

# Initialize variables
files_created = []
pitches_created = 0
stop = False
stuck = False
imu_data = {"0001": "", "0002": ""}

from tensorflow.keras.layers import Layer

class NotEqual(tf.keras.layers.Layer):
    def call(self, inputs):
        a, b = inputs
        return tf.math.not_equal(a, b)

import tensorflow as tf
from tensorflow.keras.layers import Layer

class Any(Layer):
    def __init__(self, axis=-1, keepdims=False, **kwargs):
        super().__init__(**kwargs)
        self.axis = axis
        self.keepdims = keepdims

    def call(self, inputs):
        return tf.reduce_any(inputs, axis=self.axis, keepdims=self.keepdims)

    def get_config(self):
        config = super().get_config()
        config.update({
            'axis': self.axis,
            'keepdims': self.keepdims
        })
        return config

from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Masking, Bidirectional, LSTM, Dense, Dropout
from tensorflow.keras.layers import Flatten, RepeatVector, Permute, Multiply
import tensorflow.keras.backend as K
import tensorflow as tf

# Custom attention layer (instead of Lambda)
class CustomAttention(tf.keras.layers.Layer):
    def __init__(self, temperature=0.7):
        super().__init__()
        self.temperature = temperature
        self.dense = Dense(1)
        self.flatten = Flatten()
    
    def call(self, inputs):
        attention = self.dense(inputs)
        attention = self.flatten(attention)
        attention = attention / self.temperature
        attention_weights = tf.nn.softmax(attention, name='attention_weights')
        attention_weights = RepeatVector(inputs.shape[-1])(attention_weights)
        attention_weights = Permute([2, 1])(attention_weights)
        output = inputs * attention_weights
        output = tf.reduce_sum(output, axis=1)
        return output

# Custom attention mechanism
def attention_layer(inputs, temperature=0.7):
    attention = Dense(1)(inputs)
    attention = Flatten()(attention)
    attention = Lambda(lambda x: x / temperature)(attention)  # temperature scaling
    attention_weights = Activation('softmax', name='attention_weights')(attention)
    attention_repeated = RepeatVector(inputs.shape[-1])(attention_weights)
    attention_permuted = Permute([2, 1])(attention_repeated)
    output_attention = Multiply()([inputs, attention_permuted])
    output_attention = Lambda(lambda x: K.sum(x, axis=1))(output_attention)
    return output_attention, attention_weights

# Replace this with your exact number of timesteps and features
max_length = 414  # sequence length
num_features = 20

input_layer = Input(shape=(max_length, 20))
#input_layer = Input(shape=(max_length, 4))
masked = Masking(mask_value=0.0)(input_layer)
bilstm = Bidirectional(LSTM(64, return_sequences=True))(masked)
bilstm = Bidirectional(LSTM(32, return_sequences=True))(masked)
#bilstm2 = Bidirectional(LSTM(64, return_sequences=True))(bilstm)
attention_output, attention_weights = attention_layer(bilstm)
dense = Dense(64, activation='relu')(attention_output)
dense = Dense(32, activation='relu')(dense)
dropout = Dropout(0.3)(dense)
#dense2 = Dense(32, activation='relu')(dropout)
output = Dense(1, name="output_layer")(dense)

model = Model(inputs=input_layer, outputs=[output, attention_weights])

model.compile(
    loss={'output_layer': 'mse', 'attention_weights': None},
    optimizer='adam',
    metrics={'output_layer': ['mae', 'mse']}
)

model.load_weights("bestmodel.h5")

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

def preprocessing(data):
#print(f"Processing {file}")
    df = pd(data)

    # Get acceleration and gyroscope data for both sensors
    pitch = df[['Acx0', 'Acy0', 'Acz0', 'Gyx0', 'Gyy0', 'Gyz0',
                'Acx1', 'Acy1', 'Acz1', 'Gyx1', 'Gyy1', 'Gyz1']].values

    acc0 = pitch[:, 0:3]
    gyr0 = np.deg2rad(pitch[:, 3:6])
    acc1 = pitch[:, 6:9]
    gyr1 = np.deg2rad(pitch[:, 9:12])

    # Initialize filters
    comp0 = Complementary()
    comp1 = Complementary()
    q0 = np.array([1.0, 0.0, 0.0, 0.0])
    q1 = np.array([1.0, 0.0, 0.0, 0.0])
    quats0 = []
    quats1 = []

    # Process each timestep
    for a, g in zip(acc0, gyr0):
        q0 = comp0.update(q=q0, acc=a, gyr=g)
        quats0.append(q0)

    for a, g in zip(acc1, gyr1):
        q1 = comp1.update(q=q1, acc=a, gyr=g)
        quats1.append(q1)

    quats0 = np.array(quats0)
    quats1 = np.array(quats1)

    features = np.hstack((acc0, gyr0, acc1, gyr1, quats0, quats1))

    num_features = 20

    scaler = StandardScaler()

    # Reshape to 2D for the scaler: (timesteps * 1, num_features)
    X_pitch_reshaped = features.reshape(-1, num_features)

    # Fit and transform just this one pitch
    X_pitch_scaled = scaler.fit_transform(X_pitch_reshaped)

    # Reshape back to original shape (optional here since we kept timesteps, but shown for clarity)
    X_pitch_scaled = X_pitch_scaled.reshape(features.shape)
    
    return features

# Runs model with preprocessing of data
def run_model(data):
    # Preprocess data
    preprocessed = preprocessing(data)

    # Pad
    imu_scaled_pad = pad_sequences([preprocessed], maxlen=414, padding="post", dtype='float32')

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
                print("Predicted speed: " + str(run_model(pitch)) + "mph")
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