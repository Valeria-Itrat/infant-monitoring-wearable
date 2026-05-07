#include <Wire.h>
#include "LSM6DS3.h"
#include <PDM.h>
#include <valuih-project-1_inferencing.h>
#include "edge-impulse-sdk/dsp/numpy_types.h"

// ===== Buffer IMU =====
__attribute__((aligned(16)))
static float imu_buffer[EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE];

// ===== IMU =====
LSM6DS3 myIMU(I2C_MODE, 0x6A);

// ===== Audio =====
short audioBuffer[512];
volatile int samplesRead = 0;
volatile bool audioReady = false;

// ===== Flags =====
bool capturing = false;
unsigned long lastIMU = 0;


void setup() {
  Serial.begin(230400);
  while (!Serial);

  Serial.println("=== DEBUG MODE XIAO IMU + AUDIO ===");

  // --- IMU init ---
  if (myIMU.begin() != 0) {
    Serial.println("IMU INIT FAIL");
  } else {
    Serial.println("IMU OK");
  }

  Serial.print("RAW SAMPLES: ");
  Serial.println(EI_CLASSIFIER_RAW_SAMPLE_COUNT);

  Serial.print("DSP FRAME SIZE: ");
  Serial.println(EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE);

  // --- PDM init ---
  PDM.onReceive(onPDMdata);
  PDM.setGain(30);

  if (!PDM.begin(1, 16000)) {
    Serial.println("PDM INIT FAIL");
  } else {
    Serial.println("PDM OK");
  }

  Serial.println("READY - send 'start'");
}


void loop() {

  // ===== COMMANDS =====
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.equalsIgnoreCase("start")) {
      capturing = true;
      Serial.println("<CAPTURE_START>");
    } else if (cmd.equalsIgnoreCase("stop")) {
      capturing = false;
      Serial.println("<CAPTURE_STOP>");
    }
  }

  if (!capturing) return;

  unsigned long now = millis();

  // ============= IMU LOOP ==============
  if (now - lastIMU >= EI_CLASSIFIER_INTERVAL_MS) {
    lastIMU = now;

    static int imuIndex = 0;

    float ax = myIMU.readFloatAccelX();
    float ay = myIMU.readFloatAccelY();
    float az = myIMU.readFloatAccelZ();

    // ---- DEBUG IMU READ ----
    Serial.print("IMU read: ");
    Serial.print(ax); Serial.print(", ");
    Serial.print(ay); Serial.print(", ");
    Serial.println(az);

    int idx = imuIndex * 3;
    imu_buffer[idx + 0] = ax;
    imu_buffer[idx + 1] = ay;
    imu_buffer[idx + 2] = az;

    imuIndex++;

    // ---- DEBUG IMU INDEX ----
    Serial.print("imuIndex = ");
    Serial.println(imuIndex);

    // ===== When window is full =====
    if (imuIndex >= EI_CLASSIFIER_RAW_SAMPLE_COUNT) {
      Serial.println("---- WINDOW COMPLETE ----");

      imuIndex = 0;

      // --- Create signal ---
      signal_t signal;
      int rv = numpy::signal_from_buffer(
        imu_buffer,
        EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE,
        &signal
      );

      Serial.print("signal_from_buffer returned: ");
      Serial.println(rv);

      if (rv != 0) {
        Serial.println("Signal FAIL");
        return;
      }
      Serial.println("Signal OK");

      // --- Run inference ---
      ei_impulse_result_t result;
      EI_IMPULSE_ERROR ei = run_classifier(&signal, &result, false);

      Serial.print("run_classifier returned: ");
      Serial.println(ei);

      if (ei != EI_IMPULSE_OK) {
        Serial.println("Classifier FAIL");
        return;
      }

      // ---- Print result ----
      const char* best_label = result.classification[0].label;
      float best_val = result.classification[0].value;

      if (result.classification[1].value > best_val) {
        best_val = result.classification[1].value;
        best_label = result.classification[1].label;
      }

      Serial.print("<IMU_PRED>");
      Serial.print(best_label);
      Serial.print(",");
      Serial.print(best_val, 4);
      Serial.println("</IMU_PRED>");
    }
  }


  // ============= AUDIO =============
  if (audioReady) {
    audioReady = false;

    Serial.println("<AUDIO_BLOCK>");
    for (int i = 0; i < samplesRead; i++) {
      Serial.println(audioBuffer[i]);
    }
    Serial.println("<END_AUDIO_BLOCK>");
  }
}

// Recolección a 16kHz
//void onPDMdata() {
//  int bytesAvailable = PDM.available();
//  PDM.read(audioBuffer, bytesAvailable);

//  samplesRead = bytesAvailable / 2;  // 16 bits → 2 bytes
//  audioReady = true;
//}

// recolección a 8kHz
void onPDMdata() { 
  int bytesAvailable = PDM.available();
  int16_t temp[512];
  PDM.read(temp, bytesAvailable);
  int samples = bytesAvailable / 2;

  int decimated = 0;
  for (int i = 0; i < samples; i += 2) {
    audioBuffer[decimated++] = temp[i];
  }

  samplesRead = decimated;
  audioReady = true;
}
