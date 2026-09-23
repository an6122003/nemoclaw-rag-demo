# AGS Canonical Facts (authoring control sheet — NOT part of corpus/)

Use ASCII hyphen for numeric ranges. Use °C, N·m, ±, Ω exactly as written here.

## AX-400 battery cabinet — AGS-AX400-372
usable 372 kWh | nameplate 400 kWh | module AGS-M48-100 | 8 modules, 4 racks
nominal DC 768 V | range 672-876 V | cont 186 kW charge/discharge | peak 260 kW for 10 s
RTE 94.5% | 0.5C | 6,000 cycles @ 80% DoD, 25 °C | forced air, 4 axial fans
IP54 | -20 °C to +50 °C (derate above +40 °C) | storage -30 °C to +60 °C
1,200 x 800 x 2,100 mm | 2,850 kg | DC lug 25 N·m | ground stud 12 N·m
front clearance 1,000 mm | top 600 mm | acoustic 62 dBA at 1 m | altitude 2,000 m
aerosol suppression option 2 x AGS-FS-40 | UL 9540, UL 1973, IEC 62619
faults: F-0312 fan failure, F-0101 DC overvoltage

## AX-600 battery cabinet — AGS-AX600-558
usable 558 kWh | nameplate 600 kWh | module AGS-M48-120 | 12 modules, 6 racks
nominal DC 1,152 V | range 1,008-1,314 V | cont 279 kW charge/discharge | peak 390 kW for 30 s
RTE 95.2% | 0.5C | 8,000 cycles @ 80% DoD, 25 °C | liquid cooled, 50% propylene glycol / 50% water
coolant volume 38 L | nominal coolant pressure 2.5 bar
IP55 | -25 °C to +50 °C (derate above +45 °C) | storage -30 °C to +60 °C
1,200 x 1,100 x 2,100 mm | 4,180 kg | DC lug 35 N·m | ground stud 12 N·m
front clearance 1,200 mm | acoustic 58 dBA at 1 m | altitude 2,000 m
faults: F-0207 coolant flow low

## Helios H3 PCS — AGS-H3-250
250 kW | 400 V AC 3-phase 4-wire | 50/60 Hz | max AC current 361 A
DC input 600-1,500 V | max DC current 400 A | peak eff 98.2% | CEC 97.6%
three-level NPC bidirectional | liquid cooled | IP66 | -30 °C to +55 °C
800 x 650 x 2,050 mm | 620 kg | AC lug 45 N·m | DC lug 35 N·m | THD < 3%
reactive ±250 kvar | IEEE 1547-2018, UL 1741 SB, IEC 62477-1
firmware 4.4.1 (2025-04-22), previous 4.3.0 | file AGS-H3-FW-4.4.1.bin

## Comet C2 site controller — AGS-C2-SC
quad-core ARM Cortex-A53 1.5 GHz | 4 GB RAM | 32 GB eMMC
2 x 1 GbE | 2 x RS-485 isolated | 1 x CAN 2.0B | 4 DI, 2 DO
24 V DC ±10%, 35 W | IP40 DIN-rail (35 mm) | -20 °C to +60 °C
max 64 managed devices | on-box log retention 730 days
default IP 192.168.10.40 | default Modbus TCP port 502 (3.8.2+); 1502 (3.8.0/3.8.1)
protocols Modbus TCP/RTU, DNP3, IEC 61850 MMS, SunSpec
firmware 3.7.4 (2024-09-30), 3.8.0 (2025-02-14), 3.8.1 (2025-02-28), 3.8.2 (2025-06-02)

## Aurora Cloud
portal https://cloud.auroragrid.example | MQTT over TLS 1.2 port 8883
default push interval 60 s | 1-minute retention 13 months | 15-minute retention 60 months
REST API, OAuth 2.0 | edge gateway AGS-EG-2 | SLA 99.9% | onboarding 5 business days
site ID format AGS-SITE-XXXXXX

## Safety bulletins
SB-2024-03 effective 2024-05-10: DC disconnect wait 5 minutes. SUPERSEDED.
SB-2025-01 URGENT effective 2025-03-17, supersedes SB-2024-03: wait 12 minutes + verify < 50 V DC.
SB-2025-04 effective 2025-07-01: AX-400 above +40 °C derate charge to 60%, discharge to 70%.

## Warranty / RMA / spares
AX cabinet warranty 10 years or cycle limit (6,000 AX-400 / 8,000 AX-600), max 12 years from shipment
Helios H3 5 years | Comet C2 5 years | retention >= 70% usable energy at year 10
RMA format RMA-YYYY-NNNNN | critical response 4 business hours | standard 1 business day
restocking 15% within 90 days | core return 30 calendar days | UN 38.3 Class 9 UN3480
spares: AGS-M48-100, AGS-M48-120, AGS-FAN-2201, AGS-PUMP-6602, AGS-FILT-6603,
AGS-FS-40, AGS-CTRL-3300, AGS-PSU-3305, AGS-GW-4401, AGS-CBL-7702, AGS-EG-2

## Maintenance
quarterly 90 days visual | semi-annual 180 days torque + IR scan | annual 12 months capacity test
AX-600 coolant replacement 60 months | AX-600 coolant filter 24 months
AX-400 fan assembly 40,000 operating hours | IR delta-T > 15 °C escalate
IR test >= 1 MΩ at 1,000 V DC | 72-hour notice before scheduled maintenance

## Site
150 mm reinforced concrete pad, 3,000 psi | front 1,000/1,200 mm | rear 150 mm | sides 300 mm
top 600 mm | cabinet-to-cabinet 300 mm | fence 2.1 m | ground <= 5 Ω | trench 600 mm
IEEE 1547-2018 Category III | EN 50549-2 | AS/NZS 4777.2 | power factor ±0.85
voltage ride-through 2 s at 0.5 pu | frequency 57.0-62.0 Hz (60 Hz) / 47.0-52.0 Hz (50 Hz)
