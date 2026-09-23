# Glossary of AGS Terms and Abbreviations

**Document ID:** AGS-DOC-021
**Revision:** C
**Effective date:** 2025-06-25
**Applies to:** All AGS documentation

## 1. Purpose

This glossary defines terms as they are used in AGS technical documentation. Where a term has an industry meaning that differs from the AGS meaning, the AGS meaning governs within AGS documents.

## 2. Product and system terms

**AGS** — Aurora Grid Systems, Inc., the manufacturer.

**AX-400** — The smaller AGS battery cabinet, part number AGS-AX400-372, rated 372 kWh usable, 768 V nominal DC, air cooled.

**AX-600** — The larger AGS battery cabinet, part number AGS-AX600-558, rated 558 kWh usable, 1,152 V nominal DC, liquid cooled. Not interchangeable with the AX-400.

**Helios H3** — AGS bidirectional power conversion system, part number AGS-H3-250, rated 250 kW AC.

**Comet C2** — AGS site controller, part number AGS-C2-SC. Aggregates telemetry and executes dispatch.

**Aurora Cloud** — AGS hosted telemetry and portal service.

**Edge gateway (AGS-EG-2)** — Site appliance that buffers and forwards telemetry to Aurora Cloud over MQTT.

## 3. Electrical terms

**BESS** — Battery energy storage system.

**C-rate** — Charge or discharge current normalised to capacity. Both AX-series cabinets are limited to 0.5C.

**DoD** — Depth of discharge, expressed as a percentage of nameplate energy. AGS cycle-life figures are quoted at 80% DoD and 25 °C.

**DC bus** — The high-voltage direct-current link between battery cabinets and a Helios H3. Nominal 768 V on an AX-400 system and 1,152 V on an AX-600 system.

**PCS** — Power conversion system. See Helios H3.

**RTE** — Round-trip efficiency, AC-to-AC. 94.5% for the AX-400 and 95.2% for the AX-600.

**SoC** — State of charge, expressed as a percentage of usable energy.

**pu** — Per unit, a normalised voltage or frequency value. Ride-through is quoted in pu.

## 4. Operational terms

**Aggressive Rebalance** — A dispatch mode introduced in Comet C2 firmware 3.8.0 and removed in 3.8.2. Historical only; do not enable.

**Derate** — Deliberate reduction of maximum power below the nameplate rating, usually because of ambient temperature.

**FRU** — Field-replaceable unit, a part that can be replaced on site.

**Soak test** — A 24-hour continuous run in automatic dispatch mode performed before site handover.

**Witness mark** — A torque stripe applied across a fastener and its seating surface so that loosening is visible.

## 5. Compliance and commercial terms

**AHJ** — Authority having jurisdiction.

**RMA** — Return merchandise authorisation, issued in the format RMA-YYYY-NNNNN.

**SB** — Safety bulletin, issued by AGS Product Safety. A superseding bulletin takes precedence over all earlier bulletins on the same subject.

**Superseded** — A document or instruction that has been replaced. A superseded safety instruction must not be applied. Where a supersession has an effective date, the new instruction governs work performed on or after that date.

**UN 38.3** — The transport test standard that battery modules must pass before shipment.
