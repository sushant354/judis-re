import sys
import urllib
import subprocess
import tempfile
import re
import HTMLParser
import os

import utils

class Lobis(utils.BaseCourt):
    def __init__(self, name, datadir, DEBUG):
        utils.BaseCourt.__init__(self, name, datadir, DEBUG)
        self.cookiefile  = tempfile.NamedTemporaryFile()

    def get_cookies(self):
        argList = [\
                   '/usr/bin/wget','--output-document', '-', \
                   '--keep-session-cookies', '--save-cookies', \
                   self.cookiefile.name,  '-a', self.wgetlog, \
                   self.cookieurl \
                  ]
        p = subprocess.Popen(argList, stdout=subprocess.PIPE)
        webpage = utils.read_forked_proc(p)

    def download_oneday(self, relpath, dateobj):
        #self.get_cookies()
        todate   = utils.dateobj_to_str(dateobj, '/')
        fromdate  = todate

        if self.DEBUG:
            print 'DATE %s' % todate
      
        postdata = [('juddt', todate), ('Submit', 'Submit')]
        encodedData  = urllib.urlencode(postdata)

        arglist =  [\
                   '/usr/bin/wget', '--output-document', '-', \
                   '--keep-session-cookies', '--save-cookies', \
                   self.cookiefile.name,  '-a', self.wgetlog, \
                   '--post-data', encodedData, \
                   self.dateurl \
                   ]
        p = subprocess.Popen(arglist, stdout=subprocess.PIPE)

        return self.result_page(p, relpath)

    def get_judgment(self, link, filepath):
        if link[0] == '/':
            url      = '%s%s' % (self.baseurl, link)
        else:
            url      = '%s/%s' % (self.courturl, link)

        arglist  = ['/usr/bin/wget',  '-a', self.wgetlog,
                    '--load-cookies', self.cookiefile.name, \
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
            if not re.match('\d+$', linktitle) and not \
              re.search('PREV|NEXT', linktitle):
                tmprel   = os.path.join(relpath, re.sub('/', '-', linktitle))
                filepath = os.path.join(self.datadir, tmprel)
                if not os.path.exists(filepath) and \
                       self.get_judgment(link, filepath):
                    newdls.append(tmprel)

        if len(newdls) > 0:
            for linktitle, link in courtParser.links:
                if re.match('NEXT', linktitle):
                    arglist = [\
                           '/usr/bin/wget', '--output-document', '-', \
                           '-a', self.wgetlog, \
                           '--load-cookies', self.cookiefile.name, \
                           self.baseurl + link \
                              ]
                    p = subprocess.Popen(arglist, stdout=subprocess.PIPE)
                    newdls.extend(self.result_page(p, relpath))
        return newdls
