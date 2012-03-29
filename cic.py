import tempfile
import urllib
import os

import utils

class CIC(utils.BaseCourt):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        utils.BaseCourt.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.baseurl = 'http://rti.india.gov.in'

        self.dateurl = urllib.basejoin(self.baseurl, \
                                       '/decision_categorywise.php')
        self.posturl = self.dateurl
        self.resulturl = urllib.basejoin(self.dateurl, \
                                         '/result_decision_categorywise.php')
        self.cookiefile  = tempfile.NamedTemporaryFile()

    def post_data(self, dateobj):
        postdata = [('user_id', ''), ('find_val', ''), \
                    ('cic_val', 'all'), ('val', 'CA'), \
                    ('fromday', utils.pad_zero(dateobj.day)), \
                    ('frommonth', utils.pad_zero(dateobj.month)), \
                    ('fromyear', dateobj.year), \
                    ('today', utils.pad_zero(dateobj.day)), \
                    ('tomonth', utils.pad_zero(dateobj.month)), \
                    ('toyear', dateobj.year), \
                    ('submit', 'Go') \
                   ]

        return postdata

    def get_meta_info(self, tr, dateobj):
        metainfo = { 'date': utils.date_to_xml(dateobj)}

        tds = tr.findAll('td')

        if len(tds) >= 3:
            metainfo['caseno'] = utils.get_tag_contents(tds[2])

        if len(tds) >= 4:
            metainfo['petitioner'] = utils.get_tag_contents(tds[3])

        if len(tds) >= 5:
            metainfo['respondent'] = utils.get_tag_contents(tds[4])

        return metainfo

    def dl_judgment(self, relpath, tr, link, dateobj):
        href = link.get('href')
        title = utils.get_tag_contents(link)
        relurl = None
        if href:
            metainfo = self.get_meta_info(tr, dateobj)
            if title:
                metainfo['caseno'] = title

            if metainfo.has_key('caseno'):
                relurl = metainfo['caseno'].replace('/', '-') 
                relurl = relurl.encode('ascii', 'ignore')
                relurl = os.path.join(relpath, relurl)
                relurl = self.save_judgment(relurl, \
                                         urllib.basejoin(self.posturl, href), \
                                         metainfo, \
                                         cookiefile = self.cookiefile.name)
            else:
                self.logger.warning(u'No casenum in %s' % tr)

        return relurl

    def download_oneday(self, relpath, dateobj): 
        self.download_url(self.dateurl, savecookies = self.cookiefile.name)
        resultpage = self.download_url(self.posturl, \
                                       postdata = self.post_data(dateobj), \
                                       loadcookies = self.cookiefile.name)

        return self.handle_result_page(resultpage, relpath, dateobj)
 
    def handle_result_page(self, resultpage, relpath, dateobj):
        dls = []
        d = utils.parse_webpage(resultpage)
        if not d:
            self.logger.error(u'Could not parse result page %s' % dateobj)

        # download judgments
        trs = d.findAll('tr')
        for tr in trs:
            links = tr.findAll('a')
            if len(links) == 1:
                relurl = self.dl_judgment(relpath, tr, links[0], dateobj)
                if relurl:
                    dls.append(relurl)
            else:
                self.logger.warning(u'No action for %s' % tr)

        # next page
        links = d.findAll('a')
        for link in links:
            href = link.get('href')
            t = utils.get_tag_contents(link)
            if href and t == 'Next':
                nexturl = urllib.basejoin(self.resulturl, href)  
                resultpage = self.download_url(nexturl, \
                                            loadcookies = self.cookiefile.name)
                if resultpage:
                    self.logger.info(u'Recursing  to %s' % nexturl)
                    dls.extend(self.handle_result_page(resultpage, relpath, \
                                                       dateobj))
        return dls  
