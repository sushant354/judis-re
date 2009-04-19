import os
import re
import subprocess
import urllib
import string
import tempfile
import sys

import HTMLParser
import utils


class SCParser(HTMLParser.HTMLParser):
    def __init__(self):
       HTMLParser.HTMLParser.__init__(self)
       self.linkname = None
       self.linkdata = '' 
       self.stateval = None
       self.links    = {}

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr in attrs:
                if len(attr) > 1 and attr[0] == "href":
                    self.linkname = attr[1]
        elif tag == 'input' and self.stateval == None: 
            recordval = False
            for attr in attrs:
                if len(attr) > 0 and attr[0] == 'name' and attr[1] == \
                                                               '__VIEWSTATE':
                    recordval = True
            if recordval:
                for attr in attrs:
                    if len(attr) > 0 and attr[0] == 'value':
                        self.stateval = attr[1]

    def handle_data(self, data):
        if self.linkname != None:
            self.linkdata += data

    def handle_endtag(self, tag):
        if tag == 'a':
            self.linkdata             = string.strip(self.linkdata)
            self.links[self.linkdata] = string.strip(self.linkname)
            self.linkname             = None
            self.linkdata             = ''

class SupremeCourt(utils.BaseCourt):
    def __init__(self, name, datadir, DEBUG = True):
        utils.BaseCourt.__init__(self, name, datadir, DEBUG)

        self.cookiefile  = tempfile.NamedTemporaryFile()
        self.webformUrl  = 'http://judis.nic.in/supremecourt/Chrseq.aspx'
        self.dateqryUrl  = 'http://judis.nic.in/supremecourt/DateQry.aspx' 
        self.nextpageStr = 'Next Page'
        self.prevpageStr = 'Previous Page'


    def download_oneday(self, relpath, dateobj):
        if self.DEBUG:
            print 'Downloading for the date %s' % dateobj

        self.stateval   = self.get_stateval()
        if dateobj.month < 10:
            mnth = '0%d' % dateobj.month
        else:
            mnth = '%d' % dateobj.month
	    
        if dateobj.day < 10:
            day = '0%d' % dateobj.day
        else:
            day = '%d' % dateobj.day
	    
        postdata = [('__VIEWSTATE', self.stateval), \
                     ('ddlday1', day), ('ddlmonth1', mnth),\
                     ('ddlyear1', dateobj.year),('ddlday2', day), \
                     ('ddlmonth2', mnth),('ddlyear2', dateobj.year),\
                     ('ddlreport', 'A'), ('button', 'Submit')\
                    ]

        webpage  = self.download_webpage(postdata, self.dateqryUrl)
        return self.datequery_result(webpage, relpath, 0)
        
    def datequery_result(self, webpage, relpath, pagenum):
        downloaded = []
        filehandle = open('%s/%s/index_%d.html' % (self.datadir, relpath, pagenum), 'w')
        filehandle.write(webpage)
        filehandle.close()

        # see if we need to change the stateval
        stateval  = self.extract_state(webpage)
        if stateval != None and stateval != self.stateval:
            self.stateval = stateval
            if self.DEBUG:
                print 'stateval changed'

        scParser = SCParser()

        try:
            scParser.feed(webpage)
        except HTMLParser.HTMLParseError, e:
            print >> sys.stderr, 'Malformed HTML: %s' % e

        for header in scParser.links.keys():
            filename = re.sub('/', '|', header)
            tmprel   = os.path.join (relpath, filename)
            filepath = os.path.join (self.datadir, tmprel)
            if not os.path.exists(filepath) and re.search('Coram:|Click here', \
                                                           header) == None:
                linkinfo = self.parse_link(scParser.links[header])
                if linkinfo == None:
                    print 'Warn: Could not download %s. Link is %s' % (header, \
                          scParser.links[header])
                elif header != self.nextpageStr and header != self.prevpageStr:
                    webpage = self.download_link(linkinfo)
                    if webpage: 
                        filehandle = open(filepath, 'w')
                        filehandle.write(webpage)
                        filehandle.close()
                        downloaded.append(tmprel)
        # download next page if it exists
        if self.nextpageStr in scParser.links.keys():
            header = self.nextpageStr
            linkinfo = self.parse_link(scParser.links[header])
            webpage = self.download_link(linkinfo)
            if webpage:
                nextdownloads = self.datequery_result(webpage, relpath,\
                                                      pagenum+1)
                downloaded.extend(nextdownloads)

        return downloaded

    def extract_state(self, datequery):
        stateval = None
        for line in datequery.splitlines():
            reobj = re.search('name="__VIEWSTATE"\s+value="(?P<state>[^"]+)"', line)
            if reobj != None:
                stateval = reobj.group('state')
        return stateval

    def get_stateval(self):
        argList = [\
                   '/usr/bin/wget','--output-document', '-', \
                   '--keep-session-cookies', '--save-cookies', \
                   self.cookiefile.name,  '-a', self.wgetlog, \
                   'http://judis.nic.in/supremecourt/DateQry.aspx'\
                  ]

        p = subprocess.Popen(argList, shell=False, stdout=subprocess.PIPE)
        datequery = utils.read_forked_proc(p)

        return self.extract_state(datequery)

    def download_webpage(self, postdata, posturl):
        encodedData  = urllib.urlencode(postdata)

        argList = [\
                   '/usr/bin/wget', '--output-document', '-', \
                   '-a', self.wgetlog, \
                   '--load-cookies', self.cookiefile.name,  '--post-data', \
                   "'%s'" % encodedData, posturl \
                  ]
        command = string.join(argList, ' ')

        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        return utils.read_forked_proc(p)

    def parse_link(self, linkname):
       linkRe = "javascript:__doPostBack\('(?P<event_target>[^']+)','(?P<event_arg>[^']*)'\)"
       return re.search(linkRe, linkname)

    def download_link(self, linkinfo):
        eventTarget = string.join(linkinfo.group('event_target').split('$'), ':')
        postdata = [('__VIEWSTATE',     self.stateval), ('__EVENTTARGET', eventTarget),\
                    ('__EVENTARGUMENT', linkinfo.group('event_arg'))]

        return self.download_webpage(postdata, self.webformUrl)

