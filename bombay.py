import urllib
import subprocess
import tempfile
import re
import os

import utils

class Bombay(utils.BaseCourt):
    def __init__(self, name, rawdir, metadir, logger):
        utils.BaseCourt.__init__(self, name, rawdir, metadir, logger)
        self.baseurl = 'http://bombayhighcourt.nic.in'
        self.cookiefile  = tempfile.NamedTemporaryFile()

    def get_cookies(self):
        url = urllib.basejoin(self.baseurl, '/ord_qryrepact.php')
        self.download_url(url, savecookies = self.cookiefile.name)

    def download_oneday(self, relpath, dateobj):
        self.get_cookies()
        posturl  = self.baseurl + '/ordqryrepact_action.php'

        todate   = utils.dateobj_to_str(dateobj, '-')
        fromdate  = todate

      
        postdata = [('pageno', 1), ('actcode', 0), ('frmaction', ''), \
                    ('frmdate', fromdate), \
                    ('todate', todate), ('submit1', 'Submit')]

        newdls = []
        linkdict = {}
        for sideflag in ['C', 'CR', 'OS', 'NC', 'NR', 'AC', 'AR']:
            data = [('m_sideflg', sideflag)]
            data.extend(postdata[:])
        
            encodedData  = urllib.urlencode(data)

            arglist =  [\
                        '/usr/bin/wget', '--output-document', '-', \
                        '--user-agent=%s' % self.useragent, \
                        '--tries=%d' % self.maxretries, \
                        '-a', self.wgetlog, '--post-data', \
                        "'%s'" % encodedData, \
                        '--load-cookies', self.cookiefile.name \
                       ]

            if self.logger.debuglevel >= self.logger.NOTE:
                arglist.append('--debug')

            arglist.append(posturl)

            p = subprocess.Popen(arglist, stdout=subprocess.PIPE)
            webpage = p.communicate()[0]
            newdls.extend(self.result_page(webpage, relpath, dateobj, linkdict))

        return newdls 

    def get_judgment(self, link, filepath):
        url      = urllib.basejoin (self.baseurl, link)
        webpage  = self.download_url(url)
 
        if webpage:
            self.log_debug(self.logger.NOTE, 'Successfully downloaded %s' % url)
            utils.save_file(filepath, webpage)
            return True
        else:    
            self.log_debug(self.logger.WARN, 'Got empty page for %s' % url)
            return False

    def parse_meta_info(self, tr, dateobj):
        metainfo = { 'date': utils.date_to_xml(dateobj)}

        tds = tr.findAll('td')
        i = 0
        for td in tds:
            c = utils.get_tag_contents(td)
            if c:
                if i == 0:
                    contents = utils.tag_contents_without_recurse(td)
                    names = []
                    for content in contents:
                        reobj = re.search('JUSTICE ', content)
                        if reobj:
                            names.append(content[reobj.end():])

                    if names: 
                        metainfo['bench'] = {}
                        metainfo['bench']['name']  = names

                elif i == 1:
                    metainfo['category'] = c
                elif i == 3:
                    metainfo['caseno']   = c
                    
                i += 1

        return metainfo

    def store_meta_tags(self, metapath, metainfo):
        tags = utils.obj_to_xml('document', metainfo)
        utils.save_file(metapath, tags) 

    def result_page(self, webpage, relpath, dateobj, linkdict):
        newdls      = []

        if not webpage:
            return newdls 

        courtParser = utils.parse_webpage(webpage)

        if not courtParser:
            self.log_debug(self.logger.ERR, 'Could not parse html of the result page for date %s' % dateobj)
            return newdls

        trs  = courtParser.findAll('tr')

        for tr in trs:
            link = tr.find('a')
 
            if link:
                title = utils.get_tag_contents(link)
                href  = link.get('href')
 
                if (not title) or (not href):
                    self.log_debug(self.logger.WARN, 'Could not process %s' % link)
                    continue

                if linkdict.has_key(href):
                    continue

                if not re.search('first|prev|next|last|acroread', title, \
                                 re.IGNORECASE):
                    linkdict[href] = 1
                    dl = self.handle_link(relpath, href, title, tr, dateobj)
                    if dl:
                        newdls.append(dl)

                elif title == 'Next':
                    self.log_debug(self.logger.NOTE, 'Following Next page %s' % href)
                    newlink = urllib.basejoin (self.baseurl, href)
                    webpage = self.download_url(newlink, \
                                            loadcookies = self.cookiefile.name)
               
                    newdls.extend(self.result_page(webpage, relpath, dateobj, \
                                                   linkdict))
                else:
                    self.log_debug(self.logger.NOTE, 'No action for %s' % href)
        return newdls

    def handle_link(self, relpath, href, title, tr, dateobj):
        tmprel   = os.path.join(relpath, re.sub('/', '-', title))
        filepath = os.path.join(self.rawdir, tmprel)
        metapath = os.path.join(self.metadir, tmprel)

        self.log_debug(self.logger.NOTE, 'link: %s title: %s' %  (href, title))

        if os.path.exists(filepath):
            self.log_debug(self.logger.NOTE, 'Already exists %s' % filepath)
        else:
            self.get_judgment(href, filepath)

        if os.path.exists(filepath):
            if not os.path.exists(metapath):
                metainfo = self.parse_meta_info(tr, dateobj)
                if metainfo:
                    self.store_meta_tags(metapath, metainfo) 

            return tmprel
        else:
            return None
