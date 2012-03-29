import re

import supremecourt
import utils

class Kolkata(supremecourt.SupremeCourt):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        supremecourt.SupremeCourt.__init__(self, name, rawdir, \
                                           metadir, statsdir, updateMeta)
        self.webformUrl = 'http://judis.nic.in/Judis_Kolkata/chrseq.aspx'
        self.dateqryUrl = 'http://judis.nic.in/Judis_Kolkata/Dt_Of_JudQry.aspx'
        self.dataTypes = ['O', 'J']
        self.statevalNames = ['__VIEWSTATE', '__EVENTVALIDATION']


    def date_postdata(self, dateobj, dataType):
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
                     ('seltitletype', dataType), ('button', 'Submit')\
                    ])
        return postdata

    def get_judgment_info(self, tr):
        judgedict = {}
        if tr.findAll('table'):
            return {}

        link = tr.find('a')
        if link:
            href = link.get('href')
            if href:
                judgedict['href'] = href

        tds = tr.findAll('td')
        i = 0
        caseno = ''
        for td in tds:
            i += 1
            txt = utils.get_tag_contents(td)
            reobj = re.search('JUSTICE ', txt)
            if reobj:
                author = txt[reobj.end():]
                if author:
                    judgedict['author'] = author
            elif i == 2:
                judgedict['casetype'] = txt 
            elif i == 3:
                caseno += txt
            elif i == 4:
                caseno += '/%s' % txt
        if caseno:
            judgedict['caseno'] = caseno
            judgedict['title'] = caseno

        return judgedict

    def save_meta_tags(self, metapath, judgedict, dateobj):
        tagdict = {'date': utils.date_to_xml(dateobj)}
        for k in judgedict.keys():
            if k not in ['href']:
                tagdict[k] = judgedict[k]    
        utils.print_tag_file(metapath, tagdict) 
