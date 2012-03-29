import re
import datetime 
import urllib
import os

import utils
from courtlisting import CourtListing

class Aptel(CourtListing):

    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CourtListing.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.mainurls = [u'http://aptel.gov.in/judgementnew.html']

    def get_meta_info(self, tr):
        metainfo = {}
        tds = tr.findAll('td')

        i = 0
        lastcolumn = len(tds) - 1
        for td in tds:
            content = utils.get_tag_contents(td)
            if content:
                if i == 1:
                    content = u' '.join(content.split())
                    metainfo['caseno'] = content
                elif i == 2:
                    petitioner, respondent = \
                            utils.get_petitioner_respondent(content)
                    if petitioner:
                        metainfo['petitioner'] = petitioner
                    else:
                        self.logger.info(u'Petitioner not found in %s' % content)
                    if respondent:
                        metainfo['respondent'] = respondent 
                elif i == lastcolumn:
                    dateobj = utils.datestr_to_obj(content)
                    if dateobj:
                       metainfo[self.DATE] = dateobj
                    else:
                        self.logger.info(u'No date in %s' % (content))
                i += 1
        return metainfo

    def download_info_page(self, url):
        webpage = self.download_url(url)
        d = utils.parse_webpage(webpage)
        if not d:
            self.logger.error(u'Could not parse the date search page')
            return [], None

        links = d.findAll('a')
        infolist = []
        previousurl = None
        for link in links:
            href = link.get('href')

            if previousurl == None and href:
                anchortext = utils.get_tag_contents(link)
                if anchortext and re.search('Previous >>', anchortext):
                    previousurl = urllib.basejoin(url, href)

            if href:
                 if re.match('judgements', href):
                     node = link 
                     while node.name != 'tr':
                         node = node.parent
                     if node:
                        metainfo = self.get_meta_info(node)
                        metainfo['href'] = href
                        infolist.append(metainfo)
                        self.logger.debug('metainfo: %s' % metainfo)

        return infolist, previousurl
