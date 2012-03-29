import utils
import tempfile
import urllib
import re
import os

class Allahabad(utils.BaseCourt):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        utils.BaseCourt.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.baseurl = 'http://elegalix.allahabadhighcourt.in'
        self.dateurl = urllib.basejoin(self.baseurl, '/elegalix/WebStartJudgmentDateSearch.do')
        self.cookiefile  = tempfile.NamedTemporaryFile()

    def post_data(self, parsedD, dateobj):
        postdata = [('highCourtBenchCode', 'X'), \
                    ('fromDay', '%d' % dateobj.day), \
                    ('fromMonth', '%d' % dateobj.month), \
                    ('fromYear', '%d' % dateobj.year), \
                    ('toDay', '%d' % dateobj.day), \
                    ('toMonth', '%d' % dateobj.month), \
                    ('toYear', '%d' % dateobj.year) \
                   ]
        inputobjs = parsedD.findAll('input')
        for inputobj in inputobjs: 
            postdata.append((inputobj.name, inputobj.value))

        return postdata

    def parse_result_page(self, posturl, webpage, dateobj):
        judgments = []
        d = utils.parse_webpage(webpage)
        if not d:
            self.logger.error(u'Could not parse result page %s' % dateobj)
            return judgments

        # get judgments
        trs = d.findAll('tr')
        for tr in trs:
            judgment = {}
            metainfo = { 'date': utils.date_to_xml(dateobj)}

            links = tr.findAll('a')
            for link in links:
                href = link.get('href')
                if href and re.search('WebShowJudgment.do', href):
                    t = utils.get_tag_contents(link)
                    colon = t.find(':')
                    if colon:
                        title = t[colon+1:]
                        title = title.strip()
                        metainfo['title'] = title
                        reobj = re.search(' vs\. ', title, re.IGNORECASE)
                        if reobj:
                            metainfo['petitioner'] = title[:reobj.start()]
                            metainfo['respondent'] = title[reobj.end():]
                if href and re.search('WebDownloadJudgmentDocument.do', href):
                    judgment['link'] = urllib.basejoin(posturl, href)
 
            if judgment:
                judgment['metainfo'] = metainfo
                judgments.append(judgment)
        
        # next link
        links = d.findAll('a')
        for link in links: 
            t = utils.get_tag_contents(link)          
            if re.search('Next', t):
                href = link.get('href')
             
                if href:
                    judgment = {'link': urllib.basejoin(posturl, href)}
                    judgment['next'] = True
                   
                judgments.append(judgment)
 
        return judgments

    def download_oneday(self, relpath, dateobj):
        dls = []

        webpage = self.download_url(self.dateurl, savecookies = \
                                                      self.cookiefile.name)
        d = utils.parse_webpage(webpage)
        if not d:
            self.logger.error(u'Could not parse date search page')
            return dls 

        forms = d.findAll('form')
        action = None
        for form in forms:
            if form.get('name') == 'WebJudgmentDateSearchForm':
                action = form.get('action')
                break

        if not action:
            self.logger.error(u'Could not find date search form')
            return dls

        posturl  = urllib.basejoin(self.baseurl, action)
        postdata = self.post_data(d, dateobj)         

        webpage = self.download_url(posturl, postdata = postdata, \
                                    loadcookies = self.cookiefile.name)

        dls = self.dl_result_page(relpath, posturl, webpage, dateobj, {})

        return dls

    def dl_result_page(self, relpath, posturl, webpage, dateobj, recursed):
        dls = []
        judgments = self.parse_result_page(posturl, webpage, dateobj)

        for judgment in judgments:
            if judgment.has_key('next') and \
              not recursed.has_key(judgment['link']):
                self.logger.info(u'Recursing %s' % judgment['link'])
                recursed[judgment['link']] = 1
                webpage = self.download_url(judgment['link'], \
                                            loadcookies = self.cookiefile.name)
                dls.extend(self.dl_result_page(relpath, posturl, webpage, \
                                               dateobj, recursed))
            elif not judgment.has_key('next'):
                self.logger.info(u'Processing judgment %s' % judgment['link'])
                relurl = self.get_judgment(relpath, judgment)
                if relurl:
                    dls.append(relurl)
                else:
                    self.logger.warning(u'Did not download %s' % \
                                        judgment['link'])

        return dls
    
    def get_judgment(self, relpath, judgment):
        relurl = None
        reobj = re.search('judgmentID=(?P<id>\d+)', judgment['link'])

        if not reobj:
            self.logger.warning(u'No judgment id in %s' %  judgment['link'])
        else:
            judgmentId = reobj.groupdict()['id']
            relurl = os.path.join(relpath, judgmentId)
            filepath = os.path.join(self.rawdir, relurl)
            metapath = os.path.join(self.metadir, relurl)

            if not os.path.exists(filepath):
                pdfdoc = self.download_url(judgment['link'], \
                                           loadcookies = self.cookiefile.name)
                if pdfdoc:
                    utils.save_file(filepath, pdfdoc)
                    self.logger.info(u'Saved %s' % relurl)
                else:
                    self.logger.info(u'Did not download %s' % judgment['link'])

            if os.path.exists(filepath) and \
                    (self.updateMeta or not os.path.exists(metapath)):
                utils.print_tag_file(metapath, judgment['metainfo'])
                self.logger.info(u'Saved metainfo %s' % relurl)

            if not os.path.exists(filepath):
                relurl = None

        return relurl
