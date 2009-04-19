import sys
import urllib
import subprocess
import tempfile
import re
import HTMLParser
import os

import utils

class Bombay(utils.BaseCourt):
    def __init__(self, name, datadir, DEBUG = True):
        utils.BaseCourt.__init__(self, name, datadir, DEBUG)
        self.baseurl = 'http://bombayhighcourt.nic.in'
        self.cookiefile  = tempfile.NamedTemporaryFile()

    def get_cookies(self):
        argList = [\
                   '/usr/bin/wget','--output-document', '-', \
                   '--keep-session-cookies', '--save-cookies', \
                   self.cookiefile.name,  '-a', self.wgetlog, \
                   self.baseurl + '/ord_qryrepact.php'\
                  ]
        p = subprocess.Popen(argList, stdout=subprocess.PIPE)
        webpage = utils.read_forked_proc(p)

    def download_oneday(self, relpath, dateobj):
        self.get_cookies()
        posturl  = self.baseurl + '/ordqryrepact_action.php'

        todate   = utils.dateobj_to_str(dateobj, '-')
        fromdate  = todate

        if self.DEBUG:
            print 'DATE %s' % todate
      
        postdata = [('pageno', 1), ('actcode', 0), ('frmaction', ''), \
                    ('frmdate', fromdate), \
                    ('todate', todate), ('submit1', 'Submit')]
        encodedData  = urllib.urlencode(postdata)

        arglist =  [\
                   '/usr/bin/wget', '--output-document', '-', \
                   '-a', self.wgetlog, '--post-data', "'%s'" % encodedData, \
                     '--load-cookies', self.cookiefile.name, posturl \
                   ]
        p = subprocess.Popen(arglist, stdout=subprocess.PIPE)

        return self.result_page(p, relpath)

    def get_judgment(self, link, filepath):
        url      = '%s/%s' % (self.baseurl, link)
        arglist  = ['/usr/bin/wget',  '-a', self.wgetlog,
                    '--output-document', filepath, url]
        p        = subprocess.Popen(arglist)
        p.wait()
        if os.path.exists(filepath) and os.stat(filepath).st_size > 0:
            return True
        else:    
            return False

    def result_page(self, p, relpath):
        newdls      = []
        webpage     = utils.read_forked_proc(p)

        if not webpage:
            return newdls 

        courtParser = utils.CourtParser()

        try:
            courtParser.feed(webpage)
        except HTMLParser.HTMLParseError, e:
            print >> sys.stderr, 'Malformed HTML: %s' % e

        for linktitle, link in courtParser.links:
            if not re.search('first|prev|next|last|acroread', linktitle, \
                             flags=re.IGNORECASE) and len(linktitle) > 0:
                tmprel   = os.path.join(relpath, re.sub('/', '-', linktitle))
                filepath = os.path.join(self.datadir, tmprel)
                if not os.path.exists(filepath) and \
                       self.get_judgment(link, filepath):
                    newdls.append(tmprel)

        for linktitle, link in courtParser.links:
            if linktitle == 'Next':
                link = '%s/%s' % (self.baseurl, link)
                arglist = [\
                           '/usr/bin/wget', '--output-document', '-', \
                           '-a', self.wgetlog, \
                           '--load-cookies', self.cookiefile.name, \
                           link \
                          ]
                p = subprocess.Popen(arglist, stdout=subprocess.PIPE)
                newdls.extend(self.result_page(p, relpath))
        return newdls
