import re
import getopt
import os
import sys
import datetime
import string

import utils
import supremecourt
import bombay
import kolkata
import kolkata_app
import punjab
import uttaranchal
import delhi
import jharkhand
import gujarat
import rajasthan
import jodhpur
import karnataka
import patna
import patna_orders
import allahabad
import cic

def print_usage(progname):
    print '''Usage: %s [-d debuglevel(0: Err, 1: Warn, 2: Note)]
                       [-t fromdate (DD-MM-YYYY)] [-T todate (DD-MM-YYYY)] 
                       [-s supremecourt -s bombay -s kolkata -s punjab
                        -s kolkata_app -s delhi -s jharkhand -s rajasthan
                        -s jodhpur -s patna -s patna_orders -s gujarat
                        -s uttaranchal -s karnataka -s allahabad -s cic] datadir
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

    debuglevel = 0
    progname = sys.argv[0]
    optlist, remlist = getopt.getopt(sys.argv[1:], 'd:p:t:T:hs:')
    for o, v in optlist:
        if   o == '-d':
            debuglevel = string.atoi(v)
        elif o == '-t':
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


    basedir = remlist[0]
    rawdir  = os.path.join(basedir, 'raw')
    metadir = os.path.join(basedir, 'metatags')

    utils.mk_dir(rawdir)
    utils.mk_dir(metadir)

    courtobjs = []
    dldict = {'bombay':      bombay.Bombay, \
              'kolkata':     kolkata.Kolkata, \
              'kolkata_app': kolkata_app.KolkataApp, \
              'punjab':      punjab.Punjab, \
              'uttaranchal': uttaranchal.Uttaranchal, \
              'delhi':       delhi.Delhi, \
              'jharkhand':   jharkhand.Jharkhand, \
              'gujarat':     gujarat.Gujarat,
              'rajasthan':   rajasthan.Rajasthan, \
              'jodhpur':     jodhpur.Jodhpur, \
              'karnataka':   karnataka.Karnataka, \
              'supremecourt': supremecourt.SupremeCourt, \
              'patna':        patna.Patna, \
              'patna_orders': patna_orders.PatnaOrders, \
              'allahabad'   : allahabad.Allahabad, \
              'cic'         : cic.CIC \
             }

    if not srclist:
        srclist = dldict.keys()

    for src in srclist:
        if dldict.has_key(src):
            if src == 'supremecourt':
                srcdir = 'judis.nic.in'
            else:
                srcdir = src
            logger = utils.Logger(debuglevel)
            obj = dldict[src](srcdir, rawdir, metadir, logger)
        else:
            print >> sys.stderr, 'Court %s not yet present' % src
            sys.exit(1)
        courtobjs.append(obj)

    for obj in courtobjs:
        dls = obj.sync(fromdate, todate)

        print 'Downloads from %s' % obj.name
        for dl in dls: 
            print dl
