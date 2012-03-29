import re
import urllib

from courtlisting import CourtListing
import utils
class GreenTribunal(CourtListing):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CourtListing.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.mainurls = [u'http://www.greentribunal.in/judgement.php']

    def get_next_page(self, d, baseurl):
        nextPage = None
        for link in d.findAll('a'):
            value = utils.get_tag_contents(link)
            href = link.get('href')
            if href and value and re.search('\s*Next', value):
                nextPage = urllib.basejoin(baseurl, href) 

        return nextPage

    def get_meta_info(self, tr):
        metainfo = {}
        tds = tr.findAll('td')
       
        for link in tr.findAll('a'):
            href = link.get('href')
            if href:
                metainfo['href'] = href
                break
        if not metainfo.has_key('href'):
            return {}
        i = 0
        for td in tds:
            value = utils.get_tag_contents(td)
            if value:
                if i == 0:
                    metainfo[self.CASENO] = value
                elif i == 1:
                    pet, res = utils.get_petitioner_respondent(value)
                    if pet:
                        metainfo[self.PETITIONER] = pet
                    if res:
                        metainfo[self.RESPONDENT] = res
                elif i == 2:
                    dateobj = utils.datestr_to_obj(value)
                    if dateobj:
                        metainfo[self.DATE] = dateobj
                i += 1
        return metainfo
 
    def download_info_page(self, url):
        dls      = []
        nextPage = None
        webpage  = self.download_url(url)
        if webpage:
            d = utils.parse_webpage(webpage)
            if not d:
                self.logger.error(u'Could not parse the date search page')
                return [], None
            nextPage = self.get_next_page(d, url)
            maxtr = -1
            mainTable = None
            tables = d.findAll('table')
            for table in tables:
                numtrs = table.findAll('tr')
                if numtrs > maxtr:
                    mainTable = table
                    maxtr = numtrs

            if mainTable:
                trs = table.findAll('tr')
                for tr in trs:
                    metainfo = self.get_meta_info(tr)
                    if metainfo and metainfo.has_key(self.DATE):
                        self.logger.debug(u'metainfo: %s' % metainfo)
                        dls.append(metainfo)
            dls.sort(cmp = lambda x, y: cmp(x[self.DATE], y[self.DATE]), \
                     reverse= True)
        return dls, nextPage 
