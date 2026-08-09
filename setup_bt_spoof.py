#!/usr/bin/env python3
import os
import sys
import subprocess
import time

def reverse_key(key):
    b = bytes.fromhex(key)
    return b[::-1].hex()

def write_info(radio_addr, phone_addr, key, device_name="Unknown"):
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

def restart_and_check(radio_addr, phone_addr):
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
    else:
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
        else:
            print("[!] Still not paired. Check key/addresses.")
            print(result.stdout)
            return False

import argparse

def main():
    parser = argparse.ArgumentParser(description="Inject Bluetooth link key for passwordless pairing")
    parser.add_argument("--radio", required=True, help="BT address of the radio/adapter")
    parser.add_argument("--phone", required=True, help="BT address of the phone")
    parser.add_argument("--key",   required=True, help="Link key (32 hex chars)")
    parser.add_argument("--name",  default="Unknown", help="Device name (optional)")
    parser.add_argument("--reverse", action="store_true", help="Reverse byte order of key")
    args = parser.parse_args()

    radio_addr = args.radio.upper()
    phone_addr = args.phone.upper()
    key = args.key.lower()

    if args.reverse:
        key = reverse_key(key)
        print(f"[*] Reversed key: {key}")

    if len(key) != 32:
        print("[!] Key must be 32 hex chars (16 bytes)")
        sys.exit(1)

    write_info(radio_addr, phone_addr, key, args.name)
    restart_and_check(radio_addr, phone_addr)

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("[!] Run as root")
        sys.exit(1)
    main()
