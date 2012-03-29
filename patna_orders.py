import urllib
import calendar

import utils
from patna import Patna
import datetime

class PatnaOrders(Patna):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        Patna.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.dateurl = urllib.basejoin(self.baseurl, \
                                       '/judgment/OrdrDateWise.aspx')
        self.formaction = 'OrdrDateWise.aspx'

    def base_post_data(self, dateobj):
        monthname = calendar.month_name[dateobj.month]
        monthname = monthname[:3]

        postdata = \
          [
            ('ctl00$ContentPlaceHolder1$dd1', '%d' % dateobj.day), \
            ('ctl00$ContentPlaceHolder1$mm1', monthname), \
            ('ctl00$ContentPlaceHolder1$yy1', '%d' % dateobj.year) \
          ]
        return postdata

    def get_meta_info(self, tr, dateobj):
        metainfo = { 'date': utils.date_to_xml(dateobj) }
        tds = tr.findAll('td')

        i = 0
        for td in tds:
            content = utils.get_tag_contents(td)

            if i == 1:
                metainfo['caseno'] = content

            elif i == 2:
                metainfo['petitioner'] = content
                metainfo['title']      = content 
            elif i == 3:
                metainfo['respondent'] = content
                if metainfo.has_key('title'):
                     metainfo['title']  += ' ' + content 
                else:
                    metainfo['title']    = content 

            i += 1
        return metainfo

if __name__ == '__main__':
    patna = PatnaOrders('patna_orders', '/home/sushant/dls/raw', '/home/sushant/dls/metatags', 2)

    print patna.result_page('patna/2010-01-06', open('webpage', 'r').read(), datetime.datetime(2010, 1, 6), 1)
