from courtnic import Courtnic
import utils
import string
import urllib
import re

class Jodhpur(Courtnic):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        Courtnic.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.cookieurl = 'http://courtnic.nic.in/jodh/content.asp'
        self.courturl  = urllib.basejoin(self.baseurl, '/jodh/')
 
    def get_date_url(self, dateobj):
        qs = [('datef', utils.dateobj_to_str(dateobj, '-', reverse = True)), \
              ('selfday', utils.pad_zero(dateobj.day)), \
              ('selfmonth', utils.pad_zero(dateobj.month)), \
              ('selfyear', utils.pad_zero(dateobj.year)), \
			  ('B1', 'Search')  \
             ]
        query = string.join(['%s=%s' % (q[0], q[1]) for q in qs], '&')

        return self.courturl + 'dojqry.asp?' + query
  
    def action_on_url(self, url):
        if re.match('judfile.asp', url):
            return 'save'
        elif re.match('qrydoj.asp', url):
            return 'recurse'
        return 'ignore'


