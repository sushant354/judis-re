import os
import re
import subprocess
import urllib
import string
import tempfile

import utils

class SupremeCourt(utils.BaseCourt):
    def __init__(self, name, rawdir, metadir, logger):
        utils.BaseCourt.__init__(self, name, rawdir, metadir, logger)

        self.cookiefile  = tempfile.NamedTemporaryFile()
        self.webformUrl  = 'http://judis.nic.in/supremecourt/Chrseq.aspx'
        self.dateqryUrl  = 'http://judis.nic.in/supremecourt/DateQry.aspx' 


    def download_oneday(self, relpath, dateobj):
        self.stateval   = self.get_stateval()

        if not self.stateval:
            self.log_debug(self.logger.ERR, 'No stateval for date %s' % dateobj)
            return []

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
                     ('ddlyear1', dateobj.year), ('ddlday2', day), \
                     ('ddlmonth2', mnth),('ddlyear2', dateobj.year),\
                     ('ddlreport', 'A'), ('button', 'Submit')\
                    ]

        webpage  = self.download_webpage(postdata, self.dateqryUrl)
        return self.datequery_result(webpage, relpath, 1, dateobj)

    def extract_links(self, prsdobj, pagenum):
        linkdict = {'docs': []}
 
        trs =  prsdobj.findAll('tr')
        for tr in trs:
            pageblock, nextlink = utils.check_next_page(tr, pagenum)
            if nextlink:
                linkdict['next'] = nextlink
            elif not pageblock:
                link = self.get_judgment_info(tr)
                if link:
                    linkdict['docs'].append(link)

        return linkdict

    def get_meta_tags(self, judgedict, dateobj):
        tagdict  = {}

        if judgedict.has_key('title'):
            title = judgedict['title']
            tagdict['title'] = title
  
            reobj = re.search('( vs | vs\.)', title, re.IGNORECASE)
            if reobj:
                if reobj.start() > 1:
                    petitioner = title[:reobj.start()]
                    tagdict['petitioner'] = petitioner

                if reobj.end() + 1 < len(title):
                    respondent = title[reobj.end() + 1:]
                    tagdict['respondent'] = respondent

        if judgedict.has_key('bench'):
            bench = string.split(judgedict['bench'], ',')
            if len(bench) > 0:
                benchdict = {}
                benchdict['name'] = []
                for judge in bench:
                    benchdict['name'].append(judge)
                tagdict['bench'] = benchdict 
        if dateobj:
            tagdict['date'] = utils.date_to_xml(dateobj)

        return utils.obj_to_xml('document', tagdict) 

    def get_judgment_info(self, tr):
        judgedict = {}
        link = tr.find('a') 
        if link:
            title = utils.get_tag_contents(link)
            href  = link.get('href')
            if title:
                judgedict['title'] = title

            if href:
                judgedict['href']  = href

        tds = tr.findAll('td')
        for td in tds:
            txt = utils.get_tag_contents(td)
            reobj = re.search('Coram\s*:', txt)
            if reobj and reobj.end() + 1 < len(txt):
                bench = txt[reobj.end() + 1:]
                judgedict['bench'] = bench
        return judgedict


    def datequery_result(self, webpage, relpath, pagenum, dateobj):
        downloaded = []

        d = utils.parse_webpage(webpage)

        if not d:
            self.log_debug(self.logger.ERR, 'Could not parse html of the result page for date %s' % dateobj)
            return newdls

        stateval  = self.extract_state(d)
        if stateval != None and stateval != self.stateval:
            self.stateval = stateval
            self.log_debug(self.logger.NOTE, 'stateval changed')

        linkdict = self.extract_links(d, pagenum)

        for link in linkdict['docs']:
            self.log_debug(self.logger.NOTE, 'Processing link: %s href: %s' % \
                                      (link['title'], link['href']))

            filename = re.sub('/', '|', link['title'])
            filename = re.sub("'", ' ', filename)
            tmprel   = os.path.join (relpath, filename)
            rawpath  = os.path.join (self.rawdir, tmprel)
            metapath = os.path.join (self.metadir, tmprel)

            if not os.path.exists(rawpath):
                webpage = self.download_link(link)
                if webpage:
                    utils.save_file(rawpath, webpage)
                else:
                    self.log_debug(self.logger.WARN, 'Could not download %s' % \
                                                                  link['title'])

            if os.path.exists(rawpath) and not os.path.isdir(rawpath):
                if not os.path.exists(metapath):
                    tags = self.get_meta_tags(link, dateobj)
                    utils.save_file(metapath, tags)
                downloaded.append(tmprel)
                  
        if linkdict.has_key('next'):
            link = linkdict['next']
            
            self.log_debug(self.logger.NOTE, 'Following page: %s href: %s' % \
                                      (link['title'], link['href']))

            webpage = self.download_link(link)
            if webpage:
                nextdownloads = self.datequery_result(webpage, relpath, \
                                                      pagenum + 1, dateobj)
                downloaded.extend(nextdownloads)
            else:
                self.log_debug(self.logger.WARN, 'Could not download %s'%link['title'])

        return downloaded

    def extract_state(self, prsdobj):
        stateval = None
        inputs = prsdobj.findAll('input')
        for input in inputs:
            name = input.get('name')
            if name == '__VIEWSTATE':
                stateval = input.get('value')
        return stateval

    def get_stateval(self):
        dateurl = 'http://judis.nic.in/supremecourt/DateQry.aspx'
        webpage = self.download_url(dateurl, \
                                      savecookies = self.cookiefile.name)

        d = utils.parse_webpage(webpage)
        if d:
            return self.extract_state(d)
        else:
            return None

    def download_webpage(self, postdata, posturl):
        encodedData  = urllib.urlencode(postdata)

        argList = [\
                   '/usr/bin/wget', '--output-document', '-', \
                   '--tries=%d' % self.maxretries, \
                   '-a', self.wgetlog, \
                   '--load-cookies', self.cookiefile.name,  '--post-data', \
                   "'%s'" % encodedData, posturl \
                  ]
        command = string.join(argList, ' ')

        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        return p.communicate()[0] 

    def parse_link(self, linkname):
       linkRe = "javascript:__doPostBack\('(?P<event_target>[^']+)','(?P<event_arg>[^']*)'\)"
       return re.search(linkRe, linkname)

    def download_link(self, link):
        linkinfo = self.parse_link(link['href'])
        if linkinfo == None:
            self.log_debug(self.logger.WARN, 'Values not in %s. title is %s' % \
                                      (link['href'], link['title']))
            return None

        eventTarget =string.join(linkinfo.group('event_target').split('$'), ':')
        postdata = [('__VIEWSTATE',     self.stateval), \
                    ('__EVENTTARGET', eventTarget), \
                    ('__EVENTARGUMENT', linkinfo.group('event_arg'))]

        return self.download_webpage(postdata, self.webformUrl)

