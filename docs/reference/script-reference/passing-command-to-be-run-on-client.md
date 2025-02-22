---
description: Documentation for passing commands to remote clients.
---

# Passing Command To Be Run On Client

## -cmd

The -cmd flag specifies the command to be executed on all target clients.

```bash
# Simple command example
ssh-operations-hub -ip 1 2 3 -user root -cmd "echo test"

# Using the $CLIENT_NUM variable
# NOTE: The $CLIENT_NUM variable must be escaped out like so to be used: \$CLIENT_NUM
ssh-operations-hub -ip 1 2 3 -user root -cmd "echo Client \$CLIENT_NUM ready"
```

## Known Issues

* Interactive commands (like `htop`, `vim`, etc.) are not supported
* Commands requiring user input will cause the script to hang
*   For commands that require confirmation (like `apt upgrade`), use the `-y` flag when available:

    ```bash
    ssh-operations-hub -ip 1 2 3 -user root -cmd "apt upgrade -y"
    ```
