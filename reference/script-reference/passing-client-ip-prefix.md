---
description: Documentation for customizing IP address prefixes.
---

# Passing Client IP Prefix

## -ip-prefix

This flag sets a custom prefix for IP addresses. If not specified, the default prefix is `10.200.142.`

```bash
# Change IP prefix to 192.168.1.
ssh-operations-hub -ip-prefix 192.168.1. -ip 1 2 3

# Results in connection to:
# - 192.168.1.1
# - 192.168.1.2
# - 192.168.1.3
```

The default IP prefix can be changed by following directions on this page [configuration.md](../configuration.md "mention").
