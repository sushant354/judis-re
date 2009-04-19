import select
import os
import datetime
import string

from HTMLParser import HTMLParser

def read_forked_proc(p):
    webpage = None 
    stdout_fd = p.stdout.fileno()

    while p.poll() == None:
        fdtuple = select.select([stdout_fd], [], [])

        if len(fdtuple[0]) >  0:
            txt = p.stdout.read()
            if txt != None and len(txt) > 0:
                if webpage == None:
                    webpage = txt
                else:
                    webpage += txt

    txt = p.stdout.read()
    if txt != None and len(txt) > 0:
        if webpage == None:
            webpage = txt
        else:
            webpage += txt

    return webpage

def mk_dir(dirname):
    if not os.path.exists(dirname):
        os.mkdir(dirname)

def pad_zero(t):
    if t < 10:
        tstr = '0%d' % t
    else:
        tstr = '%d' % t

    return tstr

def dateobj_to_str(dateobj, sep):
    return '%s%s%s%s%s' % (pad_zero(dateobj.day), sep, \
            pad_zero(dateobj.month), sep, pad_zero(dateobj.year))
  
class CourtParser(HTMLParser):
    def __init__(self):
       HTMLParser.__init__(self)
       self.links     = []
       self.link      = None
       self.linktitle = '' 

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr in attrs:
                if len(attr) > 1 and attr[0] == 'href':
                    self.link = attr[1]

    def handle_data(self, data):
        if self.link != None:
            self.linktitle += data

    def handle_endtag(self, tag):
        if tag == 'a':
            linktitle             =  string.strip(self.linktitle)
            self.links.append((linktitle, self.link))
            self.link             = None
            self.linktitle        = ''

class BaseCourt:
    def __init__(self, name, datadir, DEBUG):
        self.DEBUG       = DEBUG
        self.name        = name
        self.datadir     = datadir
        mk_dir(self.datadir)

        statdir          = '%s/stats' % datadir
        mk_dir(statdir)
        self.wgetlog     = '%s/stats/wgetlog' % datadir

    def sync(self, fromdate, todate):
        newdownloads = []
        dirname = os.path.join (self.datadir, self.name)
        mk_dir(dirname)

        while fromdate <= todate:
            dateobj   = fromdate.date()
            tmprel    = os.path.join (self.name, dateobj.__str__())
            datedir   = os.path.join (self.datadir, tmprel)
            mk_dir(datedir)
            dls = self.download_oneday(tmprel, dateobj)
            newdownloads.extend(dls)
            fromdate += datetime.timedelta(days=1)
        return newdownloads

