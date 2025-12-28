#include <ModbusRTU.h>

#define LED_PIN 2
#define RXD2 16
#define TXD2 17
#define RE_DE 15

#define BLINK_PERIOD 1000  // 1s

ModbusRTU mb;

bool blinkEnable = false;
bool ledState = false;
unsigned long lastMillis = 0;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(RE_DE, OUTPUT);
  digitalWrite(RE_DE, LOW);

  Serial2.begin(9600, SERIAL_8N1, RXD2, TXD2);

  mb.begin(&Serial2, RE_DE);
  mb.slave(1);       // giữ nguyên ID của ESP32

  mb.addCoil(0);
}

void loop() {
  mb.task();

  blinkEnable = mb.Coil(0);

  if (blinkEnable) {
    unsigned long now = millis();
    if (now - lastMillis >= BLINK_PERIOD / 2) {
      lastMillis = now;
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState);
    }
  } else {
    digitalWrite(LED_PIN, LOW);
    ledState = false;
  }
}
