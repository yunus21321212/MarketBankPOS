/*
  MarketBank POS Simulator (LCD Keypad Shield - PARAZİT KORUMALI)
  - Filtre: Analog buton okuma için çift kontrol (Debounce)
  - Modlar: SATIŞ ve KUPON KULLAN
*/

#include <LiquidCrystal.h>

LiquidCrystal lcd(8, 9, 4, 5, 6, 7);

#define btnRIGHT  0
#define btnUP     1
#define btnDOWN   2
#define btnLEFT   3
#define btnSELECT 4
#define btnNONE   5

const int LED_G = 12;
const int LED_R = 13;
const int BUZZ  = 11;

enum Mode { MODE_MENU, MODE_SALE, MODE_VOUCHER_PIN, MODE_VOUCHER_CARD };
Mode currentMode = MODE_MENU;
int menuOption = 0; 

int digits[4] = {0, 0, 0, 0};
int cursorIdx = 0;
String savedPin = "";
bool waitingResponse = false;

// Parazit önleyici buton okuma
int read_LCD_buttons() {
  int r1 = analogRead(0);
  delay(15); // Kısa kararlılık beklemesi
  int r2 = analogRead(0);
  if (abs(r1 - r2) > 30) return btnNONE; // Okumalar tutarsızsa parazittir
  
  int adc_key_in = r2;
  if (adc_key_in < 50)   return btnRIGHT;
  if (adc_key_in < 250)  return btnUP;
  if (adc_key_in < 450)  return btnDOWN;
  if (adc_key_in < 650)  return btnLEFT;
  if (adc_key_in < 850)  return btnSELECT;
  return btnNONE;
}

void setup() {
  Serial.begin(9600);
  pinMode(LED_G, OUTPUT);
  pinMode(LED_R, OUTPUT);
  pinMode(BUZZ, OUTPUT);
  lcd.begin(16, 2);
  updateDisplay();
}

void loop() {
  if (Serial.available() > 0) {
    String res = Serial.readStringUntil('\n');
    res.trim();
    parseResult(res);
  }

  if (waitingResponse) return;

  int button = read_LCD_buttons();
  static int lastButton = btnNONE;

  if (button != lastButton) {
    if (button != btnNONE) {
      if (currentMode == MODE_MENU) {
        if (button == btnUP || button == btnDOWN) { menuOption = !menuOption; updateDisplay(); }
        else if (button == btnSELECT) {
          if (menuOption == 0) { currentMode = MODE_SALE; resetDigits(3); }
          else { currentMode = MODE_VOUCHER_PIN; resetDigits(4); }
          updateDisplay();
        }
      } 
      else {
        int maxDigits = (currentMode == MODE_VOUCHER_PIN) ? 4 : 3;
        if (button == btnUP) { digits[cursorIdx]++; if(digits[cursorIdx]>9) digits[cursorIdx]=0; updateDisplay(); }
        else if (button == btnDOWN) { digits[cursorIdx]--; if(digits[cursorIdx]<0) digits[cursorIdx]=9; updateDisplay(); }
        else if (button == btnLEFT) { cursorIdx--; if(cursorIdx<0) cursorIdx = maxDigits-1; updateDisplay(); }
        else if (button == btnRIGHT) { cursorIdx++; if(cursorIdx>=maxDigits) cursorIdx = 0; updateDisplay(); }
        else if (button == btnSELECT) { handleSelect(); }
      }
    }
    lastButton = button;
    delay(250); // Buton hızı koruması
  }
}

void resetDigits(int n) {
  for(int i=0; i<4; i++) digits[i] = 0;
  cursorIdx = 0;
}

void handleSelect() {
  String entry = "";
  if (currentMode == MODE_SALE) {
    for(int i=0; i<3; i++) entry += digits[i];
    Serial.println(entry.toInt());
    waitingResponse = true;
    lcd.clear(); lcd.print("BANKA ONAYLIYOR..");
  } 
  else if (currentMode == MODE_VOUCHER_PIN) {
    savedPin = ""; for(int i=0; i<4; i++) savedPin += digits[i];
    currentMode = MODE_VOUCHER_CARD; resetDigits(3); updateDisplay();
  } 
  else if (currentMode == MODE_VOUCHER_CARD) {
    String cardID = ""; for(int i=0; i<3; i++) cardID += digits[i];
    Serial.println("REDEEM_VOUCHER:" + savedPin + ":" + String(cardID.toInt()));
    waitingResponse = true;
    lcd.clear(); lcd.print("KUPON KONTROL...");
  }
}

void updateDisplay() {
  if (waitingResponse) return;
  lcd.clear();
  if (currentMode == MODE_MENU) {
    lcd.print(" MARKETBANK POS");
    lcd.setCursor(0, 1); lcd.print(menuOption == 0 ? "> 1. SATIS YAP" : "> 2. KUPON KULLAN");
  } 
  else {
    lcd.print(currentMode == MODE_SALE ? "SATIS - KART NO:" : (currentMode == MODE_VOUCHER_PIN ? "PIN GIRIN:" : "HANGI KART?"));
    int n = (currentMode == MODE_VOUCHER_PIN) ? 4 : 3;
    lcd.setCursor(0, 1); lcd.print("[ ");
    for(int i=0; i<n; i++) {
      if (i == cursorIdx) { lcd.print(">"); lcd.print(digits[i]); lcd.print("<"); }
      else { lcd.print(digits[i]); lcd.print(" "); }
    }
    lcd.print("]");
  }
}

void parseResult(String data) {
  int firstColon = data.indexOf(':'); if (firstColon == -1) return;
  char type = data.charAt(0); String content = data.substring(firstColon + 1);
  if (type == 'S') {
    int s2 = content.indexOf(':'); String name = content.substring(0, s2);
    String rest = content.substring(s2 + 1); int s3 = rest.indexOf(':');
    String bal = rest.substring(0, s3); String auth = rest.substring(s3 + 1);
    lcd.clear(); lcd.print("ONAY: " + auth);
    lcd.setCursor(0, 1); lcd.print(name + " | B:" + bal);
    digitalWrite(LED_G, HIGH); delay(3000); digitalWrite(LED_G, LOW);
  } 
  else {
    lcd.clear(); lcd.print("HATA!"); lcd.setCursor(0, 1); lcd.print(content.substring(0, 16));
    digitalWrite(LED_R, HIGH); digitalWrite(BUZZ, HIGH); delay(1500); 
    digitalWrite(LED_R, LOW); digitalWrite(BUZZ, LOW);
  }
  waitingResponse = false; currentMode = MODE_MENU; updateDisplay();
}
