import os
import re
import string
import tempfile

import utils

class SupremeCourt(utils.BaseCourt):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        utils.BaseCourt.__init__(self, name, rawdir, metadir, statsdir, updateMeta)

        self.cookiefile  = tempfile.NamedTemporaryFile()
        self.webformUrl  = 'http://judis.nic.in/supremecourt/Chrseq.aspx'
        self.dateqryUrl  = 'http://judis.nic.in/supremecourt/DateQry.aspx' 

        self.dataTypes = ['A']
        self.statevalNames = ['__VIEWSTATE']

    def date_postdata(self, dateobj, dataType):
        if dateobj.month < 10:
            mnth = '0%d' % dateobj.month
        else:
            mnth = '%d' % dateobj.month
	    
        if dateobj.day < 10:
            day = '0%d' % dateobj.day
        else:
            day = '%d' % dateobj.day

        postdata = self.state_data()
        postdata.extend(
                    [ ('ddlday1', day), ('ddlmonth1', mnth),\
                     ('ddlyear1', dateobj.year), ('ddlday2', day), \
                     ('ddlmonth2', mnth),('ddlyear2', dateobj.year),\
                     ('ddlreport', dataType), ('button', 'Submit')\
                    ])
        return postdata

    def download_oneday(self, relpath, dateobj):
        newdls = []
        for dataType in self.dataTypes:
            self.stateval   = self.get_stateval(self.dateqryUrl)

            if not self.stateval:
                self.logger.error(u'No stateval for date %s' % dateobj)

            postdata = self.date_postdata(dateobj, dataType)

            webpage  = self.download_webpage(postdata, self.dateqryUrl)
            newdls.extend(self.datequery_result(webpage, relpath, 1, dateobj))
        return newdls

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

    def save_meta_tags(self, metapath, judgedict, dateobj):
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
            bench = judgedict['bench'].split(',')
            if len(bench) > 0:
                benchdict = {}
                benchdict['name'] = []
                for judge in bench:
                    benchdict['name'].append(judge)
                tagdict['bench'] = benchdict
 
        tagdict['date'] = utils.date_to_xml(dateobj)

        utils.print_tag_file(metapath, tagdict) 

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
            self.logger.error(u'Could not parse html of the result page for date %s' % dateobj)
            return downloaded 

        stateval  = self.extract_state(d)
        if stateval != None and stateval != self.stateval:
            self.stateval = stateval
            self.logger.info(u'stateval changed')

        linkdict = self.extract_links(d, pagenum)

        for link in linkdict['docs']:
            if (not link.has_key('title')) or (not link.has_key('href')):
                continue

            self.logger.info(u'Processing link: %s href: %s' % \
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
                    self.logger.warning(u'Could not download %s' % \
                                         link['title'])

            if os.path.exists(rawpath) and not os.path.isdir(rawpath):
                if not os.path.exists(metapath) or self.updateMeta:
                    self.save_meta_tags(metapath, link, dateobj)
                downloaded.append(tmprel)
                  
        if linkdict.has_key('next'):
            link = linkdict['next']
            
            self.logger.info(u'Following page: %s href: %s' % \
                             (link['title'], link['href']))

            webpage = self.download_link(link)
            if webpage:
                nextdownloads = self.datequery_result(webpage, relpath, \
                                                      pagenum + 1, dateobj)
                downloaded.extend(nextdownloads)
            else:
                self.logger.warning(u'Could not download %s' % link['title'])

        return downloaded

    def extract_state(self, prsdobj):
        stateval = {} 
        inputs = prsdobj.findAll('input')
        for input in inputs:
            name = input.get('name')
            if name in self.statevalNames:
                stateval[name] = input.get('value')
        return stateval

    def state_data(self):
        t = []
        for name in self.statevalNames:
            if self.stateval.has_key(name):
                t.append((name, self.stateval[name]))
        return t


    def get_stateval(self, url):
        webpage = self.download_url(url, \
                                    savecookies = self.cookiefile.name)

        d = utils.parse_webpage(webpage)
        if d:
            return self.extract_state(d)
        else:
            return None

    def download_webpage(self, postdata, posturl):
        webpage = self.download_url(posturl, postdata = postdata, \
                                    loadcookies = self.cookiefile.name)
        return webpage 

    def parse_link(self, linkname):
       linkRe = "javascript:__doPostBack\('(?P<event_target>[^']+)','(?P<event_arg>[^']*)'\)"
       return re.search(linkRe, linkname)

    def download_link(self, link):
        linkinfo = self.parse_link(link['href'])
        if linkinfo == None:
            self.logger.warning(u'Values not in %s. title is %s' % \
                                 (link['href'], link['title']))
            return None

        eventTarget =string.join(linkinfo.group('event_target').split('$'), ':')
        postdata = self.state_data() 
        postdata.extend([('__EVENTTARGET', eventTarget), \
                        ('__EVENTARGUMENT', linkinfo.group('event_arg'))])

        return self.download_webpage(postdata, self.webformUrl)

