---
description: Configuration options available in defaults.conf
---

# Configuration

## IP\_PREFIX

Sets the default IP prefix used when no -ip-prefix flag is provided.

```bash
# Default value
IP_PREFIX="10.200.142"

# Example change
IP_PREFIX="192.168.1"
```

## ALLOWED\_IPS

Defines valid IP octets that can be used with the script. Supports individual numbers and ranges.

```bash
# Default value
ALLOWED_IPS="1-10 15 17 20-25"

# Example: Allow only IPs 150-153
ALLOWED_IPS="150-153"
```

{% hint style="info" %}
**Note:** Ranges are inclusive and multiple ranges/numbers can be specified with spaces.
{% endhint %}
