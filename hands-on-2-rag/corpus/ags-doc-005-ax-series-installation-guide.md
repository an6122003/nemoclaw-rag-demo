# AX-Series Battery Cabinet Installation Guide

**Document ID:** AGS-DOC-005
**Revision:** F
**Effective date:** 2025-07-15
**Applies to:** AX-400 (AGS-AX400-372) and AX-600 (AGS-AX600-558)
**Supersedes:** AGS-DOC-005 Rev E (2025-01-22)

## 1. Scope

This guide covers mechanical setting, DC interconnection, grounding and first energization of AX-series battery cabinets. AC-side wiring of the Helios H3, pad design and grid-code settings are outside its scope; see AGS-DOC-018 and AGS-DOC-020. Work must be performed by personnel qualified to NFPA 70E and wearing Class 0 gloves and an arc-rated face shield.

## 2. Pre-installation checks

1. Verify the concrete pad is at least 150 mm thick, reinforced, and cured for 28 days before setting cabinets.
2. Confirm the pad is level to within 3 mm across the cabinet footprint.
3. Confirm the site ground electrode resistance is 5 Ω or less using a fall-of-potential test.
4. Verify the nameplate part number. An AX-400 reads **AGS-AX400-372**; an AX-600 reads **AGS-AX600-558**. Record both the part number and serial number on the installation record.
5. Inspect the cabinet for shipping damage and confirm the shock indicator on the door is untripped.

## 3. Setting and anchoring

Set the cabinet with a forklift rated for 1.25x the shipped weight, using the four lifting points. An AX-400 weighs **2,850 kg**; an AX-600 weighs **4,180 kg**. Anchor each cabinet with four M16 grade 8.8 bolts torqued to 180 N·m.

Maintain cabinet-to-cabinet spacing of 300 mm minimum. Front service clearance is **1,000 mm** for the AX-400 and **1,200 mm** for the AX-600 because the AX-600 requires access for coolant service. Rear clearance is 150 mm; side clearance is 300 mm; top clearance is 600 mm.

## 4. Grounding

Bond each cabinet chassis to the site ground grid with 2/0 AWG copper. Torque the cabinet ground stud to **12 N·m** on both models. Do not use the enclosure as a current-carrying conductor.

## 5. DC interconnection

DC interconnection between the cabinet and the Helios H3 uses the factory-supplied cable set. Observe the torque values below; under-torquing is the single most common cause of hot-spot faults.

| Cabinet | DC terminal | Torque |
|---|---|---|
| AX-400 | M12 stud | 25 N·m |
| AX-600 | M12 stud | 35 N·m |

Never apply the AX-600 value to an AX-400 terminal. After torquing, apply a torque witness mark and photograph the completed termination for the commissioning record.

## 6. First energization

1. Confirm all DC disconnects are open and locked out.
2. Measure insulation resistance from each DC pole to ground; the result must be 1 MΩ or greater at 1,000 V DC test voltage.
3. Close the cabinet DC disconnect. Wait the interval required by the current safety bulletin before removing any module access cover (see AGS-DOC-010).
4. Confirm the Comet C2 site controller has discovered the cabinet on CAN and that the cabinet reports a nominal DC bus consistent with its model (768 V nominal for AX-400, 1,152 V nominal for AX-600).
5. Record the closed-circuit DC voltage and proceed to AGS-DOC-006.
