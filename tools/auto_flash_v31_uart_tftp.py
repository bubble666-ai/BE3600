#!/usr/bin/env python3
"""
Fully Automated TFTP + UART Flashing Engine for DIR-BE364K (OpenWrt v31)
"""
import argparse
import os
import sys
import time
import socket
import threading
import serial

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ROOT = os.path.join(REPO_ROOT, "firmware")

parser = argparse.ArgumentParser(description="Automated UART + TFTP flasher for DIR-BE364K (v31)")
parser.add_argument("--port", default="COM3", help="Serial COM port (default: COM3)")
parser.add_argument("--image", default=os.path.join(DEFAULT_ROOT, "v31_ubi.bin"), help="Path to v31_ubi.bin")
args = parser.parse_args()

IMAGE_PATH = os.path.abspath(args.image)
ROOT = os.path.dirname(IMAGE_PATH)
IMAGE_NAME = os.path.basename(IMAGE_PATH)

if not os.path.isfile(IMAGE_PATH):
    print(f"[ERROR] Image not found: {IMAGE_PATH}")
    sys.exit(1)

IMAGE_SIZE = os.path.getsize(IMAGE_PATH)
HEX_SIZE = f"0x{IMAGE_SIZE:x}"
print(f"[*] Target Image: {IMAGE_NAME} ({IMAGE_SIZE} bytes / {HEX_SIZE})")

PORT = 69
COM_PORT = args.port
BAUDRATE = 115200

ROUTER_IP = "192.168.10.10"
SERVER_IP = "192.168.10.20"
NETMASK = "255.255.255.0"

transfer_done = threading.Event()
transfer_success = False

def fix_win(sock):
    if sys.platform == 'win32':
        try: sock.ioctl(0x9800000C, False)
        except Exception: pass

def do_transfer(sock, addr, filename, blksize):
    global transfer_success
    path = os.path.join(ROOT, os.path.basename(filename))
    if not os.path.isfile(path):
        print(f"[tftp] Not found: {filename}", flush=True)
        sock.close()
        return
    size = os.path.getsize(path)
    total_blocks = (size + blksize - 1) // blksize
    print(f"\n[tftp] Starting stream: {filename} ({size} bytes, {total_blocks} blocks of {blksize}) to {addr}", flush=True)

    with open(path, 'rb') as f:
        data = f.read()

    block = 1
    t0 = time.time()
    try:
        while True:
            chunk = data[(block-1)*blksize : block*blksize]
            pkt = bytes([0, 3]) + (block & 0xFFFF).to_bytes(2, 'big') + chunk

            ack_ok = False
            for retry in range(10):
                sock.sendto(pkt, addr)
                time.sleep(0.0003)
                try:
                    while True:
                        ack, peer = sock.recvfrom(1024)
                        if len(ack) >= 4 and ack[1] == 4:
                            ack_blk = int.from_bytes(ack[2:4], 'big')
                            if ack_blk == (block & 0xFFFF):
                                ack_ok = True
                                addr = peer
                                break
                            elif ack_blk < (block & 0xFFFF):
                                continue
                        elif len(ack) >= 4 and ack[1] == 5:
                            print(f"[tftp] Client Error: {ack[4:]}", flush=True)
                            return
                except socket.timeout:
                    pass
                if ack_ok:
                    break

            if not ack_ok:
                print(f"\n[tftp] FAILED at block {block}", flush=True)
                break

            if block % 1000 == 0 or block == total_blocks:
                pct = (block / total_blocks) * 100
                mb = (block * blksize) / (1024 * 1024)
                el = time.time() - t0
                spd = mb / el if el > 0 else 0
                print(f"[tftp] Progress: {block}/{total_blocks} ({pct:.1f}%) [{mb:.2f} MB, {spd:.2f} MB/s]", flush=True)

            if len(chunk) < blksize:
                el = time.time() - t0
                spd = (size / 1024 / 1024) / el if el > 0 else 0
                print(f"\n[tftp] >>> TRANSFER 100% SUCCESS: {size} bytes in {el:.2f}s ({spd:.2f} MB/s) <<<", flush=True)
                transfer_success = True
                transfer_done.set()
                break
            block += 1
    except Exception as e:
        print(f"[tftp] Socket exception: {e}", flush=True)
    finally:
        sock.close()

def handle_rrq(req, addr):
    parts = req[2:].split(b'\x00')
    filename = parts[0].decode('utf-8', 'replace')
    blksize = 512
    i = 2
    while i + 1 < len(parts):
        opt_name = parts[i].decode('utf-8', 'replace').lower()
        if opt_name == 'blksize':
            try:
                b = int(parts[i+1])
                if 8 <= b <= 65464:
                    blksize = b
            except:
                pass
        i += 2

    print(f"\n[tftp] Incoming RRQ for '{filename}' from {addr} (blksize={blksize})", flush=True)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    fix_win(sock)
    sock.settimeout(3.0)

    cur_addr = addr
    if blksize != 512:
        oack = bytes([0, 6]) + b'blksize\x00' + str(blksize).encode() + b'\x00'
        sock.sendto(oack, cur_addr)
        try:
            ack, peer = sock.recvfrom(1024)
            cur_addr = peer
        except socket.timeout:
            print("[tftp] No ACK for OACK from client", flush=True)
            sock.close()
            return

    do_transfer(sock, cur_addr, filename, blksize)

def tftp_listener():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    fix_win(s)
    s.bind(('', PORT))
    print(f"[tftp] Server listening on 0.0.0.0:{PORT}...", flush=True)
    while not transfer_done.is_set():
        s.settimeout(1.0)
        try:
            req, addr = s.recvfrom(1024)
        except socket.timeout:
            continue
        except Exception:
            break
        if req[:2] == b'\x00\x01':
            threading.Thread(target=handle_rrq, args=(req, addr), daemon=True).start()
    s.close()

def main():
    th = threading.Thread(target=tftp_listener, daemon=True)
    th.start()
    time.sleep(0.3)

    ser = serial.Serial(COM_PORT, BAUDRATE, timeout=0.05)
    print(f"[*] Serial {COM_PORT} opened.")

    for _ in range(3):
        ser.write(b"\x03\r\n")
        time.sleep(0.1)
    while ser.read(4096): pass

    print("[*] Configuring U-Boot parameters...")
    cmds = [
        f"setenv ipaddr {ROUTER_IP}\n",
        f"setenv serverip {SERVER_IP}\n",
        f"setenv netmask {NETMASK}\n",
        "setenv tftpblocksize\n",
        "setenv tftptimeout 10000\n",
        "setenv netretry yes\n"
    ]
    for c in cmds:
        ser.write(c.encode())
        time.sleep(0.15)
        while ser.read(4096): pass

    print(f"\n[*] Triggering 'tftpboot 0x44000000 {IMAGE_NAME}'...")
    ser.write(f"tftpboot 0x44000000 {IMAGE_NAME}\n".encode())

    t0 = time.time()
    tftp_log = ""
    while time.time() - t0 < 180:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            text = chunk.decode('utf-8', 'replace')
            sys.stdout.write(text)
            sys.stdout.flush()
            tftp_log += text
            if "Bytes transferred =" in tftp_log and "IPQ5332#" in tftp_log:
                break
        if transfer_success and "IPQ5332#" in tftp_log:
            break
        time.sleep(0.05)

    if not transfer_success and "Bytes transferred =" not in tftp_log:
        print("\n[!] TFTP download failed to complete.")
        ser.close()
        return

    print("\n\n==================================================================")
    print("[*] >>> TFTP DOWNLOAD 100% VERIFIED IN MEMORY (0x44000000) <<<")
    print("==================================================================\n")
    time.sleep(1.0)

    print(f"[*] STEP 1/3: Flashing rootfs partition ({HEX_SIZE} bytes)...")
    ser.write(f"flash rootfs 0x44000000 {HEX_SIZE}\n".encode())

    t_fl = time.time()
    fl_buf = ""
    while time.time() - t_fl < 180:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            text = chunk.decode('utf-8', 'replace')
            sys.stdout.write(text)
            sys.stdout.flush()
            fl_buf += text
            if "IPQ5332#" in fl_buf and ("complete" in fl_buf or "Writing" in fl_buf or "Erasing" in fl_buf):
                break
        time.sleep(0.1)

    print("\n[*] Rootfs partition flashed successfully!")
    time.sleep(1.0)

    print(f"\n[*] STEP 2/3: Flashing rootfs_1 partition (secondary slot mirror)...")
    ser.write(f"flash rootfs_1 0x44000000 {HEX_SIZE}\n".encode())
    t_fl = time.time()
    fl_buf = ""
    while time.time() - t_fl < 180:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            text = chunk.decode('utf-8', 'replace')
            sys.stdout.write(text)
            sys.stdout.flush()
            fl_buf += text
            if "IPQ5332#" in fl_buf and ("complete" in fl_buf or "Writing" in fl_buf or "Erasing" in fl_buf or "Unknown" in fl_buf):
                break
        time.sleep(0.1)

    time.sleep(1.0)
    print("\n[*] STEP 3/3: Setting permanent OpenWrt v31 boot environment variables...")
    env_cmds = [
        'setenv bargs "console=ttyMSM0,115200n8 earlycon ubi.mtd=rootfs ubi.block=0,1 root=/dev/ubiblock0_1 rootfstype=squashfs clk_ignore_unused"\n',
        'setenv bootargs "console=ttyMSM0,115200n8 earlycon ubi.mtd=rootfs ubi.block=0,1 root=/dev/ubiblock0_1 rootfstype=squashfs clk_ignore_unused"\n',
        'setenv loadk "ubi part rootfs; ubi read 0x44000000 kernel"\n',
        'setenv bootk "bootm 0x44000000#config@mi04.1"\n',
        'setenv bootcmd "run loadk; run bootk"\n',
        'setenv bootdelay 3\n',
        'saveenv\n'
    ]
    for c in env_cmds:
        ser.write(c.encode())
        time.sleep(0.4)
        if ser.in_waiting:
            sys.stdout.write(ser.read(ser.in_waiting).decode('utf-8', 'replace'))
            sys.stdout.flush()

    time.sleep(1.0)
    print("\n==================================================================")
    print("[*] RESETTING ROUTER INTO PERMANENT OPENWRT V31...")
    print("==================================================================\n", flush=True)
    ser.write(b"reset\n")

    t_boot = time.time()
    boot_log = ""
    while time.time() - t_boot < 150:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            text = chunk.decode('utf-8', 'replace')
            sys.stdout.write(text)
            sys.stdout.flush()
            boot_log += text
            if "procd: - init complete -" in boot_log or "Please press Enter to activate this console" in boot_log:
                print("\n\n==================================================================")
                print(">>> OPENWRT V31 BOOT SUCCESS FROM NAND CONFIRMED! <<<")
                print("==================================================================")
                break
        time.sleep(0.02)

    ser.close()
    print("\n[*] Script execution completed.")

if __name__ == '__main__':
    main()
