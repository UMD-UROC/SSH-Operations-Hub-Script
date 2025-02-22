---
description: This page explains how to pass a client username to the script.
---

# Passing Client User Names

## -user

This command defines the username for the default IP pool's clients.

```bash
# Example Usage

# Make username root
ssh-operations-hub -ip 1 2 3 -user root
```

This command will tell ssh to use root as the user when connecting to the clients.

## -suser

This flag works the same that the -user flag works except it defines the secondary client's username.

```bash
# Example Usage

# Make default pool's users root and secondary's pool users admin
ssh-operations-hub -primary 1 2 3 -user root -secondary 4 5 6 -suser admin
```



