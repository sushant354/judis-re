import tempfile
import re
import os
import urllib
import urlparse
import string

import utils

class Courtnic(utils.BaseCourt):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        utils.BaseCourt.__init__(self, name, rawdir, metadir, statsdir, updateMeta)

        self.baseurl    = 'http://courtnic.nic.in/'
        self.cookiefile = tempfile.NamedTemporaryFile()        

    def set_cookie(self):
    	self.download_url(self.cookieurl, savecookies = self.cookiefile.name)

    def download_oneday(self, relpath, dateobj):
        dateurl = self.get_date_url(dateobj)
        return self.result_url(dateurl, relpath, ['1'], dateobj)

    def get_judgment(self, url, relpath, metainfo):
        filename = utils.url_to_filename(url, False, ['yID', 'nID', 'ID'])
        if not filename:
            self.logger.warning(u'No filename for %s' % url)
            return 

        rel = os.path.join(relpath, filename)
        filepath = os.path.join(self.rawdir, rel)

        if  os.path.exists(filepath):
            self.logger.info(u'Already exists %s' % filepath)
        else:
            self.logger.info(u'Downloading %s' % url)
            webpage = self.download_url(url, loadcookies = self.cookiefile.name)
            if not webpage:
                self.logger.warning(u'Could not download %s' % url)
                return 

            utils.save_file(filepath, webpage)
            self.logger.info(u'Saved %s' % filepath)

        if  os.path.exists(filepath):
            metapath = os.path.join(self.metadir, rel)
            if metainfo and (self.updateMeta or not os.path.exists(metapath)):
                utils.print_tag_file(metapath, metainfo)

        return rel

    def find_page(self, url):
        htuple = urlparse.urlparse(url)
        query  = htuple[4]
        if query:
            qs = string.split(htuple[4], '&')
            for q in qs:
                x = string.split(q, '=')
                if x[0] == 'page':
                    return x[1]

        return None

    def get_meta_info(self, tds, dateobj):
        metainfo = {'date': utils.date_to_xml(dateobj) }

        if len(tds) > 0 and len(tds[0].contents) >= 3:
            metainfo['caseno'] = tds[0].contents[0].encode('ascii', 'ignore')

            title = tds[0].contents[2].encode('ascii', 'ignore')
            petitioner, respondent = utils.get_petitioner_respondent(title)

            if petitioner:
                metainfo['petitioner'] = petitioner
            if respondent:
                metainfo['respondent'] = respondent

        return metainfo

    def result_url(self, url, relpath, pagelist, dateobj):
        newdls = []
        webpage = self.download_url(url, loadcookies = self.cookiefile.name)
        if not webpage:
            self.logger.warning(u'Could not download %s' % url)
            return newdls

        webpage = re.sub('""', '"', webpage)
        startobj = re.search('<table', webpage)
        endobj   = re.search('</table>', webpage)
        if not startobj or not endobj or startobj.start() >= endobj.end():
            self.logger.warning(u'No table found')
            return newdls
    
        d = utils.parse_webpage(webpage[startobj.start():endobj.end()])

        if not d:
            self.logger.error(u'Could not parse html of the result page for url %s' % url)
            return newdls

        trs = d.findAll('tr')
        for tr in trs:
            tds = tr.findAll('td')
            links = tr.findAll('a')
            metainfo = self.get_meta_info(tds, dateobj)

            for link in links:
                relurl = link.get('href')
                if not relurl:
                    self.logger.warning(u'No href in %s' % link)
                    continue

                action = self.action_on_url(relurl)
                self.logger.info(u'Action %s on %s' % (action, relurl))

                if action == 'ignore':
                    continue

                url = urllib.basejoin(self.courturl, relurl)

                if action == 'save':
                    rel = self.get_judgment(url, relpath, metainfo)
                    if rel:
                       newdls.append(rel)

                elif action == 'recurse':
                    page = self.find_page(url)
                    if page and (page not in pagelist):
                        self.logger.info(u'recursing %s' % url)
                        pagelist.append(page)
                        newdls.extend(self.result_url(url, relpath, pagelist, \
                                                      dateobj))
                    else:
                        self.logger.info(u'Not recursing %s' % url)

        return newdls    
          
