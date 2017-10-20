#!/usr/bin/env python

# pythond version: 2.7.10

import os
import sys, urllib, string, re
import urllib2
import webbrowser
from time import localtime, strftime

# browserCookie.py is necessary for this import.
try:
    from browserCookie import *
except ImportError, e:
    print e
    print 'Please make sure following py file existed: "browerCookie.py"'
    sys.exit(1)

FILENAME_SCRIPT_START_DAYTIME = '.script_starttime.conf'
#######################
WIKI_PAGE_URL = 'http://wiki.letv.cn/plugins/viewsource/viewpagesrc.action?pageId=67041542'


class WikiHelper(object):
    def __init__(self):
        # gerrit server url
        self.URL_COMMIT_PRE = 'http://diana.devops.letv.com/#/c/'
        self.DEBUG = 0
        self.wikiGerritList = []
        self.excludeGerritList = []

    def log(self, text):
        if self.DEBUG:
            print text

    def exit(self, tempFileName):
        if self.DEBUG != 1 and len(tempFileName) > 0:
            try:
                os.remove(tempFileName)
            except OSError, e:
                print 'Temp file:' + tempFileName + ' delete maybe failed. Please remove it manually!'

        self.saveScriptStartTime()
        self.log('End')
        sys.exit(1)

    # file handler is returned by this function
    def getWebData(self, url):
        print url
        self.log('Using firefox cookie to open this url:{!s}'.format(url))
        cj = firefox()

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        req = urllib2.Request(url)

        # Accept:text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8
        # Accept-Encoding:gzip, deflate, sdch
        # Accept-Language:en-US,en;q=0.8
        # Cache-Control:max-age=0
        # Connection:keep-alive
        # Cookie:JSESSIONID=26FB3A78ED1F169EEE50747F6EAC3DAF; seraph.confluence=67502388%3A0db3ca854b71a991d019e7648844b89b999fd7fe; doc-sidebar=300px; crowd.token_key=hnJaZroUHLm1th2QXKvQnQ00
        # Host:wiki.letv.cn
        # Upgrade-Insecure-Requests:1
        # User-Agent:Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.90 Safari/537.36

        req.add_header('User-Agent',
                       'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:50.0) Gecko/20100101 Firefox/50.0');
        req.add_header('Accept', 'application/json');
        req.add_header('Accept-Language', 'aen-US,en;q=0.5');
        req.add_header('Accept-Encoding', 'deflate');
        req.add_header('Content-Type', 'application/json; charset=UTF-8');
        req.add_header('x-content-type-options', 'nosniff');

        return opener.open(req)

    def saveScriptStartTime(self):
        strdaytime = strftime('%d-%b-%Y', localtime())
        savedTime = self.getScriptStartTime()
        if savedTime == strdaytime:
            return

        timeFileHandle = open(FILENAME_SCRIPT_START_DAYTIME, 'w')
        timeFileHandle.write(strdaytime)
        timeFileHandle.close()

    # this start is recorded to avoid start firefox for saving cookie if no valid
    # data returned. which maybe caused by no valid cookie. But maybe not...
    def getScriptStartTime(self):
        # strdaytime = strftime('%d-%b-%Y', localtime())
        try:
            timeFileHandle = open(FILENAME_SCRIPT_START_DAYTIME, 'r')
            line = timeFileHandle.readline()
            timeFileHandle.close()
        except IOError, e:
            line = ''

        if len(line) == 0:
            return ''

        return line.strip('\n').strip()

        # Cookie maybe removed or timeout(?) sometimes.
        # Just call firefox to start corresponding url to save cookie if we did not get valid result.
        # But there is no need to start firefox if we did not get valid data every time. Just start firefox at the first time
        # when this script started every day!

    def startFirefoxToSaveCookir(self):
        strdaytime = strftime('%d-%b-%Y', localtime())
        savedTime = self.getScriptStartTime()

        if savedTime != strdaytime:
            print '\n------------------------'
            print 'Please attention that this failed maybe caused by no valid cookie saved for http://diana.devops.letv.com.',
            print 'Please waiting for firefox to open current url and then try again!'
            print '\n------------------------\n'
            webbrowser.get('firefox').open_new("http://diana.devops.letv.com")

    def loadWikiGerritList(self):
        # load exclude gerrit list first.
        self.loadExcludeGerritList()

        # if self.DEBUG == 1:
        #	fHandler = open("ret.log",'r')
        # else:
        fHandler = self.getWebData(WIKI_PAGE_URL)

        netDataSavingFileHandler = 0
        if self.DEBUG == 1:
            netDataSavingFileHandler = open('temp' + '.log', 'w')

        wikiGerritList = []
        while 1:
            line = fHandler.readline()
            if len(line) == 0:
                break;

            result = re.findall(">([^<> ].+?)<", line)
            for x in result:
                x = x.strip()
                if len(x) > 0 and x.startswith("http://diana.devops.letv.com"):
                    self.wikiGerritList.append(x)
                    if netDataSavingFileHandler != 0:
                        netDataSavingFileHandler.write(x + '\n')

        if netDataSavingFileHandler != 0:
            netDataSavingFileHandler.close()

        fHandler.close()

    def isGerritInWiki(self, gerrit):
        if len(self.wikiGerritList) == 0:
            self.log('gerrit list in wiki not loaded. loading...')
            self.loadWikiGerritList()

        if len(self.wikiGerritList) == 0:
            self.log('no gerrit found in wiki page. some error happened!')
            sys.exit(1)
            return 0

        for str in self.wikiGerritList:
            if str.find(gerrit) >= 0:
                return 1

        self.log('gerrit ' + gerrit + ' not found!')
        return 0


    def loadExcludeGerritList(self):
        fileHandler = open('exclude.txt', 'r')

        while 1:
            line = fileHandler.readline()
            if len(line) == 0:
                break;

            self.log('load exclude link: ' + line)
            self.excludeGerritList.append(line)

        fileHandler.close()


    def isInExcludeList(self, gerrit):
        if len(self.excludeGerritList) == 0:
            self.log('exlude list is empty')
            return 0

        for link in self.excludeGerritList:
            if link.find(gerrit) >= 0:
                self.log('gerrit ' + gerrit + ' is in exlude list!')
                return 1

        return 0
