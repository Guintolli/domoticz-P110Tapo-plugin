# domoticz-P110Tapo-plugin

A Domoticz plugin to manage P110 Tapo TP-Link Smart Wi-Fi Socket (TODO).
It bases on the plugin Domoticz-Tapo (which manage on/off switches for P100 Tapo) by 593304. 

## ONLY TESTED FOR Raspberry Pi

With Python version 3.7.3 & Domoticz version V2023.1
## Prerequisites

### Python version
This plugin requires Python version 3.7 or higher

### PyP100 library
This plugin is using [Toby Johnson's PyP100 library](https://pypi.org/project/PyP100/). 
Install this module by running this command: 
```
sudo pip3 install PyP100
```
You will also need the IP address of your Tapo device(s).

## Installation
Assuming that domoticz directory is installed in your home directory.
```bash
cd ~/domoticz/plugins
git clone https://github.com/Guintolli/domoticz-P110Tapo-plugin.git

# restart domoticz:
sudo /etc/init.d/domoticz.sh restart
```
## Known issues
--

## Updating

Like other plugins, in the domoticz-P110Tapo-plugin directory:
```bash
git pull
sudo /etc/init.d/domoticz.sh restart
```

## Parameters

TODO

## Acknowledgements

TODO
