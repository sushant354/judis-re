import os
import datetime
import string
import sys
import urllib
import urlparse
import subprocess
import types
from xml.sax import saxutils
from xml.parsers.expat import ExpatError
from xml.dom import minidom, Node
import re
import tempfile
import logging
import codecs
import magic
import calendar

from HTMLParser import HTMLParser, HTMLParseError
from BeautifulSoup import BeautifulSoup, NavigableString, Tag

monthre = 'january|february|march|april|may|june|july|august|september|october|november|december|frbruary|februay'

descriptiveDateRe = re.compile('(?P<day>\d+)\s*(st|nd|rd|th)?\s*(?P<month>%s)[\s.,]+(?P<year>\d+)' % monthre, flags=re.IGNORECASE)

digitsDateRe  = re.compile('(?P<day>\d+)\s*[/. -]\s*(?P<month>\d+)\s*[/. -]\s*(?P<year>\d+)')

def month_to_num(month):
    count = 0
    month = month.lower()
    if month in ['frbruary', 'februay']:
        month = 'february'
    for mth in calendar.month_name:
        if mth.lower() == month:
            return count
        count += 1
    return None

def datestr_to_obj(text):
    text = text.encode('ascii', 'ignore')
    reobj = descriptiveDateRe.search(text)
    dateobj = None
    day = month = year = None
    if reobj:
        groups = reobj.groupdict()
        year = int(groups['year'])
        month = month_to_num(groups['month'])
        day = int(groups['day'])
    else:
        reobj = digitsDateRe.search(text)
        if reobj:
            groups = reobj.groupdict()
            year  = int(groups['year'])
            month = int(groups['month'])
            day   = int(groups['day'])
    if day and month and year:
        if year in [20111, 20141, 20110]:
            year = 2011
        try:
            dateobj = datetime.datetime(year, month, day)
        except ValueError:
            dateobj = None
    return dateobj
def parse_xml(xmlpage):
    try: 
        d = minidom.parseString(xmlpage)
    except ExpatError:
        d = None
    return d

def get_node_value(xmlNodes):
    value = [] 
    ignoreValues = ['\n']
    for node in xmlNodes:
        if node.nodeType == Node.TEXT_NODE:
            if node.data not in ignoreValues:
                value.append(node.data)
    return u''.join(value)


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
        d = BeautifulSoup(webpage, convertEntities=BeautifulSoup.HTML_ENTITIES)
        return d
    except:
        return None

def date_to_xml(dateobj):
    datedict =  {}
 
    datedict['day']   = dateobj.day
    datedict['month'] = dateobj.month
    datedict['year']  = dateobj.year

    return datedict

def print_tag_file(filepath, feature):
    filehandle = codecs.open(filepath, 'w', 'utf8')

    filehandle.write(u'<?xml version="1.0" encoding="utf-8"?>\n')
    filehandle.write(obj_to_xml('document', feature))

    filehandle.close()

def obj_to_xml(tagName, obj):
    if type(obj) in types.StringTypes:
        return get_xml_tag(tagName, obj)

    tags = ['<%s>' % tagName] 
    ks = obj.keys()
    ks.sort()
    for k in ks:
        newobj = obj[k]
        if type(newobj) == types.DictType:     
            tags.append(obj_to_xml(k, newobj))
        elif type(newobj) == types.ListType:
            for o in newobj:
               tags.append(obj_to_xml(k, o))
        else:
            tags.append(get_xml_tag(k, obj[k]))
    tags.append(u'</%s>' % tagName)
    xmltags =  u'\n'.join(tags)

    return xmltags

def get_xml_tag(tagName, tagValue, escape = True):
    if type(tagValue) == types.IntType:
        xmltag = u'<%s>%d</%s>' % (tagName, tagValue, tagName)
    elif type(tagValue) == types.FloatType:
        xmltag = u'<%s>%f</%s>' % (tagName, tagValue, tagName)
    else:
        if escape:
            tagValue = escape_xml(tagValue)

        xmltag = u'<%s>%s</%s>' % (tagName, tagValue, tagName)
    return xmltag 

def escape_xml(tagvalue):
    return saxutils.escape(tagvalue)

def url_to_filename(url, catchpath, catchquery):
    htuple = urlparse.urlparse(url)
    path   = htuple[2]

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
        elif type(content) == Tag:
            retval += ' ' + get_tag_contents(content)

    return retval

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

def get_petitioner_respondent(title):
    reobj = re.search(r'\b(vs|versus|v/s|v s)\b', title, re.IGNORECASE)
    petitioner = None
    respondent = None

    if reobj:
        if reobj.start() > 0:
            petitioner = title[:reobj.start()]
            petitioner = u' '.join(petitioner.split())
            petitioner = petitioner.strip('.,:')
        if reobj.end() < len(title) - 1:
            respondent = title[reobj.end():]
            respondent = u' '.join(respondent.split())
            respondent = respondent.strip('.,:')

    return petitioner, respondent

def save_file(filepath, buf):
    h = open(filepath, 'w')
    h.write(buf)
    h.close()
   
class BaseCourt:
    def __init__(self, name, rawdir, metadir, statdir, updateMeta):
        self.name        = name
        self.rawdir      = rawdir
        self.metadir     = metadir
        self.updateMeta  = updateMeta

        if self.name == 'judis.nic.in':
            loggername = 'supremecourt'
        else:
            loggername = self.name
    
        self.logger      = logging.getLogger(u'crawler.%s' % loggername)

        mk_dir(self.rawdir)
        mk_dir(self.metadir)

        self.maxretries  = 3

        self.wgetlog     = os.path.join(statdir, '%s-wget.log' % self.name)
        self.useragent   = 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.0.10) Gecko/2009051719 Gentoo Firefox/3.0.10'

        self.PETITIONER = 'petitioner'
        self.RESPONDENT = 'respondent'
        self.DATE       = 'date'
        self.CASENO     = 'caseno'

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

            self.logger.info(u'Date %s' % dateobj)

            dls = self.download_oneday(tmprel, dateobj)
            newdownloads.extend(dls)
            fromdate += datetime.timedelta(days=1)
        return newdownloads

    def download_url(self, url, loadcookies = None, savecookies = None, \
                     postdata = None, referer = None, stderr = None, \
                     srvresponse = None, encodepost= True, headers = None):
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
            if encodepost:
                encodedData = urllib.urlencode(postdata)
            else:
                encodedData = postdata
            if len(encodedData) > 100*1000:
                postfile = tempfile.NamedTemporaryFile()
                postfile.write(encodedData)
                postfile.flush()
                arglist.extend(['--post-file', postfile.name])
            else:
                arglist.extend(['--post-data', encodedData])

        if referer:
            arglist.extend(['--referer', referer])

        if self.logger.getEffectiveLevel() <= logging.DEBUG:
            arglist.append('--debug')

        if headers:
            for hdr in headers:
                arglist.append('--header')
                arglist.append(hdr)
        arglist.append(url)

        if stderr:
            p = subprocess.Popen(arglist, stdout = subprocess.PIPE, \
                                 stderr = subprocess.PIPE)
            our, err = p.communicate()
            return out, err
        else:
            p = subprocess.Popen(arglist, stdout = subprocess.PIPE)
            webpage = p.communicate()[0]
            return webpage

    def save_judgment(self, relurl, judgeurl, metainfo, cookiefile = None):
        filepath = os.path.join(self.rawdir, relurl)
        metapath = os.path.join(self.metadir, relurl)

        if not os.path.exists(filepath):
            if cookiefile:
                doc = self.download_url(judgeurl, \
                                        loadcookies = cookiefile)
            else:
                doc = self.download_url(judgeurl)
               
            if doc:
                save_file(filepath, doc)
                self.logger.info(u'Saved rawfile %s' % relurl)
 
        if metainfo and os.path.exists(filepath) and \
                (self.updateMeta or not os.path.exists(metapath)):
            print_tag_file(metapath, metainfo)
            self.logger.info(u'Saved metainfo %s' % relurl)

        if os.path.exists(filepath):
            return relurl
        else:
            return None

def get_file_type(filepath):
    m = magic.open(magic.MAGIC_MIME)
    #m = magic.open(magic.MIME_TYPE)
    m.load()
    mtype = m.file(filepath)
    m.close()

    return mtype

def get_buffer_type(buffer):
    m = magic.open(magic.MAGIC_MIME)
    #m = magic.open(magic.MIME_TYPE)
    m.load()
    mtype = m.buffer(buffer)
    m.close()

    return mtype
