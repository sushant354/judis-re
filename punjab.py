import lobis
import utils
import urllib

class Punjab(lobis.Lobis):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        lobis.Lobis.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.baseurl   = 'http://lobis.nic.in/'
        self.courturl  = urllib.basejoin(self.baseurl, '/phhc/')
        self.cookieurl = urllib.basejoin(self.baseurl, \
                                         '/phhc/juddt.php?scode=28')
        self.dateurl   = urllib.basejoin(self.baseurl, \
                                         '/phhc/juddt1.php?dc=28&fflag=1')

    def date_in_form(self, dateobj):
        return [('juddt', '%s/%s/%s' % (utils.pad_zero(dateobj.day), \
                                        utils.pad_zero(dateobj.month), \
                                        utils.pad_zero(dateobj.year)) \
               )]
        
