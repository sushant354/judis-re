import lobis

class Uttaranchal(lobis.Lobis):
    def __init__(self, name, datadir, DEBUG=True):
        lobis.Lobis.__init__(self, name, datadir, DEBUG)
        self.baseurl   = 'http://lobis.nic.in'
        self.courturl  = self.baseurl + '/uhc'
        self.cookieurl = self.baseurl + '/uhc/juddt.php?scode=35'
        self.dateurl   = self.baseurl + '/uhc/juddt1.php?dc=35&fflag=1'
