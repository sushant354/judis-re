import utils
import urllib
import HTMLParser
import tempfile
import subprocess
import sys
import os

class KolkataParser(HTMLParser.HTMLParser):
    def __init__(self):
       HTMLParser.HTMLParser.__init__(self)
       self.links     = []

    def handle_starttag(self, tag, attrs):
        if tag == 'option':
            for attr in attrs:
                if len(attr) > 1 and attr[0] == 'value':
                    self.links.append(attr[1])
        elif tag == 'input':
            reccnt = False
            for attr in attrs:
                if attr[0] == 'name' and attr[1] == 'RecCnt':
                    reccnt = True
            if reccnt:
                for attr in attrs:
                    if attr[0] == 'value':
                        self.recordcnt = attr[1]


class Kolkata(utils.BaseCourt):
    def __init__(self, name, datadir, DEBUG = True):
        utils.BaseCourt.__init__(self, name, datadir, DEBUG)
        self.baseurl = 'http://www.judis.nic.in/Kolkata'
        self.cookiefile  = tempfile.NamedTemporaryFile()

    def get_cookies(self):
        argList = [\
                   '/usr/bin/wget','--output-document', '-', \
                   '--keep-session-cookies', '--save-cookies', \
                   self.cookiefile.name,  '-a', self.wgetlog, \
                   self.baseurl + '/DtOfJud_Qry.asp' \
                  ]
        p = subprocess.Popen(argList, stdout=subprocess.PIPE)
        webpage = utils.read_forked_proc(p)

    def download(self, fromdate, todate, doctype):
        posturl  = self.baseurl + '/FreeText_Result_1.asp'
        postdata = [('Free_Txt', 'e'), ('From_Dt', fromdate), \
                    ('To_Dt', todate), ('OJ', doctype), ('submit', 'Submit')]

        encodedData  = urllib.urlencode(postdata)

        arglist =  [\
                   '/usr/bin/wget', '--output-document', '-', \
                   '-a', self.wgetlog, '--post-data', "'%s'" % encodedData, \
                     '--load-cookies', self.cookiefile.name, posturl \
                   ]
        p = subprocess.Popen(arglist, stdout=subprocess.PIPE)

        return self.download_webpage(p)

    def download_oneday(self, relpath, dateobj):
        self.get_cookies()

        todate   = utils.dateobj_to_str(dateobj, '/')
        fromdate  = todate

        if self.DEBUG:
            print 'DATE %s' % todate

        newdls = self.new_downloads(relpath, fromdate, todate, '_J_')
        newdls.extend(self.new_downloads(relpath, fromdate, todate, '_O_'))
        return newdls

    def new_downloads(self, relpath, fromdate, todate, doctype):
        newdls = []
        courtParser  = self.download(fromdate, todate, doctype)
        for link in courtParser.links:
            relurl   = os.path.join(relpath, link)
            filepath = os.path.join(self.datadir, relurl)
            if not os.path.exists(filepath) or os.stat(filepath).st_size <= 0:
                if self.get_judgment(courtParser.recordcnt, link, filepath):
                    newdls.append(relurl)
        return newdls

    def get_judgment(self, recordcnt, link, filepath):
        posturl  = self.baseurl + '/Judge_Result_Disp.asp'
        print posturl
        postdata = [('RecCnt', recordcnt), ('MyChk', link), \
                    ('submit', 'Submit')]    

        encodedData  = urllib.urlencode(postdata)
        arglist =  [\
                   '/usr/bin/wget', '--output-document', '-', \
                   '-a', self.wgetlog, '--post-data', "'%s'" % encodedData, \
                     '--load-cookies', self.cookiefile.name, posturl \
                   ]
        p = subprocess.Popen(arglist, stdout=subprocess.PIPE)
        webpage = utils.read_forked_proc(p)
    
        if webpage != None:
            filehandle = open(filepath, 'w')
            filehandle.write(webpage)
            filehandle.close()
            return True
        else:
            return False

    def download_webpage(self, p):
        newdls = []
        webpage = utils.read_forked_proc(p)

        if not webpage:
            return newdls 

        courtParser = KolkataParser()

        try:
            courtParser.feed(webpage)
        except HTMLParser.HTMLParseError, e:
            print >> sys.stderr, 'Malformed HTML: %s' % e

        return courtParser
