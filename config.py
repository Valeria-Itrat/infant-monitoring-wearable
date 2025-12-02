"""
Configuración generál
"""
from collections import deque
import threading

SERIAL_PORT = "COM7"
BAUD_RATE = 230400

hop_len = 1024
n_mels = 64
sr = 16000
window_sec = 2     

window_samp = int(sr * window_sec)
audio_buffer = deque(maxlen=window_samp)

state_lock = threading.Lock()

def vote_cry(history, N=3, threshold=0.65):
    if len(history) < N:
        return False 
    last_probs = [float(ev["Cry Prob"]) for ev in history[-N:]]
    votes = sum(p > threshold for p in last_probs)
    return votes >= N #// 2 + 1))   
