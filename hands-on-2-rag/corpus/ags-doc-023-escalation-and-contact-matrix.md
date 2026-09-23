# Escalation and Contact Matrix

**Document ID:** AGS-DOC-023
**Revision:** C
**Effective date:** 2025-07-20

## 1. Contact channels

| Channel | Detail | Availability |
|---|---|---|
| AGS Technical Support | support@auroragrid.example | 24x7 |
| AGS Support hotline | +1-800-555-0142 | 24x7 |
| Spares desk | spares@auroragrid.example | Mon-Fri 07:00-19:00 US Mountain |
| Grid compliance | grid@auroragrid.example | Mon-Fri 08:00-17:00 US Mountain |
| RMA portal | https://support.auroragrid.example/rma | 24x7 |
| Aurora Cloud portal | https://cloud.auroragrid.example | 24x7, 99.9% SLA |

## 2. Severity definitions

| Severity | Definition | Initial response | Update cadence |
|---|---|---|---|
| S1 — Critical | Site down; no dispatch possible; or an active safety hazard | 30 minutes | Every 2 hours |
| S2 — Major | Dispatch possible at reduced capability; or a repeatable fault on a warranted assembly | 4 business hours | Every business day |
| S3 — Minor | Cosmetic issue, documentation question, or a non-blocking defect | 1 business day | On request |
| S4 — Advisory | Feature request, spare part quotation, training request | 2 business days | On request |

S1 incidents must be raised by telephone, not by email, and must be confirmed in the portal within 30 minutes so that the ticket is logged.

## 3. Escalation ladder

1. **Tier 1 — AGS Technical Support.** First point of contact for all severities. Owns the ticket until resolution.
2. **Tier 2 — AGS Field Service Engineer.** Engaged automatically for any S1 event, any on-site work, and any fault requiring a certified FRU replacement.
3. **Tier 3 — AGS Product Engineering.** Engaged by Tier 2 when a fault is not reproducible with published procedures or when a firmware defect is suspected. Tier 3 response target is 1 business day for S1 and 3 business days for S2.
4. **Tier 4 — AGS Product Safety.** Engaged for any actual or near-miss injury, any arc-flash event, and any suspected failure of a safety bulletin instruction.

## 4. Automatic escalations

The following conditions escalate without customer action:

| Condition | Escalates to | Within |
|---|---|---|
| Any S1 ticket open without a workaround | Tier 3 | 8 hours |
| Two or more F-0207 faults at one site in 7 days | Tier 3 | 1 business day |
| Cabinet intake above +50 °C on any AX-400 | Tier 2 | 1 hour |
| Cell delta above 100 mV at rest | Tier 3 | 1 business day |
| Any injury or arc-flash event | Tier 4 | Immediately |

## 5. Required information at escalation

Provide the site ID (AGS-SITE-XXXXXX), the affected part number and serial number, the active fault codes, the Aurora Cloud diagnostic bundle, and a description of the switching state at the time of the event. Escalations missing the diagnostic bundle are returned to the customer before Tier 3 engagement.

## 6. Account and commercial contacts

Contract, warranty coverage and extended-warranty questions are handled by the assigned AGS Account Manager, reachable through the regional office. Do not route commercial questions through the support queue; it delays S1 response.
