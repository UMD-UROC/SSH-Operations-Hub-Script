---
description: Documentation for IP pool configuration flags.
---

# Passing Client IP Addresses

## -ip and -primary

These flags define the default IP pool. All clients in this pool use the username specified by the -user flag. By default, the script prepends "10.200.142." to each number unless a different prefix is specified.

```bash
# Example Usage:

# Using the -ip flag (results in 10.200.142.1, 10.200.142.2, 10.200.142.3)
ssh-operations-hub -ip 1 2 3

# Using a custom prefix
ssh-operations-hub -ip-prefix 192.168.1. -ip 1 2 3
```

{% hint style="success" %}
**Note:** The -ip and -primary flags are functionally identical and can be used interchangeably.
{% endhint %}

## -secondary

This flag defines the secondary IP pool. Clients in this pool use the username specified by the -suser flag.

```bash
# Example Usage

# Using the -secondary flag
ssh-operations-hub -primary 1 2 3 -secondary 4 5 6
```
