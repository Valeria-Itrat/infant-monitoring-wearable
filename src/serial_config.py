import threading
import numpy as np
import time
import serial

from config import (
    audio_buffer,      # deque compartido
    #latest_audio_prob,
    #latest_imu,
    #status,
    state_lock
)
from audio_proc import infer_audio
from config import SERIAL_PORT, BAUD_RATE 

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE)
    status = "Connected"
except:
    status = "Not connected"

latest_imu = {"label": "unknown", "prob": 0.0}
thread_initialized = False

def read_serial():
    global status, latest_imu

    collecting_audio = False
    block = []
    last_inference_time = time.time()

    while True:
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            status = "Receiving"

            if line.startswith("<IMU_PRED>"):
                label, prob = (
                    line.replace("<IMU_PRED>", "")
                        .replace("</IMU_PRED>", "")
                        .split(",")
                )
                with state_lock:
                    latest_imu["label"] = label
                    latest_imu["prob"] = float(prob)
                continue
            if line == "<AUDIO_BLOCK>":
                collecting_audio = True
                block = []
                continue
            if line == "<END_AUDIO_BLOCK>":
                collecting_audio = False

                samples = np.array(block, dtype=np.int16)

                # buffer global
                for s in samples:
                    audio_buffer.append(s)

                # solo hago inferencia 0.8s
                if time.time() - last_inference_time >= 0.8:
                    infer_audio()
                    last_inference_time = time.time()
                continue

            if collecting_audio:
                try:
                    block.append(int(line))
                except:
                    pass

        except:
            status = "Disconnected"
            time.sleep(0.1)

if not thread_initialized:
    threading.Thread(target=read_serial, daemon=True).start()
    thread_initialized = True

print("READING...")

def send_start():
    ser.write(b"start\n")
    print(">> Sent START to device")

def send_stop():
    ser.write(b"stop\n")
    print(">> Sent STOP to device")