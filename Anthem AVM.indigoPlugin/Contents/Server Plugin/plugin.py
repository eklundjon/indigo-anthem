#! /usr/bin/env python

import indigo
import serial
import threading
import os
import time
import AvmCommands
from datetime import datetime
from threading import Thread

################################################################################
class Plugin(indigo.PluginBase):
	#####################################
	# Begin Indigo plugin API functions #
	#####################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = pluginPrefs.get("DebugFlag", False)
		
		self.serialLocks = {}	#do we still need these?
		self.serialConns = {}	#pySerial connection handles for active devices
		self.serialThreads = {} #RX thread handles
		self.exitFlags = {}		#thread exit flags

		self.tempSerial = None	#pySerial handle for factory UI

		#TODO serial init only for main devices
		for dev in indigo.devices.iter("self"):
#			if dev.deviceTypeId == "main":
			self.logger.info("Found "+dev.deviceTypeId)
			self.serialLocks[dev.id] = threading.Lock()
			self.exitFlags[dev.id] = False

	########################################
	def __del__(self):
		indigo.PluginBase.__del__(self)

	########################################
	def startup(self):
		self.logger.debug(u"startup called")

	########################################
	def shutdown(self):
		self.logger.debug(u"shutdown called")
		
	########################################
	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		self.logger.debug(u"closedPrefsConfigUi enter")
		if userCancelled:
			return

		self.debug = valuesDict.get("DebugFlag", False)
		if self.debug:
			self.logger.info("Debug logging enabled")
		else:
			self.logger.info("Debug logging disabled")

	########################################
	def processResponse(self, dev, buf):
		self.logger.debug("processResponse() enter")
		response = AvmCommands.parseResponse(buf)
		if response is not None:
			self.logger.debug("parsed response: key is "+response.get("key")+"; data is "+response.get("value"))
			dev.updateStateOnServer(response.get("key"), response.get("value"))
			return

		self.logger.warn(dev.name+": No match found for response \""+buf+"\"")

	########################################
	def commThread(self, dev):
		self.logger.info(dev.name+": Comm thread starting")
		while self.serialConns.get(dev.id) is not None:
			if self.exitFlags[dev.id]:
				self.logger.info(dev.name+": Comm thread exiting as requested")
				return

			buf = ""
			buf = self.serialConns[dev.id].readline()
			if len(buf) > 0:
				buf = buf.rstrip()
#				self.logger.debug(dev.name+": Comm thread received "+buf)
				self.processResponse(dev, buf)

		self.logger.warn(dev.name+": Comm thread exited for some unknown reason")

	########################################
	def getSerialPortUrl(self, arguments):
		#we need to figure out the serial type to find the port path
		portType = arguments.get(u"devicePortFieldId_serialConnType", u"")
		portName = arguments.get(u"devicePortFieldId_serialPortLocal", u"")
		if portType == "netRfc2217":
			portName = arguments.get(u"devicePortFieldId_serialPortNetRfc2217", u"")
		elif portType == "netSocket":
			portName = arguments.get(u"devicePortFieldId_serialPortNetSocket", u"")

		return portName

	########################################
	def deviceStartComm(self, dev, blockIfBusy=True):
		self.logger.debug(dev.name+": deviceStartComm() enter")
		#TODO remove this before release
		dev.stateListOrDisplayStateIdChanged()
		portName = self.getSerialPortUrl(dev.pluginProps)
		self.logger.info(dev.name+": opening serial port "+portName)
		self.serialConns[dev.id] = self.openSerial(dev.name, portName, 115200,
			timeout=self.defaultSerialTimeout)
		if self.serialConns[dev.id] is None:
			self.logger.error(dev.name+": unable to open serial port")
			return False
		else:
			self.serialConns[dev.id].flushInput() # abundance of caution
			self.serialConns[dev.id].flushOutput() # abundance of caution
			self.serialThreads[dev.id] = Thread(target=self.commThread, args=(dev,))
			self.serialThreads[dev.id].start()

		return

	########################################
	def deviceStopComm(self, dev, blockIfBusy=True):
		self.logger.info(dev.name+": deviceStopComm() enter for main device")
		self.exitFlags[dev.id] = True
		try:
			self.serialThreads[dev.id].join()
			self.serialConns[dev.id].close()
		except:
			pass
		self.exitFlags[dev.id] = False
		self.serialConns[dev.id] = None
		self.serialThreads[dev.id] = None

	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		self.logger.debug(u"validateDeviceConfigUi enter")

		errorsDict = indigo.Dict()
		
		#TODO only validate serialPortUi for main device

		self.validateSerialPortUi(valuesDict, errorsDict, u"devicePortFieldId")
		if len(errorsDict) > 0:
			# Some UI fields are not valid, return corrected fields and error messages (client
			# will not let the dialog window close).
			return (False, valuesDict, errorsDict)

		# User choices look good, so return True (client will then close the dialog window).
		return (True, valuesDict)

	########################################
	def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
		self.logger.debug(u"closedDeviceConfigUi enter")
		if userCancelled:
			return

		if self.tempSerial is not None:
			self.logger.info("Closing temporary serial handle")
			self.tempSerial = None

		if userCancelled:
			self.logger.info("Device Config UI Cancelled")
			return

		#TODO only create serial lock for main device

		#now that we're sure the device is actually being created,
		#we can finish variable initialization
		if self.serialLocks.get(devId) is None:
			self.serialLocks[devId] = threading.Lock()

	########################################
	def getDayString(self, i):
		dayStrings = ["NUL", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
		if i.startswith("STD"):
			day = int(i[3])
			
		return dayStrings[day]

	########################################
	def _queryDevice(self, valuesDict=None, typeId="", devId=None):
		self.logger.info("_queryDevice() enter")
		mainDev = None
		timeString = ""
		dayString = ""

		#When we support other subdevices, finding the main is more complicated
		mainDev = indigo.devices.get(devId)

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

		# !! TODO !!  Figure out if the port is already open... is easy
		# how the hell do we intercept the responses if there's a RX thread running?

		portName = self.getSerialPortUrl(valuesDict)
		self.logger.info(u"opening serial port "+portName)
		self.tempSerial = self.openSerial(mainDev.name, portName, 115200, timeout=self.defaultSerialTimeout)
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
						valuesDict["Time24hr"] = i[3] #0 or 1
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
	def _syncTime(self, valuesDict, typeId="", devId=None):
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
		timeFormat = '%I:%M%p' #12-hr AM/PM #TODO make sure AM/PM are always AM/PM
		if valuesDict.get("Time24hr", 0) == 1:
			timeFormat ='%H:%M' #24-hr
		timeCommand = "STC"+datetime.now().strftime(timeFormat)+";"
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

		# User choices look good, so return True (client will then close the dialog window).
		return (True, valuesDict)

	########################################
	def validateActionConfigUi(self, valuesDict, typeId, devId):
		self.logger.debug(u"validateActionConfigUi enter")
		errorsDict = AvmCommands.validateCommand(valuesDict)

		if len(errorsDict) == 0:
			return (True, valuesDict)
		return (False, valuesDict, errorsDict)

	########################################
	def actionControlDevice(self, action, dev): 
		self.logger.debug(dev.name+": actionControlDevice() enter") 
		
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
	def actionControlUniversal(self, action, dev):
		self.logger.debug(dev.name+": actionControlUniversal() enter")	
		###### STATUS REQUEST ######
		if action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
			self.logger.debug(dev.name+": sent status request")
			self.serialLocks[dev.id].acquire()
			if self.checkSerial(dev):
				self.logger.debug(dev.name+": Serial is OK and device is ON: querying additional status info")
				self.serialConns[dev.id].write("P1P?;P1S?;P4S?;P1VM?;P1VF?;P1VC?;P1VR?;P1VB?;P1VS?;P1VL?;")
				self.serialConns[dev.id].write("P1LM?;P1LF?;P1LR?;P1LB?;P1BM?;P1BC?;P1BF?;P1BR?;P1BB?;")
				self.serialConns[dev.id].write("P1TM?;P1TC?;P1TF?;P1TR?;P1TB?;P1TE?;")
			self.serialLocks[dev.id].release()
		else:
			self.logger.info(u"AVM devices cannot beep and have no energy counters")

	#######################################
	# Begin Anthem-specific functionality #
	#######################################
	#should these be in a separate object perhaps?
	   
	########################################
	# Protocol constants
	

	#most commands ack within 500mS but some of the status queries take a long time
	#Use a short timeout for power because the device won't respond at all if it's off
	defaultSerialTimeout = 0.5

	########################################
	# Communication utility functions

	######################
	def checkSerial(self, dev):
		# When we support more devices, need to check the main dev ID here
		id = dev.id
			
		if self.serialConns.get(id) is not None:
			junk = []
			while self.serialConns[id].in_waiting:
				junk += self.serialConns[id].read(1)
			if len(junk) > 0:
				length = str(len(junk))
				self.logger.warn(dev.name+": Received "+length+" unexpected bytes: "+binascii.hexlify(bytearray(junk)))
			return True

		#we need to figure out the serial type to find the port path
		workingDev = indigo.devices[id]
		portType = workingDev.pluginProps.get(u"devicePortFieldId_serialConnType", u"")
		portName = workingDev.pluginProps.get(u"devicePortFieldId_serialPortLocal", u"")
		if portType == "netRfc2217":
			portName = workingDev.pluginProps.get(u"devicePortFieldId_serialPortNetRfc2217", u"")
		elif portType == "netSocket":
			portName = workingDev.pluginProps.get(u"devicePortFieldId_serialPortNetSocket", u"")
		self.logger.info(dev.name+": opening serial port "+portName)
		self.serialConns[id] = self.openSerial(dev.name, portName, 115200,
			timeout=self.defaultSerialTimeout)
		if self.serialConns[id] is None:
			self.logger.error(dev.name+": unable to open serial port")
			return False
		else:
			self.serialConns[id].flushInput() # abundance of caution
			self.serialConns[id].flushOutput() # abundance of caution

		return True

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
			self.sendCommand("onOffState", "Off")
		self.serialLocks[dev.id].release()
			
	########################################
	def powerOn(self, dev):
		self.serialLocks[dev.id].acquire()
		if self.checkSerial(dev):
			self.sendCommand("onOffState", "On")
		self.serialLocks[dev.id].release()
	
	########################################
	def doNothingMethod(self, valuesDict, typeId="", devId=None):
		# This method doesn't do anything itself, but its existence
		# forces the commandGenerator method below to get called.
		#self.logger.debug("doNothingMethod called")
		return

	########################################
	def updateMainCommandValues(self, valuesDict, typeId="", devId=None):
		command = valuesDict.get("command")
		if command is None:
			indigo.server.log("AvmCommands.getValueDetails() no command to get details for")
			return valuesDict

		valuesDict["showPicker"] = False
		valuesDict["showEntry"] = False 
		valuesDict["textDescription"] = ""
		valuesDict["textValue"] = ""

		valuesDict["textDescription"] = AvmCommands.getStringDescription(command)
		if valuesDict["textDescription"] is not None:
			self.logger.debug("AvmCommands populating string details for "+command)
			valuesDict["showEntry"] = True
			valuesDict["textValue"] = AvmCommands.getStringDefault(command)
		elif AvmCommands.hasValues(command):
			self.logger.debug("AvmCommands found a value list for "+command)
			valuesDict["showPicker"] = True
		else:
			self.logger.debug("AvmCommands no details for "+command)
	
		return valuesDict

	########################################
	def commandGenerator(self, filter="", valuesDict=None, typeId="", devId=None):
		self.debugLog("commandGenerator called")
		self.logger.debug(valuesDict)

		return AvmCommands.getCommands()

	########################################
	def valueGenerator(self, filter="", valuesDict=None, typeId="", devId=None):
		self.debugLog("valueGenerator called")
		self.logger.debug(valuesDict)

		return AvmCommands.getValueList(valuesDict)
		
