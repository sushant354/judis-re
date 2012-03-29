import utils
import urllib
import tempfile
import calendar
import re
import string
import os

class Patna(utils.BaseCourt):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        utils.BaseCourt.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.baseurl = 'http://patnahighcourt.bih.nic.in'
        self.dateurl = urllib.basejoin(self.baseurl, \
                                       '/judgment/judgDateWise.aspx')
        self.formaction = 'judgDateWise.aspx'

        self.cookiefile = tempfile.NamedTemporaryFile()
        self.cookieurl = urllib.basejoin(self.baseurl, '/judgment/default.aspx')
        self.download_url(self.cookieurl, savecookies = self.cookiefile.name)

    def get_filename(self, title):
        filename = re.sub('/', '|', title)
        filename = re.sub("'", ' ', filename)
        words    = filename.split()
        return string.join(words, '_')

    def download_link(self, postdata, href):
        plist = []
        for t in postdata:
            if not (t[0] in ['__EVENTTARGET', '__EVENTARGUMENT', \
                             'ctl00$ContentPlaceHolder1$BtnGetInfo']):
                plist.append(t)

        reobj = re.search("javascript:__doPostBack\('(?P<param1>[^']+)','(?P<param2>[^']+)'", href)

        if reobj:
            groupdict = reobj.groupdict()
            plist.insert(0, ('__EVENTTARGET', groupdict['param1']))
            plist.insert(1, ('__EVENTARGUMENT', groupdict['param2']))

            webpage = self.download_url(self.dateurl, postdata = plist, \
                                       loadcookies = self.cookiefile.name)
            return webpage
        else:
            return None

    def get_judgment(self, relpath, postdata, href, metainfo):
        if not metainfo.has_key('title'):
            self.logger.warning(u'No title found for %s' % href)
            return None
 
        filename = self.get_filename(metainfo['title'])
        relurl   = os.path.join(relpath, filename)
        rawpath  = os.path.join(self.rawdir, relurl)
        metapath = os.path.join(self.metadir, relurl)
     
        if not os.path.exists(rawpath):
            judgment = self.download_link(postdata, href)
            if judgment:
                mtype = utils.get_buffer_type(judgment)
                if re.match('text/html', mtype):
                    self.logger.warning(u'Err in downloading %s: Directed to a default website' % relurl)
                else: 
                    self.logger.info(u'Downloaded %s' % relurl) 
                    utils.save_file(rawpath, judgment)
            else:
                self.logger.info(u'Could not download %s' % relurl)        
        if os.path.exists(rawpath):
            if metainfo and (self.updateMeta or not os.path.exists(metapath)):
                tags = utils.obj_to_xml('document', metainfo)
                utils.save_file(metapath, tags)

            return relurl
        else:
            return None

    def get_meta_info(self, tr, dateobj):
        metainfo = { 'date': utils.date_to_xml(dateobj) }
        tds = tr.findAll('td')
        for td in tds:
            content = utils.get_tag_contents(td)
            reobj = re.search(' vs\.? ', content, re.IGNORECASE)
            if reobj:
                metainfo['title']      = content
                metainfo['petitioner'] = content[:reobj.start()]
                metainfo['respondent'] = content[reobj.end():]

            reobj = re.search('justice ', content, re.IGNORECASE)
            if reobj:
                metainfo['author'] = content[reobj.end():]
                 
        return metainfo

    def result_page(self, relpath, webpage, dateobj, pagenum):
        newdls = []

        parsedobj = utils.parse_webpage(webpage)
        if not parsedobj:
            self.logger.error(u'Could not parse the result page')
            return newdls

        tables = parsedobj.findAll('table')
        rtable = None
        for table in tables:
            id = table.get('id')
            if id == 'ctl00_ContentPlaceHolder1_OrderGridView':
                rtable = table

        if not rtable:
            self.logger.error(u'Result table not found')
            return newdls

        postdata = self.get_post_data(parsedobj, dateobj)

        trs = rtable.findAll('tr')
        pageblock = False
        nextlink  = None

        for tr in trs:
            p, n = utils.check_next_page(tr, pagenum)

            if p:
                pageblock = p
                nextlink  = n
            else:
                relurl = self.process_judgment_row(tr, relpath, postdata, \
                                                   dateobj)
                if relurl:
                    newdls.append(relurl)

        # check if we need to recurse 
        if pageblock:
            if nextlink:
                self.logger.info(u'Recursing after pagnum %d' %  (pagenum+1))
                self.download_url(self.cookieurl, savecookies = self.cookiefile.name)
                webpage = self.download_link(postdata, nextlink['href'])
                newdls.extend(self.result_page(relpath, webpage, \
                                               dateobj, pagenum + 1))
            else:
                self.logger.info(u'Last page %d. No more recursing' % pagenum)

        return newdls

    def process_judgment_row(self, tr, relpath, postdata, dateobj):
        links = tr.findAll('a')
        judgehref = None
        relurl    = None

        for link in links:
            href  = link.get('href')
            title = utils.get_tag_contents(link)
            if re.search('View', title):
                judgehref = href
            
        if not judgehref:
            self.logger.info(u'No download link in %s' % tr) 
        else:
            self.logger.info(u'Processing %s' % judgehref)
            metainfo = self.get_meta_info(tr, dateobj)
            relurl = self.get_judgment(relpath, postdata, judgehref, metainfo)

        return relurl

    def base_post_data(self, dateobj):
        monthname = calendar.month_name[dateobj.month]
        monthname = monthname[:3]

        if monthname == 'May':
            monthname = 'MAy'

        postdata = \
          [
            ('ctl00$ContentPlaceHolder1$dd1', '%d' % dateobj.day), \
            ('ctl00$ContentPlaceHolder1$mm1', monthname), \
            ('ctl00$ContentPlaceHolder1$yy1', '%d' % dateobj.year), \
            ('ctl00$ContentPlaceHolder1$dd2', '%d' % dateobj.day), \
            ('ctl00$ContentPlaceHolder1$mm2', monthname), \
            ('ctl00$ContentPlaceHolder1$yy2', '%d' % dateobj.year)  \
          ]
        return postdata 

    def get_post_data(self, d, dateobj):
        postdata = self.base_post_data(dateobj)
        forms = d.findAll('form')
        for form in forms:
            if form.get('action') == self.formaction: 
                inputs  = form.findAll('input')
                for input in inputs:
                    name = input.get('name')
                    value = input.get('value')
                    if name == '__VIEWSTATE':
                        postdata.insert(0, (name, value))
                    else:
                        postdata.append((name, value))
        return postdata

    def download_oneday(self, relpath, dateobj):
        self.download_url(self.cookieurl, savecookies = self.cookiefile.name)
        webpage = self.download_url(self.dateurl, \
                                    loadcookies = self.cookiefile.name)
        parsedobj = utils.parse_webpage(webpage)
        if not parsedobj:
            self.logger.error(u'Could not parse the date search page')
            return []

        postdata = self.get_post_data(parsedobj, dateobj)

        webpage = self.download_url(self.dateurl, postdata = postdata, \
                                    loadcookies = self.cookiefile.name, \
                                    referer = self.dateurl)
        return self.result_page(relpath, webpage, dateobj, 1)
