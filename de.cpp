#include <Wire.h>
#include "MAX30100_PulseOximeter.h"
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>
#include <WiFi.h>
#include <IOXhop_FirebaseESP32.h>
#include <time.h>

#define Wifi_SSID "Mariya"
#define Wifi_Pass "maddy123"
#define Firebase_Host "thefinals-8caac-default-rtdb.firebaseio.com"
#define Firebase_Auth "UAVcasy2UOXrXvMTHx1rNIQTT9evMgiDneQ1Gff7"

#define SDA_PIN 8
#define SCL_PIN 9
#define ECG_OUTPUT 4
#define UPLOAD_INTERVAL 60000UL
#define ECG_WIDTH 128
#define ECG_HEIGHT 20
#define ECG_Y_OFFSET 44
#define ECG_BUFFER_SIZE ECG_WIDTH
#define ECG_STABILITY_WINDOW 16

PulseOximeter pox;
Adafruit_SH1106G display(128, 64, &Wire, -1);

float bpm = 0.0;
float spo2 = 0.0;
unsigned long lastDisplayUpdate = 0;
unsigned long lastUpload = 0;

int ecgBuffer[ECG_BUFFER_SIZE];
int ecgIndex = 0;
int ecgWindow[ECG_STABILITY_WINDOW];
int ecgWindowIdx = 0;

#define USER_ID "6904005abfb7699b9ebae033"

void ensureWiFiConnectedForever() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(Wifi_SSID, Wifi_Pass);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
    static int counter = 0;
    counter++;
    if (counter % 20 == 0) {
      WiFi.disconnect();
      WiFi.begin(Wifi_SSID, Wifi_Pass);
    }
  }
  Serial.println("\nWiFi Connected");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  digitalWrite(LED_BUILTIN, HIGH);
}

void firebase_config() {
  Firebase.begin(Firebase_Host, Firebase_Auth);
}

bool isECGStable() {
  int minV = 4095, maxV = 0;
  for (int i = 0; i < ECG_STABILITY_WINDOW; i++) {
    int v = ecgWindow[i];
    if (v < minV) minV = v;
    if (v > maxV) maxV = v;
  }
  int p2p = maxV - minV;
  return (p2p > 30 && p2p < 3000);
}

void uploadReading(float hb, int ecgRaw[], int len) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Skipping upload: WiFi not connected.");
    return;
  }

  time_t now;
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    Serial.println("Failed to obtain time");
    return;
  }
  char timeStr[30];
  strftime(timeStr, sizeof(timeStr), "%Y-%m-%d %H:%M:%S", &timeinfo);

  String basePath = "/users/" + String(USER_ID) + "/realtime";

  Firebase.setFloat((basePath + "/heart_rate").c_str(), hb);
  Firebase.setString((basePath + "/timestamp").c_str(), timeStr);

  FirebaseJson ecgJson;
  FirebaseJsonArray ecgArray;
  for (int i = 0; i < len; i++) ecgArray.add((float)ecgRaw[i]);
  ecgJson.set("ecg_data", ecgArray);
  Firebase.updateNode(basePath.c_str(), ecgJson);

  Serial.println("Uploaded to Firebase");
}

#define BPM_SMOOTH_WINDOW 6
float bpmBuffer[BPM_SMOOTH_WINDOW];
int bpmIndex = 0;

float smoothBPM(float newBPM) {
  bpmBuffer[bpmIndex++] = newBPM;
  if (bpmIndex >= BPM_SMOOTH_WINDOW) bpmIndex = 0;
  float sum = 0;
  for (int i = 0; i < BPM_SMOOTH_WINDOW; i++) sum += bpmBuffer[i];
  return sum / BPM_SMOOTH_WINDOW;
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(ECG_OUTPUT, INPUT);
  analogReadResolution(12);
  for (int i = 0; i < 50; i++) analogRead(ECG_OUTPUT);

  ensureWiFiConnectedForever();
  firebase_config();

  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(100000);

  if (!display.begin(0x3C, false)) Serial.println("OLED not found");
  if (pox.begin()) {
    pox.setIRLedCurrent(MAX30100_LED_CURR_24MA);
    Serial.println("MAX30100 initialized");
  } else {
    Serial.println("MAX30100 not found");
  }

  for (int i = 0; i < ECG_BUFFER_SIZE; i++) ecgBuffer[i] = ECG_Y_OFFSET + ECG_HEIGHT / 2;
  for (int i = 0; i < ECG_STABILITY_WINDOW; i++) ecgWindow[i] = 2048;

  configTime(0, 0, "pool.ntp.org");
  Serial.println("Setup complete.");
}

void loop() {
  pox.update();
  float rawBPM = pox.getHeartRate();
  if (rawBPM < 45 || rawBPM > 130) rawBPM = bpm;
  float rawSpO2 = pox.getSpO2();
  int ecgValue = analogRead(ECG_OUTPUT);
  if (ecgValue < 10 || ecgValue > 4085) ecgValue = 2048;
  if (rawBPM < 40 || rawBPM > 180) rawBPM = 0;
  bpm = smoothBPM(rawBPM);
  spo2 = (rawSpO2 > 50 && rawSpO2 <= 100) ? rawSpO2 : spo2;

  bool finger = (spo2 >= 70 && spo2 <= 100 && bpm >= 40 && bpm <= 130);
  bool ecgStable = isECGStable();
  bool contactValid = finger && ecgStable;

  ecgBuffer[ecgIndex++] = ECG_Y_OFFSET + ECG_HEIGHT - map(ecgValue, 0, 4095, 0, ECG_HEIGHT);
  if (ecgIndex >= ECG_BUFFER_SIZE) ecgIndex = 0;

  ecgWindow[ecgWindowIdx++] = ecgValue;
  if (ecgWindowIdx >= ECG_STABILITY_WINDOW) ecgWindowIdx = 0;

  if (millis() - lastDisplayUpdate > 200) {
    lastDisplayUpdate = millis();
    display.clearDisplay();
    display.setTextColor(SH110X_WHITE);
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("MAX30100 + AD8232");
    if (!finger) {
      display.setCursor(25, 12);
      display.println("No Finger");
    } else {
      display.setCursor(0, 12);
      display.print("BPM : ");
      display.println(bpm, 0);
      display.setCursor(0, 24);
      display.print("SpO2: ");
      display.print(spo2, 0);
      display.println("%");
      if (!ecgStable) {
        display.setCursor(0, 36);
        display.println("ECG unstable");
      }
    }
    for (int i = 0; i < ECG_BUFFER_SIZE - 1; i++) {
      int index1 = (ecgIndex + i) % ECG_BUFFER_SIZE;
      int index2 = (ecgIndex + i + 1) % ECG_BUFFER_SIZE;
      display.drawLine(i, ecgBuffer[index1], i + 1, ecgBuffer[index2], SH110X_WHITE);
    }
    display.display();

    Serial.print("BPM: ");
    Serial.print(bpm, 1);
    Serial.print(" | SpO2: ");
    Serial.print(spo2, 1);
    Serial.print(" | ECG: ");
    Serial.print(ecgValue);
    Serial.print(" | contact: ");
    Serial.println(contactValid);
  }

  if (millis() - lastUpload > UPLOAD_INTERVAL) {
    lastUpload = millis();
    if (contactValid) {
      uploadReading(bpm, ecgBuffer, ECG_BUFFER_SIZE);
    } else {
      Serial.println("Skipped upload (unstable / no contact)");
    }
  }
  delay(20);
}