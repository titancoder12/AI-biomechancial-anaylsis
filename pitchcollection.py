import serial
import time
import serial.tools.list_ports
import re
import pandas as pd
import glob

# Adjusted baud rate for proper communication
arduino_port = "/dev/ttyACM0"
baud_rate = 115200  # Corrected baud rate to match the Arduino
acc_threshold = 1
ser = serial.Serial(arduino_port, baud_rate, timeout=1)
motionless_threshold = 25
sliding_window_length = 100

def detect_pitch():

    time.sleep(2)

    # Send the "Start" command once
    ser.write("connect".encode('utf-8'))

    if ser.readline().decode('utf-8') == "connected":
        print("connected")

    pitch = []
    #sliding_window = []
    start_time = 0
    end_time = 0
    recording_pitch = False
    motionless_period = 0
    try:
        i = 0

        while True:
            #ser.write("Start".encode('utf-8'))
            i += 1
            #print(i)
            if ser.in_waiting > 0:
                #print("A")
                message = ser.readline().decode('utf-8') #.strip()  # Use strip() to remove any unwanted newline characters
                Acx0, Acy0, Acz0, Gcx0, Gcy0, Gcz0, Acx1, Acy1, Acz1, Gcx1, Gcy1, Gcz1 = extract(message)
                
                #print("B")
                if abs(Acx0) > acc_threshold or Acy0 > abs(acc_threshold) or Acz0 > abs(acc_threshold) or Acx1 > abs(acc_threshold) or Acy1 > abs(acc_threshold) or Acz1 > abs(acc_threshold):
                    recording_pitch = True
                    start_time = time.time()

                if recording_pitch:
                    end_time = time.time()
                    pitch.append({"Timestamp": end_time - start_time,
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

                    if all(abs(val) < acc_threshold for val in (Acx0, Acy0, Acz0, Acx1, Acy1, Acz1)):
                        motionless_period += 1
                    else:
                        motionless_period = 0  # Reset when motion resumes

                    if motionless_period >= motionless_threshold:
                        pitch_df = pd.DataFrame(pitch)
                        filename = create_file_name()
                        pitch_df.to_csv("./pitches/" + filename)
                        pitch = []
                        start_time = 0
                        end_time = 0
                        recording_pitch = False
                        motionless_period = 0
                
                #print((Acx0, Acy0, Acz0))
                #print(message)   
                #print(pitch)
    except KeyboardInterrupt:
        print("exiting...")

    finally:
        ser.write("disconnect".encode('utf-8'))
        ser.close()

def extract(message):
    l = []
    for t in message.split():
        try:
            n = re.sub(r"[01](AcX|AcY|AcZ|GyX|GyY|GyZ):", "", t)
            l.append(float(n))
        except ValueError:
            pass
    return tuple(l) if len(l) == 12 else (0,) * 12  # Ensure all values exist

def create_file_name():
    print("Creating file.")
    filenamenumbers = []
    for file in glob.glob("./pitches/*.csv"):  # Corrected path to CSV files
        print(file)
        filenamenumbers.append(int(re.findall(r'\d+', file)[0]))  # Safely extract numbers from filenames
    if filenamenumbers == []:
        num = 0
    else:
        max_num = max(filenamenumbers)
        num = max_num + 1
    
    print(str(num) + "\n\n\n\n")
    return "pitch_" + str(num) + ".csv"  # Adding .csv extension

detect_pitch()
