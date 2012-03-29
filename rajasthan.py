from courtnic import Courtnic
import utils
import string
import urllib
import re

class Rajasthan(Courtnic):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        Courtnic.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.courturl  = urllib.basejoin(self.baseurl, '/rajasthan/')
        self.cookieurl = urllib.basejoin(self.courturl, '/content.asp')

    def get_date_url(self, dateobj):
        qs = [ \
              ('datef', utils.dateobj_to_str(dateobj, '-', reverse = True)), \
              ('datet', utils.dateobj_to_str(dateobj, '-', reverse = True)), \
              ('selfday', utils.pad_zero(dateobj.day)), \
              ('selfmonth', utils.pad_zero(dateobj.month)), \
              ('selfyear', utils.pad_zero(dateobj.year)), \
              ('seltday', utils.pad_zero(dateobj.day)), \
              ('seltmonth', utils.pad_zero(dateobj.month)), \
              ('seltyear', utils.pad_zero(dateobj.year)), \
              ('B1', 'Search')  \
             ]  
        query = string.join(['%s=%s' % (q[0], q[1]) for q in qs], '&')

        dateurl = self.courturl + 'dojqry.asp' + '?' + query
        return dateurl

    def action_on_url(self, relurl):
        if re.match('judfile.asp', relurl):
            return 'ignore'
        elif re.match('jtextfile.asp', relurl):
            return 'save'
        elif re.match('qrydoj.asp', relurl):
            return 'recurse' 
            
