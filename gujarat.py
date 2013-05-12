import utils
import tempfile
import re
import os
import urllib
import time

class Gujarat(utils.BaseCourt):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        utils.BaseCourt.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.hostname = 'gujarathc-casestatus.nic.in'
        self.baseurl = 'http://gujarathc-casestatus.nic.in/'
        self.pageurl = urllib.basejoin(self.baseurl, \
                                       '/gujarathc/SearchHCJudge')
        self.caseurl = urllib.basejoin(self.baseurl, \
                                       '/gujarathc/GetOrderDateNew')
        self.orderurl = urllib.basejoin(self.baseurl, \
                                        '/gujarathc/OrderHistoryViewDownload')

        self.cookiefile  = tempfile.NamedTemporaryFile()

        self.download_url(self.baseurl, \
                          savecookies = self.cookiefile.name)

    def sanitize_windowopen(self, reobj):
        groupdict = reobj.groupdict()
        return '"' + groupdict['windowopen'] + '"'

    def download_oneday(self, relpath, dateobj):
        newdls  = []

        datestr = utils.dateobj_to_str(dateobj, '/')
        subrelpath = '/'.join(relpath.split('/')[:-1])

        postdata = [('hcjudgecode', ''), ('fromdate', datestr), \
                    ('todate', datestr), ('counter', '1')]

        webpage = self.download_url (self.pageurl, referer = self.baseurl, \
                                     loadcookies = self.cookiefile.name, \
                                     postdata = postdata)

        if not webpage:
            self.logger.warning(u'No webpage for %s' % self.pageurl)            
            return newdls

        d = utils.parse_webpage(webpage)
        if not d:
            self.logger.error(u'Could not parse html of the result page for date %s' % dateobj)
            return newdls

        trs = d.findAll('tr')
        for tr in trs:
            if tr.find('th'):
                continue

            onclick = tr.get('onclick')
            if not onclick:
                self.logger.info(u'No onclick in %s' % tr)
                continue

            reobj = re.search('\d+', onclick) 
            if not reobj:
                continue

            ccin = reobj.group(0)
            webpage = self.download_url (self.caseurl, referer = self.baseurl, \
                                         loadcookies = self.cookiefile.name, \
                                         postdata = [('ccin', ccin)])

            if not webpage:
                self.logger.error(u'Could not get case for %s on date %s' % (ccin, dateobj))
                continue
            newdls.extend(self.download_orders(subrelpath, ccin, dateobj, webpage))
        return newdls

    def get_order_of_fields(self, table):
        fieldOrder = {}
        thead = table.find('thead')
        if not thead:
            return fieldOrder

        ths = thead.findAll('th')
        i = 0
        for th in ths:
            text = utils.get_tag_contents(th)
            
            if text:
                if re.search('CASEDETAIL', text):
                    fieldOrder['caseno'] = i
                elif re.search('JUDGE NAME', text):
                    fieldOrder['bench'] = i
                elif re.search('DATE', text):
                    fieldOrder['date'] = i
                elif re.search('VIEW', text):
                    fieldOrder['view'] = i
                elif re.search('JUDGEMENT', text):
                    fieldOrder['judgment'] = i

            i += 1
        return fieldOrder

    def download_orders(self, relpath, ccin, dateobj, webpage):
        parsedDoc =  utils.parse_webpage(webpage)
        if not parsedDoc:
            self.logger.warning(u'Could not parse judgments list for doc: ccin %s date: %s' % (ccin, dateobj))
            return []
 
        trs = parsedDoc.findAll('tr')
        fieldOrder = self.get_order_of_fields(parsedDoc)

        newdls = [] 
        if 'view' in fieldOrder and 'caseno' in fieldOrder \
                and 'date' in fieldOrder:
            for tr in trs:
                if tr.find('th'):
                    continue

                relurl = self.process_order_tr(ccin, relpath, dateobj, \
                                               tr, fieldOrder)
                if relurl:
                    newdls.append(relurl)
                else:
                    self.logger.warning(u'Could not get judgment in tr: %s' % tr)
        else:
            self.logger.warning(u'Could not get field ordering in ccin %s date: %s' % (ccin, dateobj))
        return newdls

    def process_order_tr(self, ccin, relpath, dateobj, tr, fieldOrder):
        tds =  tr.findAll('td')
        viewIndex  = fieldOrder['view']
        dateIndex  = fieldOrder['date']
        if viewIndex >= len(tds) or dateIndex >= len(tds):
            self.logger.warning(u'Could not get date or view in tr: %s' % tr)
            return None

        viewTd  = tds[viewIndex]
        dateTd  = tds[dateIndex]

        datestr = utils.get_tag_contents(dateTd)

        if not datestr:
            self.logger.warning(u'Date: %s Could not get date in %s' % (dateobj, tr))
            return None

        subdateobj = utils.datestr_to_obj(datestr)
        if not subdateobj:
            self.logger.warning(u'Date: %s Could not get date in %s tr: %s' % (dateobj, datestr, tr))
            return None

        subdateobj = subdateobj.date() 
        metainfo = {'date':utils.date_to_xml(subdateobj), 'ccin': ccin}

        # store bench in metainfo
        if 'bench' in fieldOrder and fieldOrder['bench'] < len(tds):
            benchIndex = fieldOrder['bench']
            benchTd = tds[benchIndex]
            contents = utils.get_tag_contents(benchTd)
            if contents:
                names = []
                for reobj in re.finditer('JUSTICE ', contents):
                    names.append(contents[reobj.end():])
                if names:
                    metainfo['bench'] = {} 
                    metainfo['bench']['name'] = names

        # store isJudgment in metainfo
        if 'judgment' in fieldOrder and fieldOrder['judgment'] < len(tds):
            jTd = tds[fieldOrder['judgment']]
            contents = utils.get_tag_contents(jTd)
            if contents:
                metainfo['judgment'] = contents

        onclick  = viewTd.get('onclick')
        if onclick:
            relurl = self.download_order(relpath, subdateobj, \
                                             metainfo, onclick)
            return relurl
        else:
             self.logger.warning(u'No onclick attribute in viewTd: %s' % viewTd)
        return None 

    def get_filename(self, casedetail):
        words = casedetail.split('/')
        if len(words) == 3:
            relurl = [words[2], words[1]]
            subwords = re.split('[.\s]+', words[0])
            
            sublist = []
            for x in subwords:
                sublist.append(x[0])

            relurl.append(u''.join(sublist))

            return u'_'.join(relurl)

        return None

    def download_order(self, relpath, dateobj, metainfo, onclick):
        reobj = re.search('myfunViewDownLoad\s*\(\s*"(?P<ccin>\d+)"\s*,\s*"(?P<orderno>\d+)"\s*,\s*"(?P<flag>\w+)"\s*,\s*"(?P<casedetail>.+)"\s*,\s*"\w+"', onclick) 
        if not reobj:
            self.logger.warning(u'Could not get parameters in onclick: %s' % onclick)
            return None
 
        groupdict  = reobj.groupdict()
        ccin       = groupdict['ccin']
        orderno    = groupdict['orderno']
        flag       = groupdict['flag']
        casedetail = groupdict['casedetail']

        metainfo['caseno'] = casedetail
        filename   = self.get_filename(casedetail)

        if not filename:
            self.logger.warning(u'Could not get filename from %s' % casedetail)
            return None

        datestr = dateobj.__str__()

        utils.mk_dir(os.path.join(self.rawdir, self.name, datestr))
        utils.mk_dir(os.path.join(self.metadir, self.name, datestr))
        
        relurl   = os.path.join(relpath, datestr, filename)
        filepath = os.path.join(self.rawdir, relurl)
        metapath = os.path.join(self.metadir, relurl)

        if os.path.exists(filepath):
            self.logger.warning(u'Raw file already exists, skipping: %s ' % relurl)
        else:
            #ccin_no=001016200801769&order_no=2&flag=v&casedetail=MISC.CIVIL+APPLICATION%2F1769%2F2008&download_token_value_id=1367853726545
            self.logger.info(u'Downloading %s' % relurl)
            postdata = [('ccin_no', ccin), ('order_no', orderno), \
                        ('flag', flag), ('casedetail', casedetail), \
                        ('download_token_value_id', int(time.time())) ]

            webpage = self.download_url(self.orderurl, \
                                        referer=self.caseurl,\
                                        loadcookies = self.cookiefile.name,\
                                        postdata = postdata)

            if webpage:
                self.logger.info(u'Saving %s' % filepath)
                utils.save_file(filepath, webpage)
            else:
                self.logger.warning(u'Could not download ccin: %s number: %s ' % (ccin, orderno))
           
        if os.path.exists(filepath) and metainfo and \
                (self.updateMeta or not os.path.exists(metapath)):
            self.logger.info(u'Metainfo: %s' % metainfo)
            utils.print_tag_file(metapath, metainfo)

        if os.path.exists(filepath):
            return relurl

        return None


