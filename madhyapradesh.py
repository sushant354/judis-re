import utils
import tempfile
import urllib
import string
import os
import re

class MadhyaPradesh(utils.BaseCourt):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        utils.BaseCourt.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.cookiefile  = tempfile.NamedTemporaryFile()
        self.baseurl = 'http://ldemo.mp.nic.in'
        self.cookieurl = urllib.basejoin(self.baseurl, \
                                         'causelist/ciskiosk/ordermain.php')
        self.dateurl = urllib.basejoin(self.baseurl, \
                                '/causelist/ciskiosk/order_action.php?as9=ok3')

    def date_in_form(self, dateobj):
        return '%s/%s/%s' % (utils.pad_zero(dateobj.day), \
                             utils.pad_zero(dateobj.month), \
                             utils.pad_zero(dateobj.year)) 
               
    def get_cookies(self):
        self.download_url(self.cookieurl, savecookies = self.cookiefile.name)

    def get_meta_info(self, tr, dateobj):
        metainfo = { 'date': utils.date_to_xml(dateobj)}
        tds = tr.findAll('td')
        i = 0
        for td in tds:
            txt = utils.get_tag_contents(td)
            if txt:
                reobj = re.search(' vs ', txt, re.IGNORECASE)
                if reobj:
                    petitioner = string.strip(txt[:reobj.start()], ' \r\n-') 
                    respondent = string.strip(txt[reobj.end():], ' \r\n-')
                    if petitioner:
                        metainfo['petitioner'] = petitioner
                    if respondent:
                        metainfo['respondent'] = respondent
                elif i == 2:
                    metainfo['caseno'] = txt
                i += 1
 
        return metainfo

    def download_judgment(self, link, filepath):
        url = urllib.basejoin(self.dateurl, link)
        self.logger.info(u'Downloading link %s' % url)
        webpage = self.download_url(url, loadcookies = self.cookiefile.name)
        if webpage:
            utils.save_file(filepath, webpage)
            return True
        else:
            return False

    def handle_judgment_link(self, relpath, dateobj, tr):
        links = tr.findAll('a')
        if len(links) >= 1:
            href = links[-1].get('href')
        else:
            return None

        metainfo = self.get_meta_info(tr, dateobj)
        rel = ''
        if metainfo.has_key('caseno'):
            rel += metainfo['caseno']
        else:
            if metainfo.has_key('petitioner'):
                rel += metainfo['petitioner']
            if metainfo.has_key('respondent'):
                rel += metainfo['respondent']

        if not rel:
            return None

        rel      = string.replace(rel, '/', '-')
        tmprel   = os.path.join(relpath, rel)
        filepath = os.path.join(self.rawdir, tmprel)

        if not os.path.exists(filepath):
            self.download_judgment(href, filepath)

        if os.path.exists(filepath):
            metapath = os.path.join(self.metadir, tmprel)
            if metainfo and (self.updateMeta or not os.path.exists(metapath)):
                utils.print_tag_file(metapath, metainfo)

            return tmprel
        else:
            return None

    def page_type(self, tr):
        text = utils.get_tag_contents(tr)
        if re.search(' vs ', text, re.IGNORECASE):
            return 'judgment'
        elif self.next_link(tr.findAll('a')):
            return 'nextlink'
        else:
            return 'unknown'
                 
    def next_link(self, links):
        for link in links:
            contents = utils.get_tag_contents(link)
            if string.find(contents, 'Next') >= 0:
                return link
        return None

    def process_next_link(self, relpath, dateobj, nextlink):
        url = urllib.basejoin(self.dateurl, nextlink.get('href'))
        webpage = self.download_url(url, loadcookies = self.cookiefile.name)
        return self.process_result_page(relpath, dateobj, webpage)

    def process_result_page(self, relpath, dateobj, webpage):
        newdls = []
        d = utils.parse_webpage(webpage)
        if not d:
            self.logger.info(u'Could not parse result page for date %s' % dateobj)
            return newdls

        trs = d.findAll('tr')
        for tr in trs:
            pagetype = self.page_type(tr)
            if pagetype == 'nextlink':
                nextlink =  self.next_link(tr.findAll('a'))
                if nextlink:
                    self.logger.info(u'Going to the next page: %s' \
                                       % utils.get_tag_contents(nextlink))

                    rels = self.process_next_link(relpath, dateobj, nextlink)
                    newdls.extend(rels)
            elif pagetype == 'judgment':
                rel = self.handle_judgment_link(relpath, dateobj, tr)
                if rel:
                    newdls.append(rel)
            else:
                self.logger.info(u'Not processing %s' % tr)
        return newdls
 
    def download_oneday(self, relpath, dateobj):
        self.get_cookies()
        postdata = [('pageno', '1'), ('m_hc', '01'), ('mskey', ''), \
                    ('m_no', ''), ('m_yr', ''), ('jud1', 0), \
                    ('orddate1', ''), ('orddate2', ''), \
                    ('orddate3', self.date_in_form(dateobj)), \
                    ('petres', 'N'), ('m_party', ''), ('orddate4', ''), \
                    ('orddate5', '')]
        webpage = self.download_url(self.dateurl, postdata = postdata,  \
                                    loadcookies = self.cookiefile.name)
        return self.process_result_page(relpath, dateobj, webpage)
