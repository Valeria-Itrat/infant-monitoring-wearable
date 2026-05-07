import torch
import torch.nn as nn
import librosa
import time
import numpy as np
from collections import deque
from config import sr,window_samp,n_mels,hop_len,audio_buffer,state_lock

class CryCNN(nn.Module):
    def __init__(self):
        super(CryCNN, self).__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d((2, 2)),

            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d((2, 2)),

            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1))
        )

        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(128, 1),
        )

    def forward(self, x):
        x = self.conv(x)
        x = self.fc(x)
        return x

model = CryCNN()
model.load_state_dict(torch.load("model_weights.pth", map_location="cpu"))
model.eval()
             
#window_samp = int(sr * window_sec)
#audio_buffer = deque(maxlen=window_samp)
#last_inference = 0

def audio_proc(buffer_samp):
    """
    mel spectogram + clasificación
    voy agregando al buffer las nuevas muestras que llegan del XIAO
    """
    #global last_inference

    for s in buffer_samp:
        audio_buffer.append(s)

    if len(audio_buffer) < window_samp:
        return None
    #if time.time() - last_inference < 1.0:
    #    return None    
    #last_inference = time.time()
    y = np.array(audio_buffer, dtype=np.float32) / 32768.0 

    mel = librosa.feature.melspectrogram(
            y=y, sr=sr, n_mels=n_mels, hop_length=hop_len
        )
    mel_db = librosa.power_to_db(mel, ref=np.max)
    mel_db = (mel_db - mel_db.mean()) / (mel_db.std() + 1e-10)
    mel_tensor = torch.tensor(mel_db).unsqueeze(0).unsqueeze(0).float()

    with torch.no_grad():
        output = model(mel_tensor)
        prob = torch.sigmoid(output).item()

    return prob

latest_audio_prob = 0

def infer_audio():
    """Procesa audio_buffer cuando ya está lleno."""
    global latest_audio_prob

    if len(audio_buffer) < window_samp:
        return  # no hay ventana completa

    y = np.array(audio_buffer, dtype=np.float32) / 32768.0

    mel = librosa.feature.melspectrogram(
        y=y, sr=sr, n_mels=n_mels, hop_length=hop_len
    )
    mel_db = librosa.power_to_db(mel, ref=np.max)
    mel_db = (mel_db - mel_db.mean()) / (mel_db.std() + 1e-10)

    mel_tensor = torch.tensor(mel_db).unsqueeze(0).unsqueeze(0).float()

    with torch.no_grad():
        prob = torch.sigmoid(model(mel_tensor)).item()

    with state_lock:
        latest_audio_prob = prob