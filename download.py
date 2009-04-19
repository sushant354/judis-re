import re
import getopt
import os
import sys
import datetime
import string

import supremecourt
import bombay
import kolkata
import kolkata_app
import punjab
import uttaranchal

def print_usage(progname):
    print '''Usage: %s [-t fromdate (DD-MM-YYYY)] [-T todate (DD-MM-YYYY)] 
                       [-s supremecourt -s bombay -s kolkata -s punjab
                        -s kolkata_app] datadir
          ''' % progname
    print 'The program will download court judgments from judis'
    print 'and will place in a specified directory. Judgments will be'
    print 'placed into directories named by dates. If fromdate or todate'
    print 'is not specified then the default is your current date.'

def to_datetime(datestr):
    numlist = re.findall('\d+', datestr)
    if len(numlist) != 3:
        print >>sys.stderr, '%s not in correct format [DD/MM/YYYY]' % datestr
        return None
    else:
        datelist = []
        for num in numlist:
            datelist.append(string.atoi(num))
        return datetime.datetime(datelist[2], datelist[1], datelist[0])

if __name__ == '__main__':
    #initial values

    fromdate = None
    todate   = None
    srclist  = []

    progname = sys.argv[0]
    optlist, remlist = getopt.getopt(sys.argv[1:], 'p:t:T:hs:')
    for o, v in optlist:
        if o == '-t':
            fromdate =  to_datetime(v)
        elif o == '-T':
            todate   = to_datetime(v)
        elif o == '-s':
            srclist.append(v)                  
        else:
            print_usage(progname)
            sys.exit(0)

    if len(remlist) != 1:
        print_usage(progname)
        sys.exit(0) 

    if fromdate == None:
        if todate == None:
            todate   = datetime.datetime.today() 
            fromdate = todate - datetime.timedelta(days = 7)
        else:
            fromdate = todate

    elif todate == None:
        todate = fromdate 

    if len(srclist) <= 0:
        srclist = ['supremecourt']

    datadir = remlist[0]

    courtobjs = []
    for src in srclist:
        if src == 'supremecourt':
            obj = supremecourt.SupremeCourt('judis.nic.in', datadir)
        elif src == 'bombay':
            obj = bombay.Bombay(src, datadir)
        elif src == 'goa':
            obj = goa.Goa(src, datadir)
        elif src == 'kolkata':
            obj = kolkata.Kolkata(src, datadir)
        elif src == 'kolkata_app':
            obj = kolkata_app.KolkataApp(src, datadir)
        elif src == 'punjab':
            obj = punjab.Punjab(src, datadir)
        elif src == 'uttaranchal':
            obj = uttaranchal.Uttaranchal(src, datadir)
        else:
            print >> sys.stderr, 'Court %s not yet present' % src
            sys.exit(1)
        courtobjs.append(obj)

    for obj in courtobjs:
        dls = obj.sync(fromdate, todate)

        print 'New downloads from %s' % obj.name
        for dl in dls: 
            print dl
