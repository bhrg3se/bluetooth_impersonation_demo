# Bluetooth Impersonation Demo

Proof-of-concept for impersonating a vehicle head unit to a previously paired
phone using a BR/EDR link key recovered from a used infotainment unit.
Companion code for *"Bluetooth Impersonation from Pairing Keys Recovered in
Used Vehicle Infotainment Systems"* (Acharya, Papadopoulos, Thanasoulas —
University of Memphis).

Given the head unit's Bluetooth address and link key, the target phone
re-authenticates to a spoofed host without any user interaction, exposing the
profiles it had granted the vehicle (HFP, PBAP, MAP).

## ⚠️ Authorized use only

For security research and education on devices you own or are explicitly
authorized to test. Impersonating Bluetooth devices to reach another person's
phone data is illegal in most jurisdictions. Use at your own responsibility.

## Requirements

- Linux with BlueZ (`bluetoothctl`, `/var/lib/bluetooth`)
- Python 3 + PyBluez
- Bluetooth adapter that supports address spoofing (e.g. `hci1`)
- root (for `inject_pair.py`)

## Tools

### `inject_pair.py`
Spoofs your adapter to the head unit's address and injects the link key into
the BlueZ pairing store, so the target phone treats the host as already paired.

```
sudo python inject_pair.py \
  --radio 34:C7:31:F1:E9:E1 \   # head-unit BT address (spoof to this)
  --phone 84:AB:1A:1C:B1:EC \   # target phone BT address
  --key   <link_key_hex> \
  --name  "Head Unit" \
  --reverse \                   # byte-reverse key if endianness differs
  --hci   hci1
```

### `bt_attack.v3.py`
Interactive menu to exercise the granted profiles once impersonation succeeds.

```
python bt_attack.v3.py 84:AB:1A:1C:B1:EC
```

- **HFP**  (ch 4)  — hands-free: phonebook, call log, place/answer calls
- **PBAP** (ch 19) — full contact database
- **MAP**  (ch 26) — SMS history / incoming messages (incl. OTPs)

## Troubleshooting

- `Host is down` / `not available`: phone not currently reachable, or the
  injected pairing didn't take. Recheck address, key, and `--reverse`.
- Restart `bluetooth.service` after injection.

## Mitigation

Unpair the head unit from every phone before transferring vehicle ownership.
Factory reset is unreliable. See the paper for vendor- and phone-side fixes.
