/*
  MarketBank Admin Arduino (MEB KIT - MAX GÜVENLİK & ANTİ-PARAZİT)
  - Filtre: EMA Filter + Hysteresis (Potansiyometre zıplamasını engeller)
  - Güvenlik: 4 Haneli PIN, 3 Hak, Kilitlenme ve "HATA YOK" Reset
*/

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2); 

const int BTN_NAV = 2;    
const int BTN_OK  = 3;    
const int POT_PIN = A0;   
const int LED_G   = 12;   
const int LED_R   = 13;   
const int BUZZ    = 9;    // MEB KIT Hoparlör (Speaker) - Pin 9

enum State { PASS_ENTRY, MENU, SELECT_ID_REG, SELECT_ID_LOAD, SELECT_AMT_COUPON, SELECT_ID_WITHDRAW, SELECT_AMT_WITHDRAW, SENDING, FEEDBACK, LOCKED };
State currentState = PASS_ENTRY;

int selectedID = 1;
int selectedAmt = 10;
int menuOption = 0; 

// Güvenlik
int attempts = 0;
const int MAX_ATTEMPTS = 3;
const String ADMIN_PIN = "1234"; 
int pinDigits[4] = {0, 0, 0, 0};
int pinIdx = 0;

// Gelişmiş Filtre
float filteredPot = 512;
const float filterAlpha = 0.15; // Daha ağır filtre

void setup() {
  Serial.begin(9600);
  pinMode(BTN_NAV, INPUT_PULLUP);
  pinMode(BTN_OK, INPUT_PULLUP);
  pinMode(LED_G, OUTPUT);
  pinMode(LED_R, OUTPUT);
  pinMode(BUZZ, OUTPUT);
  
  // Tüm çıkışları kapat
  digitalWrite(BUZZ, LOW);
  digitalWrite(LED_R, LOW);
  digitalWrite(LED_G, LOW);
  
  lcd.init(); 
  lcd.backlight();
  
  updateDisplay();
}

void loop() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "HATA YOK") {
      attempts = 0; currentState = PASS_ENTRY; pinIdx = 0;
      for(int i=0; i<4; i++) pinDigits[i] = 0;
      lcd.clear(); lcd.print("HADI ISLETME"); lcd.setCursor(0, 1); lcd.print("SISTEM ACILDI"); delay(1500); updateDisplay();
    } else { parseResult(cmd); }
  }

  if (currentState == LOCKED) {
    digitalWrite(BUZZ, HIGH); delay(50); digitalWrite(BUZZ, LOW);
    lcd.setCursor(0, 0); lcd.print("!! SISTEM KILIT !!");
    lcd.setCursor(0, 1); lcd.print("CMD: HATA YOK");
    delay(1000); 
    return;
  }

  // Buton okumalarını sadece SENDING veya FEEDBACK durumunda engelle
  if (currentState != SENDING && currentState != FEEDBACK) {
    // Buton Debounce
    // Buton Debounce (Hizlandirilmis)
    static bool lastNav = HIGH; static bool lastOk = HIGH;
    bool rawNav = digitalRead(BTN_NAV); bool rawOk = digitalRead(BTN_OK);
    
    // NAV Tusu
    if (rawNav == LOW && lastNav == HIGH) { 
      delay(20); // Noise filtresi (80'den 20'ye düstü)
      if(digitalRead(BTN_NAV) == LOW) { handleButton('N'); delay(150); } 
    }
    
    // OK Tusu (Onay Tusu)
    if (rawOk == LOW && lastOk == HIGH) { 
      delay(20); // Noise filtresi (80'den 20'ye düstü)
      if(digitalRead(BTN_OK) == LOW) { handleButton('O'); delay(150); }
    }
    
    lastNav = rawNav; lastOk = rawOk;
    
    // Pot Filtre (EMA)
    int rawPot = analogRead(POT_PIN);
    filteredPot = (filterAlpha * rawPot) + ((1.0 - filterAlpha) * filteredPot);
    int smoothPot = (int)filteredPot;

    // Değer Atama (Hysteresis/Dead-band Logic)
    static int lastSmooth = -1;
    if (abs(smoothPot - lastSmooth) > 3) {
      lastSmooth = smoothPot;
      if (currentState == PASS_ENTRY) {
        int potDigit = map(smoothPot, 0, 1023, 0, 9);
        if (potDigit != pinDigits[pinIdx]) { pinDigits[pinIdx] = potDigit; updateDisplay(); }
      }
      else if (currentState == SELECT_ID_REG || currentState == SELECT_ID_LOAD || currentState == SELECT_ID_WITHDRAW) {
        int potID = map(smoothPot, 0, 1023, 1, 99);
        if (potID != selectedID) { selectedID = potID; updateDisplay(); }
      } 
      else if (currentState == SELECT_AMT_COUPON || currentState == SELECT_AMT_WITHDRAW) {
        int potAmt = map(smoothPot, 0, 1023, 1, 500);
        if (abs(potAmt - selectedAmt) > 10) { selectedAmt = potAmt; updateDisplay(); }
      }
    }
  }
}

void handleButton(char type) {
  if (currentState == PASS_ENTRY) {
    if (type == 'N') { pinIdx++; if(pinIdx > 3) pinIdx = 0; }
    else if (type == 'O') {
      if (pinIdx < 3) { pinIdx++; }
      else {
        String enteredPIN = "";
        for(int i=0; i<4; i++) enteredPIN += String(pinDigits[i]);
        if (enteredPIN == ADMIN_PIN) { attempts = 0; currentState = MENU; }
        else {
          attempts++;
          digitalWrite(BUZZ, HIGH); delay(100); digitalWrite(BUZZ, LOW);
          if (attempts >= MAX_ATTEMPTS) currentState = LOCKED;
          else {
            lcd.clear(); lcd.print("HATALI SIFRE!"); lcd.setCursor(0, 1); 
            lcd.print("KALAN HAK: "); lcd.print(MAX_ATTEMPTS - attempts);
            delay(1500); pinIdx = 0;
          }
        }
      }
    }
  }
  else if (currentState == MENU) {
    if (type == 'N') { menuOption++; if(menuOption > 3) menuOption = 0; }
    else if (type == 'O') {
      if (menuOption == 0) currentState = SELECT_ID_REG;
      else if (menuOption == 1) currentState = SELECT_ID_LOAD;
      else if (menuOption == 2) currentState = SELECT_AMT_COUPON;
      else currentState = SELECT_ID_WITHDRAW;
    }
  }
  else if (currentState == SELECT_ID_REG || currentState == SELECT_ID_LOAD || currentState == SELECT_AMT_COUPON || currentState == SELECT_ID_WITHDRAW || currentState == SELECT_AMT_WITHDRAW) {
    if (type == 'O') {
      if (currentState == SELECT_ID_WITHDRAW) {
        currentState = SELECT_AMT_WITHDRAW; // Para Cekme icin ID secildikten sonra Miktara gec
      } 
      else {
        if (currentState == SELECT_AMT_COUPON) Serial.println("GEN_VOUCHER:" + String(selectedAmt));
        else if (currentState == SELECT_AMT_WITHDRAW) Serial.println("WITHDRAW:" + String(selectedID) + ":" + String(selectedAmt));
        else Serial.println(String(currentState == SELECT_ID_REG ? "REGISTER:" : "LOAD:") + selectedID);
        currentState = SENDING; lcd.clear(); lcd.print("GONDERILIYOR...");
      }
    }
  }
  updateDisplay();
}

void updateDisplay() {
  if (currentState == SENDING || currentState == FEEDBACK || currentState == LOCKED) return;
  lcd.clear();
  if (currentState == PASS_ENTRY) { 
    lcd.print("GIRIS PIN:"); lcd.setCursor(0,1); 
    for(int i=0; i<4; i++) {
      if(i == pinIdx) { lcd.print(">"); lcd.print(pinDigits[i]); lcd.print("< "); }
      else if (i < pinIdx) { lcd.print("* "); }
      else { lcd.print(pinDigits[i]); lcd.print(" "); }
    }
    lcd.setCursor(12,1); lcd.print("H:"); lcd.print(MAX_ATTEMPTS - attempts);
  } 
  else if (currentState == MENU) { 
    lcd.print("HADI ISLETME:"); lcd.setCursor(0,1); 
    if (menuOption == 0) lcd.print("> HESAP AC");
    else if (menuOption == 1) lcd.print("> YUKLEME YAP");
    else if (menuOption == 2) lcd.print("> KOD OLUSTUR");
    else lcd.print("> NAKIT CEK");
  }
  else {
    if (currentState == SELECT_ID_REG) lcd.print("HESAP NO:");
    else if (currentState == SELECT_ID_LOAD) lcd.print("YUKLE - ID:");
    else if (currentState == SELECT_ID_WITHDRAW) lcd.print("CEKIM - ID:");
    else lcd.print("TUTAR GIR:");
    
    lcd.setCursor(0,1); 
    if (currentState == SELECT_AMT_COUPON || currentState == SELECT_AMT_WITHDRAW) lcd.print(String(selectedAmt) + " TL");
    else lcd.print(String(selectedID));
    
    lcd.print(" [ONAY]");
  }
}

void parseResult(String data) {
  int firstColon = data.indexOf(':'); if (firstColon == -1) return;
  char type = data.charAt(0); String content = data.substring(firstColon + 1);
  currentState = FEEDBACK; lcd.clear();
  if (type == 'S') {
    int s2 = content.indexOf(':'); String tag = content.substring(0, s2); String val = content.substring(s2 + 1);
    if (tag == "KOD") { lcd.print("PIN:"); lcd.setCursor(0, 1); lcd.print(">> " + val + " <<"); }
    else { lcd.print("OK: " + tag); lcd.setCursor(0, 1); lcd.print("BAL: " + val); }
    digitalWrite(LED_G, HIGH); delay(3000); digitalWrite(LED_G, LOW);
  } else {
    lcd.print("HATA!"); lcd.setCursor(0, 1); lcd.print(content.substring(0, 16));
    digitalWrite(LED_R, HIGH); 
    digitalWrite(BUZZ, HIGH);
    delay(1500);
    digitalWrite(LED_R, LOW); 
    digitalWrite(BUZZ, LOW);
  }
  currentState = MENU; updateDisplay();
}