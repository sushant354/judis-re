import lobis

class Punjab(lobis.Lobis):
    def __init__(self, name, datadir, DEBUG=True):
        lobis.Lobis.__init__(self, name, datadir, DEBUG)
        self.baseurl   = 'http://lobis.nic.in'
        self.courturl  = self.baseurl + '/phhc'
        self.cookieurl = self.baseurl + '/phhc/juddt.php?scode=28'
        self.dateurl   = self.baseurl + '/phhc/juddt1.php?dc=28&fflag=1'

        
