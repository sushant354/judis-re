import urllib
import tempfile
import re
import os

import utils

class ItatDelhi(utils.BaseCourt):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        utils.BaseCourt.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        
        self.zone        = 'DELHI'
        self.city        = 'DEL'
        self.host        = 'http://www.itatonline.in:8080'
        self.datepath    = '/itat/jsp/runBirt2.jsp'
        self.cookiefile  = tempfile.NamedTemporaryFile()

        self.TOTAL_PAGE  = 'totalPage'
        self.DOCS        = 'docs'
        self.HREF        = 'href'

    def get_query_tuples(self, dateobj, zone, city):
        datestr = utils.dateobj_to_str(dateobj, '/')
        qtuples = [ \
            ('subAction', 'showReoprt'), \
            ('__report', 'pronouncementOrderReport1_%s.rptdesign' % zone), \
            ('City', city),                 \
            ('searchWhat', 'searchByDate'), \
            ('Serial No', ''),              \
            ('Appeal No', ''),              \
            ('Assessee Name', ''),          \
            ('AssType', 'null'),            \
            ('Order Date', datestr),        \
            ('Member Name', ''),            \
            ('Pronouncement Date', ''),     \
        ]
        return qtuples

    def tuples_to_qry(self, ts):
        return u'&'.join(u'%s=%s' % (urllib.quote(x[0]), urllib.quote(x[1])) for x in ts)

    def query_part_get(self, dateobj, zone, city):
        ts = self.get_query_tuples(dateobj, zone, city)
        return self.tuples_to_qry(ts)

    def query_part_post(self, dateobj, zone, city, sessionId):
        ts = self.get_query_tuples(dateobj, zone, city)
        ts.append(('__sessionId', sessionId))
        return self.tuples_to_qry(ts)

    def get_post_data(self, dateobj, city, pagenum):
        datestr = utils.dateobj_to_str(dateobj, '/')
        postdata = '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><GetUpdatedObjects xmlns="http://schemas.eclipse.org/birt"><Operation><Target><Id>Document</Id><Type>Document</Type></Target><Operator>GetPage</Operator><Oprand><Name>City</Name><Value>%s</Value></Oprand><Oprand><Name>__isdisplay__City</Name><Value>%s</Value></Oprand><Oprand><Name>Serial No</Name><Value></Value></Oprand><Oprand><Name>__isdisplay__Serial No</Name><Value></Value></Oprand><Oprand><Name>Appeal No</Name><Value></Value></Oprand><Oprand><Name>__isdisplay__Appeal No</Name><Value></Value></Oprand><Oprand><Name>Assessee Name</Name><Value></Value></Oprand><Oprand><Name>__isdisplay__Assessee Name</Name><Value></Value></Oprand><Oprand><Name>searchWhat</Name><Value>searchByDate</Value></Oprand><Oprand><Name>__isdisplay__searchWhat</Name><Value>searchByDate</Value></Oprand><Oprand><Name>Order Date</Name><Value>%s</Value></Oprand><Oprand><Name>__isdisplay__Order Date</Name><Value>%s</Value></Oprand><Oprand><Name>Member Name</Name><Value></Value></Oprand><Oprand><Name>__isdisplay__Member Name</Name><Value></Value></Oprand><Oprand><Name>Pronouncement Date</Name><Value></Value></Oprand><Oprand><Name>__isdisplay__Pronouncement Date</Name><Value></Value></Oprand><Oprand><Name>__page</Name><Value>%d</Value></Oprand><Oprand><Name>__svg</Name><Value>true</Value></Oprand></Operation></GetUpdatedObjects></soap:Body></soap:Envelope>' % (city, city, datestr, datestr, pagenum)
        return postdata

    def extract_session_id(self, webpage):
        reobj = re.search('SessionId\s*=\s*"(?P<num>[\d_]+)"', webpage)
        if reobj:
            groupdict = reobj.groupdict()
            if groupdict.has_key('num'):
                return groupdict['num']
        return None

    def parse_date_result(self, xmlpage):
        result = {}
        d = utils.parse_xml(xmlpage)
        if d:
            x = d.getElementsByTagName('TotalPage')
            if x.length > 0:
                totalPage = utils.get_node_value(x[0].childNodes)
                if re.match('\d+$', totalPage):
                    result[self.TOTAL_PAGE] = int(totalPage)

            x = d.getElementsByTagName('Content')
            if x.length > 0:
                htmlPage = utils.get_node_value(x[0].childNodes)
                if htmlPage:
                    result.update(self.parse_html_page(htmlPage))
        return result

    def get_meta_info(self, tr):
        info = {}
        tds = tr.findAll('td')
        i = 0
        for td in tds:
            value = td.getText()
            value = value.strip() 
            if value:
                if i == 1:
                    value = value.encode('ascii', 'ignore')
                    info[self.CASENO] = re.subn('[\s/]+', '-', value)[0] 
                elif i == 2:
                    info[self.PETITIONER] = value
                elif i == 3:
                    if re.match('department', value, re.IGNORECASE):
                        info[self.RESPONDENT] = u'Department of Income Tax'
                    else:
                        info[self.RESPONDENT] = value
                elif i > 3:
                    break
                i += 1
        return info

    def parse_html_page(self, htmlPage):
        result = {}
        docs   = []

        d = utils.parse_webpage(htmlPage)

        if d:
            trs = d.findAll('tr')
            for tr in trs:
                if tr.find('table'):
                    continue
                links = tr.findAll('a')
                href = None
                if len(links) > 1:
                    for a in links:
                        h = a.get(self.HREF)
                        if h and re.search('pdf$', h):
                            href = h 
                elif len(links) == 1 and links[0].get(self.HREF):
                    href = links[0].get(self.HREF)
                if href and (not re.search('/itat/upload/blank.htm$', href)):
                    metainfo = self.get_meta_info(tr)                
                    if metainfo:
                        href = links[0].get(self.HREF)
                        if href:
                            metainfo[self.HREF] = href 
                        docs.append(metainfo)                     
        if docs:
            result[self.DOCS] = docs
       
        return result

    def fetch_results(self, relpath, dateobj, zone, city, sessionId, pagenum):
        if sessionId == None:
            return {}

        posturl = urllib.basejoin(self.host, self.datepath) + '?' + \
                      self.query_part_post(dateobj, zone, city, sessionId) 
        headers = ['Content-Type: text/xml; charset=UTF-8', \
                   'SOAPAction: ""', 'request-type: SOAP']
        postdata = self.get_post_data(dateobj, city, pagenum)
        webpage = self.download_url(posturl, postdata = postdata,       \
                                    encodepost  = False,                \
                                    loadcookies = self.cookiefile.name, \
                                    headers     = headers)
        results = self.parse_date_result(webpage)
        return results

    def download_one_bench(self, relpath, dateobj, zone, city):
        dateurl = urllib.basejoin(self.host, self.datepath) + '?' + \
                      self.query_part_get(dateobj, zone, city) 
        webpage = self.download_url(dateurl, savecookies=self.cookiefile.name)
        sessionId = self.extract_session_id(webpage)

        results = self.fetch_results(relpath, dateobj, zone, city, sessionId, 1)

        docs = []
        if results.has_key(self.DOCS):
            docs.extend(results[self.DOCS])

        if results.has_key(self.TOTAL_PAGE) and results[self.TOTAL_PAGE] > 1:
            for pagenum in range(2, results[self.TOTAL_PAGE] + 1):
                self.logger.info('Going to results page %d for date %s' % (pagenum, dateobj))
                results = self.fetch_results(relpath, dateobj, zone, \
                                             city, sessionId, pagenum)
            
            if results.has_key(self.DOCS):
                docs.extend(results[self.DOCS])

        return self.download_docs(docs, relpath, dateobj)

    def download_docs(self, docs, relpath, dateobj):
        downloaded = []
        for doc in docs:
            if not doc.has_key(self.CASENO) or not doc.has_key(self.HREF):
                self.logger.info(u'Ignoring %s' % doc)
                continue

            caseno = doc[self.CASENO]
            href   = doc[self.HREF]

            tmprel   = os.path.join (relpath, caseno)
            rawpath  = os.path.join (self.rawdir, tmprel)
            metapath = os.path.join (self.metadir, tmprel)

            if not os.path.exists(rawpath):
                self.logger.info(u'Downloading %s from %s' % (caseno, href))
                webpage = self.download_url(doc[self.HREF])
                if webpage:
                    utils.save_file(rawpath, webpage)
                else:
                    self.logger.warning(u'Could not download %s' % href)

            if os.path.exists(rawpath) and not os.path.isdir(rawpath):
                if not os.path.exists(metapath) or self.updateMeta:
                    self.logger.info(u'Saving metapath for %s' % caseno)
                    self.save_meta_tags(metapath, doc, dateobj)
                downloaded.append(tmprel)
        return downloaded

    def save_meta_tags(self, metapath, judgedict, dateobj):
        tagdict = {'date': utils.date_to_xml(dateobj)}
        for k in judgedict.keys():
            if k not in [self.HREF]:
                tagdict[k] = judgedict[k]
        utils.print_tag_file(metapath, tagdict)

    def download_oneday(self, relpath, dateobj):
        dls = self.download_one_bench(relpath, dateobj, self.zone, self.city)
        return dls

class ItatAgra(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'DELHI'
        self.city = 'AGR'
 
class ItatIndore(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'AHMEDABAD'
        self.city = 'Ind' 
 
class ItatRajkot(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'AHMEDABAD'
        self.city = 'Rjt'
 
class ItatAhmedabad(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'AHMEDABAD'
        self.city = 'Ahd'

class ItatBilaspur(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'MUMBAI'
        self.city = 'Bil' 
 
class ItatNagpur(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone =  'MUMBAI'
        self.city =  'NAG'
 
class ItatPanji(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'MUMBAI'
        self.city = 'PAN'
 
class ItatPune(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone =  'MUMBAI'
        self.city = 'PUN'
 
class ItatMumbai(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone =  'MUMBAI'
        self.city =  'Mum'

class ItatChennai(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'CHENNAI'
        self.city = 'CHNY'
 
class ItatVizag(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'HYDERABAD'
        self.city =  'VIZ'
 
class ItatHyderabad(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'HYDERABAD'
        self.city = 'HYD'

class ItatAmritsar(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'CHANDIGARH'
        self.city = 'ASR' 
 
class ItatJodhpur(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'CHANDIGARH'
        self.city = 'JODH'
 
class ItatJaipur(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'CHANDIGARH'
        self.city = 'JPR'
 
class ItatChandigarh(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'CHANDIGARH'
        self.city = 'CHANDI'

class ItatCuttack(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'KOLKATA'
        self.city = 'CTK' 
 
class ItatGauhati(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'KOLKATA'
        self.city = 'GAU'
 
class ItatPatna(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'KOLKATA'
        self.city =  'PAT'
 
class ItatRanchi(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'KOLKATA'
        self.city = 'Ran'
 
class ItatKolkata(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'KOLKATA'
        self.city = 'Kol'

class ItatAllahabad(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'LUCKNOW'
        self.city = 'ALLD' 
 
class ItatJabalpur(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'LUCKNOW'
        self.city = 'JAB'
 
class ItatLucknow(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'LUCKNOW'
        self.city = 'LKW'

class ItatCochin(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'BENGLORE'
        self.city = 'COCH' 
 
class ItatBangalore(ItatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        ItatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.zone = 'BENGLORE'
        self.city = 'Bang'

