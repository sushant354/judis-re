import sys
import os
import re
import subprocess
import urllib
import string
import tempfile
import getopt
import datetime
import select

from HTMLParser import HTMLParser

DEBUG =1

class WebformParser(HTMLParser):
    def __init__(self):
       HTMLParser.__init__(self)
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
                if len(attr) > 0 and attr[0] == 'name' and attr[1] == '__VIEWSTATE':
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

class Judis:
    def __init__(self, datadir):
        self.datadir    = datadir
        self.cookiefile = tempfile.NamedTemporaryFile()
        self.webformUrl = 'http://judis.nic.in/supremecourt/WebForm2.aspx'
        self.dateqryUrl = 'http://judis.nic.in/supremecourt/DateQry.aspx' 
        self.nextpageStr = 'Next Page'
        self.prevpageStr = 'Previous Page'

    def sync(self, fromdate, todate):
        while fromdate <= todate:
            dateobj   = fromdate.date()
            datedir   = '%s/%s' % (self.datadir, dateobj)
            if not os.path.exists(datedir):
                os.mkdir(datedir)
            self.download_oneday(datedir, dateobj)
            fromdate += datetime.timedelta(days=1)

    def download_oneday(self, datedir, dateobj):
        if DEBUG:
            print 'Downloading for the date %s' % dateobj

        self.stateval   = self.get_stateval()
        if dateobj.month < 10:
            mnth = '0%d' % dateobj.month
        else:
            mnth = '%d' % dateobj.month
        postdata = [('__VIEWSTATE', self.stateval), \
                     ('ddlday1', dateobj.day), ('ddlmonth1', mnth),\
                     ('ddlyear1', dateobj.year),('ddlday2', dateobj.day), \
                     ('ddlmonth2', mnth),('ddlyear2', dateobj.year),\
                     ('ddlreport', 'A'), ('button', 'Submit')\
                    ]

        webpage  = self.download_webpage(postdata, self.dateqryUrl)
        self.datequery_result(webpage, datedir, 0)
        
    def datequery_result(self, webpage, datedir, pagenum):
        filehandle = open('%s/index_%d.html' % (datedir, pagenum), 'w')
        filehandle.write(webpage)
        filehandle.close()

        # see if we need to change the stateval
        stateval  = self.extract_state(webpage)
        if stateval != None and stateval != self.stateval:
            self.stateval = stateval
            if DEBUG:
                print 'stateval changed'

        webformParser = WebformParser()
        webformParser.feed(webpage)

        for header in webformParser.links.keys():
            filepath = '%s/%s' % (datedir, re.sub('/', '|', header))
            if not os.path.exists(filepath) and re.search('Coram:', header) == None:
                print header, webformParser.links[header]
                linkinfo = self.parse_link(webformParser.links[header])
                if linkinfo == None:
                    print 'Warn: Could not download %s. Link is %s' % (header, \
                          webformParser.links[header])
                else:
                    if header != self.nextpageStr and header != self.prevpageStr:
                        webpage = self.download_link(linkinfo)
                        filehandle = open(filepath, 'w')
                        filehandle.write(webpage)
                        filehandle.close()
        # download next page if it exists
        if self.nextpageStr in webformParser.links.keys():
            header = self.nextpageStr
            linkinfo = self.parse_link(webformParser.links[header])
            webpage = self.download_link(linkinfo)
            self.datequery_result(webpage, datedir, pagenum+1)

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
                   self.cookiefile.name,  \
                   'http://judis.nic.in/supremecourt/DateQry.aspx'\
                  ]

        p = subprocess.Popen(argList, shell=False, stdout=subprocess.PIPE)
        datequery = self.read_forked_proc(p)

        return self.extract_state(datequery)

    def read_forked_proc(self, p):
        webpage = ''
        stdout_fd = p.stdout.fileno() 

        while p.poll() == None:
            fdtuple = select.select([stdout_fd], [], [])

            if len(fdtuple[0]) >  0:
                webpage += p.stdout.read()

        webpage += p.stdout.read()
        return webpage

    def download_webpage(self, postdata, posturl):
        encodedData  = urllib.urlencode(postdata)

        argList = [\
                   '/usr/bin/wget', '--output-document', '-', \
                   '--load-cookies', self.cookiefile.name,  '--post-data',\
                   "'%s'" % encodedData, posturl\
                  ]
        command = string.join(argList, ' ')

        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        return self.read_forked_proc(p)

    def parse_link(self, linkname):
       linkRe = "javascript:__doPostBack\('(?P<event_target>[^']+)','(?P<event_arg>[^']*)'\)"
       return re.search(linkRe, linkname)

    def download_link(self, linkinfo):
        eventTarget = string.join(linkinfo.group('event_target').split('$'), ':')
        postdata = [('__VIEWSTATE',     self.stateval), ('__EVENTTARGET', eventTarget),\
                    ('__EVENTARGUMENT', linkinfo.group('event_arg'))]

        return self.download_webpage(postdata, self.webformUrl)

def print_usage(progname):
    print 'Usage: %s [-t fromdate] [-T todate] datadir\n' % progname
    print 'The program will download supreme court judgments from judis'
    print 'and will place in a specified directory. Judgments will be'
    print 'placed into directories named by dates. If fromdate or todate'
    print 'is not specified then the default is your current date.'

def to_datetime(datestr):
    numlist = re.findall('\d+', datestr)
    if len(numlist) != 3:
        print >>sys.stderr, '%s not in correct format [DD/MM/YYYY]' % datestr
        return None
    else:
        datelist = []
        for num in numlist:
            datelist.append(string.atoi(num))
        return datetime.datetime(datelist[2], datelist[1], datelist[0])

if __name__ == '__main__':
    #initial values
    fromdate = datetime.datetime.today() 
    todate   = datetime.datetime.today()

    progname = sys.argv[0]
    optlist, remlist = getopt.getopt(sys.argv[1:], 'p:t:T:h')
    for o, v in optlist:
        if o == '-t':
            fromdate =  to_datetime(v)
        elif o == '-T':
            todate   = to_datetime(v)
        else:
            print_usage(progname)
            sys.exit(0)

    if len(remlist) != 1:
        print_usage(progname)
        sys.exit(0) 

    datadir = remlist[0]
    judis   = Judis(datadir)
    judis.sync(fromdate, todate)
 
    #main(fromdate, todate)
    #datequery_result(open('tmp', 'r').read(), None, None)
