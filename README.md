# OpenWrt 24.10 for D-Link DIR-BE364K (Wi-Fi 7 BE3600)

Community firmware for the **D-Link DIR-BE364K** dual-band Wi-Fi 7 router.
A from-scratch mainline OpenWrt port (kernel 6.18.39 + ath12k + DSA) replacing
the stock D-Link QSDK firmware. Read **Known Issues** before flashing.

**Current release: v31** (`24.10-SNAPSHOT r27648 (DIR-BE364K Community Edition v31)`, target `qualcommbe/ipq53xx`).

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

## Features

* **Motorcomm YT9215S DSA fixes**
  (`patches/9991-net-dsa-yt921x-fix-unaware-fdb-host-learning.patch`,
  `patches/tag_yt921x.c`, `patches/yt921x.c`): enables `DSA_TAG_PROTO_YT921X`,
  fixes 32-bit register truncation in `yt921x_fdb_add_index_in12()`, and maps
  VLAN-unaware `vid=0` to `YT921X_VID_UNWARE` (`4095`) via `yt921x_fdb_vid()`
  for both FDB and MDB operations.
* **Built-in PassWall 2 + Xray-core** on `/rom` (uses zero `/overlay` space):
  * `luci-app-passwall2` (`26.11.11-r1`) + `xray-core` (`26.11.9-r1`)
  * `kmod-nft-tproxy`, `kmod-nft-socket`, `curl`, `unzip`
  * Pre-installed geo datasets in `/usr/share/v2ray/`:
    `geoip.dat` (`v2ray-geoip-202611080027-r1`),
    `geosite.dat` (`v2ray-geosite-20261108011013-r1`), and
    `iran.dat` (`v2ray-geosite-ir-202610230802-r1`)
* **ABI-matched 802.11s Wi-Fi Mesh package** (`packages/wpad-mesh-mbedtls-2026.04.02~b004de0b-r1.apk`):
  compiled directly against the firmware's pinned `hostapd-common` / `libmbedtls` /
  `libucode` ABI so you can enable 802.11s mesh (`SAE`) without breaking LuCI.
* **Dual-boot ready:** the FIT carries `config@openwrt` (and `config@mi04.1` alias).
  With the U-Boot environment below, flashing stock from vendor recovery boots
  stock automatically and flashing OpenWrt factory returns to OpenWrt without UART.
* **ubiblock rootfs** (`root=/dev/ubiblock0_1`) — eliminates `EBUSY` sysupgrade
  failures; `apk` package management works cleanly.
* **Wi-Fi 7:** 2.4 GHz and 5 GHz EHT40, `sae-mixed` (WPA2/WPA3) + PMF (`ieee80211w=1`).
  5 GHz defaults to **ch40 / EHT40** (non-DFS).
* **Status LED & networking:** internet self-check every 30 s, `wwan` firewall
  zone with masquerading pre-set for repeater mode, default LAN `192.168.8.1`.

### U-Boot bootargs gotcha (important for manual work)

Kernel UBI accepts **one `ubi.mtd=` per device** — a comma-separated list is
invalid and breaks boot:

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

## Files

| File | Purpose |
|---|---|
| `firmware/openwrt-24.10-r27648-qualcommbe-ipq53xx-dlink_dir-be364k-v31-squashfs-factory.bin` | Initial install / recovery via D-Link Web Recovery (`192.168.10.10`) |
| `firmware/openwrt-24.10-r27648-qualcommbe-ipq53xx-dlink_dir-be364k-v31-squashfs-sysupgrade.bin` | Upgrades from LuCI / SSH `sysupgrade` |
| `firmware/v31_ubi.bin` | Raw UBI image (`kernel` 6 MiB + `ubi_rootfs` + `rootfs_data`) for U-Boot TFTP |
| `firmware/v31.itb` | RAM-boot image (non-destructive testing) |
| `packages/wpad-mesh-mbedtls-2026.04.02~b004de0b-r1.apk` | Optional 802.11s Wi-Fi Mesh (`wpad-mesh-mbedtls`) compiled for v31 ABI |
| `tools/auto_flash_v31_uart_tftp.py` | Automated UART + TFTP flasher (`--port COMx`) |
| `patches/` | Device tree + updated Motorcomm YT9215 DSA sources |
| `SHA256SUMS` | SHA-256 checksums for all firmware binaries and `.apk` packages |

## Installation

**Before you start:** keep the official D-Link firmware at hand for rollback;
disconnect VPNs on your PC (they intercept local traffic).

### Method 1 — Web Recovery (no UART required, recommended)
1. PC Ethernet → **LAN port 1**. Static IP `192.168.10.20 / 255.255.255.0`,
   gateway `192.168.10.10`.
2. Power off; hold **Reset** ~5 s while powering on until recovery mode starts.
3. Open **http://192.168.10.10** → upload
   `firmware/openwrt-24.10-r27648-qualcommbe-ipq53xx-dlink_dir-be364k-v31-squashfs-factory.bin`
   → **Upgrade**.
4. Wait ~2–3 min. Switch the PC NIC back to DHCP. LuCI: **http://192.168.8.1**.

### Method 2 — Automated UART + TFTP
1. UART (`GND↔GND`, `RX↔TX`, `TX↔RX`, `115200 8N1`); PC Ethernet → **WAN** port;
   static IP `192.168.10.20/24`.
2. `python tools/auto_flash_v31_uart_tftp.py --port COM3`
   The script runs an internal TFTP server, flashes `rootfs` and `rootfs_1` with
   `firmware/v31_ubi.bin`, writes the U-Boot boot environment, and reboots into OpenWrt v31.

### First boot
* LuCI: `http://192.168.8.1` — no password set initially; set a root password immediately.
* Default Wi-Fi SSIDs: `DIR-BE364K-2G` / `DIR-BE364K-5G`, encryption `sae-mixed` (WPA2/WPA3), passphrase `12345678`.

## PassWall 2 + Xray Direct Iran Rules (No Extra Flash Needed)

v31 already includes `geoip.dat`, `geosite.dat`, and `iran.dat` inside `/rom/usr/share/v2ray/`,
consuming **0 bytes** of `/overlay`:

* `PassWall 2` → **Rule Manage** → edit the `Iran` rule (`config shunt_rules 'Iran'`):
  * Note: in this version of PassWall 2 (`util_xray.lua`), lines starting with `#`,
    `rule-set:`, or `ext:` are **ignored** when generating Xray routing JSON. Also,
    `/usr/share/v2ray/geosite.dat` provides tag `CATEGORY-IR` (not bare `IR`).
  * Set **Domain** to:
    ```text
    geosite:category-ir
    regexp:.*\.ir$
    regexp:.*\.xn--mgba3a4f16a$
    ```
  * Keep **IP** as:
    ```text
    geoip:ir
    ```
* **`Geoview` note:** `Geoview` (`/usr/bin/geoview`) is an optional helper binary
  (for Sing-Box `.srs` conversion or nftables IP preloading), **not** the geo rule
  database itself. When running **Xray**, you do **not** need `Geoview` installed or updated.

## Installing Wi-Fi Mesh (`wpad-mesh-mbedtls`)

The upstream OpenWrt snapshot feed ships newer `wpad-mesh-*` builds linked against newer
`hostapd-common` / `ucode` libraries that conflict with v31's pinned userspace. Use the
prebuilt package in `packages/wpad-mesh-mbedtls-2026.04.02~b004de0b-r1.apk` instead.

Because `/etc/apk/world` pins `wpad-basic-mbedtls=2026.04.02~b004de0b-r1`, swap it in one
chained command (ideally over Ethernet so Wi-Fi reloads cleanly right after):

1. Upload the package to `/tmp/` on the router (from your PC):
   ```sh
   ssh root@192.168.8.1 "cat > /tmp/wpad-mesh-mbedtls-2026.04.02~b004de0b-r1.apk" < packages/wpad-mesh-mbedtls-2026.04.02~b004de0b-r1.apk
   ```
2. On the router (SSH as `root`):
   ```sh
   apk del --no-network wpad-basic-mbedtls && \
   apk add --no-network --allow-untrusted /tmp/wpad-mesh-mbedtls-2026.04.02~b004de0b-r1.apk && \
   rm -f /tmp/wpad-mesh-mbedtls-2026.04.02~b004de0b-r1.apk && \
   wifi reload
   ```
   *(Uses ~1.7 MiB on `/overlay`; tested cleanly with `Supported interface modes: * mesh point`.)*

## Wi-Fi settings guide (LuCI)

**Change your own SSID / password:** *Network → Wireless* → **Edit** on
`DIR-BE364K-2G` or `DIR-BE364K-5G` → set `SSID`, `Encryption`, `Password` → **Save & Apply**.

**Repeater / WISP (join an upstream AP):**
1. *Network → Wireless* → on the radio you want to use → **Scan** → **Join Network**.
2. Enter the passphrase, keep firewall zone `wwan`, **Save & Apply**.

**Channel & width rules (important for QCN6432 5 GHz AP+STA):**
* Both AP and STA interfaces on the same radio must match the **upstream AP's channel and width**
  (for example, if the upstream 5 GHz router operates on channel 100 at 80 MHz, set
  `wireless.radio1.htmode='HE80'` — `EHT40` with an 80 MHz DFS upstream can prevent `phy1-sta0`
  from bringing up traffic cleanly).
* Avoid DFS channels (52–144) on standalone local APs when you don't need them — DFS imposes a 60 s CAC at boot.

## Storage & `/opt` (42 MB on second NAND slot)

In **v31**, the compressed squashfs rootfs (~24 MB with PassWall 2 + Xray + geodata) leaves
**~14.4 MB** writable `/overlay` (`rootfs_data` on `ubi0_2`).

If you need more space for additional datasets/binaries without changing the overlay layout,
mount the second NAND slot (`rootfs_1`) as a ~42 MB `/opt` volume:

```sh
# one-time, as root:
IDX=$(grep '"rootfs_1"' /proc/mtd | sed 's/mtd\([0-9]*\):.*/\1/')
ubiattach -m "$IDX" || true
ubirmvol /dev/ubi1 -N kernel 2>/dev/null || true
ubirmvol /dev/ubi1 -N ubi_rootfs 2>/dev/null || true
ubirmvol /dev/ubi1 -N rootfs_data 2>/dev/null || true
ubimkvol /dev/ubi1 -N bigdata -m          # ~47 MB volume (keep name unique!)
# Format an empty UBIFS image on your PC and write it:
#   mkfs.ubifs -r emptydir -m 2048 -e 126976 -c 393 -o data.ubifs
#   ssh root@192.168.8.1 "cat > /tmp/data.ubifs" < data.ubifs
#   ssh root@192.168.8.1 "ubiupdatevol /dev/ubi1_0 /tmp/data.ubifs"
mkdir -p /opt
mount -t ubifs /dev/ubi1_0 /opt
df -h /opt
```

## ⚠️ Package compatibility warning (read before `apk add`)

This image uses a **pinned userspace** (`24.10-SNAPSHOT r27648`) with a custom `6.18.39` kernel:

* **Do not upgrade core packages from online snapshot feeds:** `wpad-*`, `hostapd*`,
  `ucode*`, `libucode*`, `luci*`, `libc`, `libubox*`, `libubus*`, `netifd*`, `base-files`,
  or kernel modules (`kmod-*`). Always verify `apk add --simulate <pkg>` first.
* **Safe:** pure-leaf packages that do not pull core `lib*` upgrades (for example `mesh11sd`,
  `htop`, `nano`), and custom ABI-matched packages from `packages/`.
* **Recovery if `/overlay` is broken:** boot U-Boot with `init=/bin/sh`, mount `ubi0_2`, and
  remove offending files under `upper/`.

## Upgrades

LuCI → *System → Backup / Flash Firmware* → upload
`firmware/openwrt-24.10-r27648-qualcommbe-ipq53xx-dlink_dir-be364k-v31-squashfs-sysupgrade.bin`
→ **Proceed**. Allow up to ~8 minutes before unplugging power.

## Unbricking

Bootloaders (`SBL1` / `MIBIB` / `QSEE` / `APPSBL`) are never modified by these images:
1. Hold Reset ~5 s at power-on → **http://192.168.10.10** → flash `*-squashfs-factory.bin`
   (or official D-Link firmware).
2. After a software reboot, if the router appears stuck, power-cycle for 10 s (known
   IPQ5332 warm-reboot behavior).
3. UART recovery: use `tools/auto_flash_v31_uart_tftp.py` or `tftpboot 0x44000000 v31_ubi.bin` +
   `flash rootfs 0x44000000 <exact hex size>`.

## Known issues / limitations

* **Some LAN jacks report DHCP but cannot reach LuCI/SSH** — under investigation on `yt921x`;
  v31 includes the updated `DSA_TAG_PROTO_YT921X` and 32-bit FDB/MDB fixes (`patches/`). If an
  individual port shows issues in your topology, test on LAN1/LAN2.
* **5 GHz AP + STA share one radio** (`QCN6432`): both interfaces must share the same channel
  and compatible width (`htmode`).
* **No hardware flow offload** (no NSS/PPE tc-offload in mainline); software flow offloading is available.
* **Wi-Fi 7 requires WPA3-SAE(mixed)+PMF** on the AP side; legacy clients without PMF fall back cleanly.
* On 160 MHz AP operation, DFS rules may cause `iw scan` to return `EBUSY`.

## Versioning

Releases use sequential tags (`v30`, `v31`, …) mapped to `openwrt-24.10-r27648-…-v<N>-*` filenames;
the userspace release string inside this build is `OpenWrt 24.10-SNAPSHOT r27648 (DIR-BE364K Community Edition v31)`.

## Credits / License

* OpenWrt Project — https://openwrt.org
* PassWall 2 & Xray-core projects
* Motorcomm YT9215 DSA driver — David Yang (`mmyangfl`) and upstream DSA contributors
* Device tree, packaging and testing: DIR-BE364K community
* **License: GPL-2.0-only** (see `LICENSE`). This project is a derivative
  work of OpenWrt and the Linux kernel; all build scripts, device-tree
  sources and patches in this repository are released under the same terms.
  Firmware images bundle GPL-2.0 components; complete corresponding sources
  are the upstream OpenWrt tree plus everything shipped in this repository.
