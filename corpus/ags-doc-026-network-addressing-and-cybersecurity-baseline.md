# Network Addressing and Cybersecurity Baseline

**Document ID:** AGS-DOC-026
**Revision:** B
**Effective date:** 2025-07-08
**Applies to:** Comet C2 (AGS-C2-SC), Helios H3 (AGS-H3-250), AX-400, AX-600

## 1. Purpose

This baseline defines the minimum network segmentation and access controls required for an AGS site. It must be reviewed by the site operator's security team before energization.

## 2. Default addressing

| Device | Default address | Notes |
|---|---|---|
| Comet C2 management | 192.168.10.40 /24 | Change if it conflicts with the site LAN |
| Comet C2 Modbus TCP | Port 502 on 3.7.4 and 3.8.2+; 1502 on 3.8.0/3.8.1 | See AGS-DOC-014 |
| AX-400 / AX-600 | No IP address | CAN or Modbus RTU to the controller only |
| Helios H3 | 192.168.10.41 /24 | Web service on port 443 |
| Edge gateway AGS-EG-2 | DHCP, or static per site policy | Outbound TCP 8883 only |

Battery cabinets do not have routable network interfaces. If a scan discovers an IP address on an AX-series cabinet, the address belongs to a third-party monitoring device that was not supplied by AGS.

## 3. Segmentation requirements

1. Place all AGS equipment on a dedicated storage VLAN. Do not place the Comet C2 on the corporate user VLAN.
2. Permit outbound TCP 8883 from the edge gateway to Aurora Cloud only. Deny all other outbound traffic from the storage VLAN.
3. Permit management access only from a jump host on a separate management VLAN.
4. Do not expose the Comet C2 web interface, Modbus TCP port or Helios H3 web service to the public internet.

## 4. Account and credential policy

Change the factory administrator password before the site is energised. Enable role-based accounts: Site Administrator, Operator and Read-Only. A minimum of one named account per human user is required; shared accounts are not permitted. Review accounts quarterly and remove leavers within one business day.

## 5. Firmware and patching

Only AGS-signed firmware images may be installed. The controller rejects unsigned images. Keep the controller on a supported release per AGS-DOC-024. Firmware 3.8.0 and 3.8.1 should be upgraded to 3.8.2 to restore the Modbus port default and remove the deprecated Aggressive Rebalance mode.

## 6. Logging and monitoring

Forward controller syslog to the operator's SIEM where available. Retain authentication logs for at least 12 months. Alert on three or more failed logins within 10 minutes from the same source address, and on any change to the Modbus port, the site ID or the grid profile.

## 7. Physical security

Cabinet doors must be locked with a keyed handle. Record key holders. The Comet C2 enclosure must be locked because the USB port can be used to load firmware. Report any unexplained USB activity to AGS Product Safety.

## 8. Incident response

If unauthorised access is suspected, isolate the storage VLAN, preserve controller logs, rotate all credentials and contact AGS Support before rebooting any device. Rebooting destroys volatile session data that AGS may need for analysis.
