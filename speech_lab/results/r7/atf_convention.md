# EasyCom head/array frame convention (determined from Device_ATFs.h5)

Device_ATFs.h5 (h5py view): IR (768 samples @ 48 kHz, 1020 directions, 6 channels); RealTF/ImagTF (385 bins);
Theta (polar from up, 5..156 deg, 17 values), Phi (0..354 deg, 6 deg steps, 60 values).

Test: inter-mic delays of ch1,3,4 relative to ch2, measured by 32x-upsampled cross-correlation of the measured IRs
over all 1020 directions, compared with free-field predictions from the README mic positions (mm, relative to the
tracked pose; X left, Y up, Z forward) for two hypotheses of the Phi direction.

| hypothesis | median |delay error| | corr(meas, pred) |
|---|---|---|
| u = (sinT sinP, cosT, sinT cosP): Phi increases toward +X (LEFT), i.e. counter-clockwise seen from above | 20 us | 0.966 |
| u = (-sinT sinP, cosT, sinT cosP): Phi increases toward the right | 221 us | -0.26 |
| forward flipped | 103 us | - |

Conclusion (used throughout round 7):
- Head frame = tracked-pose rigid-body frame: X left, Y up, Z forward (the README mic positions are consistent with this:
  ch1 x=+82 mm is left, ch2 z=+30 mm front-centre, ch3/ch4 right; clockwise from above = left -> front -> right).
- Azimuth az = atan2(x, z): 0 = straight ahead (array forward), +90 = left. Elevation el = atan2(y, hypot(x, z)) = 90 - Theta.
- ATF Phi == az, ATF Theta == 90 - el. The 20 us residual is consistent with head/frame scattering (not free field).
- Example: Theta=90, Phi=90 (source on the left): ch1 leads ch2 by 240 us, ch3/ch4 lag by 253/427 us.
