# Preventive Maintenance Schedule

**Document ID:** AGS-DOC-007
**Revision:** D
**Effective date:** 2025-07-01
**Applies to:** AX-400, AX-600, Helios H3, Comet C2

## 1. Intervals

Maintenance is calendar-based from the commissioning date, except where an operating-hour interval is stated. Give AGS and the site operator at least 72 hours notice before any scheduled maintenance visit that will interrupt dispatch.

| Interval | Scope |
|---|---|
| Quarterly (90 days) | Visual inspection, filter and canister check, log review |
| Semi-annual (180 days) | Torque verification, infrared thermography, coolant top-up check |
| Annual (12 months) | Capacity test, coolant analysis, firmware audit, protection test |

## 2. Quarterly tasks

1. Inspect cabinet exterior for corrosion, water ingress and damaged door gaskets.
2. Confirm the AX-400 fan assemblies rotate freely and the intake filters are clean. Replace filters if pressure drop is visibly high.
3. On the AX-600, confirm the coolant sight glass shows no bubbles and the pump reports no vibration alarm.
4. Inspect the AGS-FS-40 aerosol canisters, if fitted, and confirm the pressure indicator is in the green band.
5. Download the fault log and confirm no unresolved F-series faults are open.

## 3. Semi-annual tasks

1. Verify DC terminal torque. Use **25 N·m** on the AX-400 and **35 N·m** on the AX-600. Re-apply the witness mark after any adjustment.
2. Verify the ground stud torque of **12 N·m** on every cabinet.
3. Perform infrared thermography on all DC terminations and module interconnects under load. A temperature difference greater than **15 °C** between comparable joints or modules requires escalation to AGS Field Service before the site returns to full dispatch.
4. Inspect the Helios H3 liquid loop for leaks and confirm the reservoir is between the MIN and MAX marks.

## 4. Annual tasks

1. Perform an insulation resistance test at 1,000 V DC; the result must be **1 MΩ or greater**.
2. Perform a capacity test by discharging at 0.5C to the low-voltage cutoff and comparing delivered energy to nameplate. Record the result against the warranty retention curve.
3. Draw a coolant sample from each AX-600 and analyse for glycol concentration, pH and conductivity. Replace the coolant if glycol falls below 45% by volume.
4. Audit firmware against AGS-DOC-024 and update any device outside the supported matrix.
5. Test the site emergency stop and verify all DC contactors open within 2 s.

## 5. Replacement consumables

| Item | Interval | Part number |
|---|---|---|
| AX-400 fan assembly | 40,000 operating hours | AGS-FAN-2201 |
| AX-600 coolant filter | 24 months | AGS-FILT-6603 |
| AX-600 coolant | 60 months | AGS-CLT-6604 |
| Aerosol suppression canister | 10 years | AGS-FS-40 |

Record every replaced part with its serial number. Consumables replaced within the warranty period under a warranty claim must be returned per AGS-DOC-016.
