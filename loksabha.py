import os
import re
import urllib
import datetime

import supremecourt
import utils

class LokSabhaUrl:
    def __init__(self):
        baseurl = 'http://164.100.47.132/LssNew/psearch/'
        date2num = {\
            (datetime.date(1998, 03, 23),      \
             datetime.date(1999, 04, 24)): 12, \
            (datetime.date(1999, 10, 20),      \
             datetime.date(2004, 02, 05)): 13, \
            (datetime.date(2004, 06, 02),      \
             datetime.date(2009, 02, 26)): 14, \
            (datetime.date(2009, 06, 01),      \
             datetime.date(2014, 06, 01)): 15, \
          }
        num2webform = { 12: 'DebateAdvSearch12.aspx', \
                        13: 'DebateAdvSearch13.aspx', \
                        14: 'DebateAdvSearch14.aspx', \
                        15: 'DebateAdvSearch15.aspx', \
                      }

        num2dateqry = { 12: 'DebateAdvSearch12.aspx', \
                        13: 'DebateAdvSearch13.aspx', \
                        14: 'DebateAdvSearch14.aspx', \
                        15: 'DebateAdvSearch15.aspx', \
                      }
        self.webformUrls = {}
        for k in date2num.keys():
            self.webformUrls[k] = urllib.basejoin(baseurl, \
                                                  num2webform[date2num[k]]) 
        self.dateqryUrls = {}
        for k in date2num.keys():
            self.dateqryUrls[k] = urllib.basejoin(baseurl, \
                                                  num2dateqry[date2num[k]]) 
    def get_webform_url(self, dateobj):
        return self.get_url(self.webformUrls, dateobj)

    def get_dateqry_url(self, dateobj):
        return self.get_url(self.dateqryUrls, dateobj)

    def get_url(self, urls, dateobj):
        for k in urls.keys():
            if k[0] <= dateobj and dateobj <= k[1]:
                return urls[k]
        return None

class LokSabha(supremecourt.SupremeCourt):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        supremecourt.SupremeCourt.__init__(self, name, rawdir, \
                                           metadir, statsdir, updateMeta)

        self.urlobj = LokSabhaUrl()

        self.statevalNames = ['__VIEWSTATE', '__EVENTVALIDATION']
 
        patterndict = {'title': 'Title', 'debatetype': 'Type', \
                       'participants': 'Participants'}
        self.reobjs = {}
        for k in patterndict.keys():
            self.reobjs[k] = re.compile(patterndict[k])

    def date_postdata(self, dateobj):
        currentDate = utils.dateobj_to_str(dateobj, '-')

        postdata = [('__EVENTTARGET', ''), ('__EVENTARGUMENT', '')] 
        postdata.extend(self.state_data())

        otherdata = [\
          ('ctl00$ContPlaceHolderMain$TextBox1',   ''), \
          ('ctl00$ContPlaceHolderMain$search1',    'search'), \
          ('ctl00$ContPlaceHolderMain$btn', 'allwordbtn'), \
          ('ctl00$ContPlaceHolderMain$btn1',       'textbtn'), \
          ('ctl00$ContPlaceHolderMain$ddlmember','--- Select Member Name ---'),\
          ('ctl00$ContPlaceHolderMain$ddldebtype','--- Select Debate Type ---'),\
          ('ctl00$ContPlaceHolderMain$ddlsession', '--- Select Session ---'), \
        ]
        postdata.extend(otherdata)
        postdata.append(('ctl00$ContPlaceHolderMain$ddldatefrom', currentDate))
        postdata.append(('ctl00$ContPlaceHolderMain$ddldateto', currentDate))
        return postdata

    def download_oneday(self, relpath, dateobj):
        self.logger.info(u'Date %s' % dateobj)
        dateqryUrl = self.urlobj.get_dateqry_url(dateobj)

        if not dateqryUrl:
            self.logger.warning(u'No url for date %s' % dateobj)
            return []

        self.stateval    = self.get_stateval(dateqryUrl)
        if not self.stateval:
            self.logger.error(u'No stateval for date %s' % dateobj)

        postdata = self.date_postdata(dateobj)

        webpage  = self.download_webpage(postdata, dateqryUrl)

        newdls = self.datequery_result(dateqryUrl, webpage, relpath, dateobj, 1)
        if not newdls:
            self.logger.info(u'No downloads for date %s' % dateobj)
        return newdls

    def get_next_page(self, d, dateqryUrl, currentpage):
        nextpage = None
        links = d.findAll('a')
        for link in links:
            idattr = link.get('id')
            if idattr == 'ctl00_ContPlaceHolderMain_cmdNext':
                postdata = [\
                    ('__EVENTTARGET', 'ctl00$ContPlaceHolderMain$cmdNext'), \
                    ('__EVENTARGUMENT', '') \
                          ]
                postdata.extend(self.state_data())
                postdata.append(('ctl00$ContPlaceHolderMain$txtpage', \
                                 '%d' % currentpage))
                nextpage  = self.download_webpage(postdata, dateqryUrl)
        return nextpage

    def datequery_result(self, dateqryUrl, webpage, relpath, \
                         dateobj, currentpage):
        newdls = []

        d = utils.parse_webpage(webpage)

        if not d:
            self.logger.error(u'Could not parse html of the result page for date %s' % dateobj)
            return newdls

        stateval  = self.extract_state(d)
        if stateval != None and stateval != self.stateval:
            self.stateval = stateval
            self.logger.info(u'stateval changed')

        docs = self.extract_docs(d)
  
        for doc in docs:
            if doc.has_key('href'):
                href = doc['href']
                reobj = re.search('\d+$', href)
                if reobj:
                    filename = href[reobj.start():reobj.end()]
                    dlurl    = urllib.basejoin(dateqryUrl, href)
                    rel      = os.path.join (relpath, filename)
                    success  = self.download_debate(rel, dlurl, doc, dateobj)
                    if success:
                        newdls.append(rel)

        nextpage = self.get_next_page(d, dateqryUrl, currentpage)
        if nextpage:
            newdls.extend(self.datequery_result(dateqryUrl, nextpage, relpath, \
                                                dateobj, currentpage + 1))

        return newdls          

    def download_debate(self, rel, dlurl, doc, dateobj):
        rawpath  = os.path.join (self.rawdir, rel)
        metapath = os.path.join (self.metadir, rel)

        if os.path.exists(rawpath):
            return True
        else:
            webpage = self.download_url(dlurl)
            if webpage:
                utils.save_file(rawpath, webpage)
                self.logger.info(u'Saved %s' % rawpath)
                if os.path.exists(rawpath) and (self.updateMeta or not os.path.exists(metapath)):
                    self.save_meta_tags(metapath, doc, dateobj)
                return True
            else:
                self.logger.warning(u'Could not download ' + dlurl) 
                  
        return False 

    def extract_docs(self, d):
        docs = []
        divs = d.findAll('div')
        for div in divs:
            idvalue = div.get('id')
            if idvalue == 'ctl00_ContPlaceHolderMain_Panel2':
                tables = div.findAll('table')
                for table in tables:
                    doc = self.get_debate_info(table) 
                    docs.append(doc) 
        return docs

    def get_headline_type(self, headline):
        for k in self.reobjs.keys():
            if self.reobjs[k].search(headline):
                return k
        return None

    def get_link(self, td):
        href = None
        link = td.find('a')
        if link:
            href = link.get('href')
        return href
 
    def get_debate_info(self, table):
        info = {}
        trs = table.findAll('tr')
        for tr in trs:
            tds = tr.findAll('td')
            if len(tds) == 2:
                hl     = utils.get_tag_contents(tds[0])
                value  = utils.get_tag_contents(tds[1])
                hltype = self.get_headline_type(hl)
                if hltype:
                    info[hltype] = value
                    if hltype == 'title':
                        href = self.get_link(tds[1])
                        if href:
                            info['href'] = href
        return info
                
    def save_meta_tags(self, metapath, debatedict, dateobj):
        tagdict = {'date': utils.date_to_xml(dateobj)}
        for k in debatedict.keys():
            if k not in ['href']:
                tagdict[k] = debatedict[k]    
        utils.print_tag_file(metapath, tagdict)
