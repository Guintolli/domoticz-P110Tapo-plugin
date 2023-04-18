# P110 Tapo plugin for Domoticz

A Domoticz plugin to manage P110 Tapo TP-Link Smart Wi-Fi Socket (on/off switch & energy monitoring).
It's inspired by the [Domoticz-Tapo](https://github.com/593304/Domoticz-Tapo) plugin (which manages on/off switch for P100 Tapo socket) made by 593304.

![p110switch](https://user-images.githubusercontent.com/86910832/232882924-8dfcb660-23e5-4db3-9205-2ece749267f3.JPG)

![p110usage](https://user-images.githubusercontent.com/86910832/232883466-acde5ee0-f218-4d8b-85a9-2c26620b325e.JPG)

![p110kwh](https://user-images.githubusercontent.com/86910832/232883490-02403864-8761-4f36-abba-eec85aebbd56.JPG)


## ONLY TESTED FOR Raspberry Pi

With Python version 3.7.3 & Domoticz version V2023.1

## Prerequisites

### Python version
This plugin requires Python version 3.7 or higher

### PyP100 library
This plugin is using [Toby Johnson's PyP100 library](https://pypi.org/project/PyP100/). 
The library can be installed by running the following command: 
```
sudo pip3 install PyP100
```
You will also need the IP address of your P110 Tapo device.

## Installation
Assuming that domoticz directory is installed in your home directory.
```bash
cd ~/domoticz/plugins
git clone https://github.com/Guintolli/domoticz-P110Tapo-plugin.git

# restart domoticz:
sudo /etc/init.d/domoticz.sh restart
```
## Updating

Like other plugins, in the domoticz-P110Tapo-plugin directory:
```bash
git pull
sudo /etc/init.d/domoticz.sh restart
```

## Parameters

TODO

## Acknowledgements

* [Toby Johnson's PyP100 library](https://pypi.org/project/PyP100/)and its maintainer fishbigger
* 593304 and its P100 domoticz plugin
