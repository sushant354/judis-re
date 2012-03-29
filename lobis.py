import urllib
import tempfile
import re
import os

import utils

class Lobis(utils.BaseCourt):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        utils.BaseCourt.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.cookiefile  = tempfile.NamedTemporaryFile()

    def get_cookies(self):
        self.download_url(self.cookieurl, savecookies = self.cookiefile.name)

    def date_in_form(self, dateobj):
        return [('jday',   utils.pad_zero(dateobj.day)), \
                ('jmonth', utils.pad_zero(dateobj.month)), \
                ('jyear',  utils.pad_zero(dateobj.year)) \
               ]

    def download_oneday(self, relpath, dateobj):
        self.get_cookies()
        postdata = self.date_in_form(dateobj) 
        postdata.append(('Submit', 'Submit'))

        webpage = self.download_url(self.dateurl, postdata = postdata, \
                                    savecookies = self.cookiefile.name)
        return self.result_page(webpage, relpath, dateobj)

    def get_judgment(self, link, filepath):
        url = urllib.basejoin(self.courturl, link)
        self.logger.info(u'Downloading link %s' % url) 
        webpage = self.download_url(url, loadcookies = self.cookiefile.name)
        if webpage:
            utils.save_file(filepath, webpage)
            return True
        else:    
            return False

    def parse_meta_info(self, tr, dateobj):
        metainfo = { 'date': utils.date_to_xml(dateobj)}

        i = 0
        for td in tr.findAll('td'):
            contents = utils.get_tag_contents(td)
            if i == 1:
                metainfo['caseno'] = contents
            elif i == 3:
                reobj = re.search(' vs\.? ', contents, re.IGNORECASE)
                if reobj:
                    metainfo['petitioner'] = contents[:reobj.start()]
                    metainfo['respondent'] = contents[reobj.end():]
            elif i == 4:
                reobj = re.search('JUSTICE ', contents)
                if reobj:
                    metainfo['author'] = contents[reobj.end():]             
                
            i += 1
        return metainfo

    def handle_judgment_link(self, relpath, tr, dateobj, href, title):
        tmprel   = os.path.join(relpath, re.sub('/', '-', title))
        filepath = os.path.join(self.rawdir, tmprel)

        if not os.path.exists(filepath):
            self.get_judgment(href, filepath)

        if os.path.exists(filepath):
            metapath = os.path.join(self.metadir, tmprel)
            metainfo = self.parse_meta_info(tr, dateobj)
            if metainfo and (self.updateMeta or not os.path.exists(metapath)):
                utils.print_tag_file(metapath, metainfo)
            return tmprel
        else:
            return None

    def result_page(self, webpage, relpath, dateobj):
        newdls      = []

        if not webpage:
            return newdls

        d = utils.parse_webpage(webpage)

        if not d:
            self.logger.error(u'Could not parse html of the result page for date %s' % dateobj)
            return newdls

        trs = d.findAll('tr')

        for tr in trs:
            link  = tr.find('a')

            if not link:
                continue

            href  = link.get('href')
            title = utils.get_tag_contents(link)

            if (not href) or (not title):
                self.logger.info(u'Could not process %s' % link)
                continue

            if not re.match('\d+$', title) and not re.search('PREV|NEXT',title):
                self.logger.info(u'link: %s title: %s' % (href, title))
                rel = self.handle_judgment_link(relpath, tr, dateobj, href, title)
                if rel:
                    newdls.append(rel)

        if newdls:
            links  = d.findAll('a')
            for link in links:
                href  = link.get('href')
                title = utils.get_tag_contents(link)
                if title and href and re.match('NEXT', title):
                   self.logger.info(u'Following next page link: %s' % link)
                   webpage = self.download_url(urllib.basejoin(self.baseurl,href),\
                                               loadcookies = self.cookiefile.name)

                   newdls.extend(self.result_page(webpage, relpath, dateobj))
        return newdls
