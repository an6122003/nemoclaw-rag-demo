# Site Planning and Pad Design Guide

**Document ID:** AGS-DOC-018
**Revision:** E
**Effective date:** 2025-06-10
**Applies to:** AX-400, AX-600, Helios H3, Comet C2

## 1. Purpose

This guide defines the civil, electrical and layout requirements for a new AGS battery energy storage site. It is used by AGS Application Engineering during the design review that must be completed before equipment is released to manufacturing.

## 2. Pad and foundation

| Requirement | Value |
|---|---|
| Pad thickness | 150 mm minimum, reinforced |
| Concrete strength | 3,000 psi at 28 days |
| Cure before setting equipment | 28 days |
| Level tolerance across cabinet footprint | 3 mm |
| Pad elevation above finished grade | 150 mm minimum |

The pad must sit at least 300 mm above the 100-year flood elevation for the site.

## 3. Equipment layout and clearances

| Clearance | AX-400 | AX-600 |
|---|---|---|
| Front service clearance | 1,000 mm | 1,200 mm |
| Rear clearance | 150 mm | 150 mm |
| Side clearance | 300 mm | 300 mm |
| Top clearance | 600 mm | 600 mm |
| Cabinet-to-cabinet spacing | 300 mm | 300 mm |

The AX-600 requires more front clearance because the coolant filter and pump are accessed from the front of the cabinet. Laying out an AX-600 using AX-400 dimensions is the most common design-review finding at AGS.

Mount the Comet C2 inside a NEMA 1 or better enclosure within 30 m of the furthest CAN device to keep the trunk within the 250 m CAN limit at 125 kbit/s.

## 4. Grounding and bonding

Provide a site ground grid with a measured resistance of **5 Ω or less**. Bond each cabinet chassis with 2/0 AWG copper to the grid. Bond the Helios H3 enclosure to the same grid at a separate point. Do not daisy-chain cabinet grounds.

## 5. Electrical room and AC side

The Helios H3 AC output is 400 V AC, three-phase, four-wire at up to 361 A. Size the AC feeder for 125% of 361 A, or 452 A minimum. Provide a lockable AC disconnect within sight of each PCS. The PCS AC lug torque is **45 N·m**; the DC lug torque is **35 N·m**.

Provide a cable trench at least 600 mm deep between the cabinets and the PCS. Separate DC and AC conduits by at least 300 mm and cross them at 90° where crossing is unavoidable.

## 6. Security and access

Enclose the equipment yard with a 2.1 m fence. Provide a 3 m wide access gate for a service vehicle. Mount a site emergency stop at the gate and at the main equipment aisle; both must open all DC contactors within 2 s when pressed.

## 7. Environmental design inputs

Design ambient for the site must be established from a 10-year local weather record. AGS equipment is warranted within the published operating envelopes only; see AGS-DOC-019. If the design maximum ambient exceeds +45 °C, provide shade or active ventilation for air-cooled cabinets.

## 8. Design review deliverables

Submit the pad drawing, single-line diagram, grounding plan, clearance drawing and the site ambient study to AGS Application Engineering. Allow 10 business days for review.
