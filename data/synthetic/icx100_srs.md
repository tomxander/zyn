# ICX-100 Instrument Cluster Software Requirements Specification

Synthetic document written for the Zyn prototype harness. The ICX-100 is a fictional product. This document has no relation to any OEM or supplier specification.

## 1 Introduction

This document specifies the software behaviour of the ICX-100, a fictional 12.3-inch digital instrument cluster for a passenger vehicle. It is intended for software developers and test engineers.

## 2 Abbreviations

| Term | Meaning |
|---|---|
| DTC | Diagnostic trouble code |
| ECU | Electronic control unit |
| IGN | Ignition |

## 3 Power modes

3.1 The cluster shall enter the ACTIVE state within 1.5 s of IGN changing from OFF to ON.

3.2 When IGN changes from ON to OFF, the cluster shall display the goodbye screen for 3 s and then enter the SLEEP state.

3.3 In the SLEEP state, the cluster shall draw no more than 0.1 mA from the battery supply.

3.4 The cluster should wake up quickly when a door is opened.

## 4 Speedometer

4.1 The cluster shall display vehicle speed received in the VehicleSpeed signal, in km/h or mph according to the unit setting.

4.2 The displayed speed shall never be lower than the actual vehicle speed and shall not exceed it by more than 10 percent plus 4 km/h.

4.3 The speed value shall be updated at least every 100 ms.

Note: Over-reading is permitted so that the driver is never shown a speed lower than the true speed.

## 5 Tachometer

5.1 The cluster shall display engine speed from the EngineSpeed signal as a needle on a scale from 0 to 8000 rpm.

5.2 The red zone of the scale shall start at the value given by the configuration parameter RedlineRpm.

## 6 Fuel level

6.1 The cluster shall display the fuel level as a bar graph with eight segments.

6.2 The fuel level display shall be filtered so that it does not fluctuate when the vehicle is driving on an incline.

6.3 When the fuel level is below 10 percent, the low-fuel telltale shall be lit.

## 7 Telltales

7.1 The cluster shall control the telltales listed in Table 1 according to the stated input signal and colour.

Table 1: Telltales

| Telltale | Input signal | Colour | Behaviour |
|---|---|---|---|
| Brake system warning | BrakeWarn = 1 | Red | Steady on |
| Seat belt reminder | BeltUnfastened = 1 and vehicle speed above 20 km/h | Red | Flashing at 1 Hz |
| Low fuel | FuelLow = 1 | Amber | Steady on |
| Engine malfunction | MIL = 1 | Amber | Steady on |

7.2 At each transition to the ACTIVE state, all telltales in Table 1 shall be lit for 2 s as a bulb check.

7.3 Red telltales shall have priority over amber telltales.

7.4 A telltale whose input signal has not been received for more than 500 ms shall be lit and a DTC shall be stored.

## 8 Chimes

8.1 The cluster shall play the seat belt chime while the seat belt reminder telltale is flashing.

8.2 The chime volume should be adequate for all driving conditions.

8.3 If two chimes are requested at the same time, the cluster shall play the chime with the higher priority as defined in the chime priority list.

## 9 Steering wheel controls

9.1 The driver shall be able to scroll through the trip computer pages using the up and down buttons on the left steering wheel switch.

9.2 A long press of the OK button for more than 2 s shall reset the selected trip counter.

9.3 The cluster may offer a menu to change the display theme.

## 10 Vehicle network communication

10.1 The cluster shall communicate on the powertrain CAN bus at a bit rate of 500 kbit/s.

10.2 If a CAN signal is not received within three times its cycle time, the cluster shall treat the signal as invalid.

10.3 The cluster shall transmit the ClusterStatus message every 100 ms.

10.4 After a bus-off event, the cluster shall attempt recovery as specified in the network management document.

## 11 Diagnostics

11.1 The cluster shall store a DTC when the display backlight driver reports a fault.

11.2 Stored DTCs shall be readable by a diagnostic tester.

11.3 The cluster shall perform a display self-test at startup and report the result.

## 12 Software update

12.1 The cluster software shall be updatable through the diagnostic connector.

12.2 A software update shall be accepted only if its digital signature is valid.

12.3 If an update fails, the cluster shall return to the previously installed software version.

## 13 Cybersecurity

13.1 Diagnostic services that write memory shall require successful security access authentication.

13.2 The cluster shall protect cryptographic keys appropriately.

## 14 Functional safety

14.1 The cluster shall monitor the displayed state of the brake system warning telltale and detect a mismatch with the requested state within 200 ms.

14.2 If a mismatch is detected, the cluster shall display a text warning.

## 15 Performance

15.1 The cluster shall display the first frame within 2 s of power-up.

15.2 The graphics shall run smoothly at all times.

15.3 CPU load shall not exceed 70 percent averaged over any 1 s window.
