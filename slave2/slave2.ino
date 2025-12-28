#include <ModbusRTU.h>

#define LED_PIN 2        // GPIO2 (LED ngoài)
#define RE_DE 4          // GPIO4
#define BLINK_PERIOD 1000

ModbusRTU mb;

bool blinkEnable = false;
bool ledState = false;
unsigned long lastMillis = 0;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(RE_DE, OUTPUT);
  digitalWrite(RE_DE, LOW);

  Serial.begin(9600);

  mb.begin(&Serial, RE_DE);
  mb.slave(2);          // Slave ID ESP8266

  mb.addCoil(0);

  digitalWrite(LED_PIN, LOW);  // LED OFF ban đầu
}

void loop() {
  mb.task();

  blinkEnable = mb.Coil(0);

  if (blinkEnable) {
    unsigned long now = millis();
    if (now - lastMillis >= BLINK_PERIOD / 2) {
      lastMillis = now;
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState ? HIGH : LOW);
    }
  } else {
    digitalWrite(LED_PIN, LOW);   // OFF
    ledState = false;
  }
}
