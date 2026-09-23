# Aurora Cloud Telemetry Onboarding Guide

**Document ID:** AGS-DOC-025
**Revision:** B
**Effective date:** 2025-06-30
**Applies to:** Comet C2 (AGS-C2-SC), edge gateway AGS-EG-2

## 1. Overview

Aurora Cloud is the AGS hosted telemetry and asset-management portal at `https://cloud.auroragrid.example`. Sites publish telemetry from the Comet C2 through the AGS-EG-2 edge gateway over MQTT with TLS 1.2 on port **8883**. The default push interval is **60 s**.

Onboarding a new site takes **5 business days** from receipt of a complete site record.

## 2. Prerequisites

1. The Comet C2 is commissioned and reachable on the site LAN.
2. The controller management address is known. The factory default is **192.168.10.40**.
3. Outbound TCP 8883 to the Aurora Cloud broker is permitted through the site firewall.
4. NTP is reachable; the controller clock must be within 2 s of UTC.
5. The site record includes an operator name, a physical address and an interconnection identifier.

## 3. Site identifier

Every site receives a site ID in the format **AGS-SITE-XXXXXX**, where the six characters are uppercase alphanumerics assigned by AGS. The site ID appears on all RMA requests, support tickets and warranty claims. Do not change it; a changed site ID breaks the historical telemetry chain and requires re-onboarding.

## 4. Onboarding steps

1. Log in to the portal with an operator account holding the Site Administrator role.
2. Create the site and record the assigned AGS-SITE-XXXXXX identifier.
3. Generate the device enrolment token. The token is valid for 72 hours; generate a new one if it expires.
4. Enter the site ID and enrolment token on the Comet C2 under **Settings > Cloud**.
5. Confirm the edge gateway registers and shows **Connected** within 10 minutes.
6. Verify the device count matches the physical installation. Any mismatch is usually a CAN trunk fault.
7. Confirm at least one full telemetry cycle appears in the portal, including cabinet SoC, DC bus voltage and cell delta.
8. Configure alarms and notification recipients.

## 5. Data retention

| Resolution | Retention |
|---|---|
| 1-minute | 13 months |
| 15-minute | 60 months |
| Daily rollup | Indefinite |

The portal exposes a REST API using OAuth 2.0 client-credentials tokens. API tokens expire after 60 minutes and must be refreshed. Rate limit is 600 requests per minute per site.

## 6. Outage behaviour

If the WAN is unavailable, the Comet C2 buffers data on-box for up to **730 days** and backfills automatically on reconnect. Backfill is throttled to 10x real time so that a long outage does not saturate the site link.

## 7. Service level

Aurora Cloud is provided with a **99.9%** monthly availability target, measured at the portal. Scheduled maintenance windows are announced 5 business days in advance and are excluded from the availability calculation.
