# Quick Start

## Installation

For optimal interaction with the script, please follow the installation instructions below:

{% tabs %}
{% tab title="Ubuntu 22.04 LTS" %}
```bash
# Install via Curl
curl -s https://raw.githubusercontent.com/cdenihan/SSH-Operations-Hub-Script/main/scripts/install.bash | bash
```
{% endtab %}
{% endtabs %}

{% hint style="warning" %}
**Important:** This script has only been tested on Ubuntu Desktop 22.04 LTS.
{% endhint %}

{% hint style="danger" %}
**Security Notice:** For security-conscious users, it is recommended that you review the installation script source code and execute the commands manually.
{% endhint %}

## Run your first command

Execute your first multi-client command by running:

```bash
# This command will connect to 10.200.142.1, 10.200.142.2, and 10.200.142.3
ssh-operations-hub -ip 1 2 3 -user root -cmd "echo Client \$CLIENT_NUM ready"
```

{% hint style="info" %}
**Tip:** Each client gets assigned a $CLIENT\_NUM variable that represents its position in the IP list (starting from 1).
{% endhint %}

{% hint style="info" %}
**Note:** The -ip flag automatically appends the default IP prefix (10.200.142.) to the provided IP octets. To use a different prefix, specify it using the -ip-prefix flag, for example: `-ip-prefix 192.168.1`
{% endhint %}

{% hint style="warning" %}
**Note:** Interactive commands are not supported by this script. For more information about command compatibility, please refer to the "Passing Command To Be Run On Client" section.
{% endhint %}

**For detailed information about available commands, please consult the "Script Reference" documentation.**
