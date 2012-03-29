import lobis
import urllib
import utils

class Uttaranchal(lobis.Lobis):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        lobis.Lobis.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.baseurl   = 'http://lobis.nic.in/'
        self.courturl  = urllib.basejoin(self.baseurl, '/uhc')
        self.cookieurl = urllib.basejoin(self.baseurl, '/uhc/juddt.php?scode=35')
        self.dateurl   = urllib.basejoin(self.baseurl, '/uhc/juddt1.php?dc=35&fflag=1')

    def date_in_form(self, dateobj):
        return [('juddt', utils.dateobj_to_str(dateobj, '/'))]
