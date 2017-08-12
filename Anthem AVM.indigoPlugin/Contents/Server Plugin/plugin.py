#! /usr/bin/env python

import indigo
import serial
import threading
import os
import time
from datetime import datetime

################################################################################
class Plugin(indigo.PluginBase):
	#####################################
	# Begin Indigo plugin API functions #
	#####################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = pluginPrefs.get("DebugFlag", False)
		self.serialLocks = {}
		self.serialConns = {}
		self.tempSerial = None

		for dev in indigo.devices.iter("self"):
			if dev.deviceTypeId == "main":
				self.logger.info("Found "+dev.deviceTypeId)
				self.serialLocks[dev.id] = threading.Lock()
				self.serialConns[dev.id] = None


	def __del__(self):
		indigo.PluginBase.__del__(self)

	########################################
	def startup(self):
		self.logger.debug(u"startup called")

	########################################
	def shutdown(self):
		self.logger.debug(u"shutdown called")

	########################################
	def deviceStartComm(self, dev, blockIfBusy=True):
		if dev.deviceTypeId == "main":
			self.logger.debug("deviceStartComm() enter for main device")
# 			if self.serialLocks[dev.id].acquire(blockIfBusy):
# 				self.checkSerial(dev)
# 				self.serialLocks[dev.id].release()
# 			else:
# 				self.logger.debug(u"<<-- skipped deviceStartComm (startStop locked) -->>")
		return

	########################################
	def deviceStopComm(self, dev, blockIfBusy=True):
		if dev.deviceTypeId == "main":
			self.logger.debug("deviceStopComm() enter for main device")
# 			if self.serialLocks[dev.id].acquire(blockIfBusy):
# 				if self.serialConns[dev.id] is not None:
# 					self.serialConns[dev.id].close()
# 					self.serialConns[dev.id] = None
# 			else:
# 				self.logger.debug(u"<<-- skipped deviceStartComm (startStop locked) -->>")
		return

	########################################
	def getDeviceFactoryUiValues(self, devIdList):
		self.logger.info("getDeviceFactoryUiValues() enter")
		valuesDict = indigo.Dict()
		errorMsgDict = indigo.Dict()
		mainFound = False

		for devId in devIdList:
			dev = indigo.devices[devId]
			self.logger.debug("devIdList includes "+dev.deviceTypeId)
			if dev.deviceTypeId == "main":
				mainFound = True
				# TODO check for open serial handle
				valuesDict["devicePortFieldId_serialConnType"] = dev.pluginProps.get("devicePortFieldId_serialConnType", "")
				valuesDict["devicePortFieldId_serialPortLocal"] = dev.pluginProps.get("devicePortFieldId_serialPortLocal", "")
				valuesDict["devicePortFieldId_serialPortNetRfc2217"] = dev.pluginProps.get("devicePortFieldId_serialPortNetRfc2217", "")
				valuesDict["devicePortFieldId_serialPortNetSocket"] = dev.pluginProps.get("devicePortFieldId_serialPortNetSocket", "")
			elif dev.deviceTypeId == "tuner":
				valuesDict["enableTuner"] = True
			elif dev.deviceTypeId == "zone2":
				valuesDict["enableZone2"] = True
			elif dev.deviceTypeId == "zone3":
				valuesDict["enableZone3"] = True

		if not mainFound:
			self.logger.debug("Creating main device")
			mainDev = indigo.device.create(indigo.kProtocol.Plugin, deviceTypeId="main")
			mainDev.model = "Anthem AVM Processor"
			mainDev.subModel = "Main"
			mainDev.replaceOnServer()


		return (valuesDict, errorMsgDict)

	########################################
	def updateAddress(self, dev, address):
		localPropsCopy = dev.pluginProps
		localPropsCopy.update({"devicePortFieldId_uiAddress":address})
		dev.replacePluginPropsOnServer(localPropsCopy)

	########################################
	def validateDeviceFactoryUi(self, valuesDict, devIdList):
		self.logger.info("validateDeviceFactoryUi() enter")
		errorsDict = indigo.Dict()
		self.validateSerialPortUi(valuesDict, errorsDict, u"devicePortFieldId")
		if len(errorsDict) > 0:
			# Some UI fields are not valid, return corrected fields and error messages (client
			# will not let the dialog window close).
			return (False, valuesDict, errorsDict)

		self.logger.debug(valuesDict)

		#TODO validate 

		return (True, valuesDict, errorsDict)

	########################################
	def closedDeviceFactoryUi(self, valuesDict, userCancelled, devIdList):
		self.logger.info("closedDeviceFactoryUi() enter")
		self.logger.debug(valuesDict)
		if self.tempSerial is not None:
			self.logger.info("Closing temporary serial handle")
			self.tempSerial = None

		if userCancelled:
			self.logger.info("Factory UI Cancelled")
			return

		#A lot of the things I'm doing in validate() should really be here
		mainDev = 0
		tunerDev = 0
		zone2Dev = 0
		zone3Dev = 0
		zone2Enabled = valuesDict.get("enableZone2", False)
		zone3Enabled = valuesDict.get("enableZone3", False)
		tunerEnabled = valuesDict.get("enableTuner", False)

		for devId in devIdList:
			dev = indigo.devices[devId]
			self.logger.debug("devIdList includes "+dev.deviceTypeId)
			if dev.deviceTypeId == "main":
				mainDev = dev
#				self.logger.debug(mainDev)
			elif dev.deviceTypeId == "tuner":
				tunerDev = dev
			elif dev.deviceTypeId == "zone2":
				zone2Dev = dev
			elif dev.deviceTypeId == "zone3":
				zone3Dev = dev
			else:
				self.logger.error("Unrecognized device type ")
				
		if mainDev.address != valuesDict["devicePortFieldId_uiAddress"]:
			localPropsCopy = mainDev.pluginProps
			localPropsCopy.update({"devicePortFieldId_uiAddress" : valuesDict["devicePortFieldId_uiAddress"],
					"devicePortFieldId_serialConnType" : valuesDict["devicePortFieldId_serialConnType"],
					"devicePortFieldId_serialPortLocal" : valuesDict["devicePortFieldId_serialPortLocal"],
					"devicePortFieldId_serialPortNetRfc2217" : valuesDict["devicePortFieldId_serialPortNetRfc2217"],
					"devicePortFieldId_serialPortNetSocket" : valuesDict["devicePortFieldId_serialPortNetSocket"]})
			mainDev.replacePluginPropsOnServer(localPropsCopy)

		if tunerDev == 0 and tunerEnabled:
			self.logger.debug("Creating tuner device")
			tunerDev = indigo.device.create(indigo.kProtocol.Plugin, deviceTypeId="tuner")
			tunerDev.model = "Anthem AVM Processor"
			tunerDev.subModel = "Tuner"
			localPropsCopy = tunerDev.pluginProps
			localPropsCopy.update({"devicePortFieldId_uiAddress" : valuesDict["devicePortFieldId_uiAddress"],
					 "mainDevId" : mainDev.id})
			tunerDev.replacePluginPropsOnServer(localPropsCopy)
			tunerDev.replaceOnServer()
		elif tunerDev != 0:
			if not tunerEnabled:
				self.logger.debug("Destroying tuner device")
				indigo.device.delete(tunerDev)
				tunerDev = 0
			elif tunerDev.address != valuesDict["devicePortFieldId_uiAddress"]:
				self.updateAddress(tunerDev, valuesDict["devicePortFieldId_uiAddress"])

		if zone2Dev == 0 and zone2Enabled:
			self.logger.debug("Creating zone2 device")
			zone2Dev = indigo.device.create(indigo.kProtocol.Plugin, deviceTypeId="zone2")
			zone2Dev.model = "Anthem AVM Processor"
			zone2Dev.subModel = "Zone 2"
			localPropsCopy = zone2Dev.pluginProps
			localPropsCopy.update({"devicePortFieldId_uiAddress" : valuesDict["devicePortFieldId_uiAddress"],
					 "mainDevId" : mainDev.id})
			zone2Dev.replacePluginPropsOnServer(localPropsCopy)
			zone2Dev.replaceOnServer()
		elif zone2Dev != 0:
			if not zone2Enabled:
				self.logger.debug("Destroying zone2 device")
				indigo.device.delete(zone2Dev)
				zone2Dev = 0
			elif zone2Dev.address != valuesDict["devicePortFieldId_uiAddress"]:
				self.updateAddress(zone2Dev, valuesDict["devicePortFieldId_uiAddress"])
			
		if zone3Dev == 0 and zone3Enabled:
			self.logger.debug("Creating zone3 device")
			zone3Dev = indigo.device.create(indigo.kProtocol.Plugin, deviceTypeId="zone3")
			zone3Dev.model = "Anthem AVM Processor"
			zone3Dev.subModel = "Zone 3"
			localPropsCopy = zone3Dev.pluginProps
			localPropsCopy.update({"devicePortFieldId_uiAddress" : valuesDict["devicePortFieldId_uiAddress"],
					 "mainDevId" : mainDev.id})
			zone3Dev.replacePluginPropsOnServer(localPropsCopy)
			zone3Dev.replaceOnServer()
		elif zone3Dev != 0:
			if not zone3Enabled:
				self.logger.debug("Destroying zone3 device")
				indigo.device.delete(zone3Dev)
				zone3Dev = 0
			elif zone3Dev.address != valuesDict["devicePortFieldId_uiAddress"]:
				self.updateAddress(zone3Dev, valuesDict["devicePortFieldId_uiAddress"])

		return
	########################################
	def getDayString(self, i):
		dayStrings = ["NUL", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
		if i.startswith("STD"):
			day = int(i[3])
			
		return dayStrings[day]

	########################################
	def _queryDevice(self, valuesDict, devIdList):
		self.logger.info("_queryDevice() enter")
		mainDev = None
		timeString = ""
		dayString = ""
		for devId in devIdList:
			dev = indigo.devices[devId]
			if dev.deviceTypeId == "main":
				mainDev = dev

		if mainDev == None:
			self.logger.error("Main device not found in _queryDevice")

		errorsDict = indigo.Dict()
		self.validateSerialPortUi(valuesDict, errorsDict, u"devicePortFieldId")
		if len(errorsDict) > 0:
			# Some UI fields are not valid, return corrected fields and error messages (client
			# will not let the dialog window close).
			valuesDict["queryError"] = "Error parsing serial port"
			return valuesDict
			
		if self.tempSerial is not None:
			self.logger.error("Internal error: another device configuration is already in progress?")

		# !! TODO !!  Figure out if the port is already open 

		#we need to figure out the serial type to find the port path
		portType = valuesDict.get(u"devicePortFieldId_serialConnType", u"")
		portName = valuesDict.get(u"devicePortFieldId_serialPortLocal", u"")
		if portType == "netRfc2217":
			portName = valuesDict.get(u"devicePortFieldId_serialPortNetRfc2217", u"")
		elif portType == "netSocket":
			portName = valuesDict.get(u"devicePortFieldId_serialPortNetSocket", u"")
		self.logger.info(u"opening serial port "+portName)
		self.tempSerial = self.openSerial(dev.name, portName, 115200, timeout=self.defaultSerialTimeout)
		if self.tempSerial is not None:
			valuesDict["queryError"] = ""
			self.tempSerial.flushInput() # abundance of caution
			self.tempSerial.flushOutput() # abundance of caution
			self.tempSerial.write("P1P?;?;STC?;STD?;STF?;")
			junk = ""
			time.sleep(0.2)
			while self.tempSerial.in_waiting:
				junk += self.tempSerial.read(1)
			if len(junk) > 0:
				responses = junk.split("\n")
				for i in responses:
					self.logger.debug("response: "+i)
					if i.startswith("STC"):
						timestring = i[3:]
					elif i.startswith("STD"):
						daystring = self.getDayString(i)
					elif i.startswith("STF"):
						valuesDict["Time24hr"] = i[3]
					elif i.startswith("AVM"):
						valuesDict["querySuccessful"]=True
						valuesDict["firmwareString"]=i
						#if AVM is greater than 30, enable extended inputs too
				valuesDict["timeString"] = daystring+" "+timestring
			else:
				self.logger.debug("No characters waiting")
		else:
			valuesDict["queryError"] = "Unable to connect to processor"

		self.logger.debug(valuesDict)
		return valuesDict

	########################################
	def _syncTime(self, valuesDict, devIdList):
		self.logger.info("_syncTime() enter")
		#python days 0=Monday; AVM days 1=Sunday
		dayCommands = ["STD2;", #monday
					   "STD3;", #tuesday
					   "STD4;", #wednesday
					   "STD5;", #thursday
					   "STD6;", #friday
					   "STD7;", #saturday
					   "STD1;"] #sunday

		if self.tempSerial is None:
			valuesDict["queryError"] = "Must connect to device before time sync"
			return

		dayCommand = dayCommands[datetime.today().weekday()]
		self.logger.info("Sending "+dayCommand)
		self.tempSerial.write(dayCommand)
		timeCommand = "STC"+datetime.now().strftime('%I:%M%p')+";"
		self.logger.debug("Sending "+timeCommand)
		self.tempSerial.write(timeCommand)
		junk = ""
		timestring = ""
		datestring = ""
		self.tempSerial.write("STD?;STC?;")
		time.sleep(0.2)
		while self.tempSerial.in_waiting:
			junk += self.tempSerial.read(1)
		if len(junk) > 0:
			responses = junk.split("\n")
			for i in responses:
				self.logger.debug("response: "+i)
				if i.startswith("STC"):
					timestring = i[3:]
				elif i.startswith("STD"):
					daystring = self.getDayString(i)

			valuesDict["timeString"] = daystring+" "+timestring
		else:
			self.logger.debug("No characters waiting")

		return valuesDict
	
	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		self.logger.debug(u"validateDeviceConfigUi enter")

		errorsDict = indigo.Dict()

		self.validateSerialPortUi(valuesDict, errorsDict, u"devicePortFieldId")
		if len(errorsDict) > 0:
			# Some UI fields are not valid, return corrected fields and error messages (client
			# will not let the dialog window close).
			return (False, valuesDict, errorsDict)

		# This doesn't feel like the right place to initialize member variables
		# for new devices, but I don't see any obvious alternative
		self.serialLocks[devId] = threading.Lock()
		self.serialConns[devId] = None

		# User choices look good, so return True (client will then close the dialog window).
		return (True, valuesDict)

	########################################
	def validateActionConfigUi(self, valuesDict, typeId, devId):
		self.logger.debug(u"validateActionConfigUi enter")
		errorsDict = indigo.Dict()

		if len(errorsDict) == 0:
			return (True, valuesDict)
		return (False, valuesDict, errorsDict)

	########################################
	def actionControlDimmerRelay(self, action, dev):	
		self.logger.debug(u"actionControlDimmerRelay enter")	
		
		if action.deviceAction == indigo.kDeviceAction.TurnOn: 
			self.powerOn(dev)			 
		
		if action.deviceAction == indigo.kDeviceAction.TurnOff:
			self.powerOff(dev)		
		
		if action.deviceAction == indigo.kDeviceAction.Toggle:
			if dev.onState == True:
				self.powerOff(dev)						
			elif dev.onState == False:
				self.powerOn(dev)		   
			else:			
				self.logger.error('"' + dev.name + '" in inconsistent state')		

	########################################
	#General Action callback
	def actionControlGeneral(self, action, dev):
		self.logger.debug(u"actionControlGeneral enter")	
		###### STATUS REQUEST ######
		if action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
			indigo.server.log(u"sent \"%s\" %s" % (dev.name, "status request"))
			self.serialLocks[dev.id].acquire()
			if self.checkSerial(dev) and self.isPowerOn(dev):
				self.logger.debug(u"Serial is OK and device is ON: querying additional status info")
				dev.updateStateOnServer("onOffState", True)
#				dev.updateStateOnServer("onOffState", False)

			self.serialLocks[dev.id].release()
		else:
			self.logger.info(u"EX-Link devices cannot beep and have no energy counters")

	#######################################
	# Begin Anthem-specific functionality #
	#######################################
    #should these be in a separate object perhaps?
	   
	########################################
	# Protocol constants
	
	mainCommands = {
		"Power" : { "command" : "P1P",
					"values" : { "Off" : "0",
								 "On" : "1"} },
		"Source" : { "command" : "P1S" },
					#values are special for this one
		"Mute" : { "command" : "P1M",
					"values" : {"Off" : "0",
								"On" : "1",
								"Toggle" : "T"} },
	}

	#most commands ack within 500mS but some of the status queries take a long time
	#Use a short timeout for power because the device won't respond at all if it's off
	defaultSerialTimeout = 5
	powerSerialTimeout = 0.5

	########################################
	# Communication utility functions

	######################
	def checkSerial(self, dev):
		id = dev.pluginProps.get("mainDevId", dev.id)
			
		if self.serialConns[id] is not None:
			junk = []
			while self.serialConns[id].in_waiting:
				junk += self.serialConns[id].read(1)
			if len(junk) > 0:
				length = str(len(junk))
				self.logger.warn(u"Received "+length+" unexpected bytes: "+binascii.hexlify(bytearray(junk)))
			return True

		#we need to figure out the serial type to find the port path
		workingDev = indigo.devices[id]
		portType = workingDev.pluginProps.get(u"devicePortFieldId_serialConnType", u"")
		portName = workingDev.pluginProps.get(u"devicePortFieldId_serialPortLocal", u"")
		if portType == "netRfc2217":
			portName = workingDev.pluginProps.get(u"devicePortFieldId_serialPortNetRfc2217", u"")
		elif portType == "netSocket":
			portName = workingDev.pluginProps.get(u"devicePortFieldId_serialPortNetSocket", u"")
		self.logger.info(u"opening serial port "+portName)
		self.serialConns[id] = self.openSerial(dev.name, portName, 115200,
			timeout=self.defaultSerialTimeout)
		if self.serialConns[id] is None:
			self.logger.error(u"unable to open serial port")
			return False
		else:
			self.serialConns[id].flushInput() # abundance of caution
			self.serialConns[id].flushOutput() # abundance of caution

		return True

	########################################
	def waitForAck(self, dev):
		if self.serialConns[dev.id] is not None:
			reply = []
			reply += self.serialConns[dev.id].read(3)
			self.logger.debug(u"Command ack received: "+reply)
			return True
		self.logger.warn(u"Command not acknowledged by device")
		return False

	########################################
	def sendQuery(self, dev, query):
		return []

	########################################
	# Device state inquiries/updaters
	# Many of these are quite similar; perhaps they should be refactored

	########################################
	def isPowerOn(self, dev):
		return True;


	########################################
	# Device commands : two-way synchronized

	########################################
	def powerOff(self, dev):
		self.serialLocks[dev.id].acquire()
		if self.checkSerial(dev):
			if self.sendEnumCommand(dev, "PowerOff"):
				dev.updateStateOnServer("onOffState", False)
		self.serialLocks[dev.id].release()
			
	########################################
	def powerOn(self, dev):
		self.serialLocks[dev.id].acquire()
		if self.checkSerial(dev):
			if self.sendEnumCommand(dev, "PowerOn"):
				dev.updateStateOnServer("onOffState", True)
		self.serialLocks[dev.id].release()
	
	########################################
	def doNothingMethod(self, valuesDict, typeId="", devId=None):
		# This method doesn't do anything itself, but its existence
		# forces the commandGenerator method below to get called.
		#self.logger.debug("doNothingMethod called")
		return

	########################################
	def commandGenerator(self, filter="", valuesDict=None, typeId="", devId=None):
		self.debugLog("dynamicMenuGenerator called")
		self.logger.debug(valuesDict)
		group = valuesDict.get("CommandGroup", "")
		returnList = []

		if group == "":
			return returnList

		self.logger.debug("Looking up values for "+group)
		for command in self.enumCommands:
			if command.startswith(group):
				returnList.extend([(command, self.enumCommands[command]["name"])])
				
		return returnList
