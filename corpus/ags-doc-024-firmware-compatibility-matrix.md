# Firmware Compatibility Matrix

**Document ID:** AGS-DOC-024
**Revision:** B
**Effective date:** 2025-08-15
**Applies to:** Comet C2 (AGS-C2-SC) and Helios H3 (AGS-H3-250)

## 1. Purpose

This matrix states which firmware versions may be combined on a single site and which are supported by AGS. Combinations outside this matrix are not supported and void the performance guarantee.

## 2. Comet C2 firmware status

| Version | Release date | Status | Default Modbus TCP port | Notes |
|---|---|---|---|---|
| 3.7.4 | 2024-09-30 | Supported | 502 | Last release without Aggressive Rebalance |
| 3.8.0 | 2025-02-14 | Superseded | 1502 | Introduced Aggressive Rebalance; port change |
| 3.8.1 | 2025-02-28 | Superseded | 1502 | Hotfix for a CAN re-init defect |
| 3.8.2 | 2025-06-02 | **Current** | 502 | Removes Aggressive Rebalance; restores port 502 |

## 3. Helios H3 firmware status

| Version | Release date | Status | Notes |
|---|---|---|---|
| 4.3.0 | 2024-11-08 | Supported | Harmonic mitigation mode enabled |
| 4.4.1 | 2025-04-22 | **Current** | Harmonic mitigation mode reverted; see section 5 |

## 4. Supported combinations

| Comet C2 | Helios H3 | Supported | Comment |
|---|---|---|---|
| 3.8.2 | 4.4.1 | Yes | Recommended for all new sites |
| 3.8.2 | 4.3.0 | Yes | Allowed until the site completes re-validation |
| 3.7.4 | 4.4.1 | Yes | No SCADA change required, because both use port 502 |
| 3.7.4 | 4.3.0 | Yes | Legacy combination, supported |
| 3.8.0 or 3.8.1 | 4.4.1 | No | Modbus port mismatch risk; upgrade the controller |
| 3.8.0 or 3.8.1 | 4.3.0 | No | Same reason |

A site may not run Comet C2 3.8.0 or 3.8.1 with any Helios H3 release. AGS Support will not troubleshoot a site on an unsupported combination until the controller is upgraded to 3.8.2.

## 5. Reverted feature — Helios H3 harmonic mitigation

Helios H3 firmware 4.3.0 introduced an Active Front End harmonic mitigation mode intended to reduce low-order current harmonics below 2%. Field measurements at 11 sites showed that the mode could excite a resonance with site capacitor banks at 5th and 7th harmonic, producing current distortion above the grid-code limit. The mode was therefore reverted in firmware 4.4.1 and is no longer selectable. This is the reason firmware 4.3.0 remains supported rather than being withdrawn: sites that never enabled the mode are unaffected, and a forced upgrade is not justified.

## 6. Firmware update policy

Update firmware only during a planned outage. Take a configuration backup first. Confirm that the new combination appears in section 4 before starting. Record the resulting versions in the Aurora Cloud site record; the record is used to determine warranty and support eligibility.
