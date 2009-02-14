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

def mk_dir(dirname):
    if not os.path.exists(dirname):
        os.mkdir(dirname)

class Judis:
    def __init__(self, datadir):
        self.datadir     = datadir
	statdir          = '%s/stats' % datadir
        mk_dir(statdir)

	self.wgetlog     = '%s/stats/wgetlog' % datadir

        self.cookiefile  = tempfile.NamedTemporaryFile()
        self.webformUrl  = 'http://judis.nic.in/supremecourt/Chrseq.aspx'
        self.dateqryUrl  = 'http://judis.nic.in/supremecourt/DateQry.aspx' 
        self.nextpageStr = 'Next Page'
        self.prevpageStr = 'Previous Page'

    def sync(self, fromdate, todate, relpath):
        newdownloads = []
        dirname = '%s/%s' % (self.datadir, relpath)
        mk_dir(dirname)

        while fromdate <= todate:
            dateobj   = fromdate.date()
            tmprel    = '%s/%s' % (relpath, dateobj)	    
            datedir   = '%s/%s' % (self.datadir, tmprel)
            mk_dir(datedir)
            dls = self.download_oneday(tmprel, dateobj)
	    newdownloads.extend(dls)
            fromdate += datetime.timedelta(days=1)
        return newdownloads

    def download_oneday(self, relpath, dateobj):
        if DEBUG:
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
            if DEBUG:
                print 'stateval changed'

        webformParser = WebformParser()
        webformParser.feed(webpage)

        for header in webformParser.links.keys():
	    filename = re.sub('/', '|', header)
	    tmprel   = '%s/%s' % (relpath, filename)
            filepath = '%s/%s' % (self.datadir, tmprel)
            if not os.path.exists(filepath) and re.search('Coram:|Click here', header) == None:
                print header
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
			downloaded.append(tmprel)
        # download next page if it exists
        if self.nextpageStr in webformParser.links.keys():
            header = self.nextpageStr
            linkinfo = self.parse_link(webformParser.links[header])
            webpage = self.download_link(linkinfo)
            nextdownloads = self.datequery_result(webpage, relpath, pagenum+1)
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
		   '-a', self.wgetlog, \
                   '--load-cookies', self.cookiefile.name,  '--post-data', \
                   "'%s'" % encodedData, posturl \
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
    print 'Usage: %s [-t fromdate (DD-MM-YYYY)] [-T todate (DD-MM-YYYY)] datadir\n' % progname
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

    fromdate = None
    todate   = None

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

    if fromdate == None:
        if todate == None:
            todate   = datetime.datetime.today() 
        fromdate = todate - datetime.timedelta(days = 7)
    elif todate == None:
        todate = fromdate + datetime.timedelta(days = 7)

    datadir = remlist[0]
    judis   = Judis(datadir)
    dls = judis.sync(fromdate, todate, 'judis.nic.in')

    print 'NEW DOWNLOADS'
    for dl in dls: 
        print dl
