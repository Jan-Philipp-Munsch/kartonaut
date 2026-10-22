#include "KalmanZ.h"

KalmanZ::KalmanZ(){
  F = {1, 0,
       0, 1};
  G = {0,0};
  H = {1, 0};
  P = {0, 0,
       0, 0};
  Q = {0, 0,
       0, 0};
  R = {30*30};  // default; wird via setMeasStd() überschrieben
  S = {0,0};
}

void KalmanZ::setDt(float dt, float sigma_acc){
  F = { 1, dt,
        0, 1 };
  G = { 0.5f*dt*dt,
        dt };
  Q = G * ~G * (sigma_acc*sigma_acc);
}

void KalmanZ::setMeasStd(float std_m){
  R = { std_m * std_m };
}

void KalmanZ::setState(float z0_m, float vz0_ms){
  S = { z0_m, vz0_ms };
}

void KalmanZ::setPDiag(float pz_var, float pv_var){
  P = { pz_var, 0,
        0,      pv_var };
}

void KalmanZ::step(float accel_z, float z_meas, float& z_est, float& vz_est){
  // Predict
  BLA::Matrix<1,1> Acc = {accel_z};
  S = F*S + G*Acc;
  P = F*P*~F + Q;

  // Update
  auto L = H*P*~H + R;          // 1x1
  auto K = P*~H*Inverse(L);     // 2x1
  BLA::Matrix<1,1> M = {z_meas};
  S = S + K*(M - H*S);
  P = (BLA::Matrix<2,2>{1,0,0,1} - K*H)*P;

  z_est  = S(0,0);
  vz_est = S(1,0);
}

