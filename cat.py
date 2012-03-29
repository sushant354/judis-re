import re

import utils
import supremecourt

class CatDelhi(supremecourt.SupremeCourt):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        supremecourt.SupremeCourt.__init__(self, name, rawdir, \
                                           metadir, statsdir, updateMeta)
        self.webformUrl = 'http://judis.nic.in/judis_cat/chrseq.aspx'
        self.dateqryUrl = 'http://judis.nic.in/judis_cat/Doj_Qry.aspx'
        self.statevalNames = ['__VIEWSTATE', '__EVENTVALIDATION', '__ncforminfo']

    def date_postdata(self, dateobj):
        if dateobj.month < 10:
            mnth = '0%d' % dateobj.month
        else:
            mnth = '%d' % dateobj.month

        if dateobj.day < 10:
            day = '0%d' % dateobj.day
        else:
            day = '%d' % dateobj.day

        postdata = [('__EVENTTARGET', ''), ('__EVENTARGUMENT', '')]
        postdata.extend(self.state_data())
        postdata.extend(
                   [ ('selfday', day), ('selfmonth', mnth),\
                     ('selfyear', dateobj.year), ('seltday', day), \
                     ('seltmonth', mnth),('seltyear', dateobj.year),\
                     ('button', 'Submit')\
                    ])
        return postdata

    def get_judgment_info(self, tr):
        judgedict = {}
        link = tr.find('a')
        if link:
            title = utils.get_tag_contents(link)
            href  = link.get('href')

            if href:
                judgedict['href']  = href

        tds = tr.findAll('td')
        i = 0
        for td in tds:
            tdContent = utils.get_tag_contents(td)
            if tdContent:
                if i == 0:
                    judgedict['casetype'] = tdContent
                elif i == 1:
                    judgedict['caseno'] = tdContent
                elif i == 2:
                    judgedict['caseyear'] = tdContent
                i += 1
        if judgedict.has_key('caseno') and judgedict.has_key('caseyear'):
            title = u'%sof%s' % (judgedict['caseno'], judgedict['caseyear'])
            judgedict['title'] = title
        return judgedict

    def save_meta_tags(self, metapath, judgedict, dateobj):
        tagdict = {'date': utils.date_to_xml(dateobj)}
        for k in judgedict.keys():
            if k not in ['href']: 
                tagdict[k] = judgedict[k]
        utils.print_tag_file(metapath, tagdict)

    def extract_links(self, prsdobj, pagenum):
        linkdict = {'docs': []}

        tables = prsdobj.findAll('table')
        grid   = None
        for table in tables:
            className = table.get('class')
            if className == 'Grid':
                grid = table
                break
        if grid:
            trs =  grid.findAll('tr')
            for tr in trs:
                link = self.get_judgment_info(tr)
                if link and link.has_key('title'):
                    linkdict['docs'].append(link)
                else: 
                    pageblock, nextlink = utils.check_next_page(tr, pagenum)
                    if nextlink:
                        linkdict['next'] = nextlink
                    else:
                        self.logger.debug(u'Ignoring tr: %s' % tr)

        return linkdict

    def download_oneday(self, relpath, dateobj):
        self.stateval   = self.get_stateval(self.dateqryUrl)

        if not self.stateval:
            self.logger.error(u'No stateval for date %s' % dateobj)

        postdata = self.date_postdata(dateobj)

        webpage  = self.download_webpage(postdata, self.dateqryUrl)
        newdls = self.datequery_result(webpage, relpath, 1, dateobj)
        return newdls


class CatAhmedabad(CatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateqryUrl = u'http://judis.nic.in/judis_cat/Doj_Qry_Ahmedabad.aspx'
class CatAllahabad(CatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateqryUrl = u'http://judis.nic.in/judis_cat/Doj_Qry_allabd.aspx'

class CatBangalore(CatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateqryUrl = u'http://judis.nic.in/judis_cat/Doj_Qry_bng.aspx'

class CatChandigarh(CatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateqryUrl = u'http://judis.nic.in/judis_cat/Doj_Qry_chandigarh.aspx'

class CatCalcutta(CatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateqryUrl = u'http://judis.nic.in/judis_cat/Doj_Qry_Calcutta.aspx'

class CatChennai(CatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateqryUrl = u'http://judis.nic.in/judis_cat/Doj_Qry_chennai.aspx'

class CatCuttack(CatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateqryUrl = u'http://judis.nic.in/judis_cat/Doj_Qry_Cuttack.aspx'

class CatErnakulam(CatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateqryUrl = u'http://judis.nic.in/judis_cat/Doj_Qry_erna.aspx'

class CatGuwahati(CatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateqryUrl = u'http://judis.nic.in/judis_cat/Doj_Qry_guwahati.aspx'

class CatHyderabad(CatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateqryUrl = u'http://judis.nic.in/judis_cat/Doj_Qry_hyd.aspx'

class CatJabalpur(CatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateqryUrl = u'http://judis.nic.in/judis_cat/Doj_Qry_jabalpur.aspx'

class CatJaipur(CatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateqryUrl = u'http://judis.nic.in/judis_cat/Doj_Qry_jaipur.aspx'

class CatLucknow(CatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateqryUrl = u'http://judis.nic.in/judis_cat/Doj_Qry_Lucknow.aspx'

class CatMumbai(CatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateqryUrl = u'http://judis.nic.in/judis_cat/Doj_Qry_mum.aspx'

class CatPatna(CatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateqryUrl = u'http://judis.nic.in/judis_cat/Doj_Qry_patna.aspx'

class CatJodhpur(CatDelhi):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        CatDelhi.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateqryUrl = u'http://judis.nic.in/judis_cat/Doj_Qry_Jodh.aspx'

