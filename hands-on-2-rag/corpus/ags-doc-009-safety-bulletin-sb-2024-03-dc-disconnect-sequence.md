# SAFETY BULLETIN SB-2024-03 — DC Disconnect Sequence for AX-Series Cabinets

**Document ID:** AGS-DOC-009
**Bulletin number:** SB-2024-03
**Severity:** Important
**Effective date:** 2024-05-10
**Status:** **SUPERSEDED** — see SB-2025-01 (AGS-DOC-010), effective 2025-03-17

> This bulletin is retained for historical reference only. It is no longer the governing instruction. Do not apply the wait interval stated below to any work performed on or after 2025-03-17.

## 1. Affected products

All AX-400 (AGS-AX400-372) and AX-600 (AGS-AX600-558) battery cabinets manufactured before 2025-01-01, and all cabinets regardless of manufacture date that have not had the revised contactor firmware applied.

## 2. Background

Field investigations into two near-miss events found that residual charge on the DC link of an AX-series cabinet can persist after the main DC disconnect is opened. In both events, technicians opened a module access cover while a portion of the DC link remained energized above the 50 V threshold used in AGS work instructions.

The residual charge is held by the cabinet's internal DC-link capacitance and by module-level capacitance within each battery module. The discharge path is passive and its time constant varies with module temperature.

## 3. Required action

Until further notice, after opening the cabinet DC disconnect:

1. Apply a lockout/tagout device to the disconnect handle.
2. **Wait a minimum of 5 minutes** before removing any module access cover or touching any DC terminal.
3. Verify absence of voltage using a meter rated CAT III 1,500 V DC. Treat any reading of 50 V DC or greater as energized.
4. Only then proceed with the task.

## 4. Rationale for the interval

The 5-minute interval was derived from bench testing at 25 °C ambient. It was believed to provide a margin of approximately 2x over the measured discharge time constant of the AX-400 cabinet.

## 5. Reporting

Report any instance where the DC link measured 50 V DC or greater after the stated interval to AGS immediately. Support is available at support@auroragrid.example or +1-800-555-0142.

**Reminder:** SB-2024-03 has been superseded. The 5-minute interval must not be used for work performed on or after 2025-03-17.
