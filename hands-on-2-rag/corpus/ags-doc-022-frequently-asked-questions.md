# Frequently Asked Questions

**Document ID:** AGS-DOC-022
**Revision:** D
**Effective date:** 2025-08-05

## 1. Products and selection

**What is the difference between the AX-400 and the AX-600?**
The AX-400 stores 372 kWh usable at a nominal 768 V DC and is air cooled with four axial fans. The AX-600 stores 558 kWh usable at a nominal 1,152 V DC and is liquid cooled. They use different battery modules (AGS-M48-100 versus AGS-M48-120) and different DC lug torque values (25 N·m versus 35 N·m). They cannot share a DC bus.

**Can I mix AX-400 and AX-600 cabinets at one site?**
Only with written approval from AGS Application Engineering. Each model must feed its own Helios H3 on its own DC bus. They must never be paralleled on a shared DC bus.

**How many cabinets can one Comet C2 manage?**
Up to 64 devices in any combination, with a polling floor of 1 s.

## 2. Installation and commissioning

**What is the minimum front clearance for an AX-600?**
1,200 mm. The AX-400 needs 1,000 mm. The extra clearance on the AX-600 is required for coolant service access.

**What torque do I use on the DC terminals?**
25 N·m on the AX-400 and 35 N·m on the AX-600. Both use an M12 stud. Using the wrong value is the most common cause of hot-spot faults.

**How long is the commissioning soak test?**
24 hours of continuous automatic dispatch with zero unplanned faults.

## 3. Firmware and networking

**What is the default Modbus TCP port on the Comet C2?**
It depends on the firmware. Firmware 3.7.4 and 3.8.2 and later use port 502. Firmware 3.8.0 and 3.8.1 use port 1502. The current generally available release is 3.8.2, which uses 502.

**Which firmware version should I deploy?**
3.8.2. It is the current generally available release and restores the Modbus port to 502, so it can be installed directly from 3.7.4 with no SCADA change.

**Is Aggressive Rebalance still available?**
No. It was introduced in firmware 3.8.0 and deprecated and removed in 3.8.2.

**What is the default IP address of the Comet C2?**
192.168.10.40 with a /24 mask.

## 4. Maintenance

**How often do I replace the AX-600 coolant filter?**
Every 24 months. The coolant itself is replaced every 60 months. The AX-400 has no coolant loop and therefore no coolant filter.

**How often do I replace the AX-400 fans?**
At 40,000 operating hours, using part number AGS-FAN-2201.

**What infrared temperature difference is acceptable?**
A difference of more than 15 °C between comparable joints or modules requires escalation before returning to full dispatch.

## 5. Safety

**How long must I wait after opening the DC disconnect before removing a module cover?**
12 minutes, per urgent safety bulletin SB-2025-01 (effective 2025-03-17). The older 5-minute interval from SB-2024-03 is withdrawn and must not be used. After waiting, verify the terminals measure below 50 V DC.

**Does the 12-minute wait apply to the AX-400 as well as the AX-600?**
Yes. SB-2025-01 publishes a single interval that applies to both cabinets.

## 6. Warranty and returns

**How long is the AX-600 warranty?**
10 years or 8,000 cycles at 80% DoD, whichever comes first, capped at 12 years from shipment.

**What RMA priority applies when the whole site is down?**
Critical, acknowledged within 4 business hours.

**Which products are eligible for advance replacement?**
The Comet C2 site controller only.
