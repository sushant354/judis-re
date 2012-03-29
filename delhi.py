import lobis
import utils

class Delhi(lobis.Lobis):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        lobis.Lobis.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.baseurl   = 'http://lobis.nic.in'
        self.courturl  = self.baseurl + '/dhc'
        self.cookieurl = self.baseurl + '/dhc/juddt.php?scode=31'
        self.dateurl   = self.baseurl + '/dhc/juddt1.php?dc=31&fflag=1'

    def date_in_form(self, dateobj):
        return [('jday',   utils.pad_zero(dateobj.day)),   \
                ('jmonth', utils.pad_zero(dateobj.month)), \
                ('jyear',  utils.pad_zero(dateobj.year))   \
               ]
