import kolkata

class KolkataApp(kolkata.Kolkata):
    def __init__(self, name, rawdir, metadir, logger):
        kolkata.Kolkata.__init__(self, name, rawdir, metadir, logger)
        self.baseurl = 'http://www.judis.nic.in/Kolkata_App'
