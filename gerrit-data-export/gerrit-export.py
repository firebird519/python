#!/usr/bin/env python

# pythond version: 2.7.10

import os
import sys,urllib,string,re
import urllib2
import webbrowser
from time import localtime, strftime
global DEBUG

DEBUG = 0

FILENAME_SCRIPT_START_DAYTIME = '.script_starttime.conf'

# KEY name list
SUBJECT_KEY = 'subject'
_NUMBER_KEY = '_number'
OWNER_KEY = 'owner'
NAME_KEY = 'name'
EMAIL_KEY = 'email'
CHANGE_ID_KEY = 'change_id'
UPDATED_KEY = 'updated'


# gerrit server url
URL_COMMIT_PRE = 'http://diana.devops.letv.com/#/c/'

def log(text):
	if DEBUG:
		print text

def exit(tempFileName):
	if DEBUG != 1 and len(tempFileName) > 0:
		try:
			os.remove(tempFileName)
		except OSError, e:
			print 'Temp file:' + tempFileName + ' delete maybe failed. Please remove it manually!'

	saveScriptStartTime()
	print 'End'
	sys.exit(1)



#browserCookie.py is necessary for this import.
try:
	from browserCookie import *
except ImportError, e:
	print e
	print 'Please make sure following py file existed: "browerCookie.py"'
	exit('')

# file handler is returned by this function
def getNetJsonData(url):
	print url
	log('Using firefox cookie to open this url:{!s}'.format(url))
	cj = firefox()
	
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	req = urllib2.Request(url)

	req.add_header('User-Agent', 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:50.0) Gecko/20100101 Firefox/50.0'); 
	req.add_header('Accept', 'application/json');
	req.add_header('Accept-Language', 'aen-US,en;q=0.5');
	req.add_header('Accept-Encoding', 'deflate');
	req.add_header('Content-Type', 'application/json; charset=UTF-8');
	req.add_header('x-content-type-options', 'nosniff');

	fHandler = opener.open(req)

	return fHandler

def parseJsonItem(item, jsonFileHandler):
	# json field format should be "key":value,"key":value
	#',"' is possible for field split
	#TODO: maybe error happened for following case: "key":"xxx,\"xxx\""
	#      add case handling for it in future.
	fieldSplitPattern = re.compile(',"')
	fieldList = fieldSplitPattern.split(item)
	if fieldList:
		itemFieldIndex = 0
		fieldsCount = len(fieldList)
		log('field count:{}'.format(fieldsCount))

		for field in fieldList:
			itemFieldIndex += 1
			if itemFieldIndex == 1:
				field = field + ',\n'
			elif itemFieldIndex == fieldsCount:
				field = '"' + field
			else:
				field = '"' + field + ',\n'

			field = field.replace('}', '\n}')
			field = field.replace('":{', '": {\n')
			field = field + '\n'
			field = field.replace('\n\n','\n')
					
			jsonFileHandler.write(field)


# json item count will be returned by this function
def handleNetJsonLine(line, jsonFileHandler):
	log('line info:{!s}'.format(line[:10]))

	# split all datas by json items. every item is in one line.
	# format like following:[{"xx":"","cc":sdf},{"xx":"","cc":sdf}]
	jsonItemSplitPattern = re.compile('},{')
	itemList = jsonItemSplitPattern.split(line)

	if itemList:
		itemCount = len(itemList)
	else:
		return 0

	# ')]}`' handler special json headers 
	if 1 == itemCount and len(itemList[0]) < 6:
		log('json file header found:{!s}'.format(itemList[0]))
		jsonFileHandler.write(itemList[0])
		return 0
	
	itemIndex = 0
	# handle json items. and now every item is in one line. 
	for item in itemList:
		itemIndex += 1
			
		# Only one json items need to be handled. add line break for header and end charaters
		if itemCount == 1:
			# add line break(\n) for json items header '[{'  and ended charaters '}]'
			if item[:2] == '[{':
				temp = item[:1] + '\n' + item[1:2] + '\n' + item[2:]
				item = temp

			item = item.rstrip('\n')
			if item[-2:] == '}]':
				temp = item[:-2] + '\n' + item[-2:-1] + '\n' + item[-1:] + '\n'
				item = temp
				
			log('only one item found')
		# add characters '},{' back when split for other cases and also add line breaks
		elif itemIndex != 1 and itemIndex != itemCount:
			item = '{\n' + item + '\n},'
		# last item. a little different for others. only '{' is needed and also add line breaks
		elif itemCount == itemIndex:
			item = '{\n' + item
			# remove possible \n in last line.
			item = item.rstrip('\n')
			if item[-2:] == '}]':
				temp = item[:-2] + '\n' + item[-2:-1] + '\n' + item[-1:] + '\n'
				item = temp
				log('format last line:{!s}'.format(item[-5:]))
			else:
				item = item + '\n},'
				if item[:2] == '[{':
					temp = item[:1] + '\n' + item[1:2] + '\n' + item[2:]
					item = temp
					log('format first line:{!s}'.format(item[:5]))
		elif itemIndex == 1:
			item = item + '\n},'
			if item[:2] == '[{':
				temp = item[:1] + '\n' + item[1:2] + '\n' + item[2:]
				item = temp
				log('format first line:{!s}'.format(item[:5]))
		else:
			print 'handleNetJsonLine, impossible case!'

		parseJsonItem(item, jsonFileHandler)

	return itemCount

# format net json data. all json items are in one line after get it from network. 
# we need formatted it to one temp file and parse it
def formatNetJsonData(netDataFileHandler, tempJsonFileName):
	# save formated data to one temporary file result.json
	jsonFileHandler = open(tempJsonFileName,'w')
	
	netDataSavingFileHandler = 0
	if DEBUG == 1:
		netDataSavingFileHandler = open(tempJsonFileName + '.log','w')
	
	json_items_number = 0

	while 1:
		line = netDataFileHandler.readline()
		if len(line) == 0:
			break;

		if netDataSavingFileHandler != 0:
			netDataSavingFileHandler.write(line)

		json_items_number += handleNetJsonLine(line, jsonFileHandler)

	jsonFileHandler.close()

	if netDataSavingFileHandler != 0:
		netDataSavingFileHandler.close()

	log('json items count:{0}'.format(format(json_items_number)))
	return json_items_number


# null returned if key not found.
# currently can not parser , between "" 
def getKeyValue(data, key):
	#print data
	#print key
	keyIndex = data.find(key)
	if keyIndex < 0:
		return ''

	subString = data[keyIndex:]
	log(key + ':' + subString[:20])
	keyValueEndIndex = subString.find(',')
	sepIndex = subString.find(':')
	value = subString[sepIndex + 1: keyValueEndIndex]
	value = value.strip('"')
	value = value.strip()

	log(key + ":" + value)
	return value

def parseDictItem(fileHandler, childDict):
	while 1:
		line = fileHandler.readline()
		if len(line) == 0:
			return childDict

		#print line
		line.expandtabs()
		line.lstrip(' ')

		# end of current json. Just return null.
		if 0 == line.find(']'):
			print 'Error! not possible case'
			return childDict

		sepIndex = line.find(':')
		dictStartIndex = line.find('{')
		dictEndIndex = line.find('}')

		# separate charactor found. there must dict key exited. 
		if sepIndex > 0:
			keySubStr = line[0 : sepIndex - 1]
			keySubStr = keySubStr.expandtabs()
			keySubStr = keySubStr.strip()
			keySubStr = keySubStr.strip('"')
			
			if dictStartIndex >= 0:
				if dictEndIndex > 0:
					# for case that "key" : {}
					childDict[keySubStr] = ''
				else:					
					childrenDict = dict({})
					childrenDict = parseDictItem(fileHandler, childrenDict)
					childDict[keySubStr] = childrenDict
			else:
				ValueSubStr = line[sepIndex + 1 : len(line) - 1]
				ValueSubStr = ValueSubStr.expandtabs()
				ValueSubStr = ValueSubStr.strip()
				ValueSubStr = ValueSubStr.strip('"')
				ValueSubStr = ValueSubStr.strip(',')
				childDict[keySubStr] = ValueSubStr

			continue

		# the end of one dict item. Maybe one child dict or parent dict
		if dictEndIndex >= 0:
			return childDict

		if dictStartIndex >= 0:
			print 'Error! { case should be not possible. current is not in root dict parse state'
			print line
			return childDict

def parseJsonBlock(fileHandler):
	dictList = []
	while 1:
		line = fileHandler.readline()
		if len == 0:
			break

		line = line.strip('\n').strip()

		jsonStartIndex = line.find('[')
		if jsonStartIndex == 0:
			continue
		elif jsonStartIndex > 0:
			print 'this line is not start of one json block. continue?'
			print line
			continue

		if 0 == line.find(']'):
			return dictList
		elif 0 < line.find(']'):
			print 'this line is not end of one json block. continue?'
			print line
			return dictList

		print '.',
		sys.stdout.flush()

		if 0 <= line.find('{'):
			childDict = dict({})
			chidlDict = parseDictItem(fileHandler, childDict)
			dictList.append(childDict)
	#end of parseJsonBlock
	print ' '

def removeUnicodeCharactor(data):
	return data.encode('ascii')

# 1. remove unicode format
# 2. remove not used '"'
# 3. remove space in start and end of the string
# 4. remove ','
def formatString(stringData):
		stringData = stringData.replace('\\"','\u0022')
		stringData = stringData.strip()
		stringData = stringData.strip('"')
		stringData = stringData.replace('\u0022','"')
		stringData = stringData.replace('\u003e','>')
		stringData = stringData.replace('\u0027','\'')
		stringData = stringData.replace(',','')
		return stringData

def itemInList(itemList, item):
	item = string.lower(item.strip('\n').strip())
	for i in itemList:
		i = string.lower(i.strip('\n').strip())
		#print 'i:' + i + '-item:' + item
		if item.find(i) >= 0:
			return 1
	return 0


NAME_LIST_FILE_NAME = 'namelist.txt'
def loadNameList():
	try:
		print '\nLoading name list...\n'
		fileH = open(NAME_LIST_FILE_NAME, 'r')
		lines = fileH.readlines()
		fileH.close()
	except IOError, e:
		lines = []

	return lines

def writeDataToExcel(dictList, fileName, filterByNameOrMailList):
	print 'saving data to file:' + fileName
	filterList = []
	if filterByNameOrMailList == '1':
		#load name or mail list
		filterList = loadNameList()

	excelFileHandler = open(fileName, 'w')
	excelFileHandler.write('PID,Title,Link,Change-Id,Updated,owner,Comments\n')

	resultCount = 0

	for item in dictList:
		#print item
		print '.',
		sys.stdout.flush()
		subject = item[SUBJECT_KEY]
		subject = formatString(subject)
		gerritNumber = item[_NUMBER_KEY]
		change_id = item[CHANGE_ID_KEY]
                change_id = change_id.strip()
                if change_id[-1:] == '"':
		        change_id = change_id[:-1]
		updated = item[UPDATED_KEY]
		updated = updated.strip()
		updated = updated[:19]
		
		ownerName = ''
		ownerEmail = ''
		isInList = 0

		try:
			#print 'owner info:',
			ownerInfo = item[OWNER_KEY]
			#print ownerInfo

			ownerName = ownerInfo[NAME_KEY]
			ownerEmail = ownerInfo[EMAIL_KEY]
		except KeyError, e:
			print 'No owner info found for gerrit number:' + gerritNumber

		if len(filterList) > 0:
			try:
				isInList = itemInList(filterList, ownerName)
				
				log('filter by name result:{0}'.format(isInList))
				if isInList != 1:
					isInList = itemInList(filterList, ownerEmail)
				
				log('filter by email result:{0}'.format(isInList))

				# if item is not match filter, ignore it.
				if isInList != 1:
					continue

			except KeyError, e:
				print 'No owner info found!'
				continue

		if len(subject) > 0 and len(gerritNumber) > 0:
			pid = ''
			assertValue = ''
			link = URL_COMMIT_PRE + gerritNumber
			#pValue = getPID(gerritNumber)
			#sepIndex = pValue.find(':')
			
			#if sepIndex > 0:
			#	pid = pValue[:sepIndex]
			#	assertValue = pValue[sepIndex + 1:]

			#log(pValue)

			lineData = '"' + pid + '"'  # patch id. empty first
			lineData += ',' + subject
			lineData += ',' + link
			lineData += ',' + change_id
			lineData += ',' + updated
			lineData += ',' + ownerEmail
			lineData += ',' + assertValue # comments. empty first
			lineData += '\n'
			log(lineData)
			resultCount += 1
			excelFileHandler.write(lineData)
		else:
			print 'Error dict'
			print item
		
	print ' '
	excelFileHandler.close()
	return resultCount

def parserFormattedJsonFile(fileName,excelFileName,filterByNameOrMailList):
	jsonFileHandler = open(fileName,'r')
	dictList = []
	while 1:
		line = jsonFileHandler.readline()
		if len(line) == 0:
			break;

		#print line
		
		if line.find('[') >= 0:
			dictList.extend(parseJsonBlock(jsonFileHandler))

	jsonFileHandler.close()

	print ' '
	print 'parsing ended.'
	#whose json file parsed ended. prepare to write corresponding data to excel file
	#log('Parser Result:{0}'.format(len(dictList)))
	
	#begin get patch info for every commit.
	log('Begin get patch info for every commit')
	resultCount = writeDataToExcel(dictList, excelFileName,filterByNameOrMailList)
	return resultCount


BRANCH_COND_HISTORY_SAVING_FILE_NAME = '.branch.history'
def readHistoryBranchCondition():
	try:
		fileH = open(BRANCH_COND_HISTORY_SAVING_FILE_NAME, 'r')
		lines = fileH.readlines()
		fileH.close()
	except IOError, e:
		lines = []

	return lines

def writeQueryBranchCondition(branch, isCreateNew):
	branch = branch.strip('\n').strip()
	if isCreateNew == 1:
		flag = 'w'
	else:
		flag = 'a+'
		lines = readHistoryBranchCondition()
		for line in lines:
			line = line.strip('\n').strip()
			if line == branch:
				return

	fileH = open(BRANCH_COND_HISTORY_SAVING_FILE_NAME, flag)
	line = fileH.write(branch + '\n')
	fileH.close()

PROJECT_COND_HISTORY_SAVING_FILE_NAME = '.project.history'
def readHistoryProjectCondition():
	try:
		fileH = open(PROJECT_COND_HISTORY_SAVING_FILE_NAME, 'r')
		lines = fileH.readlines()
		fileH.close()
	except IOError, e:
		lines = []

	return lines

def writeQueryProjectCondition(project, isCreateNew):
	project = project.strip('\n').strip()
	if isCreateNew == 1:
		flag = 'w'
	else:
		flag = 'a+'
		lines = readHistoryProjectCondition()
		for line in lines:
			line = line.strip('\n').strip()
			if line == project:
				return

	fileH = open(PROJECT_COND_HISTORY_SAVING_FILE_NAME, flag)
	line = fileH.write(project + '\n')
	fileH.close()

# check if user want to exit
def checkIfExit(inputValue):
	if len(inputValue) <= 0:
		return

	if inputValue == 'e' or inputValue == 'E' or inputValue == 'exit' or inputValue == 'quit' or inputValue == 'q':
		exit('')

def inputQueryCondition():
	branch = ''
	project = ''
	status = ''
	owner = ''
	projectCondition = ''
	branchCondition = ''
	statusCondition = ''
	ownerCondition = ''
	
	ret = []

	print '\nPlease input query condition following guide!'
	while 1:
		if len(branch) <= 0:
			historyBranchs = readHistoryBranchCondition()

			if len(historyBranchs) > 0:
				print '\nPlease select git name in below list or input it manually.'
			else:
				print '\nPlease input git name.'

			index = 1
			for line in historyBranchs:
				if len(line) == 0:
					continue
				line = line.strip()
				line = line.strip('\n')
				print '{0} : {1}'.format(index, line)
				index += 1

			if index > 1:
				prompt = '\nbranch(1):'
			else:
				prompt = '\nbranch(ruby_dev_leui):'			
			branch = raw_input(prompt)
			branch = branch.strip()
			checkIfExit(branch)

			value = -1
			if len(branch) > 0:
				if len(historyBranchs) > 0:
					if branch.isdigit():
						value = string.atoi(branch)
						if value > len(historyBranchs):
							value = 1
			elif len(historyBranchs) > 0:
				value = 1				
			
			if len(historyBranchs) > 0 and value > 0 and value <= len(historyBranchs):
				branch = historyBranchs[value -1]
				branch = branch.strip('\n').strip()

			#value = 1
			#if len(historyBranchs) > 0 and len(branch) > 0 and branch.isdigit():
			#	value = string.atoi(branch)
		
			#if len(historyBranchs) > 0 and value > 0 and value <= len(historyBranchs):
			#	branch = historyBranchs[value - 1]
			#	branch = branch.strip('\n').strip()
			#else:
			#	branch = 'l-mr1-yukonodm'

			branchCondition = URL_BRANCH_PRE + branch
			#if len(branch) > 0:
			#	branchCondition = URL_BRANCH_PRE + branch	
			#elif len(historyBranch) > 0:
			#	branch = historyBranch
			#	
			print '\nbranch:' + branch

		if len(project) <= 0:
			lines = readHistoryProjectCondition()
			if len(lines) > 0:
				print '\nPlease select git name in below list or input it manually.'
			else:
				print '\nPlease input git name.'

			index = 1
			for line in lines:
				if len(line) == 0:
					continue
				line = line.strip()
				line = line.strip('\n')
				print '{0} : {1}'.format(index, line)
				index += 1
			
			if index > 1:
				prompt = '\ngit name(1):'
			else:
				prompt = '\ngit name(ruby/platform/packages/services/Telephony):'

			project = raw_input(prompt)
			project = project.strip()
			checkIfExit(project)
			value = -1
			if len(project) > 0:
				if len(lines) > 0:
					if project.isdigit():
						value = string.atoi(project)
						if value > len(lines):
							value = 1
			elif len(lines) > 0:
				value = 1				
			
			if len(lines) > 0 and value > 0 and value <= len(lines):
				project = lines[value -1]
				project = project.strip('\n').strip()			
			
			if len(project) == 0:
				project = 'ruby/platform/packages/services/Telephony'

			#if project == '1':
			#	project = 'platform/packages/apps/InCallUI'
			#elif project == '2':
			#	project = 'platform/packages/services/Telecomm'
			#elif project == '3':
			#	project = 'platform/packages/services/Telephony'

			projectCondition = URL_PROJECT_PRE + project
			print '\ngit name:' + project

		if len(status) <= 0:
			status = raw_input('\nstatus(merged):')
			status = status.strip()
			if len(status) <= 0:
				status = 'merged'

			statusCondition = URL_STATUS_PRE + status
			print '\nstatus:' + status


		if len(owner) <= 0:
			print '\nOwner filter:'
			print 'Enter  : Not filter by owner.'
			print '1      : Filter by name list or email list'
			print 'Others : Filter by user input.'
			print '(E)xit : Exit script.'
			owner = raw_input('Owner:')
			owner = owner.strip()
			if len(owner) <= 0:
				owner = ''

			print '\nowner:' + owner
			if owner == '1':
				ownerCondition = URL_OWNER_PRE + 'Name or Email list'
			else:
				ownerCondition = URL_OWNER_PRE + owner
			

		if len(branch) <= 0 or len(project) <= 0:
			print 'Please input correct query condition! press E or Q to exit!'
			continue

		#indicate to user for the query condition
		print '\nQuery condition:'
		print branchCondition
		print projectCondition
		print statusCondition
		print ownerCondition

		check = raw_input('\ncondition is right(y or n)?:')
		checkIfExit(check)

		if check == 'y' or check == 'Y':
			ret.append(project)
			ret.append(branch)
			ret.append(status)
			if len(owner) > 0:
				ret.append(owner)
			return ret
		elif check == 'n' or check == 'N':
			branch = ''
			project = ''
			status = ''
			projectCondition = ''
			branchCondition = ''
			statusCondition = ''

def manageProjectHistory():
	while 1:
		lines = readHistoryProjectCondition()
		if len(lines) == 0:
			print '\nNo git name saved before!'
			return

		print '\nGit name list:'
		index = 1
		for line in lines:
			line = line.strip()
			line = line.strip('\n')
			print '{0} : {1}'.format(index, line)
			index += 1

		print '\nPlease input index or content which you want to remove.\nInput (E)xit or (Q)uit to exit.'
		project = raw_input('\nRemove:')
		project = project.strip()
		checkIfExit(project)
		if project.isdigit():
			value = string.atoi(project) - 1
			if value >= 0 and value <= len(lines):
				print 'Remove ',lines[value] 
				del lines[value]
				print 'lines:', lines
					
		else:
			print 'Remove ',project
			try:
				lines.remove(project)
			except ValueError, e:
				print project + ' is not existed in list'

		if len(lines) > 0:
			content = ''
			for line in lines:
				content += line.strip().strip('\n') + '\n'

			content = content.strip().strip('\n')
			writeQueryProjectCondition(content, 1)
		else:
			try:
				os.remove(PROJECT_COND_HISTORY_SAVING_FILE_NAME)
			except OSError, e:
				print 'delete git name history file \"' + PROJECT_COND_HISTORY_SAVING_FILE_NAME + '\" failed. Please remove it manually!'
			exit('')
		continue



def saveScriptStartTime():
	strdaytime = strftime('%d-%b-%Y', localtime())
	savedTime = getScriptStartTime()
	if getScriptStartTime == strdaytime:
		return

	timeFileHandle = open(FILENAME_SCRIPT_START_DAYTIME, 'w')
	timeFileHandle.write(strdaytime)
	timeFileHandle.close()

# this start is recorded to avoid start firefox for saving cookie if no valid
# data returned. which maybe caused by no valid cookie. But maybe not... 
def getScriptStartTime():
	#strdaytime = strftime('%d-%b-%Y', localtime())
	try:
		timeFileHandle = open(FILENAME_SCRIPT_START_DAYTIME, 'r')
		line = timeFileHandle.readline()
		timeFileHandle.close()
	except IOError, e:
		line = ''

	if len(line) == 0:
		return ''

	return line.strip('\n').strip()


#Cookie maybe removed or timeout(?) sometimes. 
#Just call firefox to start corresponding url to save cookie if we did not get valid result.
#But there is no need to start firefox if we did not get valid data every time. Just start firefox at the first time
#when this script started every day!
def startFirefoxToSaveCookir():
	strdaytime = strftime('%d-%b-%Y', localtime())
	savedTime = getScriptStartTime()
	
	if savedTime != strdaytime:
		print '\n------------------------'
		print 'Please attention that this failed maybe caused by no valid cookie saved for review.sonyericsson.net.',
		print 'Please waiting for firefox to open current url and then try again!'
		print '\n------------------------\n'
		webbrowser.get('firefox').open_new("http://review.sonyericsson.net")

#######################
#http://diana.devops.letv.com/changes/?q=project:ruby/platform/packages/services/Telephony+branch:ruby_dev_leui+status:merged&n=100&O=81
URL_PATCHES_PRE='http://diana.devops.letv.com/changes/?q='
URL_PROJECT_PRE='project:'
URL_BRANCH_PRE='branch:'
URL_STATUS_PRE='status:'
URL_OWNER_PRE='owner:'

MAX_NET_REQUEST_ITEM_COUNT = 10000

global netRequestItemCount

netRequestItemCount = 1000

#start of main
print '\nThis program is to query gerrit list possible with patch id.\nCurrently only support git name, branch and status condition.Following \"-project\" to manage git name list.'
print 'Python version request: 2.7.10'

if DEBUG == 1:
	print sys.argv

jsonFileName = ''
if len(sys.argv) > 1:
	if '-project' == sys.argv[1].strip():
		manageProjectHistory()
		exit('')
	else:
		jsonFileName = sys.argv[1]
		print 'jsonFileName:' + jsonFileName

if len(jsonFileName) <= 0:
	branch = ''
	project = ''
	status = ''
	owner = ''
	while 1:
		#get query condition
		ret = inputQueryCondition()
		retCount = len(ret)

		if retCount < 3:
			print 'user input handling error. Please input again!'
			continue

		if retCount >= 3:
			project = ret[0]
			branch = ret[1]
			status = ret[2]

		if retCount == 4:
			owner = ret[3]
			owner = owner.strip()
		break;	

	if len(owner) > 0 and owner != '1':
		owner = owner.replace(' ', '+')
		url = URL_PATCHES_PRE + URL_PROJECT_PRE + project + '+' + URL_BRANCH_PRE + branch + '+' + URL_STATUS_PRE + status + '+' + URL_OWNER_PRE + '\"' + owner + '\"'
	else:
		url = URL_PATCHES_PRE + URL_PROJECT_PRE + project + '+' + URL_BRANCH_PRE + branch + '+' + URL_STATUS_PRE + status

	log('url:' + url)
		
	# generate temp and result file name
	index = project.rfind('/')
	projectCond = project
	if index > 0:
		projectCond = project[index + 1:]

	if len(owner) > 0:
		jsonFileName = projectCond + '_' + branch + '_' + status + '_' + owner.replace('+','-') + '.json'
	else:
		jsonFileName = projectCond + '_' + branch + '_' + status + '.json'

	jsonFileName = jsonFileName.replace('/','_')

	while 1:
		maxResultCondition = '&n={0}'.format(netRequestItemCount)

		print '\nQuerying from network...\n'	
		netFileHandler = getNetJsonData(url + maxResultCondition + '&O=881')

		itemCount = 0
		print '\nParsing data...\n'
		itemCount = formatNetJsonData(netFileHandler,jsonFileName)
		netFileHandler.close()

		if itemCount == 0:
			print 'No valid data found. Ended!'
			print 'url:' + url
			startFirefoxToSaveCookir()
			exit(jsonFileName)
		elif itemCount >= netRequestItemCount and netRequestItemCount <= MAX_NET_REQUEST_ITEM_COUNT:
			netRequestItemCount = netRequestItemCount * 2
			print 'Not all data requested. double request count and query again!'
		else:
			break

# we only save history information after some result is returned.
writeQueryBranchCondition(branch, 0)
writeQueryProjectCondition(project, 0)

dotIndex = jsonFileName.rfind('.')

if dotIndex <= 0:
	dotIndex = len(jsonFileName)

excelFileName = jsonFileName[:dotIndex] + '.csv'
resultCount = parserFormattedJsonFile(jsonFileName,excelFileName, owner)
	
print 'Result count: {0}\nResult output: {1}'.format(resultCount, excelFileName)
	
if itemCount >= netRequestItemCount:
	print 'Please attentin:\n Too many data for current query condition. Result data maybe not complete!'


exit(jsonFileName)



