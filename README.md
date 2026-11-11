# OpenWrt 24.10 for D-Link DIR-BE364K (Wi-Fi 7 BE3600)

Community firmware for the **D-Link DIR-BE364K** dual-band Wi-Fi 7 router.
A from-scratch mainline OpenWrt port (kernel 6.18 + ath12k + DSA) replacing
the stock D-Link QSDK firmware. Read **Known Issues** before flashing.

**Current release: v30** (Community Edition v30, target `qualcommbe/ipq53xx`).

---

## Hardware Specifications

| Component | Specification |
|---|---|
| **SoC** | Qualcomm IPQ5332LA (4× Cortex-A53, ARMv8-A) |
| **RAM** | 512 MB DDR4 (16-bit) — active CDT `AP-MI04.1_256M16_DDR4` (machid 8060004) |
| **Flash** | 128 MB SPI-NAND GigaDevice GD5F1GM7 (128 KB erase block, 2 KB page) |
| **2.4 GHz Wi-Fi** | IPQ5332 internal radio (2×2, Wi-Fi 7 EHT40, up to 27 dBm) |
| **5 GHz Wi-Fi** | QCN6432 companion radio (2×2, Wi-Fi 7, up to 160 MHz, 4096-QAM) |
| **WAN** | 1× 2.5 GbE — Motorcomm YT8821 PHY (MDIO 0x04) |
| **LAN** | 4× 1 GbE — Motorcomm YT9215S DSA switch (MDIO 0x1d, 2.5G CPU uplink) |
| **LEDs** | RGB status LED (`red:status` / `green:status` / `blue:status`) |
| **UART** | 115200 8N1, 3.3 V TTL, prompt `IPQ5332#` (U-Boot 2016.01) |
| **Power** | 12 V / 1.5 A |

## What's new in v30

* **Dual-boot ready:** FIT config renamed to `config@openwrt` (old
  `config@mi04.1` kept as alias). With the documented two-entry U-Boot
  `bootcmd`, flashing stock firmware from the vendor recovery page boots
  stock automatically (`#config@mi04.1` + stock bootargs) and flashing the
  OpenWrt factory image returns to OpenWrt — **no UART needed** either way.
* **Default LAN IP = `192.168.8.1`** baked into the image (was
  `192.168.50.1`).
* `apk update` fixed for apk-tools 3.x: the image now ships
  `/etc/apk/world` (generated from the installed-package database) and
  `/lib/apk/db/triggers`. Without `world`, apk 3.0.5 aborts with
  `Unable to read database: No such file or directory` before touching the
  network — the exact failure users hit from LuCI / `apk update` on v28.
* Inherited from v28: 5 GHz radio pinned to **ch40 / EHT40** (deterministic
  AP+STA coexistence on the single QCN6432 radio), status LED re-checked
  every 30 s, `wifi_autoup` removed.

### U-Boot bootargs gotcha (important for manual work)

Kernel UBI accepts **one `ubi.mtd=` per device** — a comma-separated list is
invalid and kills the boot:

```
ubi.mtd=rootfs ubi.mtd=rootfs_1     # correct (two separate parameters)
ubi.mtd=rootfs,rootfs_1             # WRONG -> "UBI error: incorrect bytes count"
```

### Optional: dual-boot U-Boot env (one-time UART)

To make vendor-recovery stock flashes boot by themselves (and keep OpenWrt
bootable from the same env), set once at the `IPQ5332#` prompt:

```
setenv bargs_ow 'console=ttyMSM0,115200n8 earlycon ubi.mtd=rootfs ubi.mtd=rootfs_1 ubi.block=0,1 root=/dev/ubiblock0_1 rootfstype=squashfs clk_ignore_unused fstools_overlay_name=data'
setenv bargs_st 'console=ttyMSM0,115200n8 ubi.mtd=rootfs root=mtd:ubi_rootfs rootfstype=squashfs rootwait clk_ignore_unused vmalloc=1G'
setenv loadk 'ubi part rootfs; ubi read 0x44000000 kernel'
setenv bootk_ow 'bootm 0x44000000#config@openwrt'
setenv bootk_st 'bootm 0x44000000#config@mi04.1'
setenv bootcmd 'run loadk; setenv bootargs ${bargs_ow}; run bootk_ow; setenv bootargs ${bargs_st}; run bootk_st'
setenv bargs 'console=ttyMSM0,115200n8 earlycon ubi.mtd=rootfs ubi.block=0,1 root=/dev/ubiblock0_1 rootfstype=squashfs clk_ignore_unused'
setenv bootargs 'console=ttyMSM0,115200n8 earlycon ubi.mtd=rootfs ubi.block=0,1 root=/dev/ubiblock0_1 rootfstype=squashfs clk_ignore_unused'
saveenv
```

## What's new in v28

* **5 GHz radio pinned to channel 40 / EHT40 (non-DFS).** Auto channel
  selection on the QCN6432 could leave the 5 GHz AP without a beacon when a
  second virtual interface (repeater STA) competes for the same radio.
  A fixed non-DFS channel makes AP+STA coexistence deterministic.
* **Internet LED now self-checking:** besides interface hotplug events, the
  status LED is re-evaluated every 30 s — green = default route present,
  red = no internet — so the LED recovers without a reboot.
* **`wifi_autoup` service removed.** It rewrote the Wi-Fi SSID at every boot
  and silently reverted user changes made from LuCI.
* Inherited from v27: **DSA VLAN-unaware FDB-learning fix**
  (`9991-net-dsa-yt921x-fix-unaware-fdb-host-learning.patch`), **ubiblock
  rootfs** (`root=/dev/ubiblock0_1`, eliminates the historical `EBUSY`
  sysupgrade failure), Wi-Fi 7 (2.4 GHz EHT40 WPA3-SAE-mixed + PMF, 5 GHz
  EHT40 WPA3-SAE-mixed + PMF), welcoming LED animation (red → blue → green →
  status), `wwan` zone with masquerading pre-set for repeater mode, apk
  feeds for `aarch64_cortex-a53`, LuCI thermal widget (5 zones).

**Upgrade path verified in the field:** v26 → v28 → v30 via
*System → Backup / Flash Firmware* with *Keep settings* — rootfs volumes
rebuilt cleanly, 42 MB extroot overlay and all settings survived.

## Files

| File | Purpose |
|---|---|
| `firmware/*-v30-squashfs-factory.bin` | Initial install via D-Link Web Recovery (192.168.10.10) |
| `firmware/*-v30-squashfs-sysupgrade.bin` | Upgrades from LuCI / SSH `sysupgrade` |
| `firmware/v30_ubi.bin` | Raw UBI image for U-Boot TFTP flashing |
| `firmware/v30.itb` | RAM-boot image (non-destructive testing) |
| `tools/auto_flash_v30_uart_tftp.py` | Automated UART + TFTP flasher |
| `patches/` | Device tree + Motorcomm YT9215 DSA sources (FDB fix included) |
| `SHA256SUMS` | Checksums for every binary above |

## Installation

**Before you start:** keep the official D-Link firmware at hand for rollback;
disconnect VPNs on your PC (they intercept local traffic).

### Method 1 — Web Recovery (no UART required, recommended)
1. PC Ethernet → **LAN port 1**. Static IP `192.168.10.20 / 255.255.255.0`,
   gateway `192.168.10.10`.
2. Power off; hold **Reset** ~5 s while powering on.
3. Open **http://192.168.10.10** → upload
   `firmware/*-v30-squashfs-factory.bin` → **Upgrade**.
4. Wait ~2–3 min. Switch the PC NIC back to DHCP. LuCI: **http://192.168.8.1**.

### Method 2 — Automated UART + TFTP
1. UART (GND↔GND, RX↔TX, TX↔RX, 115200 8N1); PC Ethernet → **WAN** port;
   static IP `192.168.10.20/24`.
2. `python tools/auto_flash_v30_uart_tftp.py --port COM5`
   (port auto-detected when omitted). The script starts an internal TFTP
   server, flashes `rootfs`, and writes the permanent boot environment.

### First boot
* LuCI `http://192.168.8.1` — no password set; set one immediately.
* Wi-Fi `DIR-BE364K-2G` / `DIR-BE364K-5G`, mixed WPA2/WPA3, passphrase `12345678`.

## Wi-Fi settings guide (LuCI)

**Change your own SSID / password:** *Network → Wireless* → **Edit** on the
`DIR-BE364K-2G` or `DIR-BE364K-5G` card → set `SSID`, `Encryption`
(`WPA2-PSK` for maximum compatibility, `WPA3-SAE mixed` for security),
`Password` (≥ 8 chars) → **Save → Apply**.

**Repeater / WISP (join an upstream AP):**
1. *Network → Wireless* → on the radio you want to use → **Scan**.
2. Find the upstream SSID → **Join Network**.
3. Enter the **exact** passphrase (case and symbol order matter), keep
   network `wwan`, **Save → Apply**.

**Channel rules (important):**
* One radio serves one channel. If the upstream AP sits on channel X, the
  local AP on the same radio must also use channel X (width ≤ upstream
  width). The image ships the 5 GHz AP on **channel 40 / EHT40**.
* Avoid DFS channels (52–144) for the local AP — they impose a 60 s CAC at
  boot before the SSID appears.
* For a repeater, prefer the 5 GHz radio when the upstream is 5 GHz; the
  2.4 GHz radio stays free as a legacy AP.

**Status LED:** green = default route present (internet up); red = no
internet. The state is re-checked at boot, on interface events, and every
30 s.

## Optional: larger overlay (extroot)

Default overlay is a `rootfs_data` volume inside the rootfs UBI slot
(~22-28 MB writable). Two documented options, both tested on hardware:

### A) Simple — grow the slot-1 overlay only

Not possible beyond ~28 MB without repartitioning: the rootfs slot is 52 MB
(kernel ~6 MB + squashfs ~11 MB + reserve). A future image can shrink the
kernel volume to 5 MB and hand the rest to `rootfs_data` (~33-35 MB) —
planned for a later release.

### B) Advanced — second-slot overlay (`data` volume on `rootfs_1`)

1. In U-Boot (one-time, UART), the bootargs **must use two separate
   parameters** (see gotcha above) and the overlay token:
   `… ubi.mtd=rootfs ubi.mtd=rootfs_1 ubi.block=0,1 root=/dev/ubiblock0_1 …
   fstools_overlay_name=data`
2. On the running router (SSH, as root):
   ```sh
   IDX=$(grep '"rootfs_1"' /proc/mtd | sed 's/mtd\([0-9]*\):.*/\1/')
   ubiattach -m "$IDX"
   ubirmvol /dev/ubi1 -N kernel 2>/dev/null || true
   ubirmvol /dev/ubi1 -N ubi_rootfs 2>/dev/null || true
   ubirmvol /dev/ubi1 -N rootfs_data 2>/dev/null || true
   ubimkvol /dev/ubi1 -N data -m          # ~47 MB volume
   ```
3. The volume must contain a UBIFS filesystem. `mkfs.ubifs` is not shipped in
   the image; either build an empty image on a PC
   (`mkfs.ubifs -r emptydir -m 2048 -e 126976 -c 393 -o data.ubifs`) and
   write it with `ubiupdatevol /dev/ubi1_0 data.ubifs`, or restore a backup
   of a UBIFS volume over it.
4. Reboot. `df -h /overlay` then reports the new size.

**Caveats we hit on real hardware:** if slot 1 *also* has a volume named
`data`, fstools mounts the first match (slot-1, 28 MB). Keep the name unique
or rely on a clean factory flash. Also note `fstools` does **not** format an
empty extroot volume — pre-format it as in step 3.

## Extra storage: `/opt` on the second NAND slot (42 MB, SSH-only)

No re-flash, no U-Boot / no env change needed. Requires that both UBI
devices are attached (the v30 dual-boot `bargs` does this). All you need is
SSH on the freshly installed system:

```sh
# one-time, as root:
IDX=$(grep '"rootfs_1"' /proc/mtd | sed 's/mtd\([0-9]*\):.*/\1/')
ubiattach -m "$IDX" || true
ubirmvol /dev/ubi1 -N kernel 2>/dev/null || true
ubirmvol /dev/ubi1 -N ubi_rootfs 2>/dev/null || true
ubirmvol /dev/ubi1 -N rootfs_data 2>/dev/null || true
ubimkvol /dev/ubi1 -N bigdata -m          # ~47 MB volume (keep name unique!)
# make a minimal UBIFS image on your PC and push it:
#   mkfs.ubifs -r emptydir -m 2048 -e 126976 -c 393 -o data.ubifs
#   ssh root@192.168.8.1 "cat > /tmp/data.ubifs" < data.ubifs
#   ssh root@192.168.8.1 "ubiupdatevol /dev/ubi1_0 /tmp/data.ubifs"
mkdir -p /opt
mount -t ubifs /dev/ubi1_0 /opt
df -h /opt        # ~42 MB free
```

Persist it with `/etc/init.d/opt` (`START=97`, `boot()` runs
`ubiattach -m 19` + mount) and add `/opt/bin` to `PATH` in `/etc/profile`.
This gives ~42 MB of persistent space next to the ~27 MB overlay — useful
for large binaries/datasets (Xray, sing-box, scripts), while `apk` packages
themselves still install to `/usr` on the overlay.


LuCI → *System → Backup / Flash Firmware* → upload `*sysupgrade.bin` →
*(Keep settings recommended; the extroot overlay survives either way)* →
**Proceed**. Upgrading from any v26+ image is safe: root is mounted from
`ubiblock0_1`, so the running rootfs volume is never locked during the
upgrade. The router reboots automatically; allow up to ~8 minutes
(upload → flash → boot) before touching anything.

## Unbricking

Bootloaders (SBL1 / MIBIB / QSEE / APPSBL) are never touched by these
images, so recovery is always available.
1. Hold Reset 5 s at power-on → **http://192.168.10.10** → flash factory
   image (or official D-Link firmware).
2. If the router seems dead after a **software reboot**, pull the power cord
   for 10 s and re-plug (known Qualcomm warm-reboot lockup on this platform).
3. UART route: at `IPQ5332#`: `tftpboot 0x44000000 v30_ubi.bin` →
   `flash rootfs 0x44000000 <exact size of v30_ubi.bin>` → set `bargs`
   (text above without the overlay token), `loadk`, `bootk`, `bootcmd`,
   `saveenv`, `reset`.

## Known issues / limitations

* **Some LAN jacks report DHCP but cannot reach LuCI/SSH** — a client on an
  affected jack obtains an IP (broadcast works) but unicast to the router is
  dropped on that switch port. Under investigation (yt921x per-port
  unicast-to-CPU path). Workaround: use LAN1/LAN2 until fixed.
* **5 GHz AP + STA share one radio** (QCN6432): both must stay on the same
  channel and width; the image pins ch40/EHT40 for this reason.
* **No hardware flow offload** (no NSS/PPE tc-offload in mainline); software
  flow offloading is enabled.
* **Wi-Fi 7 requires WPA3-SAE(mixed)+PMF** on the AP side; clients without
  PMF fall back to Wi-Fi 6 by design.
* On 160 MHz AP operation, background scans are inhibited by DFS rules —
  `iw scan` returning `EBUSY` at 160 MHz is expected behavior, not a bug.

## Versioning

Releases use simple sequential tags (`v30`) mapped to
`openwrt-24.10-r27648-…-v30-*` file names; the userspace version string
inside the image is `24.10-SNAPSHOT r27648 (DIR-BE364K Community Edition v30)`.

## Credits / License

* OpenWrt Project — https://openwrt.org
* Motorcomm YT9215 DSA driver — David Yang (`mmyangfl`) and upstream DSA
  maintainers; FDB-learning fix from the RD15/BE3600 community port.
* Device tree, packaging and testing: DIR-BE364K community.
* **Project code, build scripts, device-tree sources and documentation:
  MIT** (see `LICENSE`).
* **Firmware images** bundle OpenWrt and the Linux kernel, which are
  **GPL-2.0**: complete corresponding sources are the upstream OpenWrt tree
  plus the `patches/` and build scripts shipped in this repository
  (GPL-2.0 compliance statement).
