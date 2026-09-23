# Comet C2 Firmware Release Notes — Version 3.8.2

**Document ID:** AGS-DOC-014
**Product:** Comet C2 site controller (AGS-C2-SC)
**Firmware version:** 3.8.2
**Release date:** 2025-06-02
**Distribution file:** `AGS-C2-FW-3.8.2.bin`
**Status:** **Current generally available release.**

## 1. Summary

Firmware 3.8.2 restores the Modbus TCP default port to 502 and deprecates the Aggressive Rebalance mode introduced in 3.8.0. It also fixes two defects reported against 3.8.0 and 3.8.1.

## 2. Reverted behaviour — Modbus TCP default port

The default Modbus TCP server port in 3.8.0 and 3.8.1 was **1502**. Based on customer feedback that the change created unnecessary migration work and broke existing SCADA integrations, the default is reverted: firmware 3.8.2 and later listen on port **502** by default, matching firmware 3.7.4.

The port remains configurable. Sites that already migrated to 1502 may keep that value; the change affects only the factory default applied on a fresh install or after a factory reset.

## 3. Deprecated and removed feature — Aggressive Rebalance

The Aggressive Rebalance dispatch mode introduced in firmware 3.8.0 is **deprecated and disabled in 3.8.2**. It is removed entirely; the setting is no longer present in the dispatch menu.

Reason: AGS analysis of 31 sites showed that repeated aggressive full-power rebalancing increased measured cell degradation by 12% over six months on AX-400 cabinets, with no reduction in the mean time to clear an F-0512 imbalance compared to the scheduled weekly balance window. The scheduled weekly balance window remains, and the standard balance current is unchanged.

Sites that enabled Aggressive Rebalance on 3.8.0 or 3.8.1 will find it automatically disabled after upgrading to 3.8.2. No action is required beyond confirming that F-0512 events are being cleared by the weekly window.

## 4. New features

- Ambient derate enforcement for the AX-400 is now automatic when the intake thermistor is installed and the derate table is loaded (see SB-2025-04).

## 5. Fixed issues

- Fixed a defect in which a device removed from the CAN trunk remained in the device list until reboot.
- Fixed an inaccurate coolant pressure reading on the AX-600 when the pump was at minimum speed.

## 6. Upgrade notes

Upgrade over the local web interface or from Aurora Cloud. The controller reboots once and takes approximately 210 s. Upgrade directly from 3.7.4 is supported and requires no SCADA change, because the Modbus port default is unchanged at 502. Take a configuration backup before upgrading.
