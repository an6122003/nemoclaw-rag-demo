# Comet C2 Firmware Release Notes — Version 3.8.0

**Document ID:** AGS-DOC-013
**Product:** Comet C2 site controller (AGS-C2-SC)
**Firmware version:** 3.8.0
**Release date:** 2025-02-14
**Distribution file:** `AGS-C2-FW-3.8.0.bin`
**Status:** Superseded by 3.8.2. Do not deploy to new sites.

## 1. Summary

Firmware 3.8.0 is a feature release that **changes the default Modbus TCP server port** and introduces the Aggressive Rebalance dispatch mode. Sites upgrading to 3.8.0 must update their SCADA and Aurora Cloud collector configuration before the upgrade window, or telemetry will stop.

## 2. Behaviour change — Modbus TCP default port

In firmware 3.7.4 and earlier, the Comet C2 Modbus TCP server listened on port **502**. In firmware 3.8.0 the default changed to port **1502**.

This was done to avoid a port conflict with the local web interface on some hardened site networks. The change is not optional in 3.8.0: the server binds only to the configured port.

Action required before upgrading: update every Modbus client, including the Aurora Cloud edge gateway (AGS-EG-2), to poll port 1502. Sites that cannot change their client configuration should remain on 3.7.4 until 3.8.2 is available.

## 3. New features

- **Aggressive Rebalance** dispatch mode. When enabled, the controller drives an intentional full charge to 100% SoC at 0.5C whenever any cell delta exceeds 30 mV, rather than waiting for the scheduled weekly balance window. This reduces the time to clear an F-0512 imbalance.
- Per-string SoC reporting for AX-600 cabinets with six racks.
- Ambient derate table import for the AX-400.
- Support for up to 64 devices at a guaranteed 1 s polling interval, correcting the 3.7.4 scaling defect.

## 4. Fixed issues

- Fixed the 3.7.4 defect in which sites with more than 48 devices fell back to a 1.5 s polling interval.
- Fixed time-zone parsing for the `Etc/GMT+` identifier family.

## 5. Known issues

- Aggressive Rebalance can raise cell temperature by up to 6 °C above the normal charge profile on an AX-400 cabinet in still air. Monitor cabinet intake temperature when enabling it above +35 °C ambient.
- The Modbus port cannot be reverted to 502 by configuration in this release; a firmware change is required.

## 6. Upgrade notes

The controller reboots once and takes approximately 210 s. Take a configuration backup before upgrading. Downgrade to 3.7.4 requires a factory reset.
