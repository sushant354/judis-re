import utils
import tempfile
import os
import re

class Kolkata(utils.BaseCourt):
    def __init__(self, name, rawdir, metadir, logger):
        utils.BaseCourt.__init__(self, name, rawdir, metadir, logger)
        self.baseurl = 'http://www.judis.nic.in/Kolkata'
        self.cookiefile  = tempfile.NamedTemporaryFile()

    def get_cookies(self):
        self.download_url(self.baseurl + '/DtOfJud_Qry.asp' , \
                                    savecookies = self.cookiefile.name)

    def download(self, dateobj, doctype):
        posturl  = self.baseurl + '/FreeText_Result_1.asp'
        datestr  = utils.dateobj_to_str(dateobj, '/')
        postdata = [('Free_Txt', 'e'), ('From_Dt', datestr), \
                    ('To_Dt', datestr), ('OJ', doctype), ('submit', 'Submit')]

        webpage = self.download_url(posturl, postdata = postdata, \
                                    loadcookies = self.cookiefile.name)
 
        return webpage

    def download_oneday(self, relpath, dateobj):
        self.get_cookies()


        newdls = self.new_downloads(relpath, dateobj, '_J_')
        newdls.extend(self.new_downloads(relpath, dateobj, '_O_'))
        return newdls

    def new_downloads(self, relpath, dateobj, doctype):
        newdls = []
        webpage  = self.download(dateobj, doctype)

        d = utils.parse_webpage(webpage)

        if not d:
            self.log_debug(self.logger.ERR, 'Could not parse html of the result page for date %s' % dateobj)
            return newdls

        inputs = d.findAll('input')

        reccnt = None
        for inputtag in inputs:
            name = inputtag.get('name')
            value = inputtag.get('value')     
            if name =='RecCnt' and value:
                reccnt = value

        if not reccnt:
            self.log_debug(self.logger.WARN, 'No reccnt for date %s' % dateobj)
            return newdls
        
        options = d.findAll('option')
 
        if len(options) <= 0:
            self.log_debug(self.logger.WARN, 'No links for date %s' % dateobj)
            return newdls

        for option in options:
            link = option.get('value')
            if not link:
                continue


            self.log_debug(self.logger.NOTE, 'link %s' % link)

            relurl   = os.path.join(relpath, link)
            filepath = os.path.join(self.rawdir, relurl)
            metapath = os.path.join(self.metadir, relurl)
            if not os.path.exists(filepath) or os.stat(filepath).st_size <= 0:
                self.get_judgment(reccnt, link, filepath)

            
            if os.path.exists(filepath):
                if not os.path.exists(metapath):
                    metainfo = self.parse_meta_info(option, dateobj)
                    tags = utils.obj_to_xml('document', metainfo)
                    utils.save_file(metapath, tags)

                newdls.append(relurl)
        return newdls

    def parse_meta_info(self, option, dateobj):
        metainfo = {'date':utils.date_to_xml(dateobj)}
        contents = utils.get_tag_contents(option)

        reobj = re.search('&nbsp;&nbsp;', contents)
        if reobj:
           startobj = re.search('JUSTICE ', contents)
           if startobj and startobj.end() < reobj.start():
               metainfo['author'] = contents[startobj.end():reobj.start()]
               remains = contents[reobj.end():]
               reobj = re.search('&nbsp;&nbsp;', remains)
               if reobj:
                   caseno = remains[:reobj.end()]
                   caseno = re.sub('&nbsp;', '', caseno)
                   if caseno:
                      metainfo['caseno'] = caseno
   
        return metainfo

    def get_judgment(self, recordcnt, link, filepath):
        posturl  = self.baseurl + '/Judge_Result_Disp.asp'
        postdata = [('RecCnt', recordcnt), ('MyChk', link), \
                    ('submit', 'Submit')]    

        webpage = self.download_url(posturl, postdata = postdata, \
                                    loadcookies = self.cookiefile.name)
        if webpage:
            self.log_debug(self.logger.NOTE, 'Saving %s' % link)
            utils.save_file(filepath, webpage)
            return True
        else:
            self.log_debug(self.logger.NOTE, 'No download %s' % link)
            return False
