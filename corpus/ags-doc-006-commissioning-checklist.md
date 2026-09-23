# Site Commissioning Checklist

**Document ID:** AGS-DOC-006
**Revision:** E
**Effective date:** 2025-07-15
**Applies to:** All AGS BESS sites using AX-series cabinets, Helios H3 and Comet C2

## 1. How to use this checklist

Complete every step in order and record the measured value in the site commissioning record. Steps marked **HOLD** require AGS Field Service or a customer witness before proceeding. Do not mark a step complete on the basis of a previous site's results.

## 2. Pre-energization

| # | Step | Acceptance criterion | HOLD |
|---|---|---|---|
| 1 | Verify cabinet nameplate | Part number matches the bill of materials | No |
| 2 | Verify torque marks on all DC terminations | Witness mark aligned; AX-400 at 25 N·m, AX-600 at 35 N·m | Yes |
| 3 | Insulation resistance, each pole to ground | ≥ 1 MΩ at 1,000 V DC | No |
| 4 | Ground electrode resistance | ≤ 5 Ω | No |
| 5 | Coolant level and pressure (AX-600 only) | 38 L nominal fill; 2.5 bar nominal | No |
| 6 | Fire suppression canisters seated (if fitted) | Two AGS-FS-40 units, indicators green | No |
| 7 | Controller firmware version | 3.7.4 minimum; 3.8.2 recommended | No |

## 3. Energization and bring-up

1. Close the AC feed to the Helios H3 and confirm the PCS self-test completes with no active faults.
2. Close each cabinet DC disconnect. Wait the interval required by the governing safety bulletin before opening any module access cover (see AGS-DOC-010).
3. Confirm CAN discovery: every cabinet appears in the Comet C2 device list within 60 s.
4. Confirm the controller management address. Factory default is **192.168.10.40**; change it if it conflicts with the site LAN and record the new address.
5. Confirm the Modbus TCP server port matches the installed firmware: 1502 on firmware 3.8.0 and 3.8.1, and 502 on firmware 3.7.4 and 3.8.2 and later.
6. Set the site time zone and confirm NTP synchronization to within 2 s.

## 4. Functional tests

| Test | Method | Acceptance criterion |
|---|---|---|
| Charge test | Command 50% of rated power for 30 min | No fault; power within ±3% of setpoint |
| Discharge test | Command 50% of rated power for 30 min | No fault; power within ±3% of setpoint |
| SoC calibration | Full charge to 100%, hold 30 min | Reported SoC 98-100%; cell delta ≤ 50 mV |
| Comms failover | Unplug WAN for 10 min | No telemetry gap after reconnect |
| Emergency stop | Press site E-stop | All DC contactors open within 2 s |

## 5. Soak and handover

Run a 24-hour soak with the site in automatic dispatch mode. Zero unplanned faults are permitted during the soak; any fault resets the soak clock. After a clean soak, upload the commissioning record to Aurora Cloud, confirm the site appears with a valid AGS-SITE-XXXXXX identifier, and obtain customer sign-off.
