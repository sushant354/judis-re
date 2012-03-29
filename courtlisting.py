import os
import urllib
import re

import utils

class CourtListing(utils.BaseCourt):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        utils.BaseCourt.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.mainurls = []

    def download_info_page(self, url):
        return [], None

    def sync(self, fromdate, todate):
        dirname = os.path.join (self.rawdir, self.name)
        utils.mk_dir(dirname)

        dirname = os.path.join (self.metadir, self.name)
        utils.mk_dir(dirname)

        dls = []

        for mainurl in self.mainurls:
            while 1:
                infolist, nexturl = self.download_info_page(mainurl)
                finished, newdls = self.process_infolist(mainurl, infolist, \
                                                         fromdate, todate)
                dls.extend(newdls)
                if finished or nexturl == None:
                    break
                self.logger.info(u'Going to the next page: %s' % nexturl)
                mainurl = nexturl
        return dls

    def download_doc(self, baseurl, info, relpath):
        judgeurl =  urllib.basejoin(baseurl, info['href'])
        filename = info['href'].split('/')[-1]
        
        filename = u' '.join(filename.split())
        filename = re.sub('/|&|\(|\)', '-', filename)
        relurl = os.path.join(relpath, filename)
        info['date'] = utils.date_to_xml(info['date'])
        return self.save_judgment(relurl, judgeurl, info)

    def process_infolist(self, baseurl, infolist, fromdate, todate):
        newdls = []
        found = False
        finished = False
        for info in infolist: 
            if info.has_key(self.DATE):
                dateobj = info[self.DATE]
                if dateobj >= fromdate and dateobj <= todate:
                    found = True
                    datestr = dateobj.date().__str__()
                    tmprel = os.path.join (self.name, datestr)

                    rawdatedir   = os.path.join (self.rawdir, tmprel)
                    utils.mk_dir(rawdatedir)

                    metadatedir = os.path.join (self.metadir, tmprel)
                    utils.mk_dir(metadatedir)

                    relurl = self.download_doc(baseurl, info, tmprel)
                    if relurl:
                        newdls.append(relurl)
                elif found:
                    finished = True
        if not finished or not found:
            return False, newdls
        else:
            return True, newdls
