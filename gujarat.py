import utils
import tempfile
import re
import os
import urllib

class Gujarat(utils.BaseCourt):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        utils.BaseCourt.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.baseurl = 'http://gujarathc-casestatus.nic.in/'
        self.cookiefile  = tempfile.NamedTemporaryFile()
        self.agree_to_tc()

    def agree_to_tc(self):
        postdata = [('agree', 'Y')]
        tcurl = urllib.basejoin(self.baseurl, '/gujarathc/validPageChk.jsp')
        self.download_url(tcurl, \
                          savecookies = self.cookiefile.name, \
                          postdata    = postdata)

    def sanitize_windowopen(self, reobj):
        groupdict = reobj.groupdict()
        return '"' + groupdict['windowopen'] + '"'

    def download_oneday(self, relpath, dateobj):
        newdls  = []

        pageurl = urllib.basejoin(self.baseurl, '/gujarathc/')

        datestr = utils.dateobj_to_str(dateobj, '-')
        dateurl = pageurl + 'orderdatewisedata.jsp?fdate=%s&tdate=%s' % \
                                (datestr, datestr)

        webpage = self.download_url (dateurl, referer = self.baseurl, \
                                     loadcookies = self.cookiefile.name)

        if not webpage:
            self.logger.warning(u'No webpage for %s' % dateurl)            
            return newdls

        webpage = re.sub('(?P<windowopen>window.open\([^)]+\))', \
                         self.sanitize_windowopen, webpage)

        d = utils.parse_webpage(webpage)

        if not d:
            self.logger.error(u'Could not parse html of the result page for date %s' % dateobj)
            return newdls

        trs = d.findAll('tr')
        for tr in trs:
            link = tr.find('a')
            if not link:
                self.logger.info(u'No link in %s' % tr)
                continue

            href = link.get('onclick')
            if not href:
                self.logger.info(u'No href in %s' % tr)
                continue

            reobj = re.search("showoj.jsp?[^'\s]+", href)

            (start, end) = reobj.span()

            pagerelurl = href[start:end]          
            url = urllib.basejoin(pageurl, pagerelurl)

            filename = utils.url_to_filename(url, False, ['caseyr', 'caseno', \
                                                          'casetype'])

            if not filename:
                self.logger.error(u'Could not get filename for %s' % url)
                continue
            relurl   = os.path.join(relpath, filename)
            filepath = os.path.join(self.rawdir, relurl)
            metapath = os.path.join(self.metadir, relurl)

            if not os.path.exists(filepath):
                self.logger.info(u'Downloading %s %s' % (url, filename))
                j = self.download_url(url, loadcookies = self.cookiefile.name)
                 
                if not j:
                    self.logger.warning(u'No webpage: %s' % url)
                else:
                    self.logger.info(u'Saving %s' % filepath)
                    utils.save_file(filepath, j)
                    newdls.append(relurl)
           
            if os.path.exists(filepath) and \
                    (self.updateMeta or not os.path.exists(metapath)):
                metainfo = self.get_meta_info(link, tr, dateobj)
                if metainfo:
                    utils.print_tag_file(metapath, metainfo)

        return newdls

    def get_meta_info(self, link, tr, dateobj):
        metainfo = {'date':utils.date_to_xml(dateobj)}
        metainfo['caseno'] = utils.get_tag_contents(link)
        tds = tr.findAll('td')
        for td in tds:
            contents = utils.get_tag_contents(td)
            reobj = re.search('JUSTICE ', contents)
            if  reobj:
               metainfo['author'] = contents[reobj.end():]

        return metainfo
