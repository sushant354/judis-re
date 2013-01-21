import lobis
import utils
import urllib
import calendar

class Punjab(lobis.Lobis):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        lobis.Lobis.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.baseurl   = 'http://lobis.nic.in/'
        self.courturl  = urllib.basejoin(self.baseurl, '/phhc/')
        self.cookieurl = urllib.basejoin(self.baseurl, \
                                         '/phhc/juddt.php?scode=28')
        self.dateurl   = urllib.basejoin(self.baseurl, \
                                         '/phhc/juddt1.php?dc=28&fflag=1')

    def get_date_string(self, dateobj):
        return '%s/%s/%s' % (utils.pad_zero(dateobj.day), \
                             calendar.month_abbr[dateobj.month].lower(), \
                             utils.pad_zero(dateobj.year))

    def date_in_form(self, dateobj):
         # juddtfr=01-jun-12&juddtto=01-jul-12
        return [('juddtfr', self.get_date_string(dateobj)), 
                ('juddtto', self.get_date_string(dateobj))
               ]
        
