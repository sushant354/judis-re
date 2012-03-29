import utils
import urllib
import tempfile
import re
import os

class Karnataka(utils.BaseCourt):
    def __init__(self, srcdir, rawdir, metadir, statsdir, updateMeta = False):
        utils.BaseCourt.__init__(self, srcdir, rawdir, metadir, statsdir, updateMeta)
        self.baseurl  = 'http://judgmenthck.kar.nic.in'
        self.courturl = urllib.basejoin(self.baseurl, '/judgments/')
        self.cookiefile = tempfile.NamedTemporaryFile()
        self.get_cookies()

    def get_cookies(self):
        self.download_url(self.courturl, savecookies = self.cookiefile.name)

    def action_on_link(self, link, linktitle):
        if re.match('/judgments/handle', link):
            return 'judgmentlink'
        elif re.match('/judgments/bitstream.+pdf', link):
            return 'save'
        elif re.match('next', linktitle, re.IGNORECASE):
            return 'recurse'
        return 'ignore'
    
    def download_oneday(self, relpath, dateobj):
        getdata = [('type', 'datecreated'), ('order', 'ASC'), ('rpp', '20'), \
                  ('value', utils.dateobj_to_str(dateobj, '-', reverse = True))]

        url = self.courturl + 'browse?' + \
                          '&'.join(['%s=%s' % (x[0], x[1]) for x in getdata])

        return self.result_page(relpath, url, dateobj, {})

    def get_judgment(self, relpath, url, filename, metainfo):
        relurl = os.path.join(relpath, filename)
        filepath = os.path.join(self.rawdir, relurl)
        metapath = os.path.join(self.metadir, relurl)

        if not os.path.exists(filepath):
            webpage = self.download_url(url, loadcookies = self.cookiefile.name)
            if not webpage:
                self.logger.warning(u'Could not download judgment %s' % url)
                return None
       
 
            utils.save_file(filepath, webpage)
            self.logger.info(u'Saved %s' % filepath)

        if os.path.exists(filepath):
            if self.updateMeta or not os.path.exists(metapath):
                metainfo['url'] = url
                utils.print_tag_file(metapath, metainfo)

            return relurl
        else:
            return None
       
    def get_meta_info(self, d, dateobj):
        metainfo = { 'date': utils.date_to_xml(dateobj) }
        trs = d.findAll('tr')
        for tr in trs:
            tds = tr.findAll('td')

            i = 0
            tdtype = None
            for td in tds[:-1]:
                 content = utils.get_tag_contents(td)

                 if re.search('Case Number', content):
                     tdtype = 'caseno'
                     break

                 if re.search('Judge', content):
                     tdtype = 'author'
                     break

                 if re.search('Petitioner', content):
                     tdtype = 'petitioner'
                     break

                 if re.search('Respondent', content):
                     tdtype = 'respondent'
                     break

                 if re.search('Location', content):
                     tdtype = 'location'
                     break


                 i += 1
            if tdtype and i + 1 < len(tds):
                 content = utils.get_tag_contents(td)
                 metainfo[tdtype] = utils.get_tag_contents(tds[i+1])

        return metainfo             

    def process_judgment_page(self, relpath, url, dateobj):
        webpage = self.download_url(url, loadcookies = self.cookiefile.name)
        if not webpage:
            self.logger.warning(u'Could not download %s' % url)
            return None

        d = utils.parse_webpage(webpage)
        if not d:
            self.logger.warning(u'Could not parse %s' % url)
            return None

        metainfo = self.get_meta_info(d, dateobj)

        for link in d.findAll('a'):
            href = link.get('href')
            title = utils.get_tag_contents(link)

            if (not href) or (not title):
                self.logger.warning(u'Could not process %s' % link)
                continue

            action = self.action_on_link(href, title)
            newurl = urllib.basejoin(url, href)
            if action == 'save':
                self.logger.info(u'Downloading %s' % newurl)
                return self.get_judgment(relpath, newurl, title, metainfo)

        return None

    def result_page(self, relpath, url, dateobj, linkdict):
        newdls = []
        webpage = self.download_url(url, loadcookies = self.cookiefile.name)

        d = utils.parse_webpage(webpage)

        if not d:
            self.logger.error(u'Could not parse html of the result page for date %s' % dateobj)
            return newdls

        for link in d.findAll('a'):
            href = link.get('href')
            title = utils.get_tag_contents(link)

            if (not href) or (not title) or linkdict.has_key(href):
                self.logger.warning(u'Could not process %s' % link)
                continue

            linkdict[href] = 1

            action = self.action_on_link(href, title)
            self.logger.info(u'Action %s on link %s title %s' %\
                                     (action, href, title))       
            newurl = urllib.basejoin(url, href)
            if action == 'judgmentlink':
                relurl = self.process_judgment_page(relpath, newurl, dateobj)
                if relurl:
                    newdls.append(relurl)
                else:
                    self.logger.warning(u'Judgment link not working %s' % newurl)
            elif action == 'recurse':
                newdls.extend(self.result_page(relpath, newurl, dateobj, 
                                               linkdict))
           
        return newdls
