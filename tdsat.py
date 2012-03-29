import utils

from courtlisting import CourtListing

class Tdsat(CourtListing):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CourtListing.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.mainurls = [u'http://www.tdsat.nic.in/judgements.htm']

    def get_meta_info(self, tr):
        tds = tr.findAll('td')
        metainfo = {}
        link = tr.find('a')
        if link:
            href = link.get('href')
            if href:
                metainfo['href'] = href

        else:
            return metainfo

        valueList = []
        for td in tds:
            value = utils.get_tag_contents(td)
            valueList.append(value)

        i = 0
        for value in valueList:
            i += 1
            if value:
                value = value.strip()
                if (i == 2 or i == 3) and not metainfo.has_key(self.PETITIONER):
                    pet, res = utils.get_petitioner_respondent(value)
                    if pet:
                        metainfo[self.PETITIONER] = pet
                        metainfo[self.CASENO] = valueList[i-1]
                    if res:
                        metainfo[self.RESPONDENT] = res
                elif metainfo.has_key(self.PETITIONER):
                    dateobj = utils.datestr_to_obj(value)
                    if dateobj:
                        metainfo[self.DATE] = dateobj
      
        # try one more heuristics
        if not metainfo.has_key(self.DATE) and metainfo.has_key('href'): 
            dateobj = utils.datestr_to_obj(metainfo['href'])
            if dateobj:
                metainfo[self.DATE] = dateobj

        if not metainfo.has_key(self.DATE) and \
                not metainfo.has_key(self.PETITIONER):
            self.logger.info(u'No petitioner/date found: %s %s' % \
                              (metainfo, valueList))
        elif not metainfo.has_key(self.PETITIONER): 
            self.logger.info(u'No petitioner found: %s %s' % \
                                 (metainfo, valueList))
        elif not metainfo.has_key(self.DATE): 
            self.logger.info(u'No date found: %s %s' % \
                                 (metainfo, valueList))

        return metainfo

    def download_info_page(self, url):
        infolist = []
        webpage = self.download_url(url)
        if webpage:
            d = utils.parse_webpage(webpage)
            if not d:
                self.logger.error(u'Could not parse the date search page')
                return [], None
            tables = d.findAll('table')
            for table in tables:
                if not table.find('table'):
                    trs = table.findAll('tr')
                    for tr in trs:
                        metainfo = self.get_meta_info(tr)
                        if metainfo:
                            self.logger.debug('metainfo: %s' % metainfo)
                            infolist.append(metainfo)
        return infolist, None
