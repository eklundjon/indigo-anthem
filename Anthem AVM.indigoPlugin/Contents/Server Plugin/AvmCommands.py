#! /usr/bin/env python

import re
import indigo

# dictionary key
# "IndigoDeviceVariableName" : { "command" : "base command to send AVM",
#								 "arg" : "regex to satisfy first argument where applicable",
#								 "input" : True when command has an input before the argument,
#	  for enum commands:	   "values" : { "Indigo UI name of first option" : "AVM representation of first option",
#											"Indigo UI name of nth option" : "AVM representation of nth option"}
#	  for numeric commands:		 "min" : minimum value of numerical options,
#	  for numeric commands:		 "max" : maximum value of numerical options}
#TODO: how to handle arbitrary string commands?	 Is the regex  enough?
#
_DefaultInputMap = {
	"CD" : "0",
	"2-Ch BAL" : "1",
	"6-Ch SE" : "2",
	"Tape" : "3",
	"Tuner" : "4",
	"DVD1" : "5",
	"TV1" : "6",
	"SAT1" : "7",
	"VCR" : "8",
	"AUX" : "9",
	"current" : "c",
#note following sources not available in "older versions"
#TODO determine minimum version
	"DVD2" : "d",
	"DVD3" : "e",
	"DVD4" : "f",
	"TV2" : "g",
	"TV3" : "h",
	"TV4" : "i",
	"SAT2" : "j"
}

_mainCommands = {
	"onOffState" : { "command" : "P1P",
				"arg1" : "[01]",
				"values" : { "Off" : "0",
							 "On" : "1" } },
	"Source" : { "command" : "P1S",
				"uiName" : "Select Source",
				"arg1" : "[0-9c-j]",
				"values" : { "CD" : "0",
							"2-Ch BAL" : "1",
							"6-Ch SE" : "2",
							"Tape" : "3",
							"Tuner" : "4",
							"DVD1" : "5",
							"TV1" : "6",
							"SAT1" : "7",
							"VCR" : "8",
							"AUX" : "9",
							"current" : "c",
						#note following sources not available in "older versions"
						#TODO determine minimum version
							"DVD2" : "d",
							"DVD3" : "e",
							"DVD4" : "f",
							"TV2" : "g",
							"TV3" : "h",
							"TV4" : "i",
							"SAT2" : "j" } },
#	"SourceSimulcast" : { "command" : "P1X",
#				"arg1" : "input" ,
#				"arg2" : "input" },
	"RecSource" : { "command" : "P4S",
				"uiName" : "Recording Source",
				"arg1" : "input" },
#	"RecSourceSimulcast" : { "command" : "P4X",
#				"arg1" : "input" ,
#				"arg2" : "input" },
	"Mute" : { "command" : "P1M",
				"uiName" : "Mute",
				"arg1" : "[01]",
				"values" : {"Off" : "0",
							"On" : "1",
							"Toggle" : "T"} },
	"HeadphoneMute" : { "command" : "HM",
				"uiName" : "Headphone Mute",
				"arg1" : "[01]",
				"values" : {"Off" : "0",
							"On" : "1",
							"Toggle" : "T"} },
	"MasterVolume" : { "command" : "P1VM",
				"uiName" : "Set Master Volume",
				"uiDescription" : "-95.5 to 31.5 in increments of 0.5",
				"arg1" : "[+-]\d+.[05]",
			"min" : -95.5,
			"max" : 31.5},
	"MasterVolumeUp" : { "command" : "P1VMU",
				"uiName" : "Master Volume Up",
				"arg1" : "[+-]\d+.[05]",
			"min" : 0.5,
			"max" : 5},
	"MasterVolumeDown" : { "command" : "P1VMD",
				"uiName" : "Master Volume Down",
				"arg1" : "[+-]\d+.[05]",
			"min" : 0.5,
			"max" : 5},
	"HeadphoneVolume" : { "command" : "HV",
				"uiName" : "Set Headphone Volume",
				"arg1" : "[+-]\d+.[05]",
			"min" : -62.5,
			"max" : 10},
	"MaxVolume" : { "command" : "SV1M",
				"arg1" : "[+-]\d+.[05]",
			"min" : -95.5,
			"max" : 31.5},
	"PowerOnVolume" : { "command" : "SV1O",
				"arg1" : "[+-]\d+.[05]",
			"min" : -95.5,
			"max" : 31.5},
	"VolumeFront" : { "command" : "P1VF",
				"uiName" : "Set Front Volume",
				"arg1" : "[+-]\d+.[05]",
			"min" : -10,
			"max" : 10},
	"VolumeCenter" : { "command" : "P1VC",
				"uiName" : "Set Center Volume",
				"arg1" : "[+-]\d+.[05]",
			"min" : -10,
			"max" : 10},
	"VolumeSurround" : { "command" : "P1VR",
				"arg1" : "[+-]\d+.[05]",
			"min" : -10,
			"max" : 10},
	"VolumeBack" : { "command" : "P1VB",
				"arg1" : "[+-]\d+.[05]",
			"min" : -10,
			"max" : 10},
	"VolumeSub" : { "command" : "P1VS",
				"arg1" : "[+-]\d+.[05]",
			"min" : -30,
			"max" : 20},
	"VolumeLFE" : { "command" : "P1VL",
				"arg1" : "[+-]\d+.[05]",
			"min" : -10,
			"max" : 0},
	"MasterBalance" : { "command" : "P1LM",
				"arg1" : "[+-]\d+.[05]",
			"min" : -10,
			"max" : 10},
	"HeadphoneBalance" : { "command" : "HB",
				"arg1" : "[+-]\d+.[05]",
			"min" : -12.5,
			"max" : 12.5},
	"BalanceFront" : { "command" : "P1LF",
				"arg1" : "[+-]\d+.[05]",
			"min" : -10,
			"max" : 10},
	"BalanceSurround" : { "command" : "P1LR",
				"arg1" : "[+-]\d+.[05]",
			"min" : -10,
			"max" : 10},
	"BalanceBack" : { "command" : "P1LB",
				"arg1" : "[+-]\d+.[05]",
			"min" : -10,
			"max" : 10},
	"MasterBass" : { "command" : "P1BM",
				"arg1" : "[+-]\d+.[05]",
			"min" : -12,
			"max" : 12},
	"HeadphoneBass" : { "command" : "HB",
				"arg1" : "[+-]\d+.[05]",
			"min" : -14,
			"max" : 14},
	"BassFront" : { "command" : "P1BF",
				"arg1" : "[+-]\d+.[05]",
			"min" : -12,
			"max" : 12},
	"BassCenter" : { "command" : "P1BC",
				"arg1" : "[+-]\d+.[05]",
			"min" : -12,
			"max" : 12},
	"BassSurround" : { "command" : "P1BR",
				"arg1" : "[+-]\d+.[05]",
			"min" : -12,
			"max" : 12},
	"BassRear" : { "command" : "P1BB",
				"arg1" : "[+-]\d+.[05]",
			"min" : -12,
			"max" : 12},
	"MainTreble" : { "command" : "P1TM",
				"arg1" : "[+-]\d+.[05]",
			"min" : -12,
			"max" : 12},
	"HeadphoneTreble" : { "command" : "HT",
				"arg1" : "[+-]\d+.[05]",
			"min" : -14,
			"max" : 14},
	"TrebleFront" : { "command" : "P1TF",
				"arg1" : "[+-]\d+.[05]",
			"min" : -12,
			"max" : 12},
	"TrebleCenter" : { "command" : "P1TC",
				"arg1" : "[+-]\d+.[05]",
			"min" : -12,
			"max" : 12},
	"TrebleSurround" : { "command" : "P1TR",
				"arg1" : "[+-]\d+.[05]",
			"min" : -12,
			"max" : 12},
	"TrebleRear" : { "command" : "P1TB",
				"arg1" : "[+-]\d+.[05]",
			"min" : -12,
			"max" : 12},
	#Yes, these are backwards.	the command is "tone enable" but
	#I think that's confusing.	Invert the logic when reporting to Indigo.
	"ToneBypass" : { "command" : "P1TE",
				"arg1" : "[01]",
		   "values" : {"On" : "0",
						"Off" : "1"} },						
	"Compression" : { "command" : "P1C",
				"uiName" : "Dynamic Compression",
				"arg1" : "[0-2]",
		   "values" : {"Normal" : "0",
						"Reduced" : "1",
						"Night" : "2"} },
		"DisplayStatus" : { "command" : "P1s",
				"uiName" : "Show status on main display"},
	"SourceSeek" : { "command" : "P1SS",
		   "values" : {"Next" : "+",
						"Prev" : "-"} },
	"SleepTimer" : { "command" : "P1Z",
				"uiName" : "Set Sleep Timer",
				"arg1" : "[0-3]",
		   "values" : {"Off" : "0",
						"Thirty Minutes" : "1",
						"Sixty Minutes" : "2",
						"Ninety Minutes" : "3"} },
	"DisplayMessage1" : { "command" : "P1z1",
		   "arg1" : "\w+"},
	"DisplayMessage2" : { "command" : "P1z2",
		   "arg1" : "\w+"},
	"DecoderStatus" : { "command" : "P1D", #query/response only
				"arg1" : "input",
				"arg2" : "[0-9]",
				"values" : {"Stereo" : "0",
						"Dolby Digital" : "1",
						"DTS" : "2",
						"MPEG" : "3",
						"6-ch" : "4",
						"2-ch analog direct" : "5",
						"No Signal" : "6",
						"Dolby Digital Plus" : "7",
						"Dolby TrueHD" : "8",
						"DTS-HD" : "9"} },
	"DecoderFlagStatus" : { "command" : "P1DF", #query/response only
				"arg1" : "input",
				"arg2" : "[0-9A]",
				"values" : {"No Signal" : "0",
						"Mono" : "1",
						"2Ch Unflagged" : "2",
						"2Ch Flagged" : "3",
						"6Ch Unflagged Dolby" : "4",
						"Dolby Digital 5.1 EX" : "5",
						"6Ch Unflagged DTS" : "6",
						"DTS EX Matrix" : "7",
						"DTS EX Discrete" : "8",
						"6Ch Analog or PCM" : "9",
						"8 Channel" : "A"} },
	"SourceType" : { "command" : "P1DS", #query/response only
				"arg1" : "input",
				"arg2" : "[0-9a-e]",
				"values" : {"Digital" : "0",
						"DTS 24/96" : "1",
						"Analog DSP" : "2",
						"Analog Direct" : "3",
						"Auto Digital" : "4",
						"DTS-HD Low Bit Rate" : "5",
						"DTS-HD Master Audio" : "6",
						"DTS-ES Discrete" : "7",
						"DTS-HD Matrix" : "8",
						"PCM" : "9",
						"Dolby Digital" : "a",
						"DTS Digital Surround" : "b",
						"Dolby Digital Plus" : "c",
						"Dolby TrueHD" : "d",
						"DTS-HD High Resolution" : "e"} },
	"CurrentProcessingModeText" : { "command" : "P1Q", #query/response only
				"arg1" : "\w+"}, #arbitrary ASCII string
	"AC3Status" : { "command" : "P1A", #query/response only
				"arg1" : "input",
				"arg2" : "[0-2]",
				"values" : {"Not AC3" : "0",
						"AC3 2-Channel" : "1",
						"AC3 Multichannel" : "2"} },
	"AC3DialogNormalization" : { "command" : "P1AD", #query/response only
				"arg1" : "input",
				"arg2" : "\d"},
	"StereoInputFx" : { "command" : "P1E",
				"uiName" : "Stereo Effects",
				"arg1" : "input",
				"arg2" : "[0-9A-D]",
		   "values" : {"off" : "0",
						"AnthemLogic Music" : "1",
						"AnthemLogic Cinema" : "2",
						"ProLogic IIx Music" : "3",
						"ProLogic IIx Movie" : "4",
						"ProLogic" : "5",
						"Neo:6 Music" : "6",
						"Neo:6 Cinema" : "7",
						"All-Channel Stereo" : "8",
						"All-Channel Mono" : "9",
						"Mono" : "A",
						"Mono Academy" : "B",
						"ProLogic IIx Matrix" : "C",
						"ProLogic IIx Game" : "D"} },
	"DolbyStereoFx" : { "command" : "P1EF",
				"uiName" : "Dolby Digital 2.0 Effects",
				"arg1" : "input",
				"arg2" : "[0-9A-D]",
		   "values" : {"off" : "0",
						"AnthemLogic Music" : "1",
						"AnthemLogic Cinema" : "2",
						"ProLogic IIx Music" : "3",
						"ProLogic IIx Movie" : "4",
						"ProLogic" : "5",
						"Neo:6 Music" : "6",
						"Neo:6 Cinema" : "7",
						"All-Channel Stereo" : "8",
						"All-Channel Mono" : "9",
						"Mono" : "A",
						"Mono Academy" : "B",
						"ProLogic IIx Matrix" : "C",
						"ProLogic IIx Game" : "D"} },
	"DolbyExFx" : { "command" : "P1EE",
				"uiName" : "Dolby Digital EX Effects",
				"arg1" : "input",
				"arg2" : "[0-7]",
		   "values" : {"Off" : "0",
						"Dolby Digital EX" : "1",
						"THX Surround EX" : "2",
						"ProLogic IIx Movie" : "3",
						"ProLogic IIx Movie THX" : "4",
						"ProLogic IIx Music" : "5",
						"Neo:6" : "6",
						"Neo:6 THX" : "7"} },
	"DtsMatrixFx" : { "command" : "P1ES",
				"uiName" : "DTS Matrix Effects",
				"arg1" : "input",
				"arg2" : "[0-6]",
			#Yes this really has 5 different off values
		   "values" : {"Off" : "0",
						"Off" : "1",
						"THX Cinema" : "2",
						"Off" : "3",
						"THX Cinema" : "4",
						"Off" : "5",
						"Off" : "6"} },
	"DolbyStereoTHX" : { "command" : "P1EU",
				"uiName" : "Dolby Stereo THX",
				"arg1" : "input",
				"arg2" : "[0-2]",
		   "values" : {"Off" : "0",
						"THX Cinema" : "1",
						"THX Games" : "2"} },
	"StereoInputTHX" : { "command" : "P1ET",
				"uiName" : "Stereo Input THX",
				"arg1" : "input",
				"arg2" : "[0-2]",
		   "values" : {"Off" : "0",
						"THX Cinema" : "1",
						"THX Game" : "2"} },
	"SevenOneInputTHX" : { "command" : "P1EW",
				"uiName" : "7.1 Input THX",
				"arg1" : "input",
				"arg2" : "[0-1]",
		   "values" : {"Off" : "0",
						"THX Cinema" : "1"} },
	"DolbyDigitalFx" : { "command" : "P1EX",
				"uiName" : "Dolby Digital Input Effects",
				"arg1" : "input",
				"arg2" : "[0-9AB]",
		   "values" : {"Off" : "0",
						"THX Cinema 5.1" : "1",
						"THX Ultra2 Cinema" : "2",
						"THX MusicMode" : "3",
						"THX Surround EX" : "4",
						"THX Games" : "5",
						"PLIIx Movie" : "6",
						"PLIIx Movie THX" : "7",
						"PLIIx Music" : "8",
						"Dolby Digital EX" : "9",
						"Neo:6" : "A",
						"Neo:6 THX" : "B"} },
	"SixZeroInputFx" : { "command" : "P1EY",
				"uiName" : "6.0 Input Effects",
				"arg1" : "input",
				"arg2" : "[0-9AB]",
		   "values" : {"Off" : "0",
						"THX Cinema 5.1" : "1",
						"THX Ultra2 Cinema" : "2",
						"THX MusicMode" : "3",
						"THX Surround EX" : "4",
						"THX Games" : "5",
						"PLIIx Movie" : "6",
						"PLIIx Movie THX" : "7",
						"PLIIx Music" : "8",
						"Dolby Digital EX" : "9",
						"Neo:6" : "A",
						"Neo:6 THX" : "B"} },
	"DtsInputFx" : { "command" : "P1ED",
				"uiName" : "DTS 5.1 Input Effects",
				"arg1" : "input",
				"arg2" : "[0-9A]",
		   "values" : {"Off" : "0",
						"THX Cinema 5.1" : "1",
						"THX Ultra2 Cinema" : "2",
						"THX MusicMode" : "3",
						"Neo:6 THX" : "4",
						"THX Games" : "5",
						"PLIIx Movie" : "6",
						"PLIIx Movie THX" : "7",
						"PLIIx Music" : "8",
						"Dolby Digital EX" : "9",
						"Neo:6" : "A"} },
	"ChangeThxMode" : { "command" : "P1EB",
				"uiName" : "Change THX Mode",
				"arg1" : "[01]",
		   "values" : {"Down" : "0",
						"Up" : "1"} },
	"ChangeAudioMode" : { "command" : "P1EC",
				"uiName" : "Change Audio Mode",
				"arg1" : "[01]",
		   "values" : {"Down" : "0",
						"Up" : ""} },
	"PrologicMusicPanorama" : { "command" : "P1EMP",
				"uiName" : "Dolby Prologic Music Panorama",
				"arg1" : "input",
				"arg2" : "[01]",
		   "values" : {"Off" : "0",
						"On" : "1"} },
	"PrologicMusicWidth" : { "command" : "P1EMC",
				"uiName" : "Dolby Prologic Music Width",
				"arg1" : "input",
				"arg2" : "[0-7]",
			"min" : 0,
			"max" : 7},
	"PrologicMusicDimension" : { "command" : "P1EMD",
				"uiName" : "Dolby Prologic Music Dimension",
				"arg1" : "input",
				"arg2" : "[0-6]",
			"min" : 0,
			"max" : 6},
	"DTSNeo6CenterGain" : { "command" : "P1EMG",
				"uiName" : "DTS Neo:6 Center Gain",
				"arg1" : "input",
				"arg2" : "[0-5]",
			"min" : 0,
			"max" : 5},
	"ThxFrontChannelReEQThx" : { "command" : "P1ER",
				"uiName" : "THX Front Channel Re-EQ (THX On)",
				"arg1" : "input",
				"arg2" : "[01]",
		   "values" : {"Off" : "0",
						"On" : "1"} },
	"ThxFrontChannelReEQNonThx" : { "command" : "P1EN",
				"uiName" : "THX Front Channel Re-EQ (THX Off)",
				"arg1" : "input",
				"arg2" : "[01]",
		   "values" : {"Off" : "0",
						"On" : "1"} }
}

########################################
#return list of known commands
def getCommands():
	returnList = []
	for key in _mainCommands:
		if _mainCommands[key].get("uiName") is not None:
			returnList.extend([(key, _mainCommands[key].get("uiName"))])
	return returnList

########################################
#return UI description text for a non-enumerated command, otherwise None
def getStringDescription(command):
	try:
		return _mainCommands[command].get("uiDescription")
	except:
		indigo.server.log("AvmCommands Can't find command "+str(command));

########################################
#return default value for a non-enumerated command (if applicable), otherwise None
def getStringDefault(command):
	try:
		return _mainCommands[command].get("uiDefault")
	except:
		indigo.server.log("AvmCommands Can't find command "+str(command));

########################################
#return true if command has enumerated values
def hasValues(command):
	try:
		return (_mainCommands[command].get("values") is not None)
	except:
		indigo.server.log("AvmCommands Can't find command "+str(command));

########################################
#return enumeration list for command 
#TODO clean this up to move valuesDict to plugin.py
def getValueList(valuesDict):
	returnList = []
	command = valuesDict.get("command")

	try:
		if _mainCommands[command].get("values") is not None:
			indigo.server.log("AvmCommands.getValueList() populating list details for "+command)
			for key in _mainCommands[command]["values"]:
				returnList.extend([(_mainCommands[command]["values"][key],key)])
		else:
			indigo.server.log("AvmCommands.getValueDetails() no list for "+command)
	except:
		indigo.server.log("AvmCommands Can't find command "+str(command))
	
	return returnList

########################################
#validate command and values
#TODO refactor to move indigoDicts to plugin.py
def validateCommand(valuesDict):
	errorsDict = indigo.Dict()
#	if args.get("key") is None:
#		indigo.server.log("AvmCommands.validateCommand() no key in command")
#		return False
#
#	if _mainCommands.get("key") is None:
#		indigo.server.log("AvmCommands.validateCommand() key not found in main zone")
#		return False
#
#	if args.get("value") is not None and _mainCommands.get("key").get("arg1") is not None:
#		if re.match(_mainCommands.get("key").get("arg1"), args.get("value")):
#			indigo.server.log("AvmCommands.validateCommand() value \""+args.get("value")+"\" matches key "+args.get("key")
#			return True
#		else:
#			indigo.server.log("AvmCommands.validateCommand() value \""+args.get("value")+"\" not valid for key "+args.get("key")
#			return False
#	elif _mainCommands.get("key").get("arg1") is not None:
#		indigo.server.log("AvmCommands.validateCommand() key "+args.get("key")+" requires a value")
#		return False
#	else:
#		indigo.server.log("AvmCommands.validateCommand() error 1: command value format unknown")
#		return False

	#TODO numerical range validation
	
	indigo.server.log("AvmCommands.validateCommand() OK: no validation performed")
	return errorsDict

########################################
def parseResponse(buf):
	for key in _mainCommands:
		#the first response is going to take an awfully long time to process
		#maybe this should go in a library init function ?
		regex = _mainCommands[key].get("regex")

		if regex is None and _mainCommands[key].get("arg1") is not None:
			response = None
			arg1 = _mainCommands[key].get("arg1")
			if _mainCommands[key].get("arg2") is not None:
			    if arg1 == "input":
			        arg1 = "[0-9c-j]"
				response = "%s(%s)(%s)" % (_mainCommands[key].get("command"),
											arg1,
											_mainCommands[key].get("arg2"))
			else:
				response = "%s(%s)" % (_mainCommands[key].get("command"),
										_mainCommands[key].get("arg1"))
			if response is not None:
				_mainCommands[key]["regex"] = re.compile(response)
				regex = _mainCommands[key]["regex"]
				
		
		if regex is not None:
			m = regex.match(buf)
			if m is not None:
				result = {}
				result["zone"] = "main"
				result["key"] = key
				num_groups = len(m.groups())
				if num_groups > 1:
					result["value"] = m.group(2)
					result["value2"] = m.group(1)
				elif num_groups > 0:
					result["value"] = m.group(1)
				if _mainCommands[key].get("values") is not None:
				    result["value"] = _mainCommands[key]["values"][result["value"]]

				return result
