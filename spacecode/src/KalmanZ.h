#pragma once
#include <BasicLinearAlgebra.h>
using namespace BLA;

struct KalmanZ {
  // States: [z, vz]^T
  BLA::Matrix<2,2> F;
  BLA::Matrix<2,1> G;
  BLA::Matrix<2,2> P;
  BLA::Matrix<2,2> Q;
  BLA::Matrix<2,1> S;   // state
  BLA::Matrix<1,2> H;
  BLA::Matrix<1,1> R;

  KalmanZ();

  // Model mit gemessenem dt anpassen
  void setDt(float dt, float sigma_acc);

  // Tuning/Init bequem verstellbar:
  void setMeasStd(float std_m);             // R = std^2
  void setState(float z0_m, float vz0_ms);  // initialer Zustand
  void setPDiag(float pz_var, float pv_var);// initiale Unsicherheit

  // Filter-Schritt
  void step(float accel_z, float z_meas, float& z_est, float& vz_est);
};


