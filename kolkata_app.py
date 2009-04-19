import kolkata

class KolkataApp(kolkata.Kolkata):
    def __init__(self, name, datadir, DEBUG = True):
        kolkata.Kolkata.__init__(self, name, datadir, DEBUG)
        self.baseurl = 'http://www.judis.nic.in/Kolkata_App'
