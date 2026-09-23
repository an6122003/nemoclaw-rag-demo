# Arc-Flash and DC Hazard Analysis Summary

**Document ID:** AGS-DOC-027
**Revision:** A
**Effective date:** 2025-05-12
**Applies to:** AX-400 (AGS-AX400-372), AX-600 (AGS-AX600-558), Helios H3 (AGS-H3-250)

## 1. Scope and limitations

This document summarises the incident-energy and shock-hazard analysis performed by AGS for AX-series cabinets and the Helios H3. It is a design summary. The site operator is responsible for producing a site-specific arc-flash label and an energized-work permit under NFPA 70E.

## 2. DC bus parameters used in the analysis

| Parameter | AX-400 | AX-600 |
|---|---|---|
| Nominal DC voltage | 768 V | 1,152 V |
| Maximum DC voltage | 876 V | 1,314 V |
| Available short-circuit current | 22 kA | 31 kA |
| Bolted-fault clearing time | 40 ms | 40 ms |

The higher voltage and higher available fault current of the AX-600 produce a materially higher incident energy than the AX-400 at the same working distance. Do not apply AX-400 working distances to an AX-600.

## 3. Incident energy

At the recommended working distance and with the cabinet doors closed and latched, incident energy is at or below 1.2 cal/cm² for both cabinet models, which permits work with ordinary arc-rated clothing. Opening a module access cover raises incident energy:

| Task | AX-400 | AX-600 | Minimum PPE category |
|---|---|---|---|
| Doors closed, external measurement | 1.1 cal/cm² | 1.2 cal/cm² | 4 cal/cm² clothing |
| Module access cover removed | 6.8 cal/cm² | 11.4 cal/cm² | 12 cal/cm² clothing |
| DC terminal work, covers removed | 8.9 cal/cm² | 15.6 cal/cm² | 20 cal/cm² clothing |

For any task above 12 cal/cm², use a remote racking or remote measurement tool and treat the work as energized work requiring a permit.

## 4. Shock hazard

The AX-400 maximum DC voltage of 876 V and the AX-600 maximum of 1,314 V both exceed the 50 V threshold for arc and shock hazard. Class 0 insulating gloves rated 1,000 V AC / 1,500 V DC are required for the AX-400 and are the minimum for the AX-600; AGS recommends Class 2 gloves for AX-600 DC terminal work.

## 5. Residual energy

Both cabinets retain charge on the internal DC link after the disconnect is opened. The residual-energy hazard is governed by urgent safety bulletin **SB-2025-01**, which requires a **12-minute wait** and a below-50 V DC verification before any cover is removed. The 5-minute interval formerly published in SB-2024-03 is withdrawn.

## 6. Arc-flash boundary

The arc-flash boundary at 1.2 cal/cm² is 1,400 mm for the AX-400 and 2,300 mm for the AX-600 with covers removed. Barricade the boundary and post the label before any cover is opened.

## 7. Training and records

All personnel performing work on AGS equipment must hold current NFPA 70E qualified-person status for DC systems above 1,000 V where the AX-600 is installed. Retain training records and arc-flash labels for the life of the site.
