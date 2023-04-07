# P110 Tapo TP-Link Plugin
#
# Author: Guintolli
#
"""
<plugin key="P110TapoPlugin" name="TP-Link P110 Tapo Plugin" author="Guintolli" version="1.0" externallink="https://github.com/Guintolli/domoticz-P110Tapo-plugin">
    <description>
        <h2>TP-Link P110 Tapo Plugin</h2><br/>
        <p>The plugin will connect to a P110 Tapo device with the given IP address, username(e-mail address) and password.</p>
        <p>Before using this plugin, you have to install the<a href="https://pypi.org/project/PyP100/" style="margin-left: 5px">PyP100 module</a></p>
        <br />
        <br />
    </description>
    <params>
        <param field="Username" label="Username" width="250px" required="true"/>
        <param field="Password" label="Password" width="250px" required="true" password="true"/>
        <param field="Address" label="IP address" width="250px" required="true"/>
        <param field="Mode2" label="Debug" width="50px">
            <options>
                <option label="Off" value="0" default="true"/>
                <option label="On" value="1"/>
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
from PyP100 import PyP110
import json
from datetime import date
from datetime import datetime
from typing import List
import requests
#from requests.auth import HTTPBasicAuth

HEARTBEAT_INTERVAL_DEFAULT = 10 #Interval in second between heartbeats
HEARTBEAT_INACTIVE_COUNTER_DEFAULT = 3 #HeartBeat will be active each HEARTBEAT_INTERVAL_DEFAULT * HEARTBEAT_INACTIVE_COUNTER_DEFAULT seconds
HEARTBEAT_INACTIVE_COUNTER_LOW = 30 #HeartBeat will be active each HEARTBEAT_INTERVAL_DEFAULT * HEARTBEAT_INACTIVE_COUNTER_LOW seconds

UNIT_SWITCH_DEVICE = 1
UNIT_WATT_USAGE_DEVICE = 2
UNIT_ENERGY_KWH_DEVICE = 3

DOMOTICZ_IP = '127.0.0.1'
DOMOTICZ_PORT = '8080'

# Class to manage the heartBeat settings
class Heartbeat:

    def __init__(self):
        self.callback = None
        self.interval: int = HEARTBEAT_INTERVAL_DEFAULT
        self.inactiveCounter: int = HEARTBEAT_INACTIVE_COUNTER_DEFAULT

    def setHeartbeat(self, callback):
        Domoticz.Heartbeat(self.interval)
        Domoticz.Log("Heartbeat interval is " + str(self.interval) + ".")
        self.callback = callback

    def setHeartbeatInactiveCounterToDefault(self):
        self.inactiveCounter = HEARTBEAT_INACTIVE_COUNTER_DEFAULT

    def setHeartbeatInactiveCounterToLow(self):
        self.inactiveCounter = HEARTBEAT_INACTIVE_COUNTER_LOW

    def beatHeartbeat(self):
        self.callback()


class P110TapoPlugin:
    def __init__(self):
        self.p110 = None
        self.lastState: dict = None
        self.todayEnergyInWh: int = 0 #today Watt-hour consumption
        self.isEnergyInitiated: bool = False
        self.userVariableEnergyPreviousDays: userVariable = None
        self.heartbeat: Heartbeat = Heartbeat()
        return

    def onStart(self):
        Domoticz.Log("onStart called")
        
        # Setting up debug mode
        if Parameters["Mode2"] != "0":
            Domoticz.Debugging(1)
            Domoticz.Debug("Debug mode enabled")
        
        # Setting up heartbeat
        self.heartbeat.setHeartbeat(self.update)

        # Creating PyP110 object
        ip: str = Parameters["Address"]
        email: str = Parameters["Username"]
        password: str = Parameters["Password"]
        self.p110 = PyP110.P110(ip, email, password)
        Domoticz.Debug("P110 Tapo object created with IP: " + ip)

        # Creating devices
        if UNIT_SWITCH_DEVICE not in Devices:
            # Switch ON/OFF device
            Domoticz.Device(
                Name="P110 switch",
                Unit=UNIT_SWITCH_DEVICE,
                TypeName="Selector Switch",
                Switchtype=0,
                Image=9,
                Options={}).Create()

        if UNIT_WATT_USAGE_DEVICE not in Devices:
            # Watt Usage device           
            Domoticz.Device(
                Name="P110 Usage (W)",
                Unit=UNIT_WATT_USAGE_DEVICE,
                TypeName="Usage").Create()

        if UNIT_ENERGY_KWH_DEVICE not in Devices:
            # General KwH device
            Domoticz.Device(
                Name="P110 General kWh",
                Unit=UNIT_ENERGY_KWH_DEVICE,
                TypeName="kWh").Create()

        # Get user variable to know the consumption of previous days
        userVariableEnergyPreviousDaysName = "P110TapoPlugin_DeviceID" + str(Devices[UNIT_ENERGY_KWH_DEVICE].ID) + "_EnergyPreviousDays"
        self.userVariableEnergyPreviousDays = userVariable(DOMOTICZ_IP, DOMOTICZ_PORT).getOrCreateUserVariableIdByName(userVariableEnergyPreviousDaysName)
        if self.userVariableEnergyPreviousDays is None:
            Domoticz.Error("userVariable " + userVariableEnergyPreviousDaysName + " not available")
        else:
            Domoticz.Debug("userVariable " + userVariableEnergyPreviousDaysName + " available, idx: " + str(self.userVariableEnergyPreviousDays.id))

        self.update()

        DumpConfigToLog()

        return

    def onStop(self):
        Domoticz.Log("onStop called")
        return

    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called; connection: %s, status: %s, description: %s" % (str(Connection), str(Status), str(Description)))
        return

    def onMessage(self, Connection, Data):
        Domoticz.Log("onMessage called; connection: %s, data: %s" % (str(Connection), str(Data)))
        return

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        if Unit != UNIT_SWITCH_DEVICE:
            Domoticz.Error("Unknown device with unit: " + str(Unit))
            return

        commandValue = 1 if Command == "On" else 0
        if self.lastState["device_on"] == commandValue:
            Domoticz.Log("Command and last state is the same, nothing to do")
            return
        
        self.p110.handshake()
        self.p110.login()
        if Command == "On":
            self.p110.turnOn()
        else:
            self.p110.turnOff()
        self.update()

        return

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)
        return

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")
        return

    def onHeartbeat(self):
        self.heartbeat.inactiveCounter -= 1
        if self.heartbeat.inactiveCounter != 0:
            # nothing to do
            Domoticz.Debug("onHeartbeat called, run again in " + str(self.heartbeat.inactiveCounter) + " heartbeats.")
        else:
            self.heartbeat.setHeartbeatInactiveCounterToDefault()
            self.heartbeat.beatHeartbeat()
        return


    def update(self):
        # Log in to device
        try:
            self.p110.handshake()
            self.p110.login()
        except Exception as ex:
            Domoticz.Error("Exception occurred during connection to device : " + type(ex).__name__ + ", arguments: " + repr(ex.args) + ". Next try in " + str(self.heartbeat.interval * HEARTBEAT_INACTIVE_COUNTER_LOW) + " seconds")
            self.heartbeat.setHeartbeatInactiveCounterToLow()
            return
        else:
            self.heartbeat.setHeartbeatInactiveCounterToDefault()

        # Get Information from Device
        deviceInfo = self.p110.getDeviceInfo()
        self.lastState = self.__getP110ResultFromRawResult(deviceInfo, "Device Info")

        # Update Switch ON/OFF device
        if self.lastState is not None:
            powerState: bool = self.lastState["device_on"]
            powerStateNValue: int = 1 if powerState else 0
            powerStateSValue: str = "On" if powerState else "Off"
            if (Devices[UNIT_SWITCH_DEVICE].nValue != powerStateNValue) or (Devices[UNIT_SWITCH_DEVICE].sValue != powerStateSValue):
                Domoticz.Debug("Updating %s (%d, %s)" % (Devices[UNIT_SWITCH_DEVICE].Name, powerStateNValue, powerStateSValue))
                Devices[UNIT_SWITCH_DEVICE].Update(nValue=powerStateNValue, sValue=powerStateSValue)

        currentPowerInWatt: int = 0 #current Watt usage
        # Get Energy Usage from P110 device if switch is on (or if we don't know)
        if not self.isEnergyInitiated or self.lastState is None or powerStateNValue:
            deviceEnergyUsage = self.p110.getEnergyUsage()
            lastEnergyUsage = self.__getP110ResultFromRawResult(deviceEnergyUsage, "Energy Usage")
            if lastEnergyUsage is not None:
                currentPowerInMilliwatt: float = lastEnergyUsage["current_power"]
                Domoticz.Debug("Current power from device: " + str(currentPowerInMilliwatt) + " mW")
                currentPowerInWatt = round(currentPowerInMilliwatt / 1000)

                self.todayEnergyInWh = lastEnergyUsage["today_energy"]
                Domoticz.Debug("Today energy from device: " + str(self.todayEnergyInWh) + " Wh")
                self.isEnergyInitiated = True

        # Update Watt Usage device
        if Devices[UNIT_WATT_USAGE_DEVICE].sValue != str(currentPowerInWatt):
            Domoticz.Debug("Updating %s (%i)" % (Devices[UNIT_WATT_USAGE_DEVICE].Name, currentPowerInWatt))
            Devices[UNIT_WATT_USAGE_DEVICE].Update(nValue=0, sValue=str(currentPowerInWatt))

        # Update General KwH device
        dateToday = date.today()
        #user variable 'userVariableEnergyPreviousDays' has not been updated today
        if self.userVariableEnergyPreviousDays.lastUpdate.date() < dateToday:
            Domoticz.Debug("userVariableEnergyPreviousDays to old, need to be updated")

            energyPreviousDaysValue: int
            if getLastUpdateFromDomoticzKwhDevice().date() < dateToday:
                Domoticz.Debug("KwH Device has not been updated today")
                energyPreviousDaysValue = getEnergyFromDomoticzKwhDevice()
            else:
                Domoticz.Debug("KwH Device has been updated today")
                energyPreviousDaysValue = getEnergyFromDomoticzKwhDevice() - self.todayEnergyInWh

            self.userVariableEnergyPreviousDays.updateValue(energyPreviousDaysValue)
            Domoticz.Debug("EnergyPreviousDays updated to: " + str(self.userVariableEnergyPreviousDays.value))

        Domoticz.Debug("previousTodayEnergy: " + str(self.userVariableEnergyPreviousDays.value) + ", todayEnergyInWh: " + str(self.todayEnergyInWh))
        kWhSValue: str = str(currentPowerInWatt) + ";" + str(self.userVariableEnergyPreviousDays.value + self.todayEnergyInWh)
        if Devices[UNIT_ENERGY_KWH_DEVICE].sValue != kWhSValue:
            Devices[UNIT_ENERGY_KWH_DEVICE].Update(nValue=0, sValue=kWhSValue)

        return

    @staticmethod
    def __getP110ResultFromRawResult(p110RawResultFromApiCall, callType: str) -> dict:
        resultTmp: dict
        if not isinstance(p110RawResultFromApiCall, dict):
            resultTmp = json.loads(p110RawResultFromApiCall)
        else:
            resultTmp = p110RawResultFromApiCall

        result: dict = None
        if resultTmp["error_code"] != 0:
            Domoticz.Error("Cannot get " + callType + " from device, error code: " + str(resultTmp["error_code"]))
        else:
            result = resultTmp["result"]
            Domoticz.Debug(callType + " data from device: " + json.dumps(result))

        return result


global _plugin
_plugin = P110TapoPlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

#Return energy stored by Domoticz for Energy Kwh Device
def getEnergyFromDomoticzKwhDevice() -> int:
    sValuePreviousUpdate: str = Devices[UNIT_ENERGY_KWH_DEVICE].sValue
    listValuePreviousUpdate: List[str] = sValuePreviousUpdate.split(";")

    energy: int = 0
    if len(listValuePreviousUpdate) != 2:
        Domoticz.Error("Something wrong during extract of svalue of Device[" + str(UNIT_ENERGY_KWH_DEVICE) + "] from last update")
    else:
        energy = int(float(listValuePreviousUpdate[1]))

    return energy

#Return the last update datetime for Energy Kwh Device
def getLastUpdateFromDomoticzKwhDevice() -> datetime:
    return datetime.fromisoformat(Devices[UNIT_ENERGY_KWH_DEVICE].LastUpdate)



# Class to manage the domoticz user variables (stored in database)
class userVariable:
    domoticzIP: str
    domoticzPort: str
    name: str
    value: int
    id: int
    lastUpdate: datetime
    type: str

    def __init__(self, domoticzIP, domoticzPort):
        self.domoticzIP = domoticzIP
        self.domoticzPort = domoticzPort

    def __call(self, jsonUrl: str, isReturnResult: bool):
        userVariablesUrl: str = 'http://' + DOMOTICZ_IP + ':' + DOMOTICZ_PORT + jsonUrl
        r = requests.get(userVariablesUrl)
        status: int = r.status_code

        if status != 200:
            Domoticz.Error("Error during call to : " + jsonUrl + ", error code: " + str(status))
            if isReturnResult:
                return None
        else:
            Domoticz.Debug("result of call " + jsonUrl + " : " + str(r.json()))
            if isReturnResult:
                return r.json()["result"]


    def getOrCreateUserVariableIdByName(self, userVariableName: str):
        Domoticz.Debug("getOrCreateUserVariableIdByName, userVariableName: " + userVariableName)

        usrVariable = self.getUserVariableByName(userVariableName)
        if usrVariable is None:
            Domoticz.Debug("userVariable not found, add it")
            self.addUserVariable(userVariableName)
            usrVariable = self.getUserVariableByName(userVariableName)

        return usrVariable


    def getUserVariableByName(self, userVariableName: str):
        Domoticz.Debug("getUserVariableByName, userVariableName: " + userVariableName)

        jsonUserVariablesUrl: str = '/json.htm?type=command&param=getuservariables'
        userVariables = self.__call(jsonUserVariablesUrl, True)
        if userVariables is not None:
            for x in userVariables:
                if x["Name"] == userVariableName:
                    Domoticz.Debug("user Variable with name: " + userVariableName + " found, idx: " + str(x["idx"]))
                    usrVar = userVariable(self.domoticzIP, self.domoticzPort)
                    usrVar.id = int(x["idx"])
                    usrVar.name = x["Name"]
                    usrVar.lastUpdate = datetime.fromisoformat(x["LastUpdate"])
                    usrVar.type = x["Type"]
                    usrVar.value = int(x["Value"])
                    return usrVar

        return None

    def getUserVariableByID(self, userVariableId: int):
        Domoticz.Debug("getUserVariableByID, userVariableId: " + str(userVariableId))

        jsonUserVariablesUrl: str = '/json.htm?type=command&param=getuservariable&idx=' + str(userVariableId)
        result = self.__call(jsonUserVariablesUrl, True)
        if result is not None:
            Domoticz.Debug("user Variable with idx: " + str(userVariableId) + " found, name: " + result[0]["Name"])
            usrVar = userVariable(self.domoticzIP, self.domoticzPort)
            usrVar.id = int(result[0]["idx"])
            usrVar.name = result[0]["Name"]
            usrVar.lastUpdate = datetime.fromisoformat(result[0]["LastUpdate"])
            usrVar.type = result[0]["Type"]
            usrVar.value = int(result[0]["Value"])
            return usrVar
        else:
            return None

    def addUserVariable(self, userVariableName: str):
        Domoticz.Debug("addUserVariable, userVariableName: " + userVariableName)

        jsonAddUserVariablesUrl: str = '/json.htm?type=command&param=adduservariable&vname=' + userVariableName + '&vtype=0&vvalue=0'
        self.__call(jsonAddUserVariablesUrl, False)

    def __deleteUserVariable(self, userVariableId: int):
        Domoticz.Debug("deleteUserVariable, userVariableId: " + str(userVariableId))

        jsonUserVariablesUrl: str = '/json.htm?type=command&param=deleteuservariable&idx==' + str(userVariableId)
        self.__call(jsonUserVariablesUrl, False)

    def delete(self):
        self.__deleteUserVariable(self.id)

    def updateUserVariable(self, userVariableName: str, userVariableValue: int):
        Domoticz.Debug("updateUserVariable, userVariableName: " + userVariableName + ", userVariableValue: " + str(userVariableValue))

        jsonUserVariablesUrl: str = '/json.htm?type=command&param=updateuservariable&vname=' + userVariableName + '&vtype=0&vvalue=' + str(userVariableValue)
        self.__call(jsonUserVariablesUrl, False)

    def updateValue(self, value: int):
        self.value = value
        self.updateUserVariable(self.name, value)
        usFromDomo: userVariable = self.getUserVariableByID(self.id)
        self.lastUpdate = usFromDomo.lastUpdate