# SSH Operations Hub

A bash script for managing and executing commands across multiple clients via ssh.

**Full Documentation:** [SSH Operations Hub Documentation](https://cdenihan.gitbook.io/ssh-operations-hub-script-docs)

## Basic Usage

```bash
./ssh-operations-hub [-primary|-ip ip_list] [-puser|-user username] [-secondary ip_list] [-suser username] [-cmd command] [-prefix ip_prefix]
```

### Quick Example

```bash
./ssh-operations-hub -primary 1 2 3 -user root -cmd "echo Hello from client \$CLIENT_NUM"
```

## Features

- Execute commands across multiple SSH clients
- IP address validation and deduplication
- Support for primary and secondary drone groups
- Variable substitution in commands
- Comprehensive error handling

For complete documentation, configuration options, and advanced usage examples, please visit:
https://cdenihan.gitbook.io/ssh-operations-hub-script-docs
