#!/usr/bin/env python

# pythond version: 2.7.10

import os
import sys,urllib,string,re
import urllib2
import webbrowser

DEBUG = 1


URL_COMMIT_DETAILS_PRE = 'http://review.sonyericsson.net/changes/'
URL_END = 'detail?O=404'
GIT_NAME_KEY = 'project'

#browserCookie.py is necessary for this import.
try:
	from browserCookie import *
except ImportError, e:
	print e
	print 'Please make sure following py file existed: "browerCookie.py"'
	exit('')


def log(text):
	if DEBUG:
		print text


# file handler is returned by this function
def getNetJsonData(url):
	#print url
	#print 'Using firefox cookie to open this url:{!s}'.format(url)
	cj = firefox()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	req = urllib2.Request(url)

	req.add_header('User-Agent', 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0'); 
	req.add_header('Accept', 'application/json');
	req.add_header('Host', 'review.sonyericsson.net');
	req.add_header('Accept-Language', 'aen-US,en;q=0.5');
	req.add_header('Accept-Encoding', 'deflate');
	req.add_header('Content-Type', 'application/json; charset=UTF-8');
	req.add_header('x-content-type-options', 'nosniff');

	fHandler = opener.open(req)

	return fHandler


def getGitName(gerritNumber):
	# no gerrit number inputted
	if len(gerritNumber) <= 0:
		return ''
	gerritNumber = gerritNumber.strip('\n').strip()
	#print gerritNumber

	url = URL_COMMIT_DETAILS_PRE + gerritNumber + '/' + URL_END
	#print 'url:',url
	commitData = getNetJsonData(url)

	gitName = ''
	#print commitData.readlines()
	while 1:
		line = commitData.readline()
		if len(line)==0:
           		break
		#print line

		if len(gitName) == 0:
			gitName = getKeyValue(line, GIT_NAME_KEY)

		if len(gitName) > 0:
			break;

	if len(gitName) == 0:
		return ''

	return gitName

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


# ---------------------------------------
print 'start'
try:
	filehandle = open('origin.csv', 'r')
except IOError, e:
	print 'file open error. exit!'
	sys.exit(1)

excelFileHandler = open('result.csv', 'w')
excelFileHandler.write('PID,Title,Link,owner,Comments\n')

while 1:
	line = filehandle.readline()
	if len(line) == 0:
		break;

	line = line.strip('\n').strip()
	#print line

	sepIndex = line.rfind('/')

	gitName = ''
	if sepIndex >= 0:
		gerritNumber = line[sepIndex + 1:]
		gitName = getGitName(gerritNumber)

	if len(gitName) == 0:
		print 'get gitname failed. line data:',line
		
	else:
		print '.',
		sys.stdout.flush()	

	ret = line + ',' + gitName + '\n'
	excelFileHandler.write(ret)	

filehandle.close()
excelFileHandler.close()

print 'End'
sys.exit(1)


