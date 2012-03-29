import kolkata

class KolkataApp(kolkata.Kolkata):
    def __init__(self, name, rawdir, metadir, statsdir, updateMeta = False):
        kolkata.Kolkata.__init__(self, name, rawdir, metadir, statsdir, updateMeta)
        self.webformUrl = 'http://judis.nic.in/Judis_Kolkata_App/chrseq.aspx'
        self.dateqryUrl = 'http://judis.nic.in/Judis_Kolkata_App/Dt_Of_JudQry.aspx'
