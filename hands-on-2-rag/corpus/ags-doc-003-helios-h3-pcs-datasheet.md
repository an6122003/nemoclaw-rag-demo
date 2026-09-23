# Helios H3 Power Conversion System — Product Datasheet

**Document ID:** AGS-DOC-003
**Revision:** B
**Effective date:** 2025-05-20
**Supersedes:** AGS-DOC-003 Rev A (2024-10-07)
**Product:** Helios H3 bidirectional power conversion system, part number AGS-H3-250
**Manufacturer:** Aurora Grid Systems, Inc., Boulder, CO 80301, USA

## 1. Description

The Helios H3 is a three-level neutral-point-clamped (NPC) bidirectional power conversion system (PCS) that couples an AGS DC battery bus to a three-phase AC grid. It performs DC-to-AC discharge, AC-to-DC charge, reactive power support, and grid-forming or grid-following operation depending on the configured grid profile. One Helios H3 nominally serves 372 kWh to 600 kWh of AX-series storage.

The H3 is liquid cooled and has no external fans. It is delivered with a factory-set grid profile and must be re-profiled by AGS Field Service before energization on a grid operating under a different code (see AGS-DOC-020).

## 2. AC specification

| Parameter | Value |
|---|---|
| Rated AC power | 250 kW |
| AC output voltage | 400 V AC, three-phase, four-wire |
| AC frequency | 50/60 Hz |
| Maximum AC current | 361 A |
| Power factor range | ±0.85 |
| Reactive power capability | ±250 kvar |
| Current THD | < 3% at rated power |
| AC terminal | M12 stud, 45 N·m |
| Grid support functions | Volt-var, volt-watt, frequency-watt |

## 3. DC specification

| Parameter | Value |
|---|---|
| DC input range | 600-1,500 V |
| Maximum DC input current | 400 A |
| Maximum DC power | 260 kW |
| DC terminal | M12 stud, 35 N·m |
| Pre-charge | Internal, 8 s ramp |

## 4. Efficiency and thermal

| Parameter | Value |
|---|---|
| Peak efficiency | 98.2% |
| CEC weighted efficiency | 97.6% |
| Cooling | Liquid, closed loop |
| Ingress protection | IP66 |
| Operating temperature | -30 °C to +55 °C |
| Dimensions (W x D x H) | 800 x 650 x 2,050 mm |
| Weight | 620 kg |
| Acoustic noise | 66 dBA at 1 m |

## 5. Firmware and controls

The Helios H3 runs its own firmware train, independent of the Comet C2 site controller. The current generally available release is firmware 4.4.1 (2025-04-22), distributed as `AGS-H3-FW-4.4.1.bin`. Firmware 4.3.0 remains supported for sites that have not completed the harmonic mitigation re-validation. Firmware older than 4.3.0 is not supported for new commissioning.

The PCS accepts a DC input from either AX-series cabinet. Note that the AX-600 DC operating range of 1,008-1,314 V sits near the upper end of the H3 input window; sites using AX-600 cabinets must confirm the maximum DC input voltage setting is left at the factory default of 1,500 V.

The H3 DC interface is limited to 260 kW. An AX-600 operating at its 279 kW continuous rating, or at its 390 kW peak, therefore requires two H3 units operating in parallel. A single H3 covers the AX-400 in full, including its 260 kW peak.

## 6. Compliance

Certified to UL 1741 SB, IEEE 1547-2018, IEC 62477-1 and IEC 62109-1/-2.

Technical support: support@auroragrid.example, +1-800-555-0142.
