# Grid-Code Compliance Notes

**Document ID:** AGS-DOC-020
**Revision:** D
**Effective date:** 2025-05-30
**Applies to:** Helios H3 (AGS-H3-250) with Comet C2 (AGS-C2-SC)

## 1. Scope

This note summarises the grid-support functions implemented by the Helios H3 and the grid-code profiles shipped with Comet C2 firmware. It is a compliance summary, not a substitute for the interconnection agreement. The authority having jurisdiction governs.

## 2. Certifications

The Helios H3 is certified to UL 1741 SB, IEEE 1547-2018, IEC 62477-1, IEC 62109-1 and IEC 62109-2. The Comet C2 is a controller and does not itself hold a grid-protection listing; protection is provided by the Helios H3 and, where required, by a site protection relay.

## 3. Shipped grid profiles

| Region | Profile | Standard |
|---|---|---|
| United States | US-CAT3 | IEEE 1547-2018 Category III |
| European Union | EU-50549-2 | EN 50549-2 |
| Australia | AU-4777-2 | AS/NZS 4777.2 |
| United Kingdom | UK-G99 | ENA Engineering Recommendation G99 |

The profile is set at the factory. Changing the profile requires AGS Field Service to unlock the profile menu; the customer cannot change it from Aurora Cloud.

## 4. Ride-through settings

| Function | Default |
|---|---|
| Voltage ride-through, low | 2 s at 0.5 pu |
| Voltage ride-through, high | 1 s at 1.2 pu |
| Frequency ride-through, 60 Hz nominal | 57.0-62.0 Hz |
| Frequency ride-through, 50 Hz nominal | 47.0-52.0 Hz |
| Anti-islanding trip time | 2 s |
| Reconnect delay after trip | 300 s |

Hold times and trip thresholds are set by the selected profile and must not be adjusted to satisfy a local requirement without written AGS approval, because doing so invalidates the UL 1741 SB listing.

## 5. Grid-support functions

The H3 provides volt-var, volt-watt and frequency-watt control. The power factor range is **±0.85**, and reactive capability is **±250 kvar** at rated AC power. The default volt-var curve for the US-CAT3 profile is a four-point curve with a deadband of ±0.02 pu.

Frequency-watt droop is shipped disabled on the US-CAT3 profile and enabled at 3% droop on EU-50549-2. Confirm the setting against the interconnection agreement before energization.

## 6. Interaction with battery state of charge

Grid-support functions are limited by available battery headroom. The Comet C2 reserves 5% of usable energy at each end of the SoC window for grid-support response, so a cabinet dispatched to its normal limits still has reserve to answer a frequency event. For an AX-400 this reserves 18.6 kWh at each end; for an AX-600 it reserves 27.9 kWh at each end.

## 7. Site documentation

Maintain at the site: the interconnection agreement, the as-built single-line diagram, the protection settings record, the grid profile declaration and the most recent protection test report. AGS Field Service signs the grid profile declaration at commissioning.

## 8. Changes and re-validation

Any change to protection settings, the grid profile or the PCS firmware major version requires re-validation and a new signed declaration. Contact grid@auroragrid.example for the re-validation procedure.
