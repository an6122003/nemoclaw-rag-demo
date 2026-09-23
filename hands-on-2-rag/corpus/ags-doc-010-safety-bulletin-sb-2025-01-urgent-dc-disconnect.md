# SAFETY BULLETIN SB-2025-01 (URGENT) — Revised DC Disconnect and Lockout Sequence for AX-Series Cabinets

**Document ID:** AGS-DOC-010
**Bulletin number:** SB-2025-01
**Severity:** **URGENT — MANDATORY ACTION**
**Effective date:** 2025-03-17
**Supersedes:** SB-2024-03 (AGS-DOC-009), effective 2024-05-10
**Action required by:** 2025-04-30

## 1. Summary

This bulletin **supersedes SB-2024-03 in its entirety**. The 5-minute wait interval published in SB-2024-03 is withdrawn and must not be used. All personnel performing work inside an AX-series battery cabinet must apply the revised sequence below immediately.

## 2. Why this bulletin was issued

Bench testing at 25 °C underestimated the DC-link discharge time constant at low temperature. AGS re-tested AX-400 and AX-600 cabinets at -20 °C and at end-of-life capacitance (80% of nameplate). At -20 °C the measured time to fall below 50 V DC was 9 minutes 40 seconds on the AX-400 and 10 minutes 25 seconds on the AX-600. The previous 5-minute interval therefore did not provide an adequate margin.

Two additional near-miss events have been reported since SB-2024-03 was issued. Neither resulted in injury.

## 3. Affected products

All AX-400 (AGS-AX400-372) and AX-600 (AGS-AX600-558) battery cabinets, all manufacture dates, all firmware versions. There are no exceptions for cabinets with the revised contactor firmware; the firmware shortens but does not eliminate the discharge time.

## 4. Required action

After opening the cabinet DC disconnect, and before removing any module access cover or touching any DC terminal:

1. Apply a lockout/tagout device to the disconnect handle and verify the handle cannot be moved.
2. **Wait a minimum of 12 minutes.** This interval is mandatory and replaces the 5-minute interval in SB-2024-03.
3. Verify absence of voltage at the DC terminals using a meter rated CAT III 1,500 V DC. **Confirm the reading is below 50 V DC** before proceeding.
4. If the reading is 50 V DC or greater, wait an additional 5 minutes and re-measure. Repeat until the reading is below 50 V DC.
5. Only then remove the module access cover.

The 12-minute interval applies to both cabinets. The AX-600 requires the full 12 minutes even though its measured discharge at -20 °C was slightly longer; AGS has elected to publish a single conservative interval so that a technician working on a mixed site cannot apply the wrong value.

## 5. Documentation and training

Update all site switching procedures and permit-to-work forms to reference SB-2025-01. Retrain all affected technicians by 2025-04-30 and retain the training record for audit. Printed copies of SB-2024-03 must be removed from site binders.

## 6. Contact

Urgent technical support: +1-800-555-0142 (24x7) or support@auroragrid.example.
