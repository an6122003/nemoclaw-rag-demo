# Comet C2 Firmware Release Notes — Version 3.7.4

**Document ID:** AGS-DOC-012
**Product:** Comet C2 site controller (AGS-C2-SC)
**Firmware version:** 3.7.4
**Release date:** 2024-09-30
**Distribution file:** `AGS-C2-FW-3.7.4.bin`
**Status:** Supported. Superseded by 3.8.0, 3.8.1 and 3.8.2, but retained on the supported list for sites awaiting grid-code re-validation.

## 1. Summary

Firmware 3.7.4 is a maintenance release on the 3.7 branch. It is the last release before the 3.8 branch introduced the revised Modbus server behaviour and the Aggressive Rebalance dispatch mode.

## 2. New and changed

- Added SunSpec Modbus model 701 support for AX-series cabinets.
- Added the site time-zone field to the local web interface.
- Improved CAN bus recovery: the controller now re-initializes the CAN interface after three consecutive bus-off events instead of five.
- Reduced controller reboot time during firmware installation from 240 s to **210 s**.

## 3. Defaults established in this release

| Setting | Default value in 3.7.4 |
|---|---|
| Management IP address | 192.168.10.40 |
| Modbus TCP server port | 502 |
| Telemetry push interval | 60 s |
| Device polling floor | 1 s |
| Maximum managed devices | 64 |

These defaults are carried forward to firmware 3.8.2. They are **not** the defaults used in firmware 3.8.0 and 3.8.1, which listen on Modbus TCP port 1502.

## 4. Fixed issues

- Fixed an intermittent loss of the on-box log index after an unclean power cycle.
- Fixed incorrect reporting of AX-400 cabinet state after a site emergency stop.
- Fixed a defect in which the DNP3 unsolicited response counter wrapped at 65,535 instead of resetting cleanly.

## 5. Known issues

- Sites with more than 48 devices may see a 1.5 s polling interval instead of the configured 1 s. This was corrected in 3.8.0.
- The site time-zone field does not accept the `Etc/GMT+` family of identifiers. Use a city identifier instead.

## 6. Upgrade notes

Upgrade over the local web interface or from Aurora Cloud. The controller reboots once and takes approximately 210 s. Downgrading from 3.8.0 or later to 3.7.4 requires a factory reset and re-provisioning; take a configuration backup first.
