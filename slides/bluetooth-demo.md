---
title: Bluetooth
sub_title: what's left behind
author: Bhargab
theme:
  name: dark
---

<!-- end_slide -->

![]()

<!-- IMG: junkyard car interior, or parted honda dashboard -->
<!-- speaker: "what's still in here?" -->

<!-- end_slide -->

The stack
===

![]()

<!-- IMG SEARCH: "bluetooth protocol stack diagram" -->
<!-- speaker: radio -> baseband -> L2CAP -> profiles. we care about the top -->

<!-- end_slide -->

BR/EDR vs BLE
===

![]()

<!-- IMG SEARCH: "bluetooth classic vs ble comparison chart" -->
<!-- speaker: different pairing, different attack surfaces -->

<!-- end_slide -->

Pairing, over time
===

![]()

<!-- IMG SEARCH: "bluetooth pairing methods timeline" -->
<!-- or draw your own: Legacy -> SSP -> Secure Connections -> LE SC -->
<!-- speaker: each one fixed the last one's sins. mostly. -->

<!-- end_slide -->

Where the keys live
===

![]()

<!-- IMG SEARCH: "bluetooth pairing phone car icon" -->
<!-- want: phone <-> key <-> car -->
<!-- speaker: both sides store the link key. forever. -->

<!-- end_slide -->

The flash chip
===

![](placeholder.jpg)

<!-- IMG SEARCH: "emmc chip pcb macro" or "spi flash soic8 closeup" -->
<!-- speaker: this is where the key sleeps after the car dies -->

<!-- end_slide -->

Extraction
===

![](placeholder.jpg)

<!-- IMG: your own photo of the rig - UART clips, CH341, logic analyzer -->
<!-- speaker: walk through your actual setup -->

<!-- end_slide -->

The key
===

```
LinkKey: 4f 8a 2e b7 91 c3 d0 55
         6a 1f 88 4c 29 7e 3b 90

BDADDR:  AA:BB:CC:DD:EE:FF
```

<!-- speaker: this is all you need. -->

<!-- end_slide -->

The real prize
===

# HFP · PBAP · MAP

<!-- speaker: radio layer is boring. profiles are where your data lives. -->
<!-- HFP = calls, PBAP = contacts, MAP = sms -->

<!-- end_slide -->

Impersonation
===

![]()

<!-- IMG: draw your own - attacker laptop -> victim phone, arrow labeled "I'm the car" -->
<!-- speaker: spoof BDADDR, load the key, phone reconnects happily -->

<!-- end_slide -->

# demo

<!-- speaker: live fire -->

<!-- end_slide -->

What this doesn't break
===

- Secure Connections + numeric compare
- Locked screens (mostly)
- Devices that rotate keys
- Phones out of range

<!-- speaker: be honest about limits. crowd respects it. -->

<!-- end_slide -->

It's not just cars
===

![](placeholder.jpg)

<!-- IMG SEARCH: collage - rental car dashboard, uber interior, airbnb smart lock, hotel tv -->
<!-- speaker: anywhere a device outlives its owner -->

<!-- end_slide -->

Wipe your pairings
===

# thanks

<!-- contact info / questions -->
