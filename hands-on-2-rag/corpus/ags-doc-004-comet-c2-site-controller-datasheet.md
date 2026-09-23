# Comet C2 Site Controller — Product Datasheet

**Document ID:** AGS-DOC-004
**Revision:** C
**Effective date:** 2025-06-18
**Supersedes:** AGS-DOC-004 Rev B (2025-02-20)
**Product:** Comet C2 site controller, part number AGS-C2-SC
**Manufacturer:** Aurora Grid Systems, Inc., Boulder, CO 80301, USA

## 1. Description

The Comet C2 is the site-level controller for AGS microgrid and storage installations. It aggregates telemetry from AX-series battery cabinets and Helios H3 power conversion systems, executes the site dispatch schedule, enforces grid-code profiles, buffers data during network outages, and forwards telemetry to Aurora Cloud.

The Comet C2 is a DIN-rail device rated IP40 and must be installed inside a NEMA 1 or better enclosure. It is not a power conversion device and does not perform AC grid protection; that function belongs to the Helios H3 and the site protection relay.

## 2. Hardware specification

| Parameter | Value |
|---|---|
| Processor | Quad-core ARM Cortex-A53, 1.5 GHz |
| Memory | 4 GB RAM |
| Storage | 32 GB eMMC |
| Ethernet | 2 x 1 GbE |
| Serial | 2 x RS-485, isolated |
| Fieldbus | 1 x CAN 2.0B |
| Digital inputs | 4 |
| Digital outputs | 2, dry contact |
| Power supply | 24 V DC ±10%, 35 W |
| Mounting | 35 mm DIN rail |
| Ingress protection | IP40 |
| Operating temperature | -20 °C to +60 °C |
| On-box log retention | 730 days |

## 3. Capacity and protocols

A single Comet C2 manages up to 64 devices (any combination of AX-400, AX-600 and Helios H3 units) with a polling floor of 1 s. Supported protocols are Modbus TCP, Modbus RTU, DNP3, IEC 61850 MMS and SunSpec Modbus.

The factory default management address is **192.168.10.40** with a /24 subnet mask. The default Modbus TCP server port depends on firmware: firmware 3.8.0 and 3.8.1 listen on port **1502**, while firmware 3.7.4 and firmware 3.8.2 and later listen on port **502**. See AGS-DOC-013 and AGS-DOC-014.

## 4. Firmware

| Version | Release date | Status |
|---|---|---|
| 3.7.4 | 2024-09-30 | Supported |
| 3.8.0 | 2025-02-14 | Superseded |
| 3.8.1 | 2025-02-28 | Superseded |
| 3.8.2 | 2025-06-02 | Current generally available |

Firmware is installed by uploading `AGS-C2-FW-<version>.bin` through the local web interface or Aurora Cloud. The controller reboots once during installation; the process takes approximately 210 s.

## 5. Aurora Cloud integration

The Comet C2 uploads to Aurora Cloud over MQTT with TLS 1.2 on port 8883. The default push interval is 60 s. Up to 730 days of local history is retained, so short WAN outages do not create telemetry gaps. Device onboarding requires a site ID in the format AGS-SITE-XXXXXX.

## 6. Ordering

| Item | Part number |
|---|---|
| Comet C2 site controller | AGS-C2-SC |
| Spare controller board | AGS-CTRL-3300 |
| Spare 24 V power supply | AGS-PSU-3305 |

Technical support: support@auroragrid.example, +1-800-555-0142.
