import time
import re
import pandas as pd
from bleak import BleakClient
import asyncio
import sys
import select
from tensorflow import keras
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import load_model
from tensorflow.keras.layers import (
    Input, Bidirectional, LSTM, Dense, Dropout, Masking, Flatten,
    RepeatVector, Multiply, Permute, Activation, Lambda
)
from sklearn.preprocessing import StandardScaler
import numpy as np
from ahrs.filters import Complementary
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras import backend as K
from keras.utils import get_custom_objects
from tensorflow import not_equal
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import joblib

# Hardware settings
arduino_port = "/dev/cu.usbmodem14301" # Mac
#arduino_port = "/dev/ttyACM0" # Linux
#arduino_port = "/dev/COM3" # Windows
baud_rate = 115200  
ADDRESS = "FF09F8C5-BEAA-C5D6-CE44-82876D5CB88B"  # Address of the BLE device
UUID_X = "180A"
UUIDS = ["0001", "0002"] 
model = None

# Initialize variables
files_created = []
pitches_created = 0
stop = False
stuck = False
imu_data = {"0001": "", "0002": ""}

# Custom attention mechanism
def attention_layer(inputs, temperature=0.7):
    attention = Dense(1)(inputs)
    attention = Flatten()(attention)
    attention = Lambda(lambda x: x / temperature)(attention)  # temperature scaling
    attention_weights = Activation('softmax', name='attention_weights')(attention)
    attention_repeated = RepeatVector(inputs.shape[-1])(attention_weights)
    attention_permuted = Permute([2, 1])(attention_repeated)
    output_attention = Multiply()([inputs, attention_permuted])
    output_attention = Lambda(lambda x: K.sum(x, axis=1), output_shape=lambda input_shape: (input_shape[0], input_shape[2]))(output_attention)
    return output_attention, attention_weights

def load_model():
    global model
    max_length = 414 
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
    model.load_weights("velo_predictor.keras")

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
    df = pd.DataFrame(data)

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

    # Reshape to 2D for the scaler: (timesteps * 1, num_features)
    X_pitch_reshaped = features.reshape(-1, num_features)

    scaler = joblib.load('scaler.pkl')
    X_pitch_scaled = scaler.transform(X_pitch_reshaped)

    # Reshape back to original shape (optional here since we kept timesteps, but shown for clarity)
    X_pitch_scaled = X_pitch_scaled.reshape(features.shape)

    imu_scaled_pad = pad_sequences([X_pitch_scaled], maxlen=414, padding="post", dtype='float32')
    
    return imu_scaled_pad

# Runs model with preprocessing of data
def run_model(data):
    global model
    return model.predict(data)

def plot_attention_weights(att_weights, pitch_pred, features):
    timesteps = features.shape[0]
    attention = np.squeeze(att_weights)  # remove any extra dimensions (e.g. (1, 1, 241) → (241,))
    attention = attention[:timesteps]  # ensure same length

    # Normalize
    normalized_attention = (attention - np.min(attention)) / (np.max(attention) - np.min(attention) + 1e-8)

    # Multiply for visualization
    attended_data = features * normalized_attention[:, np.newaxis]  # (timesteps, 20)

    plt.figure(figsize=(14, 6))
    sns.heatmap(attended_data.T, cmap='viridis', xticklabels=10, yticklabels=[
        'Shoulder-Acx', 'Shoulder-Acy', 'Shoulder-Acz', 'Shoulder-Gyx', 'Shoulder-Gyy', 'Shoulder-Gyz',
        'Hip-Acx', 'Hip-Acy', 'Hip-Acz', 'Hip-Gyx', 'Hip-Gyy', 'Hip-Gyz',
        'S0Q0', 'S0Q1', 'S0Q2', 'S0Q3', 'S1Q0', 'S1Q1', 'S1Q2', 'S1Q3',
    ])
    plt.title(f"Attention-Weighted Sensor Data (Predicted Speed: {float(pitch_pred[0]):.1f} mph)")
    plt.xlabel("Time Step")
    plt.ylabel("Sensor Channels")
    plt.tight_layout()
    plt.show(block=True)

def plot_dual_motion_with_attention(features, attention_weights, title="Motion vs Attention (Shoulder + Hip)"):
    import matplotlib.pyplot as plt
    import numpy as np

    # Trim attention to match timesteps
    attention = np.squeeze(attention_weights)[:features.shape[0]]  # (timesteps,)

    # Extract acceleration data
    acc_shoulder = features[:, 0:3]  # Acx0, Acy0, Acz0
    acc_hip = features[:, 6:9]       # Acx1, Acy1, Acz1

    # Compute magnitudes
    shoulder_mag = np.linalg.norm(acc_shoulder, axis=1)
    hip_mag = np.linalg.norm(acc_hip, axis=1)

    # Normalize for overlay
    shoulder_mag_norm = (shoulder_mag - shoulder_mag.min()) / (shoulder_mag.max() - shoulder_mag.min() + 1e-8)
    hip_mag_norm = (hip_mag - hip_mag.min()) / (hip_mag.max() - hip_mag.min() + 1e-8)
    attention_norm = (attention - attention.min()) / (attention.max() - attention.min() + 1e-8)

    # Plot
    plt.figure(figsize=(14, 5))
    plt.plot(shoulder_mag_norm, label="Shoulder Acc Magnitude", color='blue')
    plt.plot(hip_mag_norm, label="Hip Acc Magnitude", color='green')
    plt.plot(attention_norm, label="Attention Weights", color='red', linestyle='--', alpha=0.7)

    plt.xlabel("Timestep")
    plt.ylabel("Normalized Value")
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_attention_heatmap_by_sensor(features, attention_weights, prediction):
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np

    attention = np.squeeze(attention_weights)[:features.shape[0]]  # (timesteps,)
    attention = (attention - attention.min()) / (attention.max() - attention.min() + 1e-8)

    # Apply attention weights
    attended = features * attention[:, np.newaxis]

    # Break out into shoulder vs hip feature groups
    shoulder_features = attended[:, :6].T  # Acx0–Gyz0
    hip_features = attended[:, 6:12].T     # Acx1–Gyz1

    fig, axs = plt.subplots(2, 1, figsize=(14, 7), sharex=True)

    sns.heatmap(shoulder_features, cmap="Blues", ax=axs[0], xticklabels=10,
                yticklabels=['S-Acx', 'S-Acy', 'S-Acz', 'S-Gyx', 'S-Gyy', 'S-Gyz'])
    axs[0].set_title("Attention-Weighted Shoulder Features")

    sns.heatmap(hip_features, cmap="Greens", ax=axs[1], xticklabels=10,
                yticklabels=['H-Acx', 'H-Acy', 'H-Acz', 'H-Gyx', 'H-Gyy', 'H-Gyz'])
    axs[1].set_title("Attention-Weighted Hip Features")

    plt.suptitle(f"Predicted Speed: {prediction:.1f} mph", fontsize=14)
    plt.xlabel("Time Step")
    plt.tight_layout()
    plt.show()

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
                print("Pitch length: " + str(len(pitch)) + " samples")
                preprocessed = preprocessing(pitch)
                prediction, attention_weights = run_model(preprocessed)
                features = preprocessed[0, :, :]
 
                print("Predicted speed: " + str(prediction[0][0]) + "mph")
                plot_attention_weights(attention_weights, prediction, features)
                plot_dual_motion_with_attention(features, attention_weights)
                prediction = prediction[0][0]

            pitch = []

# Initiate the pitch detection
try:
    print("Access recorded pitches at /pitches in the current directory.")
    print("Press Ctrl+C to exit.\n")

    print("Loading model...")
    load_model()

    print("Connecting to BLE device...")
    while True:
        asyncio.run(detect_pitch())
except KeyboardInterrupt or TracebackError or pynput._util.AbstractListener.StopException:
    print("Exiting...")

