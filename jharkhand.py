import utils
import urllib
import os
import re

class Jharkhand(utils.BaseCourt):
    def __init__(self, name, rawdir, metadir, logger):
        utils.BaseCourt.__init__(self, name, rawdir, metadir, logger)
        self.baseurl = 'http://jhr.nic.in'

    def get_meta_info(self, title, dateobj):
        metainfo = {'date': utils.date_to_xml(dateobj)}
        reobj = re.search('Dated', title)
        if reobj:
            title = title[:reobj.start()]
        metainfo['caseno'] = title

        return metainfo

    def download_oneday(self, relpath, dateobj):
        dateurl = urllib.basejoin(self.baseurl, '/hcjudge/date_output.php')
        postdata = [('d1', dateobj.day), ('m1', dateobj.month),  \
                    ('y1', dateobj.year), ('d2', dateobj.day),   \
                    ('m2', dateobj.month), ('y2', dateobj.year), \
                    ('button', 'Submit')]

        encodedData  = urllib.urlencode(postdata)

        webpage = self.download_url(dateurl, postdata = postdata)

        if not webpage:
            self.log_debug(self.logger.WARN, 'No webpage for %s date: %s' % \
                                                            (dateurl, dateobj))
            return []

        d = utils.parse_webpage(webpage)

        if not d:
            self.log_debug(self.logger.ERR, 'HTML parsing failed for date: %s' % 
                                      dateobj)
            return []

        newdls = []

        for link in d.findAll('a'):
            href = link.get('href')
            title = utils.get_tag_contents(link)

            if (not href) or (not title):
                self.log_debug(self.logger.WARN, 'Could not process %s' % link)
                continue

            words = href.split('/')
            filename = words[-1]

            url = urllib.basejoin(dateurl, href)

            self.log_debug(self.logger.NOTE, 'link: %s title: %s' % \
                                      (href, title))

            relurl = os.path.join (relpath, filename)
            filepath = os.path.join(self.rawdir, relurl)
            metapath = os.path.join(self.metadir, relurl)

            if not os.path.exists(filepath):
                webpage = self.download_url(url)

                if not webpage:
                    self.log_debug(self.logger.WARN, 'No webpage %s' % url)
                else:
                    utils.save_file(filepath, webpage)
                    self.log_debug(self.logger.NOTE, 'Saved %s' % url)
                    newdls.append(relurl)

            if os.path.exists(filepath) and not os.path.exists(metapath):
                metainfo = self.get_meta_info(title, dateobj)
                if metainfo:
                    tags = utils.obj_to_xml('document', metainfo)
                    utils.save_file(metapath, tags)

        return newdls     
