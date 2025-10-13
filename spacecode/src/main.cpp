
// ToDo
// implement GPS
// implement radio

// angle conversion to servo output

// flight script
// start
// ensure electricity
// recovery
// Vec3 Library+aufräumen
// Exmem


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
#include <LittleFS.h>
#include <INA219_WE.h>

// HC12 radio

HardwareSerial& hc12 = Serial8; 

// 5V-Loop Multimeter

#define I2C_ADDRESS 0x40
INA219_WE ina219 = INA219_WE(I2C_ADDRESS);

// Flash Logger

LittleFS_QSPIFlash myfs;  // Used to create FS on QSPI NOR flash chips located on the bottom of the T4.1 such as the W25Q16JV*IQ/W25Q16FV,  for the full list of supported NOR flash see https://github.com/PaulStoffregen/LittleFS#nor-flash

File dataFile;  // Specifes that dataFile is of File type

int record_count = 0;
bool write_data = false;

// Roll motor
const int IN1 = 2;  // PWM-fähig
const int IN2 = 3;  // PWM-fähig

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

float shuntVoltage_mV = 0.0;
float loadVoltage_V = 0.0;
float busVoltage_V = 0.0;
float current_mA = 0.0;
float power_mW = 0.0; 

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

Quaternion q_IMU;
Quaternion q_target = {1, 0, 0, 0}; // Identitätsrotation

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


// setup functions

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
  // entfernt:   WIRE_PORT.begin();
  //WIRE_PORT.setClock(400000);
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

  SERIAL_PORT.println(F("ICM20948 initialisiert."));

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

void LittleFS_setup(){
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

  write_data = true;   // sets flag to continue to write data until new command is received
  // opens a file or creates a file if not present,  FILE_WRITE will append data to
  // to the file created.
  dataFile = myfs.open("datalog.txt", FILE_WRITE);
}

void INA_setup() {

  if(!ina219.init()){
    Serial.println("INA219 not connected!");
    while(1);
  }
  Serial.println("INA219 initialisiert");
 
}

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

void HC12_setup(int baudrate){
  hc12.begin(baudrate); // oder deine HC-12 Baudrate
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
  Wire.begin();
  Wire.setClock(1000000);

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

  LittleFS_setup();

  INA_setup();

  HC12_setup(9600);

  Indicate_success();

  LoopTimer = micros();
  
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

void INA_signals(){
  bool ina219_overflow = false;
  
  shuntVoltage_mV = ina219.getShuntVoltage_mV();
  busVoltage_V = ina219.getBusVoltage_V();
  current_mA = ina219.getCurrent_mA();
  power_mW = ina219.getBusPower();
  loadVoltage_V  = busVoltage_V + (shuntVoltage_mV/1000);
  ina219_overflow = ina219.getOverflow();
  
  if(false){
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

void stabilizeRPY(){ // calculations based on gyrometer

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

void logFloatArray(float* array, int size)
{ 
  // if the file is available, write to it:
  if (dataFile) {
    u_int64_t timer = micros();
      for (int i = 0; i < size; i++)
      {
        dataFile.print(array[i],5);
        if (i < (size-1)){
          dataFile.print(",");
        }
        else{
          dataFile.println();
        }
        
      }

    //Serial.println(micros()-timer);
    // print to the serial port too:
    record_count += 1;
  } else {
    // if the file isn't open, pop up an error:
    Serial.println("error opening datalog.txt");
  }

}

void loop()
{   

  //takes about 1.3ms
  //BMP_signals();
  //IMU_signals();
  //INA_signals();
  //printQuaternion(q_IMU);
  //stabilizeRPY();

  //float daten[] = {1.0, 2.0, 3.0};
  //logFloatArray(daten, 3);

  const char* msg = "Hello! How are you? BlaBliBlub\n";

  if (hc12.availableForWrite() > strlen(msg)) {
    hc12.write(msg); // Achtung: write ist meist schnell, aber blockiert bei vollem Buffer
  }

  if(false){

    kalman_2d();

    if(calib_kal & (millis() > 10000)){
      offset = AltitudeKalman;
      calib_kal = false;
    }
  
    Serial.print(">Altitude:");
    Serial.println(AltitudeKalman - offset);
    Serial.print(">Vertical velocity:");
    Serial.println(VelocityVerticalKalman);
  }
   
  Serial.println(micros()-LoopTimer);
  while (micros() - LoopTimer < dt*1e6); 
  LoopTimer=micros(); 

  return;
}