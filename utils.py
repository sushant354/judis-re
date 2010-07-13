import select
import os
import datetime
import string
import sys
import urllib
import urlparse
import subprocess
import types
from xml.sax import saxutils
import re
import tempfile
import threading
import time

from HTMLParser import HTMLParser, HTMLParseError
from BeautifulSoup import BeautifulSoup, NavigableString

def check_next_page(tr, pagenum):
    links    = tr.findAll('a')

    if len(links) <= 0:
        return False, None

    for link in links:
        contents = get_tag_contents(link) 
        if not contents or not re.match('[\d.]+$', contents):
            return False, None

    pageblock = True
    nextlink  = None

    for link in links:
        contents = get_tag_contents(link)
        try:
            val = string.atoi(contents)
        except ValueError:
            continue

        if val == pagenum + 1 and link.get('href'):
            nextlink = {'href': link.get('href'), 'title': '%d' % val}
            break

    return pageblock, nextlink

def parse_webpage(webpage):
    try:
        d = BeautifulSoup(webpage)
        return d
    except:
        return None

def date_to_xml(dateobj):
    datedict =  {}
 
    datedict['day']   = dateobj.day
    datedict['month'] = dateobj.month
    datedict['year']  = dateobj.year

    return datedict

def obj_to_xml(tagName, obj):
    if type(obj) in types.StringTypes:
        return get_xml_tag(tagName, obj)

    xmltags = '<%s>\n' % tagName
    ks = obj.keys()
    ks.sort()
    for k in ks:
        if type(obj[k]) == types.DictType:
            xmltags += obj_to_xml(k, obj[k])
        elif type(obj[k]) == types.ListType:
            for o in obj[k]:
                xmltags += obj_to_xml(k, o)
        else:
            xmltags += get_xml_tag(k, obj[k])
    xmltags += '</%s>\n' % tagName
    return xmltags


t = "".join(map(chr, range(256)))
d = "".join(map(chr, range(0,31) + range(128,256)))

def remove_cntl_chars(tagValue):
    global t
    global d

    if type(tagValue) == types.UnicodeType:
        tagValue = tagValue.encode('ascii', 'ignore')

    return tagValue.translate(t, d)

def get_xml_tag(tagName, tagValue):
    if type(tagValue) == types.IntType:
        xmltag = '<%s>%d</%s>\n' % (tagName, tagValue, tagName)
    elif type(tagValue) == types.FloatType:
        xmltag = '<%s>%f</%s>\n' % (tagName, tagValue, tagName)
    else:
        tagValue = remove_cntl_chars(tagValue)
        xmltag = '<%s>%s</%s>\n' % (tagName, saxutils.escape(tagValue), tagName)

    return xmltag


def url_to_filename(url, catchpath, catchquery):
    htuple = urlparse.urlparse(url)
    path   = htuple[2]
    query  = htuple[4]

    words = []

    if catchpath:
        pathwords = string.split(path, '/')
        words.extend(pathwords)
    
    if catchquery:
        qs = string.split(htuple[4], '&')
        qdict = {}
        for q in qs:
            x = string.split(q, '=')
            if len(x) == 2:
                qdict[x[0]] = x[1]
        for q in catchquery:
            if qdict.has_key(q):
                words.append(qdict[q])

    if words:
        wordlist = []
        for word in words:
            word =  string.replace(word, '/', '_')
            wordlist.append(word)
        filename = string.join(wordlist, '_')
        return filename
    return None

def get_tag_contents(tag):
    retval = ''
    for content in tag.contents:
        if type(content) == NavigableString:
            retval += content
        else:
            retval += ' ' + get_tag_contents(content)

    return string.strip(retval)

def tag_contents_without_recurse(tag):
    contents = []
    for content in tag.contents:
        if type(content) == NavigableString:
            contents.append(content)

    return contents
 
def mk_dir(dirname):
    if not os.path.exists(dirname):
        os.mkdir(dirname)

def pad_zero(t):
    if t < 10:
        tstr = '0%d' % t
    else:
        tstr = '%d' % t

    return tstr

def dateobj_to_str(dateobj, sep, reverse = False):
    if reverse:
        return '%s%s%s%s%s' % (pad_zero(dateobj.year), sep, \
                pad_zero(dateobj.month), sep, pad_zero(dateobj.day))
    else:
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
 
    def feed_webpage(self, webpage):
        try:
            self.feed(webpage)
        except HTMLParseError, e:
            print >> sys.stderr, 'Malformed HTML: %s' % e
            return False

        return True


def save_file(filepath, buf):
    h = open(filepath, 'w')
    h.write(buf)
    h.close()

class Logger:
    def __init__(self, debuglevel, filename = None, newlog = False):
        self.debuglevel = debuglevel
        self.lock       = threading.Lock()
 
        if filename:
            if newlog:
                opt = 'w'
            else:
                opt = 'a'
            self.fhandle = open(filename, opt)
        else:
            self.fhandle = sys.stdout

        self.ERR, self.WARN, self.NOTE = range(3)

    def log(self, level, msg):
        if level <= self.debuglevel:
            secs = time.time()
            self.lock.acquire()
            self.fhandle.write('%s: %s\n' % (time.ctime(secs), msg))
            self.lock.release()
   
class BaseCourt:
    def __init__(self, name, rawdir, metadir, logger):
        self.logger      = logger
        self.name        = name
        self.rawdir      = rawdir
        self.metadir     = metadir

        mk_dir(self.rawdir)
        mk_dir(self.metadir)

        self.maxretries  = 3


        statdir          = '%s/stats' % rawdir
        mk_dir(statdir)
        self.wgetlog     = '%s/wgetlog' % statdir
        self.useragent   = 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.0.10) Gecko/2009051719 Gentoo Firefox/3.0.10'

    def sync(self, fromdate, todate):
        newdownloads = []
        dirname = os.path.join (self.rawdir, self.name)
        mk_dir(dirname)

        dirname = os.path.join (self.metadir, self.name)
        mk_dir(dirname)

        while fromdate <= todate:
            dateobj   = fromdate.date()
            tmprel    = os.path.join (self.name, dateobj.__str__())
            datedir   = os.path.join (self.rawdir, tmprel)
            mk_dir(datedir)

            datedir   = os.path.join (self.metadir, tmprel)
            mk_dir(datedir)

            self.log_debug(self.logger.NOTE, 'Date %s' % dateobj)

            dls = self.download_oneday(tmprel, dateobj)
            newdownloads.extend(dls)
            fromdate += datetime.timedelta(days=1)
        return newdownloads

    def download_url(self, url, loadcookies = None, savecookies = None, \
                     postdata = None, referer = None, stderr = None, \
                     srvresponse = None):
        arglist = [\
                   '/usr/bin/wget', '--output-document', '-', \
                   '--tries=%d' % self.maxretries, \
                   '--user-agent=%s' % self.useragent, \
                  ]

        if srvresponse:
            arglist.append('-S')

        if not stderr:
            arglist.extend(['-a', self.wgetlog])

        if loadcookies:
            arglist.extend(['--load-cookies', loadcookies])

        elif savecookies:
            arglist.extend(['--keep-session-cookies', \
                            '--save-cookies', savecookies]) 

        if postdata:
            encodedData = urllib.urlencode(postdata)
            if len(encodedData) > 100*1000:
                postfile = tempfile.NamedTemporaryFile()
                postfile.write(encodedData)
                postfile.flush()
                arglist.extend(['--post-file', postfile.name])
            else:
                arglist.extend(['--post-data', encodedData])

        if referer:
            arglist.extend(['--referer', referer])

        if self.logger.debuglevel >= self.logger.NOTE:
            arglist.append('--debug')

        arglist.append(url)

        if stderr:
            p = subprocess.Popen(arglist, stdout = subprocess.PIPE, \
                                 stderr = subprocess.PIPE)
            return p.communicate()
        else:
            p = subprocess.Popen(arglist, stdout = subprocess.PIPE)
            return p.communicate()[0]

    def save_judgment(self, relurl, judgeurl, metainfo):
        filepath = os.path.join(self.rawdir, relurl)
        metapath = os.path.join(self.metadir, relurl)

        if not os.path.exists(filepath):
            doc = self.download_url(judgeurl, \
                                    loadcookies = self.cookiefile.name)
            if doc:
                save_file(filepath, doc)
                self.log_debug(self.logger.NOTE, 'Saved rawfile %s' % relurl)
 
        if metainfo and os.path.exists(filepath) and \
          not os.path.exists(metapath):
            tags = obj_to_xml('document', metainfo)
            save_file(metapath, tags)
            self.log_debug(self.logger.NOTE, 'Saved metainfo %s' % relurl)

        if os.path.exists(filepath):
            return relurl
        else:
            return None

    def log_debug(self, level, s):
        msg = self.name
        if level == self.logger.ERR:
           msg += '-ERR'
        elif level == self.logger.WARN:
           msg += '-WARN'
        elif level == self.logger.NOTE:
           msg += '-NOTE'
        msg = '%s: %s' % (msg, s)
        self.logger.log(level, msg)
