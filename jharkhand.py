import utils
import urllib
import os
import re

class Jharkhand(utils.BaseCourt):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        utils.BaseCourt.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.baseurl  = 'http://jhr.nic.in'
        self.hostname = 'jhr.nic.in'
        self.dateurl  = urllib.basejoin(self.baseurl, '/hcjudge/date_output.php')

    def get_meta_info(self, tr, dateobj):
        metainfo = {'date': utils.date_to_xml(dateobj)}

        for td in tr.findAll('td'):
            text = utils.get_tag_contents(td)
            if text:
                reobj = re.search('\s+vs\s+', text, re.IGNORECASE)
                if reobj:
                    caseReobj = re.search('(?P<num>\d+)\s+of\s+(?P<year>\d+)', text, re.IGNORECASE)
                    if caseReobj and caseReobj.end() < reobj.start():
                        groupdict = caseReobj.groupdict()
                        metainfo['caseno'] = u'%s/%s' % (groupdict['num'], groupdict['year'])
                       
                        petitioner = text[caseReobj.end():reobj.start()]
                    else:
                        petitioner = text[:reobj.start()]

                    if reobj.end() < len(text):
                        respondent = text[reobj.end():]
                        metainfo['respondent'] = respondent.strip()

                    metainfo['petitioner'] = petitioner.strip()
                    break
                    
        return metainfo

    def download_oneday(self, relpath, dateobj):
        postdata = [('d1', dateobj.day), ('m1', dateobj.month),  \
                    ('y1', dateobj.year), ('d2', dateobj.day),   \
                    ('m2', dateobj.month), ('y2', dateobj.year), \
                    ('button', 'Submit')]

        webpage = self.download_url(self.dateurl, postdata = postdata)

        if not webpage:
            self.logger.warning(u'No webpage for %s date: %s' % \
                                 (self.dateurl, dateobj))
            return []

        newdls = self.download_orders_from_page(relpath, dateobj, webpage)
        return newdls

    def download_orders_from_page(self, relpath, dateobj, webpage):
        newdls = []

        d = utils.parse_webpage(webpage)

        if not d:
            self.logger.error(u'HTML parsing failed for date: %s' %  dateobj)
            return []

        for tr in d.findAll('tr'):
            href = None
            for link in tr.findAll('a'):
                title = utils.get_tag_contents(link)
                if re.search('view\s+order', title, re.IGNORECASE):
                    href = link.get('href')
                    break
                
            if (not href):
                self.logger.warning(u'Could not process %s' % tr)
                continue

            words = href.split('/')
            filename = words[-1]

            url = urllib.basejoin(self.dateurl, href)

            self.logger.info(u'link: %s' % href)

            relurl = os.path.join (relpath, filename)
            filepath = os.path.join(self.rawdir, relurl)
            metapath = os.path.join(self.metadir, relurl)

            if not os.path.exists(filepath):
                webpage = self.download_url(url)

                if not webpage:
                    self.logger.warning(u'No webpage %s' % url)
                else:
                    utils.save_file(filepath, webpage)
                    self.logger.info(u'Saved %s' % url)

            if os.path.exists(filepath):
                newdls.append(relurl)
                if self.updateMeta or not os.path.exists(metapath):
                    metainfo = self.get_meta_info(tr, dateobj)
                    self.logger.info(u'relurl: %s metainfo: %s' % (relurl, metainfo))
                    if metainfo:
                        utils.print_tag_file(metapath, metainfo)

        for link in d.findAll('a'):
            text = utils.get_tag_contents(link)
            href = link.get('href')
            if href and text and re.match('\s*next\s*$', text, re.IGNORECASE):
                url = urllib.basejoin(self.dateurl, href)
                webpage = self.download_url(url)
                if webpage:
                    self.logger.info(u'Recursing to the nextpage: %s' % url)
                    nextPageDls = self.download_orders_from_page(relpath, dateobj, webpage)
                    newdls.extend(nextPageDls)  
                else:
                    self.logger.warning(u'Could not download the next webpage: %s' % url)
        return newdls     
