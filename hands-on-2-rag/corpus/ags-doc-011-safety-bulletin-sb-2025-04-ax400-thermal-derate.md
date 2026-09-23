# SAFETY BULLETIN SB-2025-04 — Thermal Derate Above 40 °C for AX-400 Cabinets

**Document ID:** AGS-DOC-011
**Bulletin number:** SB-2025-04
**Severity:** Important
**Effective date:** 2025-07-01

## 1. Affected products

AX-400 battery cabinet, part number AGS-AX400-372 only. This bulletin does **not** apply to the AX-600 (AGS-AX600-558), which is liquid cooled and derates above +45 °C as documented in AGS-DOC-019.

## 2. Background

The AX-400 uses forced-air cooling with four axial fans. At ambient temperatures above +40 °C the cabinet's ability to reject cell heat is reduced, and sustained full-power operation accelerates cell ageing. Field data from 14 sites in the southwestern United States showed a 9% reduction in delivered energy after 24 months at sites that operated above +40 °C without derating.

The AX-400 datasheet (AGS-DOC-001) already states that the cabinet derates above +40 °C. This bulletin quantifies that derate and makes it mandatory.

## 3. Required action

When the ambient temperature measured at the cabinet intake is above +40 °C:

| Ambient at intake | Maximum charge power | Maximum discharge power |
|---|---|---|
| At or below +40 °C | 186 kW (100%) | 186 kW (100%) |
| Above +40 °C to +45 °C | 112 kW (60%) | 130 kW (70%) |
| Above +45 °C to +50 °C | 93 kW (50%) | 112 kW (60%) |
| Above +50 °C | Charge and discharge inhibited | Charge and discharge inhibited |

The derate must be enforced by the Comet C2 site controller dispatch schedule, not left to operator discretion. Sites running Comet C2 firmware 3.8.2 or later can enable the automatic ambient derate table; on earlier firmware the derate must be applied manually in the dispatch schedule.

## 4. Verification

1. Confirm the intake thermistor reading against a calibrated handheld meter. A discrepancy greater than 2 °C requires thermistor replacement.
2. Confirm the derate is active by inspecting the dispatch log during the hottest part of the day.
3. Record the maximum observed intake temperature each month in the site log.

## 5. Effective date and applicability

This bulletin takes effect 2025-07-01. It applies to all AX-400 cabinets in all regions. It does not impose requirements on any other AGS product.

Contact: support@auroragrid.example, +1-800-555-0142.
