import lobis
import utils

class Punjab(lobis.Lobis):
    def __init__(self, name, datadir, DEBUG=True):
        lobis.Lobis.__init__(self, name, datadir, DEBUG)
        self.baseurl   = 'http://lobis.nic.in'
        self.courturl  = self.baseurl + '/phhc'
        self.cookieurl = self.baseurl + '/phhc/juddt.php?scode=28'
        self.dateurl   = self.baseurl + '/phhc/juddt1.php?dc=28&fflag=1'

    def date_in_form(self, dateobj):
        return [('juddt', '%s/%s/%s' % (utils.pad_zero(dateobj.day), \
                                        utils.pad_zero(dateobj.month), \
                                        utils.pad_zero(dateobj.year)) \
               )]
        
