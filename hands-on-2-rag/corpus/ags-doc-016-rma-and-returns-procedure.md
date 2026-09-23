# RMA and Returns Procedure

**Document ID:** AGS-DOC-016
**Revision:** D
**Effective date:** 2025-05-06
**Applies to:** All AGS hardware returns, warranty and non-warranty

## 1. Opening an RMA

Submit a request through the AGS support portal at `https://support.auroragrid.example/rma`. Every request must include the site ID (format AGS-SITE-XXXXXX), the affected part number, the serial number, the fault code and a fault log export from Aurora Cloud.

An RMA number is issued in the format **RMA-YYYY-NNNNN** and must appear on all shipping documentation and on the outside of every carton. Shipments without a visible RMA number are refused at the receiving dock.

## 2. Response targets

| Priority | Definition | Acknowledgement target |
|---|---|---|
| Critical | Site down, no dispatch possible | 4 business hours |
| High | Degraded dispatch or an active safety fault | 1 business day |
| Standard | Non-urgent replacement or spare | 2 business days |

Acknowledgement is not an approval. Do not ship anything until the RMA is approved.

## 3. Advance replacement

Advance replacement is available for the Comet C2 site controller (AGS-C2-SC) only, because it is a single point of failure for telemetry. A credit card or purchase order must be on file. If the faulty unit is not returned within **30 calendar days**, the card is charged at list price plus 20%.

Battery modules and Helios H3 units are not eligible for advance replacement. They ship after the faulty unit is received and inspected.

## 4. Packaging and transport

Battery modules are UN 38.3 tested and must ship as **Class 9, UN3480** unless they are installed in or packed with equipment. Use the original AGS crate where possible. Where it is not available, use a UN-certified fibreboard box with the correct Class 9 label and a state-of-charge not exceeding 30%.

Wrap circuit boards in the AGS ESD bag, part number **AGS-PKG-ESD-1**, and pack in anti-static foam. Do not return a controller board in a plain cardboard box.

## 5. Return shipping and fees

AGS pays return shipping on all warranty-approved RMAs within the continental United States. The customer pays shipping on non-warranty returns and on all international returns.

| Scenario | Charge |
|---|---|
| Warranty-approved return | No charge |
| Non-warranty return within 90 days of shipment, unopened | 15% restocking fee |
| Non-warranty return, opened or installed | Evaluated case by case |
| Missing core (battery module not returned in 30 calendar days) | List price plus 20% |

## 6. Core return

Battery modules and coolant pumps are core items. Return the core within **30 calendar days** of receiving the replacement. Cores must be discharged to below 30% SoC and must have the RMA number on the carton.

## 7. Disposition

Returned units are inspected within 10 business days of receipt. AGS will repair, replace or scrap at its option and will issue a failure analysis report on request for warranty returns. Scrapped battery modules are recycled through an AGS-approved recycler and a certificate of recycling is issued to the site owner.
