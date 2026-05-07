import streamlit as st
import numpy as np
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

import audio_proc
from serial_new import latest_imu, send_start, send_stop, status
from config import audio_buffer, state_lock

st.set_page_config(page_title="Infant Monitor", page_icon="🍼", layout="wide")

# STATIC CSS
st.markdown("""<style>
.big-status {
    font-size: 42px;
    font-weight: bold;
    text-align: center;
    padding: 20px;
    border-radius: 12px;
    margin: 15px 0;
}
.sleeping { background-color:#B4D7FF; color:#004488; }
.awake { background-color:#FFE5B4; color:#BB6600; }
.crying { background-color:#FFB4B4; color:#AA0000; }
.not-crying { background-color:#B4FFB4; color:#008800; }
</style>""", unsafe_allow_html=True)

# barra lateral
auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
interval_ms = st.sidebar.slider("Refresh every (ms)", 100, 2000, 1000)
refresh = auto_refresh
if st.sidebar.button("Start Device"):
    send_start()
    state = 'Started'
    refresh = auto_refresh

if st.sidebar.button("Stop Device"):
    send_stop()
    refresh = False
    state = 'Stoped'

if refresh:
    st_autorefresh(interval=interval_ms, key="refresh")

# secciones
st.title("🍼 Real-Time Infant Monitoring Dashboard")
st.markdown("---")

col1, col2 = st.columns(2)
sleep_placeholder = col1.empty()
cry_placeholder = col2.empty()

st.markdown("---")
m1, m2 = st.columns(2)
audio_metric = m2.empty()
imu_metric = m1.empty()

st.markdown("---")
m3, m4, m5 = st.columns(3)
time_metric  = m3.empty()
conn_metric  = m4.empty()
state_metric = m5.empty()

# lectura
with state_lock:
    imu_label = latest_imu["label"]
    imu_prob  = latest_imu["prob"]
    cry_prob   = audio_proc.latest_audio_prob

timestamp = datetime.now().strftime("%H:%M:%S")

# interpretación
is_crying = cry_prob > 0.65
is_awake = (imu_label.lower() == "moving")

# display
if is_crying: 
    cry_html = '<div class="big-status crying">😭 CRYING</div>' 
    sleep_html = '<div class="big-status crying">😭 AWAKE</div>' 
else:
    cry_html = '<div class="big-status not-crying">😊 NOT CRYING</div>'
    if is_awake:
        sleep_html = '<div class="big-status awake">😊 AWAKE</div>'
    else: 
        sleep_html = '<div class="big-status sleeping">😴 SLEEPING</div>'
        
cry_placeholder.markdown(cry_html, unsafe_allow_html=True)   
sleep_placeholder.markdown(sleep_html, unsafe_allow_html=True)

# metricas
audio_metric.metric("Cry Probability", f"{cry_prob:.2f}")
imu_metric.metric("IMU State", f"{imu_label} ({imu_prob:.2f})")
time_metric.metric("Last Update", timestamp)
conn_metric.metric("System Status", status)
try:
    state_metric.metric("Device", state)
except:
    state_metric.metric("Device", "Started")

# plot de audio
if len(audio_buffer) > 200:
    wf = np.array(audio_buffer)[-800:]  # mostrar últimos 800 samples
    st.line_chart(wf)
