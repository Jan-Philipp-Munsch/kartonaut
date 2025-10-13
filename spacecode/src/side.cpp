/*
// mehrstufiger Programmablauf

#include <Arduino.h>
#include <Servo.h>
#include <Wire.h>
#include <SPI.h>

enum Phase {
    INITIALIZATION,
    PAD_IDLE,
    START,
    DECENT,
    ABORT,
    LANDED
};

float gndps;
float gndtemp;
float g = 9.81;
float lastTime;

Phase currentPhase = INITIALIZATION;

// BMP 280 uses I2C PINS 18 and 19
#include <Adafruit_BMP280.h>
Adafruit_BMP280 bmp; // I2C

// RollMotor uses digital PINS 0 and 1
const int IN1 = 2;
const int IN2 = 3; 

// Servos use digital PINS 2,3 and 4
const int XServo_PIN = 7;
const int YServo_PIN = 8;
const int ChuteServo_PIN = 9;
Servo XServo;
Servo YServo;
Servo ChuteServo;

//Beeper uses digital PIN 5

const int Beeper_PIN = 13;

// LED uses digital PIN 5 and 6 !!!
#include <FastLED.h>

#define LED1_PIN 6
#define LED2_PIN 5

CRGB led1;
CRGB led2;

// IMU uses I2C PINS 16 and 17
#include <ICM_20948.h>
#define SERIAL_PORT Serial
#define WIRE_PORT Wire1 // Your desired Wire port.      Used when "USE_SPI" is not defined
// The value of the last bit of the I2C address.
// On the SparkFun 9DoF IMU breakout the default is 1, and when the ADR jumper is closed the value becomes 0
#define AD0_VAL 0 // AD0 an 3V3
ICM_20948_I2C myICM; // Create an ICM_20948_I2C object


void setup() {
    // Initialisierung von PressureSensor, IMU, Beeper, LED, RollMotor, Servos
    Serial.begin(115200);
    pinMode(LED_BUILTIN, OUTPUT);

    // Servos
    XServo.attach(XServo_PIN);
    YServo.attach(YServo_PIN);
    ChuteServo.attach(ChuteServo_PIN);

    // RollMotor
    pinMode(IN1, OUTPUT);
    pinMode(IN2, OUTPUT);

    //BMP 280
    Wire.begin();
    while ( !Serial ) delay(100);   // wait for native usb
    Serial.println(F("BMP280 test"));
    unsigned status;
    status = bmp.begin(0x76);
    if (!status) {
        Serial.println(F("Could not find a valid BMP280 sensor, check wiring or "
                        "try a different address!"));
        Serial.print("SensorID was: 0x"); Serial.println(bmp.sensorID(),16);
        Serial.print("        ID of 0xFF probably means a bad address, a BMP 180 or BMP 085\n");
        Serial.print("   ID of 0x56-0x58 represents a BMP 280,\n");
        Serial.print("        ID of 0x60 represents a BME 280.\n");
        Serial.print("        ID of 0x61 represents a BME 680.\n");
        while (1) delay(10);
    }

    
    bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,     // Operating Mode. 
                    Adafruit_BMP280::SAMPLING_X1,     // Temp. oversampling 
                    Adafruit_BMP280::SAMPLING_X1,    // Pressure oversampling 
                    Adafruit_BMP280::FILTER_X2,      // Filtering. 
                    Adafruit_BMP280::STANDBY_MS_1); // Standby time.
    // LED
    FastLED.addLeds<WS2812B, LED1_PIN, GRB>(&led1, 1);
    FastLED.addLeds<WS2812B, LED2_PIN, GRB>(&led2, 1);
    FastLED.clear();
    FastLED.show();

    // Beeper

    pinMode(Beeper_PIN, OUTPUT);

    // IMU
    
    SERIAL_PORT.begin(115200); // Start the serial console
    #ifndef QUAT_ANIMATION
      SERIAL_PORT.println(F("ICM-20948 Example"));
    #endif
    
      delay(100);
    
    #ifndef QUAT_ANIMATION
      while (SERIAL_PORT.available()) // Make sure the serial RX buffer is empty
        SERIAL_PORT.read();
    
      SERIAL_PORT.println(F("Press any key to continue..."));
    
      while (!SERIAL_PORT.available()) // Wait for the user to press a key (send any serial character)
        ;
    #endif
    
    #ifdef USE_SPI
      SPI_PORT.begin();
    #else
      WIRE_PORT.begin();
      WIRE_PORT.setClock(400000);
    #endif
    
    #ifndef QUAT_ANIMATION
      //myICM.enableDebugging(); // Uncomment this line to enable helpful debug messages on Serial
    #endif
    
      bool initialized = false;
      while (!initialized)
      {
    
        // Initialize the ICM-20948
        // If the DMP is enabled, .begin performs a minimal startup. We need to configure the sample mode etc. manually.
    #ifdef USE_SPI
        myICM.begin(CS_PIN, SPI_PORT);
    #else
        myICM.begin(WIRE_PORT, AD0_VAL);
    #endif
    
    #ifndef QUAT_ANIMATION
        SERIAL_PORT.print(F("Initialization of the sensor returned: "));
        SERIAL_PORT.println(myICM.statusString());
    #endif
        if (myICM.status != ICM_20948_Stat_Ok)
        {
    #ifndef QUAT_ANIMATION
          SERIAL_PORT.println(F("Trying again..."));
    #endif
          delay(500);
        }
        else
        {
          initialized = true;
        }
      }
    
    #ifndef QUAT_ANIMATION
      SERIAL_PORT.println(F("Device connected!"));
    #endif
    
      bool success = true; // Use success to show if the DMP configuration was successful
    
      // Initialize the DMP. initializeDMP is a weak function. You can overwrite it if you want to e.g. to change the sample rate
      success &= (myICM.initializeDMP() == ICM_20948_Stat_Ok);
    
      // Enable the DMP orientation sensor
      success &= (myICM.enableDMPSensor(INV_ICM20948_SENSOR_ORIENTATION) == ICM_20948_Stat_Ok);
    
      success &= (myICM.setDMPODRrate(DMP_ODR_Reg_Quat9, 0) == ICM_20948_Stat_Ok); // Set to the maximum
    
      // Enable the FIFO
      success &= (myICM.enableFIFO() == ICM_20948_Stat_Ok);
    
      // Enable the DMP
      success &= (myICM.enableDMP() == ICM_20948_Stat_Ok);
    
      // Reset DMP
      success &= (myICM.resetDMP() == ICM_20948_Stat_Ok);
    
      // Reset FIFO
      success &= (myICM.resetFIFO() == ICM_20948_Stat_Ok);
    
      // Check success
      if (success)
      {
    #ifndef QUAT_ANIMATION
        SERIAL_PORT.println(F("DMP enabled!"));
    #endif
      }
      else
      {
        SERIAL_PORT.println(F("Enable DMP failed!"));
        SERIAL_PORT.println(F("Please check that you have uncommented line 29 (#define ICM_20948_USE_DMP) in ICM_20948_C.h..."));
        while (1)
          ; // Do nothing more
      }



}

struct Quaternion {
    float w, x, y, z;
  
    Quaternion conjugate() {
      return {w, -x, -y, -z};
    }
  
    Quaternion operator*(const Quaternion& b) {
        return {
            w*b.w - x*b.x - y*b.y - z*b.z,
            w*b.x + x*b.w + y*b.z - z*b.y,
            w*b.y - x*b.z + y*b.w + z*b.x,
            w*b.z + x*b.y - y*b.x + z*b.w
        };
    }
};

Quaternion rotateVector(Quaternion q, float ax, float ay, float az) {
    Quaternion v = {0, ax, ay, az};
    Quaternion q_conj = q.conjugate();
    Quaternion rotated = q * v * q_conj;
    return rotated;
};

Quaternion getQFromIMU() {
    return;
};

float getaxFromIMU() {
    return;
};
float getayFromIMU() {
    return;
};
float getazFromIMU() {
    return;
};

struct Kalman1D {
    float position = 0;
    float velocity = 0;
    float P[2][2] = {{1, 0}, {0, 1}}; // Unsicherheiten
  
    float accel_noise = 0.1;
    float baro_noise = 1.0;
  
    void predict(float acc, float dt) {
      // Zustandsvorhersage
      position += velocity * dt + 0.5 * acc * dt * dt;
      velocity += acc * dt;
  
      // Fehlerkovarianz aktualisieren
      P[0][0] += dt * (dt*P[1][1] - P[0][1] - P[1][0] + accel_noise*dt);
      P[0][1] += dt * (P[1][1] - accel_noise*dt);
      P[1][0] += dt * (P[1][1] - accel_noise*dt);
      P[1][1] += accel_noise * dt;
    }
  
    void update(float baro_alt) {
      float y = baro_alt - position;
      float S = P[0][0] + baro_noise;
      float K0 = P[0][0] / S;
      float K1 = P[1][0] / S;
  
      position += K0 * y;
      velocity += K1 * y;
  
      // Kovarianzmatrix anpassen
      float P00 = P[0][0], P01 = P[0][1];
      P[0][0] -= K0 * P00;
      P[0][1] -= K0 * P01;
      P[1][0] -= K1 * P00;
      P[1][1] -= K1 * P01;
    }
  };
  
  // Globale Instanz
  Kalman1D kalman;
  


float getHeight() {

    Quaternion orientation = getQFromIMU();
    Quaternion IMUacc = rotateVector(orientation, getaxFromIMU(), getayFromIMU(), getazFromIMU());

    float acc_z = IMUacc.z - g;

    float now = millis() / 1000.0;
    float dt = now - lastTime;
    lastTime = now;

    float accZ = acc_z;  // ggf. Offset abziehen
    float baro = bmp.readAltitude(gndps);

    kalman.predict(accZ, dt);
    kalman.update(baro);

    return kalman.position;
}


            

void loop() {
    switch (currentPhase) {
        case INITIALIZATION:

            for (int i = 0; i < 3; i++) // Show Power On (300 ms)
            {
                digitalWrite(Beeper_PIN, HIGH);  // Beeper ein
                led1 = CRGB::Green;
                led2 = CRGB::Green;
                FastLED.show();
                delay(50);    
                digitalWrite(Beeper_PIN, LOW);
                FastLED.clear();
                delay(50);   
            }
            
            led1 = CRGB::Orange;    
            led2 = CRGB::Orange;
            FastLED.show();  // LED auf Orange signalisiert initialisierung läuft
            
            for (int i = 0; i < 10; i++)
            {
                gndps += bmp.readPressure()/10;
                gndtemp += bmp.readTemperature()/10;
                delay(20);
            };
             
            Serial.print("Luftdurck:");
            Serial.println(gndps);
            Serial.print("Temperatur:");
            Serial.println(gndtemp);
            

            delay(20000);

            currentPhase = INITIALIZATION;
            
            // Check all sensors, calibrate coordinates and angles

            break;
        case PAD_IDLE:

            // Ready to launch

            // Determine lauch via Accelerometer

            break;
        case START:
            
            break;
        case DECENT:
            
            break;
        case ABORT:
            
            break;
        case LANDED:
            
            break;
    }
}


*/



/*
//RollMotor test

#include <Arduino.h>
#include <Wire.h>
#include <INA219_WE.h>
#define I2C_ADDRESS 0x40



INA219_WE ina219 = INA219_WE(I2C_ADDRESS);

// Pin-Zuweisung
const int IN1 = 2;  // PWM-fähig
const int IN2 = 3;  // PWM-fähig

void setup() {
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  Serial.begin(115200);
  Wire.begin();
   Wire.setClock(1000000);
  if(!ina219.init()){
    Serial.println("INA219 not connected!");
    while(1);
  }

  Serial.println("INA219 Current Sensor Example Sketch - Continuous");
 
}

void readMultimeter(){
uint64_t timer = micros();
  float shuntVoltage_mV = 0.0;
  float loadVoltage_V = 0.0;
  float busVoltage_V = 0.0;
  float current_mA = 0.0;
  float power_mW = 0.0; 
  bool ina219_overflow = false;
  
  shuntVoltage_mV = ina219.getShuntVoltage_mV();
  busVoltage_V = ina219.getBusVoltage_V();
  current_mA = ina219.getCurrent_mA();
  power_mW = ina219.getBusPower();
  loadVoltage_V  = busVoltage_V + (shuntVoltage_mV/1000);
  ina219_overflow = ina219.getOverflow();
  
  Serial.print(">Shunt Voltage [mV]:"); Serial.println(shuntVoltage_mV);
  Serial.print(">Bus Voltage [V]:"); Serial.println(busVoltage_V);
  Serial.print(">Load Voltage [V]:"); Serial.println(loadVoltage_V);
  Serial.print(">Current[mA]:"); Serial.println(current_mA);
  Serial.print(">Bus Power [mW]:"); Serial.println(power_mW);
}

void loop() {
  analogWrite(IN1, 50);  // Schnell vorwärts
  analogWrite(IN2, 0);
  for (int i = 0; i < 50; i++)
  {
    readMultimeter();
    delay(20);
  }
  analogWrite(IN1, 110);  // Schnell vorwärts
  analogWrite(IN2, 0);
  for (int i = 0; i < 50; i++)
  {
    readMultimeter();
    delay(20);
  }

  analogWrite(IN1, 170);  // Schnell vorwärts
  analogWrite(IN2, 0);
  for (int i = 0; i < 50; i++)
  {
    readMultimeter();
    delay(20);
  }

  analogWrite(IN1, 0);    // Bremsen
  analogWrite(IN2, 0);
  for (int i = 0; i < 50; i++)
  {
    readMultimeter();
    delay(20);
  }
}
*/



/*
//servo test 

#include <Arduino.h>
#include <Servo.h>



//accelerometers



//servos

boolean servos = true;

Servo yServo;
Servo xServo;

int delaytime = 200;

void setup() {
    Serial.begin(115200);

    if(servos){
        xServo.attach(0);
        yServo.attach(1);
    }
}


void loop() {


    //servo test
    if(true){

        if(servos){
            xServo.write(30); 
            yServo.write(60);
        }

        delay(delaytime);
        if(servos){
            xServo.write(115); 
            yServo.write(60);
        }

        delay(delaytime);
        if(servos){ 
            xServo.write(115); 
            yServo.write(130);
        }

        delay(delaytime);
        if(servos){ 
            xServo.write(30); 
            yServo.write(130);
        }

        delay(delaytime);
    }
   
}

*/




/*

// i2c_scanner

#include <Wire.h>
 
void setup()
{
  Wire.begin();
 
  Serial.begin(9600);
  while (!Serial);             // Leonardo: wait for serial monitor
  Serial.println("\nI2C Scanner");
}
 

void loop()
{
  byte error, address;
  int nDevices;
 
  Serial.println("Scanning...");
 
  nDevices = 0;
  for(address = 1; address < 127; address++ )
  {
    // The i2c_scanner uses the return value of
    // the Write.endTransmisstion to see if
    // a device did acknowledge to the address.
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
 
    if (error == 0)
    {
      Serial.print("I2C device found at address 0x");
      if (address<16)
        Serial.print("0");
      Serial.print(address,HEX);
      Serial.println("  !");
 
      nDevices++;
    }
    else if (error==4)
    {
      Serial.print("Unknown error at address 0x");
      if (address<16)
        Serial.print("0");
      Serial.println(address,HEX);
    }    
  }
  if (nDevices == 0)
    Serial.println("No I2C devices found\n");
  else
    Serial.println("done\n");
 
  delay(5000);           // wait 5 seconds for next scan
}

*/


/*

// Servo reactiontime test
#include <Arduino.h>
#include <Servo.h>
#include <I2Cdev.h>
#include <MPU6050.h>
#include "Wire.h"

#include <I2Cdev.h>
#include <MPU6050.h>

MPU6050 accelgyro;

int16_t ax, ay, az;
int16_t gx, gy, gz;

#define OUTPUT_READABLE_ACCELGYRO

bool blinkState = false;

Servo yServo;
Servo xServo;
float servo_position;
unsigned long timekeep;

void MPU6500_setup(){
  // join I2C bus (I2Cdev library doesn't do this automatically)
    #if I2CDEV_IMPLEMENTATION == I2CDEV_ARDUINO_WIRE
        Wire.begin();
    #elif I2CDEV_IMPLEMENTATION == I2CDEV_BUILTIN_FASTWIRE
        Fastwire::setup(400, true);
    #endif

    // initialize serial communication
    // (38400 chosen because it works as well at 8MHz as it does at 16MHz, but
    // it's really up to you depending on your project)
    Serial.begin(115200);

    // initialize device
    Serial.println("Initializing I2C devices...");
    accelgyro.initialize();

    // verify connection
    Serial.println("Testing device connections...");
    Serial.println(accelgyro.testConnection() ? "MPU6050 connection successful" : "MPU6050 connection failed");

    // use the code below to change accel/gyro offset values
    
    Serial.println("Updating internal sensor offsets...");
    // -76	-2359	1688	0	0	0


    accelgyro.setXGyroOffset(0);// /4
    accelgyro.setYGyroOffset(0);
    accelgyro.setZGyroOffset(0);
    accelgyro.setXAccelOffset(0);
    accelgyro.setYAccelOffset(0);
    accelgyro.setZAccelOffset(0);

    Serial.print(accelgyro.getXAccelOffset()); Serial.print("\t"); // -76
    Serial.print(accelgyro.getYAccelOffset()); Serial.print("\t"); // -2359
    Serial.print(accelgyro.getZAccelOffset()); Serial.print("\t"); // 1688
    Serial.print(accelgyro.getXGyroOffset()); Serial.print("\t"); // 0
    Serial.print(accelgyro.getYGyroOffset()); Serial.print("\t"); // 0
    Serial.print(accelgyro.getZGyroOffset()); Serial.print("\t"); // 0
    Serial.print("\n");

}

void Servo_setup(){
  xServo.attach(28);
  yServo.attach(29);

  servo_position = 95;
  yServo.write(servo_position); 
  delay(500);
}

void setup() {

  Serial.begin(115200);

  Servo_setup();

  MPU6500_setup();

}

unsigned long checkStart;
float angleX = 0, angleY = 0, angleZ = 0;


void MPU6500_signals(){

//int sum = 0;

  //int sum = 0;
  //int64_t gx_sum = 0;
  //int64_t gy_sum = 0;
  //int64_t gz_sum = 0;

  // read raw accel/gyro measurements from device
  accelgyro.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

  float gyroX = (gx+21.3)/16.348;  // je nach config
  float gyroY = (gy-5.2)/16.348;
  float gyroZ = (gz-7.1)/16.348;

  float dt = 0.002;

  angleX += gyroX * dt;
  angleY += gyroY * dt;
  angleZ += gyroZ * dt;


  //Serial.print(">AngleX:");
  //Serial.println(angleX);
  //Serial.print(">AngleY:");
  //Serial.println(angleY);
  //Serial.print(">AngleZ:");
  //Serial.println(angleZ);

  //Serial.print(">time:");
  //Serial.println(millis()-checkStart);
    
  //Serial.print("offset gx: ");
  //Serial.println(gx_sum/(double)sum);
  //Serial.print("offset gy: ");
  //Serial.println(gy_sum/(double)sum);
  //Serial.print("offset zx: ");
  //Serial.println(gz_sum/(double)sum);
}

void checkResponse(){
  unsigned long loopStart = micros();
  MPU6500_signals();
  if(false){
    Serial.print(">AngleX:");
    Serial.println(angleX);
    Serial.print(">time:");
    Serial.println(millis()-checkStart);
    Serial.print(">Servo:");
    Serial.println(servo_position);
  }
  Serial.print(millis()-timekeep);
  Serial.print(", ");
  Serial.print(servo_position);
  Serial.print(", ");
  Serial.println(angleX);
  

  while (micros() - loopStart < 2000) {
    // Nichts tun (Busy-Wait)
  }

  //Serial.print("here");
}

void loop() {
  
  delay(1000);
  checkStart = millis();
  timekeep = millis();

  checkResponse();

  while (millis()-checkStart<400)
  {
    checkResponse();
  }


  checkStart = millis();
  servo_position = 95;
  yServo.write(servo_position);

  while (millis()-checkStart<400)
  {
    checkResponse();
  }

  checkStart = millis();
  servo_position = 130;
  yServo.write(servo_position);

  while (millis()-checkStart<400)
  {
    checkResponse();
  }
  checkStart = millis();
  servo_position = 95;
  yServo.write(servo_position);

  while (millis()-checkStart<400)
  {
    checkResponse();
  }

  checkStart = millis();
  servo_position = 80;
  yServo.write(servo_position);

  while (millis()-checkStart<100)
  {
    checkResponse();
  }

  checkStart = millis();
  servo_position = 95;
  yServo.write(servo_position);

  while (millis()-checkStart<400)
  {
    checkResponse();
  }

  checkStart = millis();

  while (millis()-checkStart<1000)
  {
    servo_position = (int)(95 + 35*sin((millis()-checkStart)/100.0));
    yServo.write(servo_position);
    checkResponse();
  }

  checkStart = millis();

  while (millis()-checkStart<1000)
  {
    servo_position = (int)(95 + 35*sin((millis()-checkStart)/50.0));
    yServo.write(servo_position);
    checkResponse();
  }

  servo_position = 95;
  yServo.write(servo_position);
  checkResponse();

}
*/

/*

void loop() {

  xServo.write(30); 
  //yServo.write(60);

  checkResponse();

  xServo.write(73); 
  //yServo.write(60);

  checkResponse();

  xServo.write(115); 
  //yServo.write(130);

    checkResponse();

  xServo.write(73); 
  //yServo.write(130);

  checkResponse();

}

*/

/*

// LED Test
#include <Arduino.h>
#include <FastLED.h>

// Pins definieren
#define LED1_PIN 6
#define LED2_PIN 5

CRGB led1;
CRGB led2;

// Einstellungen
uint8_t brightness = 0;  // aktuelle Helligkeit (0–255)
int fadeAmount = 1;      // Schrittweite des Fades
unsigned long lastUpdate = 0;
const int fadeDelay = 5; // Zeit zwischen Helligkeitsänderungen (ms)

CRGB colors[] = {CRGB::Red, CRGB::Green, CRGB::Blue}; // Farben zum Durchwechseln
int currentColor = 0;

void setup() {
    FastLED.addLeds<WS2812B, LED1_PIN, GRB>(&led1, 1);
    FastLED.addLeds<WS2812B, LED2_PIN, GRB>(&led2, 1);
    FastLED.clear();
    FastLED.show();
}

void loop() {
    unsigned long now = millis();
    if (now - lastUpdate >= fadeDelay) {
        lastUpdate = now;

        // Farbe setzen mit aktueller Helligkeit
        led1 = colors[currentColor];
        led1.fadeLightBy(255 - brightness); // fadeLightBy reduziert Helligkeit
        led2 = colors[currentColor];
        led2.fadeLightBy(255 - brightness);

        FastLED.show();

        // Helligkeit verändern
        brightness += fadeAmount;

        // Umkehren bei voller Helligkeit oder Aus
        if (brightness <= 0 || brightness >= 255) {
            fadeAmount = -fadeAmount; // Richtung ändern

            // Wenn komplett dunkel, nächste Farbe nehmen
            if (brightness <= 0) {
                currentColor++;
                if (currentColor >= (sizeof(colors) / sizeof(colors[0]))) {
                    currentColor = 0; // Zurück zur ersten Farbe
                }
            }
        }
    }
}

*/

/*
// Beeper test
#include <Arduino.h>
#define BEEPER_PIN 13

void setup() {
  pinMode(BEEPER_PIN, OUTPUT);
}

void loop() {
  digitalWrite(BEEPER_PIN, HIGH); // Beeper ein
  delay(100);                     // 100 ms Ton
  digitalWrite(BEEPER_PIN, LOW);  // Beeper aus
  delay(400);                     // 400 ms Pause
}
*/




// BMP 280 test andere Version nutzen!!! (sampling)
/*
#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP280.h>

// BMP280-Objekt über I2C
Adafruit_BMP280 bmp; // I2C

void setup() {
  Serial.begin(115200);
  while (!Serial);  // Warte auf Serial Monitor (optional für Teensy)

  if (!bmp.begin(0x76)) {  // Alternativadresse prüfen: 0x76 oder 0x77
    Serial.println("BMP280 nicht gefunden. Bitte Verkabelung prüfen!");
    while (1);
  }

  // Sensor-Einstellungen für schnelles Abtasten (~100 Hz möglich)
  bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,
                  Adafruit_BMP280::SAMPLING_X2,     // Temperatur-Oversampling
                  Adafruit_BMP280::SAMPLING_X16,    // Druck-Oversampling
                  Adafruit_BMP280::FILTER_X16,      // Filter
                  Adafruit_BMP280::STANDBY_MS_1);   // Standby-Zeit (1 ms)

  Serial.println("BMP280 initialisiert.");
}

void loop() {
  Serial.print(">Temperatur:");
  Serial.println(bmp.readTemperature());


  Serial.print(">Druck:");
  Serial.println(bmp.readPressure() / 100.0);  // Pa → hPa


  delay(100);  // 10 Hz (je nach Sampling kann auch schneller)
}

*/


/*
// IMU test

#include "ICM_20948.h"

#define SERIAL_PORT Serial
#define WIRE_PORT Wire1
#define AD0_VAL 0
ICM_20948_I2C myICM; 

void setup()
{
  SERIAL_PORT.begin(115200); // Start the serial console
  delay(100);
  WIRE_PORT.begin();
  WIRE_PORT.setClock(400000);
  bool initialized = false;
  while (!initialized)
  {

    myICM.begin(WIRE_PORT, AD0_VAL);

    SERIAL_PORT.print(F("Initialization of the sensor returned: "));
    SERIAL_PORT.println(myICM.statusString());

    if (myICM.status != ICM_20948_Stat_Ok)
    {
      SERIAL_PORT.println(F("Trying again..."));
      delay(500);
    }
    else
    {
      initialized = true;
    }
  }

  SERIAL_PORT.println(F("Device connected!"));

  bool success = true; // Use success to show if the DMP configuration was successful
  success &= (myICM.initializeDMP() == ICM_20948_Stat_Ok);

  // Enable the DMP orientation sensor
  success &= (myICM.enableDMPSensor(INV_ICM20948_SENSOR_ORIENTATION) == ICM_20948_Stat_Ok);
  // Enable any additional sensors / features
  success &= (myICM.enableDMPSensor(INV_ICM20948_SENSOR_ACCELEROMETER) == ICM_20948_Stat_Ok);

  success &= (myICM.setDMPODRrate(DMP_ODR_Reg_Quat9, 0) == ICM_20948_Stat_Ok); // Set to the maximum
  success &= (myICM.setDMPODRrate(DMP_ODR_Reg_Accel, 0) == ICM_20948_Stat_Ok); // Set to the maximum

  // Enable the FIFO
  success &= (myICM.enableFIFO() == ICM_20948_Stat_Ok);
  // Enable the DMP
  success &= (myICM.enableDMP() == ICM_20948_Stat_Ok);
  // Reset DMP
  success &= (myICM.resetDMP() == ICM_20948_Stat_Ok);
  // Reset FIFO
  success &= (myICM.resetFIFO() == ICM_20948_Stat_Ok);
  // Check success
  if (success)
  {
    SERIAL_PORT.println(F("DMP enabled!"));

  }
  else
  {
    SERIAL_PORT.println(F("Enable DMP failed!"));
    SERIAL_PORT.println(F("Please check that you have uncommented line 29 (#define ICM_20948_USE_DMP) in ICM_20948_C.h..."));
    while (1)
      ;
  }
}
  // Hilfsfunktionen
  struct Vec3 {
    float x, y, z;

    // Konstruktor
    Vec3(float x = 0, float y = 0, float z = 0) : x(x), y(y), z(z) {}

    // Addition
    Vec3 operator+(const Vec3& other) const {
        return {x + other.x, y + other.y, z + other.z};
    }

    // Skalierung (Vektor * Skalar)
    Vec3 operator*(float scalar) const {
        return {x * scalar, y * scalar, z * scalar};
    }

    // Skalierung (Skalar * Vektor)
    friend Vec3 operator*(float scalar, const Vec3& v) {
        return {v.x * scalar, v.y * scalar, v.z * scalar};
    }

    // Addition mit Zuweisung (+=)
    Vec3& operator+=(const Vec3& other) {
        x += other.x; y += other.y; z += other.z;
        return *this;
    }
};
  void printVec3(Vec3 v) {
    SERIAL_PORT.print(v.x, 3);
    SERIAL_PORT.print(",");
    SERIAL_PORT.print(v.y, 3);
    SERIAL_PORT.print(",");
    SERIAL_PORT.println(v.z, 3);
  }

  void printTeleplotVec3(Vec3 v, String s) {

    SERIAL_PORT.print(">X_" + s + ":");
    SERIAL_PORT.println(v.x, 3);
    SERIAL_PORT.print(">Y_" + s + ":");
    SERIAL_PORT.println(v.y, 3);
    SERIAL_PORT.print(">Z_" + s + ":");
    SERIAL_PORT.println(v.z, 3);
  }

  struct Quaternion {
    float w, x, y, z;

    Quaternion conjugate() const {
        return {w, -x, -y, -z};
    }

    Quaternion operator*(const Quaternion& b) const {
        return {
            w*b.w - x*b.x - y*b.y - z*b.z,
            w*b.x + x*b.w + y*b.z - z*b.y,
            w*b.y - x*b.z + y*b.w + z*b.x,
            w*b.z + x*b.y - y*b.x + z*b.w

        };
    }
    Quaternion normalize() const {
      float mag = sqrt(w*w + x*x + y*y + z*z);
      if (mag == 0) return {1, 0, 0, 0}; // fallback
      return {w/mag, x/mag, y/mag, z/mag};
    }
  };

  Vec3 rotateVector(const Quaternion& q, const Vec3& v) {
    // Quaternion v als rein imaginären Vektor (w = 0)
    Quaternion qv = {0, v.x, v.y, v.z}; 
    Quaternion q_conj = q.conjugate();
    Quaternion rotated = q * qv * q_conj;

    return Vec3(rotated.x, rotated.y, rotated.z);
  }

  void printQuaternion(Quaternion q) {
    SERIAL_PORT.print(q.w, 3);
    SERIAL_PORT.print(",");
    SERIAL_PORT.print(q.x, 3);
    SERIAL_PORT.print(",");
    SERIAL_PORT.print(q.y, 3);
    SERIAL_PORT.print(",");
    SERIAL_PORT.println(q.z, 3);
  }

  Vec3 v_Rocket = {0, 0, 0};
  Vec3 p_Rocket = {0, 0, 0};
  Vec3 calib = {-0.005, 0.02, 0.007};
  Vec3 gravity = {0, 0, -1};

  unsigned long now;
  float dt;
  unsigned long last = 0;
  boolean firstloop = true;

void loop()
{

  icm_20948_DMP_data_t data;
  myICM.readDMPdataFromFIFO(&data);

  if ((myICM.status == ICM_20948_Stat_Ok) || (myICM.status == ICM_20948_Stat_FIFOMoreDataAvail)) // Was valid data available?
  {

    if (((data.header & DMP_header_bitmap_Quat9) > 0) & ((data.header & DMP_header_bitmap_Accel) > 0)) // We have asked for orientation data so we should receive Quat9
    {

      // Scale to +/- 1
      double q1 = ((double)data.Quat9.Data.Q1) / 1073741824.0; // Convert to double. Divide by 2^30
      double q2 = ((double)data.Quat9.Data.Q2) / 1073741824.0; // Convert to double. Divide by 2^30
      double q3 = ((double)data.Quat9.Data.Q3) / 1073741824.0; // Convert to double. Divide by 2^30
      double q0 = sqrt(1.0 - ((q1 * q1) + (q2 * q2) + (q3 * q3)));

      Quaternion q_IMU = {(float)q0, (float)q1, (float)q2, (float)q3};

      //q_IMU.normalize();
      //printQuaternion(q_IMU);

      //SERIAL_PORT.print(F(" Accuracy:"));
      //SERIAL_PORT.println(data.Quat9.Data.Accuracy);

      Vec3 a_IMU = {(float)data.Raw_Accel.Data.X/8192 , (float)data.Raw_Accel.Data.Y/8192 , (float)data.Raw_Accel.Data.Z/8192};
      a_IMU += calib;

      Vec3 a_Rocket = rotateVector(q_IMU, a_IMU) + gravity;

      //printTeleplotVec3(a_Rocket, "acceleration");
      //printQuaternion(q_IMU);
      //printTeleplotVec3(a_IMU, "IMU");


      // position estimates

      if(millis() > 20000)
      {

        if(firstloop)
        {
          last = micros();
          firstloop = false;
        }
        now = micros();
        dt = (now-last)/1e6f;
        //SERIAL_PORT.println(dt,6);
        last = now;
        p_Rocket += v_Rocket * dt * 0.5 + a_Rocket * dt * 0.5;
        v_Rocket += a_Rocket * dt;

        delay(10);
        printTeleplotVec3(p_Rocket, "position");
      }

    }
  }

}

*/



// ToDo
// implement GPS
// implement radio, condensator???
// implement data logging

// angle conversion to servo output

// flight script
// start
// ensure electricity
// recovery

/*
#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP280.h>
#include "ICM_20948.h"
#include <FastLED.h>
#include <BasicLinearAlgebra.h>
#include <math.h>
#include <FastLED.h>
#include <PWMServo.h>
#include <Servo.h>


// Roll motor
const int IN1 = 2;  // PWM-fähig
const int IN2 = 3
;  // PWM-fähig

// BMP280 uses 1. I2C port
Adafruit_BMP280 bmp; // I2C

float gndps;
float gndtemp;

// IMU uses 1. I2C port
#define SERIAL_PORT Serial
#define WIRE_PORT Wire
#define AD0_VAL 0
ICM_20948_I2C myICM; 

// Beeper uses digital PIN 13

const int Beeper_PIN = 13;

// LEDs use digital PIN 5 and 6

#define LED1_PIN 5
#define LED2_PIN 6
CRGB led1;
CRGB led2;

// TVC servos
const int yawServo_PIN = 28;
const int pitchServo_PIN = 29;
const int ChuteServo_PIN = 9;
PWMServo yawServo;
//yaw-outer Servo @333Hz
PWMServo pitchServo;
// pitch-inner @333Hz
Servo ChuteServo;
//standard Servo @50Hz

// Kalman

// Globale Instanzen

float z_BMP;
float z_vel_BMP;
float z_IMU;
float z_vel_IMU;
float z_merged;
float z_vel_merged;
float g = 9.81;
float dt = 0.01;
unsigned long now;
unsigned long last = 0;

float LoopTimer;
float Servotimer;
using namespace BLA;
float AltitudeKalman, VelocityVerticalKalman;

BLA::Matrix<2,2> F; BLA::Matrix<2,1> G;
BLA::Matrix<2,2> P; BLA::Matrix<2,2> Q;
BLA::Matrix<2,1> S; BLA::Matrix<1,2> H;
BLA::Matrix<2,2> I; BLA::Matrix<1,1> Acc;
BLA::Matrix<2,1> K; BLA::Matrix<1,1> R;
BLA::Matrix<1,1> L; BLA::Matrix<1,1> M;

boolean calib_kal = true;
float offset = 0;


void kalman_2d_setup(){
  F = {1, dt,
    0, 1};  
G = {0.5*dt*dt,
    dt};
H = {1, 0};
I = {1, 0,
   0, 1};
Q = G * ~G*10.0f*10.0f;
R = {30*30};
P = {0, 0,
   0, 0};
S = {0,
   0};
}

void Indicate_success(){  
  for (int i = 0; i < 4; i++){
    digitalWrite(Beeper_PIN, LOW);
    FastLED.clear();
    delay(50);
    if(i == 3){
      break;
    }
    digitalWrite(Beeper_PIN, HIGH);  // Beeper ein
    led1 = CRGB::Green;
    led2 = CRGB::Green;
    FastLED.show();
    delay(50);    
  }
}

void Indicate_waiting(){
  digitalWrite(Beeper_PIN, LOW);
  digitalWrite(Beeper_PIN, HIGH); 
  FastLED.clear();
  led1 = CRGB::Orange;    
  led2 = CRGB::Orange;
  FastLED.show();
}

void LED_setup(){
  FastLED.addLeds<WS2812B, LED1_PIN, GRB>(&led1, 1);
  FastLED.addLeds<WS2812B, LED2_PIN, GRB>(&led2, 1);
  FastLED.clear();
  FastLED.show();
}

void RollMotor_setup(){
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
}

void BMP_setup(){
  if (!bmp.begin(0x76)) {  // Alternativadresse prüfen: 0x76 oder 0x77
    Serial.println("BMP280 nicht gefunden. Bitte Verkabelung prüfen!");
    while (1);
  }

  // Sensor-Einstellungen für schnelles Abtasten (~100 Hz möglich)
  bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,
                  Adafruit_BMP280::SAMPLING_X1,     // Temperatur-Oversampling
                  Adafruit_BMP280::SAMPLING_X4,    // Druck-Oversampling
                  Adafruit_BMP280::FILTER_X4,      // Filter
                  Adafruit_BMP280::STANDBY_MS_1);   // Standby-Zeit (1 ms)

  Serial.println("BMP280 initialisiert.");
}

void IMU_setup(){
  WIRE_PORT.begin();
  WIRE_PORT.setClock(400000);
  bool initialized = false;
  while (!initialized)
  {

    myICM.begin(WIRE_PORT, AD0_VAL);

    SERIAL_PORT.print(F("Initialization of the sensor returned: "));
    SERIAL_PORT.println(myICM.statusString());

    if (myICM.status != ICM_20948_Stat_Ok)
    {
      SERIAL_PORT.println(F("Trying again..."));
      delay(500);
    }
    else
    {
      initialized = true;
    }
  }

  SERIAL_PORT.println(F("Device connected!"));

  bool success = true; // Use success to show if the DMP configuration was successful
  success &= (myICM.initializeDMP() == ICM_20948_Stat_Ok);

  // Enable the DMP orientation sensor
  success &= (myICM.enableDMPSensor(INV_ICM20948_SENSOR_ORIENTATION) == ICM_20948_Stat_Ok);
  // Enable any additional sensors / features
  success &= (myICM.enableDMPSensor(INV_ICM20948_SENSOR_ACCELEROMETER) == ICM_20948_Stat_Ok);
  success &= (myICM.enableDMPSensor(INV_ICM20948_SENSOR_GYROSCOPE) == ICM_20948_Stat_Ok);

  success &= (myICM.setDMPODRrate(DMP_ODR_Reg_Quat9, 0) == ICM_20948_Stat_Ok); // Set to the maximum
  success &= (myICM.setDMPODRrate(DMP_ODR_Reg_Accel, 0) == ICM_20948_Stat_Ok); // Set to the maximum
  success &= (myICM.setDMPODRrate(DMP_ODR_Reg_Gyro, 0) == ICM_20948_Stat_Ok); // Set to the maximum
  success &= (myICM.setDMPODRrate(DMP_ODR_Reg_Gyro_Calibr, 0) == ICM_20948_Stat_Ok); // Set to the maximum

  // Enable the FIFO
  success &= (myICM.enableFIFO() == ICM_20948_Stat_Ok);
  // Enable the DMP
  success &= (myICM.enableDMP() == ICM_20948_Stat_Ok);
  // Reset DMP
  success &= (myICM.resetDMP() == ICM_20948_Stat_Ok);
  // Reset FIFO
  success &= (myICM.resetFIFO() == ICM_20948_Stat_Ok);
  // Check success
  if (success)
  {
    SERIAL_PORT.println(F("DMP enabled!"));

  }
  else
  {
    SERIAL_PORT.println(F("Enable DMP failed!"));
    SERIAL_PORT.println(F("Please check that you have uncommented line 29 (#define ICM_20948_USE_DMP) in ICM_20948_C.h..."));
    while (1)
      ;
  }

}

void Servo_setup(){
  yawServo.attach(yawServo_PIN,760,2300); 
  pitchServo.attach(pitchServo_PIN,760,2300);
  ChuteServo.attach(ChuteServo_PIN);

  //yawServo.write();
  //pitchServo.write();
}

void BMP_calib(){
  for (int i = 0; i < 100; i++)
      {
        gndps += bmp.readPressure()/1000; // in hPa
        gndtemp += bmp.readTemperature()/10;
        delay(10);
      };
    Serial.print("air pressure at calibration:");
    Serial.println(gndps);
    Serial.print("temperature at calibration:");
    Serial.println(gndtemp);
    Serial.println("BMP280 calibrated");
}

void IMU_calib(){
  Serial.println("Please move IMU");
  //delay(20000);
  Serial.println("IMU calibrated");
}

void setup()
{
  SERIAL_PORT.begin(115200); // Start the serial console

  Indicate_success(); // delays 350ms

  Indicate_waiting();

  LED_setup();
  led1 = CRGB::Green;
  led2 = CRGB::Green;
  FastLED.show();

  RollMotor_setup();

  BMP_setup();
  BMP_calib();

  IMU_setup();
  IMU_calib();

  kalman_2d_setup();

  Servo_setup();

  Indicate_success();

  LoopTimer = micros();
}
  // Hilfsfunktionen
  // Vec3 library!!!

  struct Vec3 {
    float x, y, z;

    // Konstruktor
    Vec3(float x = 0, float y = 0, float z = 0) : x(x), y(y), z(z) {}

    // Addition
    Vec3 operator+(const Vec3& other) const {
        return {x + other.x, y + other.y, z + other.z};
    }
    // Skalierung (Vektor * Skalar)
    Vec3 operator*(float scalar) const {
        return {x * scalar, y * scalar, z * scalar};
    }
    // Skalierung (Skalar * Vektor)
    friend Vec3 operator*(float scalar, const Vec3& v) {
        return {v.x * scalar, v.y * scalar, v.z * scalar};
    }
    // Addition mit Zuweisung (+=)
    Vec3& operator+=(const Vec3& other) {
        x += other.x; y += other.y; z += other.z;
        return *this;
    }
  };

// consts for accel
Vec3 a_IMU = {0, 0, 0};
Vec3 v_IMU = {0, 0, 0};

Vec3 a_Rocket = {0, 0, 0};
Vec3 v_Rocket = {0, 0, 0};
Vec3 p_Rocket = {0, 0, 0};
Vec3 calib = {0.0, 0.0, 0.011};
Vec3 gravity = {0, 0, -9.81};
// consts for gyro
Vec3 int_rot_Rocket = {0, 0, 0};
Vec3 rot_Rocket = {0, 0, 0};
Vec3 omega_Rocket = {0, 0, 0};

  float normOfVec3(Vec3 v){
      return sqrtf(v.x*v.x+v.y*v.y+v.z*v.z);
    }

  void printVec3(Vec3 v) {
    SERIAL_PORT.print(v.x, 3);
    SERIAL_PORT.print(",");
    SERIAL_PORT.print(v.y, 3);
    SERIAL_PORT.print(",");
    SERIAL_PORT.println(v.z, 3);
  }

  void printTeleplotVec3(Vec3 v, String s) {

    SERIAL_PORT.print(">X_" + s + ":");
    SERIAL_PORT.println(v.x, 3);
    SERIAL_PORT.print(">Y_" + s + ":");
    SERIAL_PORT.println(v.y, 3);
    SERIAL_PORT.print(">Z_" + s + ":");
    SERIAL_PORT.println(v.z, 3);
  }

  struct Quaternion {
    float w, x, y, z;

    Quaternion conjugate() const {
        return {w, -x, -y, -z};
    }

    Quaternion operator*(const Quaternion& b) const {
        return {
            w*b.w - x*b.x - y*b.y - z*b.z,
            w*b.x + x*b.w + y*b.z - z*b.y,
            w*b.y - x*b.z + y*b.w + z*b.x,
            w*b.z + x*b.y - y*b.x + z*b.w

        };
    }

    Quaternion normalize() const {
      float mag = sqrt(w*w + x*x + y*y + z*z);
      if (mag == 0) return {1, 0, 0, 0}; // fallback
      return {w/mag, x/mag, y/mag, z/mag};
    }
  };

  Quaternion q_IMU;
  Quaternion q_target = {1, 0, 0, 0}; // Identitätsrotation

  Vec3 rotateVector(const Quaternion& q, const Vec3& v) {
    // Quaternion v als rein imaginären Vektor (w = 0)
    Quaternion qv = {0, v.x, v.y, v.z}; 
    Quaternion q_conj = q.conjugate();
    Quaternion rotated = q * qv * q_conj;

    return Vec3(rotated.x, rotated.y, rotated.z);
  }
  
  void printQuaternion(Quaternion q) {
    SERIAL_PORT.print(q.w, 3);
    SERIAL_PORT.print(",");
    SERIAL_PORT.print(q.x, 3);
    SERIAL_PORT.print(",");
    SERIAL_PORT.print(q.y, 3);
    SERIAL_PORT.print(",");
    SERIAL_PORT.println(q.z, 3);
  }

  Vec3 QuantToEuler(Quaternion q) {

    // roll (x-axis rotation)
    double t0 = +2.0 * (q.w * q.x + q.y * q.z);
    double t1 = +1.0 - 2.0 * (q.x * q.x + q.y * q.y);
    double roll = atan2(t0, t1) * 180.0 / PI;

    // pitch (y-axis rotation)
    double t2 = +2.0 * (q.w * q.y - q.x * q.z);
    t2 = t2 > 1.0 ? 1.0 : t2;
    t2 = t2 < -1.0 ? -1.0 : t2;
    double pitch = asin(t2) * 180.0 / PI;

    // yaw (z-axis rotation)
    double t3 = +2.0 * (q.w * q.z + q.x * q.y);
    double t4 = +1.0 - 2.0 * (q.y * q.y + q.z * q.z);
    double yaw = atan2(t3, t4) * 180.0 / PI;

    SERIAL_PORT.print(">Roll:");
    SERIAL_PORT.println(roll, 1);
    SERIAL_PORT.print(">Pitch:");
    SERIAL_PORT.println(pitch, 1);
    SERIAL_PORT.print(">Yaw:");
    SERIAL_PORT.println(yaw, 1);

    return Vec3 {yaw, pitch, roll};
  }

void BMP_signals(){
  z_BMP = bmp.readAltitude(gndps);
  //SERIAL_PORT.print(">BMP_z:");
  //SERIAL_PORT.println(z_BMP);
}

void IMU_signals(){
  icm_20948_DMP_data_t data;
  myICM.readDMPdataFromFIFO(&data);

  if ((myICM.status == ICM_20948_Stat_Ok) || (myICM.status == ICM_20948_Stat_FIFOMoreDataAvail)) // Was valid data available?
  {
    if ((data.header & DMP_header_bitmap_Quat9) > 0) // We have asked for orientation data so we should receive Quat9
    {
      // Scale to +/- 1
      double q1 = ((double)data.Quat9.Data.Q1) / 1073741824.0; // Convert to double. Divide by 2^30
      double q2 = ((double)data.Quat9.Data.Q2) / 1073741824.0; // Convert to double. Divide by 2^30
      double q3 = ((double)data.Quat9.Data.Q3) / 1073741824.0; // Convert to double. Divide by 2^30
      double q0 = sqrt(1.0 - ((q1 * q1) + (q2 * q2) + (q3 * q3)));

      q_IMU = {(float)q0, (float)q1, (float)q2, (float)q3};
      //QuantToEuler(q_IMU);
      //q_IMU.normalize();

      //Vec3 angles_IMU = QuantToEuler(q_IMU);

      //SERIAL_PORT.print(F(" Accuracy:"));
      //SERIAL_PORT.println(data.Quat9.Data.Accuracy);
    }
    else{
      Serial.println("caution! skipped quant. data");
    }
        if ((data.header & DMP_header_bitmap_Accel) > 0) // We have asked for orientation data so we should receive Quat9
    {
      a_IMU = {(float)data.Raw_Accel.Data.X/8192 , (float)data.Raw_Accel.Data.Y/8192 , (float)data.Raw_Accel.Data.Z/8192};
      a_IMU = (a_IMU + calib)*9.81;

      a_Rocket = (rotateVector(q_IMU, a_IMU) + gravity);

      //SERIAL_PORT.print(">IMU_Acc:");
      //SERIAL_PORT.println(a_Rocket.z);
      //printTeleplotVec3(a_IMU, "IMU");
      //printTeleplotVec3(a_Rocket, "acceleration");
    }
    else{
      Serial.println("caution! skipped accel. data");
    }

    if ((data.header & DMP_header_bitmap_Gyro_Calibr) > 0) // Check for Gyro
    {
      omega_Rocket = {(float)(data.Raw_Gyro.Data.X+12.1)/16.384, (float)(data.Raw_Gyro.Data.Y-7.96)/16.384, (float)(data.Raw_Gyro.Data.Z+2.44)/16.384};
      //printTeleplotVec3(omega_Rocket,"omega");
    }
    else{
      Serial.println("caution! skipped gyro. data");
    }
  }

}

void kalman_2d(){
  Acc = {a_Rocket.z};
  S=F*S+G*Acc;
  P=F*P*~F+Q;
  L=H*P*~H+R;
  K=P*~H*Inverse(L);
  M={z_BMP};
  S=S+K*(M-H*S);
  AltitudeKalman=S(0,0); 
  VelocityVerticalKalman=S(1,0); 
  P=(I-K*H)*P;
}

// Roll-PID-Parameter
float Kp_R = 1.2;
float Ki_R = 0.0;
float Kd_R = 1;

  // Pitch/Yaw-PID-Parameter demo
  float Kp_PY = 5;
  float Ki_PY = 0;
  float Kd_PY = 1;

  // Pitch/Yaw-PID-Parameter
  //float Kp_PY = 3.1;
  //float Ki_PY = 5;
  //float Kd_PY = 0.00572;


float moment_arm = 0.3;
float mass = 0.7;
//float overroll = 0;

void stabilizeRPY(){ // calculations based on gyrometer

  rot_Rocket += omega_Rocket*dt; // x, y, z entspricht yaw, pitch, roll
  //printTeleplotVec3(rot_Rocket,"rot");
  int_rot_Rocket += rot_Rocket*dt;
  //printTeleplotVec3(int_rot_Rocket, "Rotation");
  
  if(false){ //Berechnung des Fehler-Quaternions
    Quaternion q_error = q_target * (q_target.conjugate() * q_IMU).conjugate();
  }
  
  if(false){ // roll control
    float roll_output = (Kp_R * rot_Rocket.z + Ki_R * int_rot_Rocket.z + Kd_R * omega_Rocket.z)/200.0;
    
    roll_output = constrain(roll_output, -1.0f, 1.0f);
    SERIAL_PORT.print(">PID_OUT:");
    SERIAL_PORT.println(roll_output);
    
    int pwmValue = abs(roll_output * 170);//max 255
    if (roll_output < 0) {
      analogWrite(IN1, pwmValue);
      analogWrite(IN2, 0);
    } 
    else if (roll_output > 0) {
      analogWrite(IN1, 0);
      analogWrite(IN2, pwmValue);
    } 
    else {
      analogWrite(IN1, 0);
      analogWrite(IN2, 0);
    }
  }

  if(true){ // pitch and yaw control

    float yaw_moment = (Kp_PY * rot_Rocket.x/(-100.0) + Ki_PY * int_rot_Rocket.x/(-100.0) + Kd_PY * omega_Rocket.x/(-100.0)); //returns torque
    float pitch_moment = (Kp_PY * rot_Rocket.y/(-100.0) + Ki_PY * int_rot_Rocket.y/(-100.0) + Kd_PY * omega_Rocket.y/(-100.0)); //returns torque

    float yaw_TVC = asin(constrain(yaw_moment/(moment_arm*mass*normOfVec3(a_IMU)),-0.99,0.99));//conversion to angle
    float pitch_TVC = asin(constrain(pitch_moment/(moment_arm*mass*normOfVec3(a_IMU)),-0.99,0.99));

    // conversion angle to servo output, todo with MPU!!!
    yaw_TVC = yaw_TVC*(-23) + 92.5;
    pitch_TVC = pitch_TVC*23 + 82.5;


    if(false){
      if(yaw_TVC<70.0f){
       yaw_TVC = 70.0f;
      }
      if(yaw_TVC>115.0f){
        yaw_TVC = 115.0f;
      }
      if(pitch_TVC<60.0f){
        pitch_TVC = 60.0f;
      }
      if(pitch_TVC<105.0f){
        pitch_TVC = 105.0f;
      }
      int pitch_Servo_out = (int)pitch_TVC;
      int yaw_Servo_out = (int)yaw_TVC;
    }
    
    float yaw_Servo_out = constrain(yaw_TVC, 70.0f, 115.0f);
    float pitch_Servo_out = constrain(pitch_TVC, 60.0f, 105.0f);


    SERIAL_PORT.print(">PID_OUT:");
    SERIAL_PORT.println(pitch_Servo_out);
    yawServo.write((int)yaw_Servo_out); 
    pitchServo.write((int)pitch_Servo_out);
    Servotimer = millis();
  }
}


void loop()
{   

  //takes about 1.3ms
  BMP_signals();
  IMU_signals();
  //printQuaternion(q_IMU);
  //kalman_2d();
  //if(millis() > 40000)
  stabilizeRPY();

  
  if(false){
    if(calib_kal & (millis() > 10000)){
      offset = AltitudeKalman;
      calib_kal = false;
    }
  
    Serial.print(">Altitude:");
    Serial.println(AltitudeKalman - offset);
    Serial.print(">Vertical velocity:");
    Serial.println(VelocityVerticalKalman);
  }
    
  
  //Serial.print(micros()-LoopTimer);
  while (micros() - LoopTimer < dt*1e6); 
  LoopTimer=micros(); 
}


*/


/*

// SSD test

// Test Teensy SDIO with write busy in a data logger demo.
//
// The driver writes to the uSDHC controller's FIFO then returns
// while the controller writes the data to the SD.  The first sector
// puts the controller in write mode and takes about 11 usec on a
// Teensy 4.1. About 5 usec is required to write a sector when the
// controller is in write mode.

#include "SdFat.h"
#include "RingBuf.h"

// Use Teensy SDIO
#define SD_CONFIG  SdioConfig(FIFO_SDIO)

// Interval between points for 25 ksps.
#define LOG_INTERVAL_USEC 40

// Size to log 10 byte lines at 25 kHz for more than ten minutes.
#define LOG_FILE_SIZE 10*25000*600  // 150,000,000 bytes.

// Space to hold more than 800 ms of data for 10 byte lines at 25 ksps.
#define RING_BUF_CAPACITY 400*512
#define LOG_FILENAME "SdioLogger.csv"

SdFs sd;
FsFile file;

// RingBuf for File type FsFile.
RingBuf<FsFile, RING_BUF_CAPACITY> rb;

void logData() {
  // Initialize the SD.
  if (!sd.begin(SD_CONFIG)) {
    sd.initErrorHalt(&Serial);
  }
  // Open or create file - truncate existing file.
  if (!file.open(LOG_FILENAME, O_RDWR | O_CREAT | O_TRUNC)) {
    Serial.println("open failed\n");
    return;
  }
  // File must be pre-allocated to avoid huge
  // delays searching for free clusters.
  if (!file.preAllocate(LOG_FILE_SIZE)) {
     Serial.println("preAllocate failed\n");
     file.close();
     return;
  }
  // initialize the RingBuf.
  rb.begin(&file);
  Serial.println("Type any character to stop");

  // Max RingBuf used bytes. Useful to understand RingBuf overrun.
  size_t maxUsed = 0;

  // Min spare micros in loop.
  int32_t minSpareMicros = INT32_MAX;

  // Start time.
  uint32_t logTime = micros();
  // Log data until Serial input or file full.
  while (!Serial.available()) {
    // Amount of data in ringBuf.
    size_t n = rb.bytesUsed();
    if ((n + file.curPosition()) > (LOG_FILE_SIZE - 20)) {
      Serial.println("File full - quitting.");
      break;
    }
    if (n > maxUsed) {
      maxUsed = n;
    }
    if (n >= 512 && !file.isBusy()) {
      // Not busy only allows one sector before possible busy wait.
      // Write one sector from RingBuf to file.
      if (512 != rb.writeOut(512)) {
        Serial.println("writeOut failed");
        break;
      }
    }
    // Time for next point.
    logTime += LOG_INTERVAL_USEC;
    int32_t spareMicros = logTime - micros();
    if (spareMicros < minSpareMicros) {
      minSpareMicros = spareMicros;
    }
    if (spareMicros <= 0) {
      Serial.print("Rate too fast ");
      Serial.println(spareMicros);
      break;
    }
    // Wait until time to log data.
    while (micros() < logTime) {}

    // Read ADC0 - about 17 usec on Teensy 4, Teensy 3.6 is faster.
    uint16_t adc = analogRead(0);
    // Print spareMicros into the RingBuf as test data.
    rb.print(spareMicros);
    rb.write(',');
    // Print adc into RingBuf.
    rb.println(adc);
    if (rb.getWriteError()) {
      // Error caused by too few free bytes in RingBuf.
      Serial.println("WriteError");
      break;
    }
  }
  // Write any RingBuf data to file.
  rb.sync();
  file.truncate();
  file.rewind();
  // Print first twenty lines of file.
  Serial.println("spareMicros,ADC0");
  for (uint8_t n = 0; n < 20 && file.available();) {
    int c = file.read();
    if (c < 0) {
      break;
    }
    Serial.write(c);
    if (c == '\n') n++;
  }
  Serial.print("fileSize: ");
  Serial.println((uint32_t)file.fileSize());
  Serial.print("maxBytesUsed: ");
  Serial.println(maxUsed);
  Serial.print("minSpareMicros: ");
  Serial.println(minSpareMicros);
  file.close();
}
void clearSerialInput() {
  for (uint32_t m = micros(); micros() - m < 10000;) {
    if (Serial.read() >= 0) {
      m = micros();
    }
  }
}
void setup() {
  Serial.begin(9600);
  while (!Serial) {}
  // Go faster or log more channels.  ADC quality will suffer.
  // analogReadAveraging(1);
}

void loop() {
  clearSerialInput();
  Serial.println("Type any character to start");
  while (!Serial.available()) {};
  clearSerialInput();
  logData();
}

*/

/*
// gps test
#include <TinyGPSPlus.h>
#include <SoftwareSerial.h>

static const int RXPin = 0, TXPin = 1;
static const uint32_t GPSBaud = 9600;

// The TinyGPSPlus object
TinyGPSPlus gps;

// The serial connection to the GPS device
SoftwareSerial ss(RXPin, TXPin);

// This custom version of delay() ensures that the gps object
// is being "fed".
static void smartDelay(unsigned long ms)
{
  unsigned long start = millis();
  do 
  {
    while (ss.available())
      gps.encode(ss.read());
  } while (millis() - start < ms);
}

static void printFloat(float val, bool valid, int len, int prec)
{
  if (!valid)
  {
    while (len-- > 1)
      Serial.print('*');
    Serial.print(' ');
  }
  else
  {
    Serial.print(val, prec);
    int vi = abs((int)val);
    int flen = prec + (val < 0.0 ? 2 : 1); // . and -
    flen += vi >= 1000 ? 4 : vi >= 100 ? 3 : vi >= 10 ? 2 : 1;
    for (int i=flen; i<len; ++i)
      Serial.print(' ');
  }
  smartDelay(0);
}

static void printInt(unsigned long val, bool valid, int len)
{
  char sz[32] = "*****************";
  if (valid)
    sprintf(sz, "%ld", val);
  sz[len] = 0;
  for (int i=strlen(sz); i<len; ++i)
    sz[i] = ' ';
  if (len > 0) 
    sz[len-1] = ' ';
  Serial.print(sz);
  smartDelay(0);
}

static void printDateTime(TinyGPSDate &d, TinyGPSTime &t)
{
  if (!d.isValid())
  {
    Serial.print(F("********** "));
  }
  else
  {
    char sz[32];
    sprintf(sz, "%02d/%02d/%02d ", d.month(), d.day(), d.year());
    Serial.print(sz);
  }
  
  if (!t.isValid())
  {
    Serial.print(F("******** "));
  }
  else
  {
    char sz[32];
    sprintf(sz, "%02d:%02d:%02d ", t.hour(), t.minute(), t.second());
    Serial.print(sz);
  }

  printInt(d.age(), d.isValid(), 5);
  smartDelay(0);
}

static void printStr(const char *str, int len)
{
  int slen = strlen(str);
  for (int i=0; i<len; ++i)
    Serial.print(i<slen ? str[i] : ' ');
  smartDelay(0);
}

void setup()
{
  Serial.begin(115200);
  ss.begin(GPSBaud);

  Serial.println(F("FullExample.ino"));
  Serial.println(F("An extensive example of many interesting TinyGPSPlus features"));
  Serial.print(F("Testing TinyGPSPlus library v. ")); Serial.println(TinyGPSPlus::libraryVersion());
  Serial.println(F("by Mikal Hart"));
  Serial.println();
  Serial.println(F("Sats HDOP  Latitude   Longitude   Fix  Date       Time     Date Alt    Course Speed Card  Distance Course Card  Chars Sentences Checksum"));
  Serial.println(F("           (deg)      (deg)       Age                      Age  (m)    --- from GPS ----  ---- to London  ----  RX    RX        Fail"));
  Serial.println(F("----------------------------------------------------------------------------------------------------------------------------------------"));
}

void loop()
{
  
  static const double LONDON_LAT = 51.508131, LONDON_LON = -0.128002;

  printInt(gps.satellites.value(), gps.satellites.isValid(), 5);
  printFloat(gps.hdop.hdop(), gps.hdop.isValid(), 6, 1);
  printFloat(gps.location.lat(), gps.location.isValid(), 11, 6);
  printFloat(gps.location.lng(), gps.location.isValid(), 12, 6);
  printInt(gps.location.age(), gps.location.isValid(), 5);
  printDateTime(gps.date, gps.time);
  printFloat(gps.altitude.meters(), gps.altitude.isValid(), 7, 2);
  printFloat(gps.course.deg(), gps.course.isValid(), 7, 2);
  printFloat(gps.speed.kmph(), gps.speed.isValid(), 6, 2);
  printStr(gps.course.isValid() ? TinyGPSPlus::cardinal(gps.course.deg()) : "*** ", 6);

  unsigned long distanceKmToLondon =
    (unsigned long)TinyGPSPlus::distanceBetween(
      gps.location.lat(),
      gps.location.lng(),
      LONDON_LAT, 
      LONDON_LON) / 1000;
  printInt(distanceKmToLondon, gps.location.isValid(), 9);

  double courseToLondon =
    TinyGPSPlus::courseTo(
      gps.location.lat(),
      gps.location.lng(),
      LONDON_LAT, 
      LONDON_LON);

  printFloat(courseToLondon, gps.location.isValid(), 7, 2);

  const char *cardinalToLondon = TinyGPSPlus::cardinal(courseToLondon);

  printStr(gps.location.isValid() ? cardinalToLondon : "*** ", 6);

  printInt(gps.charsProcessed(), true, 6);
  printInt(gps.sentencesWithFix(), true, 10);
  printInt(gps.failedChecksum(), true, 9);
  Serial.println();
  
  smartDelay(1000);

  if (millis() > 5000 && gps.charsProcessed() < 10)
    Serial.println(F("No GPS data received: check wiring"));
}


*/

/*
#include <Arduino.h>

// radio test

HardwareSerial& hc12 = Serial8; 

void setup() {
  hc12.begin(9600); // oder deine HC-12 Baudrate
}

void loop() {
  // Nicht blockierendes Schreiben: idealerweise Daten puffern und dann senden
  const char* msg = "Hello!\n";

  if (hc12.availableForWrite() > strlen(msg)) {
    hc12.write(msg); // Achtung: write ist meist schnell, aber blockiert bei vollem Buffer
  }

  delay(1000);

}

*/

/*
//Psram test
#include<Arduino.h>

extern "C" uint8_t external_psram_size;

bool memory_ok = false;
uint32_t *memory_begin, *memory_end;

bool check_fixed_pattern(uint32_t pattern);
bool check_lfsr_pattern(uint32_t seed);

void setup()
{
	while (!Serial) ; // wait
	pinMode(13, OUTPUT);
	uint8_t size = external_psram_size;
	Serial.printf("EXTMEM Memory Test, %d Mbyte\n", size);
	if (size == 0) return;
	const float clocks[4] = {396.0f, 720.0f, 664.62f, 528.0f};
	const float frequency = clocks[(CCM_CBCMR >> 8) & 3] / (float)(((CCM_CBCMR >> 29) & 7) + 1);
	Serial.printf(" CCM_CBCMR=%08X (%.1f MHz)\n", CCM_CBCMR, frequency);
	memory_begin = (uint32_t *)(0x70000000);
	memory_end = (uint32_t *)(0x70000000 + size * 1048576);
	elapsedMillis msec = 0;
	if (!check_fixed_pattern(0x5A698421)) return;
	if (!check_lfsr_pattern(2976674124ul)) return;
	if (!check_lfsr_pattern(1438200953ul)) return;
	if (!check_lfsr_pattern(3413783263ul)) return;
	if (!check_lfsr_pattern(1900517911ul)) return;
	if (!check_lfsr_pattern(1227909400ul)) return;
	if (!check_lfsr_pattern(276562754ul)) return;
	if (!check_lfsr_pattern(146878114ul)) return;
	if (!check_lfsr_pattern(615545407ul)) return;
	if (!check_lfsr_pattern(110497896ul)) return;
	if (!check_lfsr_pattern(74539250ul)) return;
	if (!check_lfsr_pattern(4197336575ul)) return;
	if (!check_lfsr_pattern(2280382233ul)) return;
	if (!check_lfsr_pattern(542894183ul)) return;
	if (!check_lfsr_pattern(3978544245ul)) return;
	if (!check_lfsr_pattern(2315909796ul)) return;
	if (!check_lfsr_pattern(3736286001ul)) return;
	if (!check_lfsr_pattern(2876690683ul)) return;
	if (!check_lfsr_pattern(215559886ul)) return;
	if (!check_lfsr_pattern(539179291ul)) return;
	if (!check_lfsr_pattern(537678650ul)) return;
	if (!check_lfsr_pattern(4001405270ul)) return;
	if (!check_lfsr_pattern(2169216599ul)) return;
	if (!check_lfsr_pattern(4036891097ul)) return;
	if (!check_lfsr_pattern(1535452389ul)) return;
	if (!check_lfsr_pattern(2959727213ul)) return;
	if (!check_lfsr_pattern(4219363395ul)) return;
	if (!check_lfsr_pattern(1036929753ul)) return;
	if (!check_lfsr_pattern(2125248865ul)) return;
	if (!check_lfsr_pattern(3177905864ul)) return;
	if (!check_lfsr_pattern(2399307098ul)) return;
	if (!check_lfsr_pattern(3847634607ul)) return;
	if (!check_lfsr_pattern(27467969ul)) return;
	if (!check_lfsr_pattern(520563506ul)) return;
	if (!check_lfsr_pattern(381313790ul)) return;
	if (!check_lfsr_pattern(4174769276ul)) return;
	if (!check_lfsr_pattern(3932189449ul)) return;
	if (!check_lfsr_pattern(4079717394ul)) return;
	if (!check_lfsr_pattern(868357076ul)) return;
	if (!check_lfsr_pattern(2474062993ul)) return;
	if (!check_lfsr_pattern(1502682190ul)) return;
	if (!check_lfsr_pattern(2471230478ul)) return;
	if (!check_lfsr_pattern(85016565ul)) return;
	if (!check_lfsr_pattern(1427530695ul)) return;
	if (!check_lfsr_pattern(1100533073ul)) return;
	if (!check_fixed_pattern(0x55555555)) return;
	if (!check_fixed_pattern(0x33333333)) return;
	if (!check_fixed_pattern(0x0F0F0F0F)) return;
	if (!check_fixed_pattern(0x00FF00FF)) return;
	if (!check_fixed_pattern(0x0000FFFF)) return;
	if (!check_fixed_pattern(0xAAAAAAAA)) return;
	if (!check_fixed_pattern(0xCCCCCCCC)) return;
	if (!check_fixed_pattern(0xF0F0F0F0)) return;
	if (!check_fixed_pattern(0xFF00FF00)) return;
	if (!check_fixed_pattern(0xFFFF0000)) return;
	if (!check_fixed_pattern(0xFFFFFFFF)) return;
	if (!check_fixed_pattern(0x00000000)) return;
	Serial.printf(" test ran for %.2f seconds\n", (float)msec / 1000.0f);
	Serial.println("All memory tests passed :-)");
	memory_ok = true;
}

bool fail_message(volatile uint32_t *location, uint32_t actual, uint32_t expected)
{
	Serial.printf(" Error at %08X, read %08X but expected %08X\n",
		(uint32_t)location, actual, expected);
	return false;
}

// fill the entire RAM with a fixed pattern, then check it
bool check_fixed_pattern(uint32_t pattern)
{
	volatile uint32_t *p;
	Serial.printf("testing with fixed pattern %08X\n", pattern);
	for (p = memory_begin; p < memory_end; p++) {
		*p = pattern;
	}
	arm_dcache_flush_delete((void *)memory_begin,
		(uint32_t)memory_end - (uint32_t)memory_begin);
	for (p = memory_begin; p < memory_end; p++) {
		uint32_t actual = *p;
		if (actual != pattern) return fail_message(p, actual, pattern);
	}
	return true;
}

// fill the entire RAM with a pseudo-random sequence, then check it
bool check_lfsr_pattern(uint32_t seed)
{
	volatile uint32_t *p;
	uint32_t reg;

	Serial.printf("testing with pseudo-random sequence, seed=%u\n", seed);
	reg = seed;
	for (p = memory_begin; p < memory_end; p++) {
		*p = reg;
		for (int i=0; i < 3; i++) {
			// https://en.wikipedia.org/wiki/Xorshift
			reg ^= reg << 13;
			reg ^= reg >> 17;
			reg ^= reg << 5;
		}
	}
	arm_dcache_flush_delete((void *)memory_begin,
		(uint32_t)memory_end - (uint32_t)memory_begin);
	reg = seed;
	for (p = memory_begin; p < memory_end; p++) {
		uint32_t actual = *p;
		if (actual != reg) return fail_message(p, actual, reg);
		//Serial.printf(" reg=%08X\n", reg);
		for (int i=0; i < 3; i++) {
			reg ^= reg << 13;
			reg ^= reg >> 17;
			reg ^= reg << 5;
		}
	}
	return true;
}

void loop()
{
	digitalWrite(13, HIGH);
	delay(100);
	if (!memory_ok) digitalWrite(13, LOW); // rapid blink if any test fails
	delay(100);
}

*/ 

// test multimeter
/*
#include <Wire.h>
#include <INA219_WE.h>
#define I2C_ADDRESS 0x40



INA219_WE ina219 = INA219_WE(I2C_ADDRESS);

void setup() {
  Serial.begin(115200);
  Wire.begin();
   Wire.setClock(1000000);
  if(!ina219.init()){
    Serial.println("INA219 not connected!");
    while(1);
  }

  Serial.println("INA219 Current Sensor Example Sketch - Continuous");
 
}

void loop() {
  uint64_t timer = micros();
  float shuntVoltage_mV = 0.0;
  float loadVoltage_V = 0.0;
  float busVoltage_V = 0.0;
  float current_mA = 0.0;
  float power_mW = 0.0; 
  bool ina219_overflow = false;
  
  shuntVoltage_mV = ina219.getShuntVoltage_mV();
  busVoltage_V = ina219.getBusVoltage_V();
  current_mA = ina219.getCurrent_mA();
  power_mW = ina219.getBusPower();
  loadVoltage_V  = busVoltage_V + (shuntVoltage_mV/1000);
  ina219_overflow = ina219.getOverflow();
  
  Serial.print("Shunt Voltage [mV]: "); Serial.println(shuntVoltage_mV);
  Serial.print("Bus Voltage [V]: "); Serial.println(busVoltage_V);
  Serial.print("Load Voltage [V]: "); Serial.println(loadVoltage_V);
  Serial.print("Current[mA]: "); Serial.println(current_mA);
  Serial.print("Bus Power [mW]: "); Serial.println(power_mW);
  if(!ina219_overflow){
    Serial.println("Values OK - no overflow");
  }
  else{
    Serial.println("Overflow! Choose higher PGAIN");
  }
  delay(200);

}
*/


// camera test
/*
#include<Arduino.h>
// Pin-Definition
const int pin = 13;  // Du kannst diesen Pin bei Bedarf ändern

void setup() {
  pinMode(pin, OUTPUT); // Setze den Pin als Ausgang
}

void loop() {
  digitalWrite(pin, HIGH); // Schalte Pin auf HIGH
  delay(5000);             // Warte 1 Sekunde
  digitalWrite(pin, LOW);  // Schalte Pin auf LOW
  delay(1000);             // Warte 1 Sekunde
}
*/

//flash logging test 

/*

#include <LittleFS.h>

// LittleFS supports creating file systems (FS) in multiple memory types.  Depending on the 
// memory type you want to use you would uncomment one of the following constructors

LittleFS_QSPIFlash myfs;  // Used to create FS on QSPI NOR flash chips located on the bottom of the T4.1 such as the W25Q16JV*IQ/W25Q16FV,  for the full list of supported NOR flash see https://github.com/PaulStoffregen/LittleFS#nor-flash

File dataFile;  // Specifes that dataFile is of File type

int record_count = 0;
bool write_data = false;

void logData()
{
    // make a string for assembling the data to log:
    String dataString = "";
    int size = 8;
    float current[size]= {0.0};
  
    // read three sensors and append to the string:
    for (int analogPin = 0; analogPin < 3; analogPin++) {
      int sensor = analogRead(analogPin);
      dataString += String(sensor);
      if (analogPin < 2) {
        dataString += ",";
      }
    }
  
    // if the file is available, write to it:
    if (dataFile) {
      u_int64_t timer = micros();
        for (size_t i = 0; i < size; i++)
        {
          dataFile.print(current[i],5);
          if (i < (size-1)){
            dataFile.print(",");
          }
          else{
            dataFile.println();
          }
          
        }

      Serial.println(micros()-timer);
      // print to the serial port too:
      Serial.println(dataString);
      record_count += 1;
    } else {
      // if the file isn't open, pop up an error:
      Serial.println("error opening datalog.txt");
    }
    delay(4); // run at a reasonable not-too-fast speed for testing
}

void stopLogging()
{
  Serial.println("\nStopped Logging Data!!!");
  write_data = false;
  // Closes the data file.
  dataFile.close();
  Serial.printf("Records written = %d\n", record_count);
}


void dumpLog()
{
  Serial.print("\nDumping Log");
  // open the file.
  u_int64_t timer = micros();
  dataFile = myfs.open("datalog.txt");
  Serial.print(" in ");
  Serial.print(micros()-timer);
  Serial.println(" ms.");

  // if the file is available, write to it:
  if (dataFile) {
    while (dataFile.available()) {
      Serial.write(dataFile.read());
    }
    dataFile.close();
  }  
  // if the file isn't open, pop up an error:
  else {
    Serial.println("error opening datalog.txt");
  } 
}

void menu()
{
  Serial.println();
  Serial.println("Menu Options:");
  Serial.println("\tl - List files on disk");
  Serial.println("\te - Erase files on disk");
  Serial.println("\ts - Start Logging data (Restarting logger will append records to existing log)");
  Serial.println("\tx - Stop Logging data");
  Serial.println("\td - Dump Log");
  Serial.println("\th - Menu");
  Serial.println();
}

void printSpaces(int num) {
  for (int i=0; i < num; i++) {
    Serial.print(" ");
  }
}

void printDirectory(File dir, int numSpaces) {
   while(true) {
     File entry = dir.openNextFile();
     if (! entry) {
       //Serial.println("** no more files **");
       break;
     }
     printSpaces(numSpaces);
     Serial.print(entry.name());
     if (entry.isDirectory()) {
       Serial.println("/");
       printDirectory(entry, numSpaces+2);
     } else {
       // files have sizes, directories do not
       printSpaces(36 - numSpaces - strlen(entry.name()));
       Serial.print("  ");
       Serial.println(entry.size(), DEC);
     }
     entry.close();
   }
}

void printDirectory(FS &fs) {
  Serial.println("Directory\n---------");
  printDirectory(fs.open("/"), 0);
  Serial.println();
}



void listFiles()
{
  Serial.print("\n Space Used = ");
  Serial.println(myfs.usedSize());
  Serial.print("Filesystem Size = ");
  Serial.println(myfs.totalSize());

  printDirectory(myfs);
}

void eraseFiles()
{
  myfs.quickFormat();  // performs a quick format of the created di
  Serial.println("\nFiles erased !");
}


void setup()
{

  // Open serial communications and wait for port to open:
  Serial.begin(115200);
  while (!Serial) {
    // wait for serial port to connect.
  }
  Serial.println("\n" __FILE__ " " __DATE__ " " __TIME__);

  Serial.print("Initializing LittleFS ...");

  // see if the Flash is present and can be initialized:
  if (!myfs.begin()) {
    Serial.printf("Error starting %s\n", "QSPI FLASH");
    while (1) {
      // Error, so don't do anything more - stay stuck here
    }
  }
  Serial.println("LittleFS initialized.");
  
  menu();
  
}

void loop()
{ 
  if ( Serial.available() ) {
    char rr;
    rr = Serial.read();
    switch (rr) {
      case 'l': listFiles(); break;
      case 'e': eraseFiles(); break;
      case 's':
        {
          Serial.println("\nLogging Data!!!");
          write_data = true;   // sets flag to continue to write data until new command is received
          // opens a file or creates a file if not present,  FILE_WRITE will append data to
          // to the file created.
          dataFile = myfs.open("datalog.txt", FILE_WRITE);
          logData();
        }
        break;
      case 'x': stopLogging(); break;
      case 'd': dumpLog(); break;
      case '\r':
      case '\n':
      case 'h': menu(); break;
    }
    while (Serial.read() != -1) ; // remove rest of characters.
  } 

  if(write_data) logData();
}


*/


// high frequency servo test
/*
#include <PWMServo.h>
#include<Arduino.h>
#include <I2Cdev.h>
#include <MPU6050.h>
#include "Wire.h"

MPU6050 accelgyro;

int16_t ax, ay, az;
int16_t gx, gy, gz;

#define OUTPUT_READABLE_ACCELGYRO

bool blinkState = false;

PWMServo myservo;
PWMServo myservo2;  // create servo object to control a servo

float servo_position;



void MPU6500_setup(){

  // join I2C bus (I2Cdev library doesn't do this automatically)
    #if I2CDEV_IMPLEMENTATION == I2CDEV_ARDUINO_WIRE
        Wire.begin();
    #elif I2CDEV_IMPLEMENTATION == I2CDEV_BUILTIN_FASTWIRE
        Fastwire::setup(400, true);
    #endif

    // initialize serial communication
    // (38400 chosen because it works as well at 8MHz as it does at 16MHz, but
    // it's really up to you depending on your project)
    Serial.begin(115200);

    // initialize device
    Serial.println("Initializing I2C devices...");
    accelgyro.initialize();

    // verify connection
    Serial.println("Testing device connections...");
    Serial.println(accelgyro.testConnection() ? "MPU6050 connection successful" : "MPU6050 connection failed");

    // use the code below to change accel/gyro offset values
    
    Serial.println("Updating internal sensor offsets...");
    // -76	-2359	1688	0	0	0


    accelgyro.setXGyroOffset(0);// /4
    accelgyro.setYGyroOffset(0);
    accelgyro.setZGyroOffset(0);
    accelgyro.setXAccelOffset(0);
    accelgyro.setYAccelOffset(0);
    accelgyro.setZAccelOffset(0);

    Serial.print(accelgyro.getXAccelOffset()); Serial.print("\t"); // -76
    Serial.print(accelgyro.getYAccelOffset()); Serial.print("\t"); // -2359
    Serial.print(accelgyro.getZAccelOffset()); Serial.print("\t"); // 1688
    Serial.print(accelgyro.getXGyroOffset()); Serial.print("\t"); // 0
    Serial.print(accelgyro.getYGyroOffset()); Serial.print("\t"); // 0
    Serial.print(accelgyro.getZGyroOffset()); Serial.print("\t"); // 0
    Serial.print("\n");

}

void Servo_setup(){
  myservo.attach(0,760,2300);  // attaches the servo on pin 9 to the servo object
  myservo2.attach(1,760,2300);

  servo_position = 85;
  myservo.write(servo_position); 
  myservo2.write(servo_position); 
  delay(500);
}

void setup() {

  Serial.begin(115200);

  Servo_setup();

  MPU6500_setup();

}

unsigned long checkStart;
float angleX = 0, angleY = 0, angleZ = 0;
uint64_t timekeep;


void MPU6500_signals(){

//int sum = 0;

  //int sum = 0;
  //int64_t gx_sum = 0;
  //int64_t gy_sum = 0;
  //int64_t gz_sum = 0;

  // read raw accel/gyro measurements from device
  accelgyro.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

  float gyroX = (gx+21.3)/16.348;  // je nach config
  float gyroY = (gy-5.2)/16.348;
  float gyroZ = (gz-7.1)/16.348;

  float dt = 0.002;

  angleX += gyroX * dt;
  angleY += gyroY * dt;
  angleZ += gyroZ * dt;


  //Serial.print(">AngleX:");
  //Serial.println(angleX);
  //Serial.print(">AngleY:");
  //Serial.println(angleY);
  //Serial.print(">AngleZ:");
  //Serial.println(angleZ);

  //Serial.print(">time:");
  //Serial.println(millis()-checkStart);
    
  //Serial.print("offset gx: ");
  //Serial.println(gx_sum/(double)sum);
  //Serial.print("offset gy: ");
  //Serial.println(gy_sum/(double)sum);
  //Serial.print("offset zx: ");
  //Serial.println(gz_sum/(double)sum);
}

void checkResponse(){
  unsigned long loopStart = micros();
  MPU6500_signals();
  if(true){
    Serial.print(">AngleZ:");
    Serial.println(angleZ);
    Serial.print(">time:");
    Serial.println(millis()-checkStart);
    Serial.print(">Servo:");
    Serial.println(servo_position);
  }
  if(false){
    Serial.print(millis()-timekeep);
    Serial.print(", ");
    Serial.print(servo_position);
    Serial.print(", ");
    Serial.println(angleX);
  }
  
  while (micros() - loopStart < 2000) {
    // Nichts tun (Busy-Wait)
  }

  //Serial.print("here");
}

uint8_t delaytime = 1000;

void loop() {
  
    //outer Servo (60-105)
    // inner Servo (70-115)

  myservo.write(70);
  delay(delaytime);
  myservo2.write(60);
  delay(delaytime);
  myservo.write(115);
  delay(delaytime);
  myservo2.write(105);
  delay(delaytime);
  
}

*/

/*
#include <LittleFS.h>

// nicht mir LittleFS ohne spikes alle 55kb möglich :(

// ===== QSPI-LittleFS Setup =====
LittleFS_QSPIFlash myfs;
File logFile;

// ===== Parameter =====
static const uint32_t LOOP_HZ   = 250;
static const uint32_t LOOP_US   = 1000000UL / LOOP_HZ;   // 4000 µs
static const uint32_t LOG_BYTES = 4UL * 1024UL * 1024UL; // 4 MB Datei
static const size_t   NUM_WORDS = 20;                    // 20 × int16_t
static const size_t   REC_BYTES = 4 + NUM_WORDS * 2;     // 44 B / Datensatz
static const size_t PAGE_SIZE = 512;                     // Schreibblock statt 256


// ===== Record-Struktur =====
typedef struct __attribute__((packed,aligned(4))) {
  uint32_t ts_us;
  int16_t  v[NUM_WORDS];
} Record;

// ===== Globale Variablen =====
static uint32_t logOffset = 0;
static uint32_t t_next    = 0;
static uint8_t  pageBuf[PAGE_SIZE];
static size_t   pageFill  = 0;
bool logging = false, paused = false;

// ===== Helper: Open ab Anfang (kein Append) =====
File openWriteFromBegin(const char* path) {
#ifdef FILE_WRITE_BEGIN
  return myfs.open(path, FILE_WRITE_BEGIN);
#else
  File f = myfs.open(path, FILE_WRITE);
  if (f) f.seek(0);
  return f;
#endif
}

// ===== Pre-Allokation (4 MB 0xFF) =====
// ======================================================
// 1) Pre-Allokation + Öffnen ab Dateianfang (kein Append)
//    -> inkl. optionalem "Warm-up", um den ersten Commit
//       vor den Messbetrieb zu verlagern.
// ======================================================
bool preallocateAndOpen(const char* path) {
  if (logFile) logFile.close();
  Serial.printf("Pre-allocating %lu bytes (0xFF)…\n", (unsigned long)LOG_BYTES);

  // Datei anlegen & mit 0xFF füllen (blockierend – gewollt)
  File f = myfs.open(path, FILE_WRITE);              // Erstellen/Größe setzen
  if (!f) { Serial.println("open failed (prealloc)"); return false; }

  const size_t BU = 4096;
  static uint8_t ff[BU];
  memset(ff, 0xFF, sizeof(ff));

  f.seek(0);
  for (uint32_t off = 0; off < LOG_BYTES; off += BU) {
    size_t n = (LOG_BYTES - off >= BU) ? BU : (LOG_BYTES - off);
    if (f.write(ff, n) != n) {
      Serial.println("prealloc write failed");
      f.close();
      return false;
    }
  }
  f.flush();     // hier darf es dauern
  f.close();

  // Für den Messbetrieb OHNE Append ab Anfang öffnen:
#ifdef FILE_WRITE_BEGIN
  logFile = myfs.open(path, FILE_WRITE_BEGIN);
#else
  logFile = myfs.open(path, FILE_WRITE);
  if (logFile) logFile.seek(0);
#endif
  if (!logFile) { Serial.println("open failed (logging)"); return false; }

  // Schreibe von Anfang an, kein seek() mehr während des Betriebs
  logOffset = 0;
  pageFill  = 0;
  logFile.seek(0);

  // ---------- Optionales "Warm-up" (empfohlen) ----------
  // ein paar KB schreiben & flushen, damit der erste größere
  // FS-Commit vor den eigentlichen Messdaten passiert.
  {
    static uint8_t warm[1024];
    memset(warm, 0xFF, sizeof(warm));
    for (int i = 0; i < 4; ++i) logFile.write(warm, sizeof(warm)); // 4 KB
    logFile.flush();
    // zurück zum Start für den echten Log
    logFile.seek(0);
    logOffset = 0;
  }
  // ------------------------------------------------------

  Serial.println("Pre-allocation done. Logging file open.");
  return true;
}


// ===== Erase / List =====
void eraseFS() { Serial.println("Formatting FS…"); myfs.quickFormat(); Serial.println("done."); }
void listFiles() {
  Serial.print("\nSpace Used = "); Serial.println(myfs.usedSize());
  Serial.print("Filesystem = "); Serial.println(myfs.totalSize());
  File dir = myfs.open("/"); Serial.println("Directory:");
  while (true) {
    File e = dir.openNextFile(); if (!e) break;
    Serial.printf(" %-20s %u B\n", e.name(), (unsigned)e.size());
    e.close();
  }
}

// ===== Datenquelle =====
void makeSample(Record& r) {
  r.ts_us = micros();
  for (size_t i = 0; i < NUM_WORDS; ++i)
    r.v[i] = (int16_t)random(-32768, 32767);
}

// ===== Schreiben direkt in Datei =====
// =======================================
// 2) flushPage() – ohne seek(), cursor-basiert
//    (seek() wurde bereits EINMAL vorab
//     auf 0 gesetzt; write() erhöht logOffset)
// =======================================
void flushPage() {
  if (!logFile || pageFill == 0) return;

  // Optional: Schutz, nicht über LOG_BYTES hinaus schreiben
  if (logOffset + pageFill > LOG_BYTES) {
    size_t clamp = LOG_BYTES - logOffset;
    if ((int32_t)clamp <= 0) { pageFill = 0; return; }
    size_t w = logFile.write(pageBuf, clamp);
    if (w != clamp) Serial.println("[WARN] write() short/failed (clamp)");
    logOffset += w;
    pageFill = 0;
    return;
  }

  // Direkt schreiben (KEIN seek() hier!)
  size_t w = logFile.write(pageBuf, pageFill);
  if (w != pageFill) Serial.println("[WARN] write() short/failed");
  logOffset += w;
  pageFill = 0;
}


void writeRecord(const Record& r) {
  if (!logFile) return;
  const uint8_t* p = (const uint8_t*)&r;
  for (size_t i = 0; i < sizeof(r); ++i) {
    pageBuf[pageFill++] = p[i];
    if (pageFill >= PAGE_SIZE) flushPage();
  }
}

// ===== Dump-Hilfen =====
static inline bool isAllFF(const uint8_t* p, size_t n) {
  for (size_t i = 0; i < n; ++i) if (p[i] != 0xFF) return false;
  return true;
}
uint32_t findUsedLength(File& f, uint32_t cap) {
  const size_t CH = 4096; static uint8_t buf[CH];
  uint32_t used=0,last=0; f.seek(0);
  while (used < cap) {
    size_t n = (cap - used >= CH) ? CH : (cap - used);
    int r = f.read(buf, n); if (r <= 0) break;
    if (!isAllFF(buf, r)) last = used + r;
    used += r;
  }
  return (last / REC_BYTES) * REC_BYTES;
}
void dumpCSV(File& f, uint32_t maxB) {
  Serial.print("ts_us");
  for (int i=0;i<(int)NUM_WORDS;++i){Serial.print(",int");Serial.print(i);}
  Serial.println();
  Record r;
  uint32_t readB=0;
  while (readB+REC_BYTES<=maxB) {
    if (f.read((uint8_t*)&r, REC_BYTES)!=REC_BYTES) break;
    readB+=REC_BYTES;
    Serial.print(r.ts_us);
    for (size_t i=0;i<NUM_WORDS;++i){Serial.print(',');Serial.print(r.v[i]);}
    Serial.println();
  }
  Serial.println("<end>");
}

// ===== Dump-Varianten =====
static const char* LOG_PATH = "/log_i16_ts.bin";
void dumpCurrent() {
  Serial.println("\nDump current session:");
  if (logOffset+pageFill==0){Serial.println("(no data)");return;}
  flushPage(); File f=myfs.open(LOG_PATH); if(!f){Serial.println("open failed");return;}
  dumpCSV(f, logOffset); f.close();
}
void dumpExisting() {
  Serial.println("\nDump existing file (auto-len):");
  File f=myfs.open(LOG_PATH); if(!f){Serial.println("open failed");return;}
  uint32_t len=findUsedLength(f,LOG_BYTES);
  if(!len){Serial.println("(empty)");f.close();return;}
  f.seek(0); dumpCSV(f,len); f.close();
}

// ===== Menü =====
void menu() {
  Serial.println("\nCommands:");
  Serial.println(" s=start (prealloc+log)  p=pause  x=stop");
  Serial.println(" d=dump current  D=dump existing  l=list  e=erase  h=help");
}

// ===== Hauptlogik =====
void setup() {
  Serial.begin(115200);
  while(!Serial&&millis()<3000){}
  Serial.println("\nTeensy 4.1 – 250 Hz QSPI Flash Logger");
  if(!myfs.begin()){Serial.println("Flash init FAILED");while(1){}}
  Serial.println("LittleFS ready.");
  randomSeed(analogRead(A0)^micros());
  t_next=micros()+LOOP_US;
  menu();
}

void loop() {
  // ---- Konsole ----
  if (Serial.available()) {
    char c=Serial.read();
    switch(c){
      case 'e': eraseFS(); break;
      case 'l': listFiles(); break;
      case 's': logging=false;paused=false;
                if(preallocateAndOpen(LOG_PATH)){logging=true;Serial.println("Logging started.");} break;
      case 'p': paused=true;Serial.println("Paused.");break;
      case 'x': logging=false;flushPage();Serial.printf("Stopped. Bytes =%lu\n",(unsigned long)logOffset);
                if(logFile)logFile.close();break;
      case 'd': dumpCurrent();break;
      case 'D': dumpExisting();break;
      case 'h': menu();break;
    }
    while(Serial.read()!=-1){}
  }

  // ---- 250 Hz Loop ----
  uint32_t now=micros();
  if((int32_t)(now-t_next)>=0){
    uint32_t t0=micros();
    if(logging&&!paused){
      Record r; makeSample(r);
      writeRecord(r);
    }
    uint32_t loopTime=micros()-t0;
    if(loopTime>LOOP_US)
      Serial.printf("\n⚠️ Loop %lu us (> %lu) off=%lu\n",
        (unsigned long)loopTime,(unsigned long)LOOP_US,(unsigned long)logOffset);
    t_next+=LOOP_US;
    if((int32_t)(micros()-t_next)>10*(int32_t)LOOP_US)
      t_next=micros()+LOOP_US;
  }
}
*/