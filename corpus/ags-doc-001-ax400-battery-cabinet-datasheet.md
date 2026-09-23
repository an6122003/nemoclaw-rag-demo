# AX-400 Battery Cabinet — Product Datasheet

**Document ID:** AGS-DOC-001
**Revision:** C
**Effective date:** 2025-08-12
**Supersedes:** AGS-DOC-001 Rev B (2025-02-03)
**Product:** AX-400 battery cabinet, part number AGS-AX400-372
**Manufacturer:** Aurora Grid Systems, Inc., 4820 Kestrel Parkway, Building C, Boulder, CO 80301, USA

## 1. Description

The AX-400 is a single-enclosure lithium iron phosphate (LFP) battery cabinet for behind-the-meter and distribution-connected commercial and industrial sites. It ships fully assembled, charged to 40% state of charge (SoC), and is commissioned as a DC-coupled resource with a Comet C2 site controller and one or more Helios H3 power conversion systems.

The AX-400 is not interchangeable with the AX-600. The two cabinets use different battery module part numbers, different nominal DC bus voltages, different cooling methods and different service clearances. They must never be paralleled onto a shared DC bus, and a mixed string requires written approval from AGS Application Engineering.

## 2. Electrical specification

| Parameter | Value |
|---|---|
| Usable energy | 372 kWh |
| Nameplate (gross) energy | 400 kWh |
| Cell chemistry | LFP (lithium iron phosphate) |
| Battery module | AGS-M48-100 |
| Modules per cabinet | 8 |
| Racks per cabinet | 4 |
| Nominal DC voltage | 768 V |
| DC operating range | 672-876 V |
| Maximum continuous charge power | 186 kW |
| Maximum continuous discharge power | 186 kW |
| Peak discharge power | 260 kW for 10 s |
| Round-trip efficiency | 94.5% |
| Maximum C-rate | 0.5C |
| Cycle life | 6,000 cycles at 80% depth of discharge (DoD), 25 °C |
| DC terminal | M12 stud, 25 N·m |
| Ground stud | M10, 12 N·m |

## 3. Mechanical and environmental

| Parameter | Value |
|---|---|
| Enclosure | 2.0 mm galvanized steel, RAL 7035 |
| Ingress protection | IP54 |
| Cooling | Forced air, 4 x axial fans |
| Dimensions (W x D x H) | 1,200 x 800 x 2,100 mm |
| Weight (as shipped) | 2,850 kg |
| Operating temperature | -20 °C to +50 °C |
| Thermal derate threshold | Above +40 °C, see AGS-DOC-011 |
| Storage temperature | -30 °C to +60 °C |
| Relative humidity | 5% to 95%, non-condensing |
| Maximum altitude | 2,000 m without derate |
| Acoustic noise | 62 dBA at 1 m |
| Front service clearance | 1,000 mm |

## 4. Communications and compliance

The cabinet exposes Modbus TCP and CAN 2.0B. Cell voltages, temperatures and contactor states are polled by the Comet C2 site controller. Fire suppression is available as an option using two AGS-FS-40 aerosol canisters.

Certified to UL 9540, UL 1973 and IEC 62619. Battery modules are listed to UN 38.3 for transport.

## 5. Ordering

| Configuration | Part number |
|---|---|
| AX-400 cabinet, 372 kWh | AGS-AX400-372 |
| Aerosol suppression option | AGS-AX400-FS |
| Spare battery module | AGS-M48-100 |
| Spare fan assembly | AGS-FAN-2201 |

Technical support: support@auroragrid.example, +1-800-555-0142.
