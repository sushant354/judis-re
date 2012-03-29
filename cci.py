from courtlisting import CourtListing
import utils
import urllib

class Cci(CourtListing):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CourtListing.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.mainurls = [ \
        u'http://www.cci.gov.in/index.php?option=com_content&task=view&id=150',
        u'http://www.cci.gov.in/index.php?option=com_content&task=view&id=171' \
        ]

    def get_meta_info(self, tr, baseurl):
        metainfo = {} 
        tds = tr.findAll('td')
        i = 0
        for td in tds:
            value = utils.get_tag_contents(td)
            i += 1
            if value:
                if i == 1:
                    metainfo[self.CASENO] = value
                elif i == 2:
                    pet, res = utils.get_petitioner_respondent(value)
                    if pet:
                        metainfo[self.PETITIONER] = pet
                    else:
                        metainfo[self.PETITIONER] = value

                    if res:
                        metainfo[self.RESPONDENT] = res 
                elif i == 3 or i == 4:
                   dateobj = utils.datestr_to_obj(value)
                   if dateobj:
                       metainfo[self.DATE] = dateobj

        if not metainfo.has_key(self.DATE):
            self.logger.info(u'No date found %s' % metainfo)

        ms = []
        if metainfo:
            self.logger.debug(u'metainfo: %s' % metainfo)
            links = tr.findAll('a')
            for link in links:
                href = link.get('href')
                if href:
                    m = metainfo.copy()
                    m['href'] = href
                    m['url']  =  urllib.basejoin(baseurl, href)
                    ms.append(m)
        return ms

    def download_info_page(self, url):
        webpage = self.download_url(url)
        dls = [] 
        if webpage:
            d = utils.parse_webpage(webpage)
            if not d:
                self.logger.error(u'Could not parse the date search page')
                return [], None

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
                    metainfos = self.get_meta_info(tr, url)
                    if metainfos:
                        dls.extend(metainfos)
        return dls, None
               
