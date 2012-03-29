import re
import getopt
import os
import sys
import datetime
import string
import logging

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
import orissa
import madhyapradesh 
import loksabha
import aptel
import cat
import itat
import tdsat
import cci
import greentribunal

def print_usage(progname):
    print '''Usage: %s [-d level(0: Critical 1: Err, 2: Warn, 3: Note, 4:Debug)]
                       [-m (updateMeta)]
                       [-f logfile]
                       [-t fromdate (DD-MM-YYYY)] [-T todate (DD-MM-YYYY)] 
                       [
                        -s supremecourt -s bombay -s kolkata -s punjab
                        -s kolkata_app -s delhi -s jharkhand -s rajasthan
                        -s jodhpur -s patna -s patna_orders -s gujarat
                        -s uttaranchal -s karnataka -s allahabad -s cic
                        -s orissa -s madhyapradesh -s loksabha -s aptel
                        -s cat_delhi      -s cat_ahmedabad -s cat_allahabad
                        -s cat_bangalore  -s cat_chandigarh -s cat_chennai
                        -s cat_cuttack    -s cat_ernakulam -s cat_guwahati 
                        -s cat_hyderabad  -s cat_jabalpur -s cat_jaipur
                        -s cat_lucknow -s cat_mumbai -s cat_patna -s cat_jodhpur
                        -s itat_delhi     -s itat_ahmedabad -s itat_mumbai
                        -s itat_chennai   -s itat_hyderabad -s itat_chandigarh
                        -s itat_kolkata   -s itat_lucknow   -s itat_bangalore
                        -s itat_agra      -s itat_indore    -s itat_rajkot
                        -s itat_bilaspur  -s itat_nagpur    -s itat_panji
                        -s itat_pune      -s itat_vizag     -s itat_hyderabad
                        -s itat_amritsar  -s itat_jodhpur   -s itat_jaipur
                        -s itat_cuttack   -s itat_gauhati   -s itat_patna 
                        -s itat_ranchi    -s itat_allahabad -s itat_jabalpur
                        -s itat_cochin 
                        -s aptel -s itat -s tdsat -s cci
                       ] datadir
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
    filename = None
    updateMeta = False
    optlist, remlist = getopt.getopt(sys.argv[1:], 'd:mf:p:t:T:hs:')
    for o, v in optlist:
        if   o == '-d':
            debuglevel = string.atoi(v)
        elif o == '-f':
            filename = v
        elif o == '-m':
            updateMeta = True 
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


    basedir  = remlist[0]
    rawdir   = os.path.join(basedir, 'raw')
    metadir  = os.path.join(basedir, 'metatags')
    statsdir = os.path.join(basedir, 'stats')

    utils.mk_dir(rawdir)
    utils.mk_dir(metadir)
    utils.mk_dir(statsdir)

    courtobjs = []
    dldict = {'bombay'        : bombay.Bombay,               \
              'kolkata'       : kolkata.Kolkata,             \
              'kolkata_app'   : kolkata_app.KolkataApp,      \
              'punjab'        : punjab.Punjab,               \
              'uttaranchal'   : uttaranchal.Uttaranchal,     \
              'delhi'         : delhi.Delhi,                 \
              'jharkhand'     : jharkhand.Jharkhand,         \
              'gujarat'       : gujarat.Gujarat,             \
              'rajasthan'     : rajasthan.Rajasthan,         \
              'jodhpur'       : jodhpur.Jodhpur,             \
              'karnataka'     : karnataka.Karnataka,         \
              'supremecourt'  : supremecourt.SupremeCourt,   \
              'patna'         : patna.Patna,                 \
              'patna_orders'  : patna_orders.PatnaOrders,    \
              'allahabad'     : allahabad.Allahabad,         \
              'cic'           : cic.CIC,                     \
              'orissa'        : orissa.Orissa,               \
			  'madhyapradesh' : madhyapradesh.MadhyaPradesh, \
              'aptel'         : aptel.Aptel,                 \
              'cat_delhi'     : cat.CatDelhi,                \
              'cat_ahmedabad' : cat.CatAhmedabad,            \
              'cat_allahabad' : cat.CatAllahabad,            \
              'cat_bangalore' : cat.CatBangalore,            \
              'cat_chandigarh': cat.CatChandigarh,           \
              'cat_chennai'   : cat.CatChennai,              \
              'cat_cuttack'   : cat.CatCuttack,              \
              'cat_ernakulam' : cat.CatErnakulam,            \
              'cat_guwahati'  : cat.CatGuwahati,             \
              'cat_hyderabad' : cat.CatHyderabad,            \
              'cat_jabalpur'  : cat.CatJabalpur,             \
              'cat_jaipur'    : cat.CatJaipur,               \
              'cat_lucknow'   : cat.CatLucknow,              \
              'cat_mumbai'    : cat.CatMumbai,               \
              'cat_patna'     : cat.CatPatna,                \
              'cat_jodhpur'   : cat.CatJodhpur,              \
              'itat_delhi'    : itat.ItatDelhi,              \
              'itat_ahmedabad': itat.ItatAhmedabad,          \
              'itat_mumbai'   : itat.ItatMumbai,             \
              'itat_chennai'  : itat.ItatChennai,            \
              'itat_hyderabad': itat.ItatHyderabad,          \
              'itat_chandigarh': itat.ItatChandigarh,        \
              'itat_kolkata'  : itat.ItatKolkata,            \
              'itat_lucknow'  : itat.ItatLucknow,            \
              'itat_bangalore': itat.ItatBangalore,          \
              'itat_agra'     : itat.ItatAgra,               \
              'itat_indore'   : itat.ItatIndore,             \
              'itat_rajkot'   : itat.ItatRajkot,             \
              'itat_bilaspur' : itat.ItatBilaspur,           \
              'itat_nagpur'   : itat.ItatNagpur,             \
              'itat_panji'    : itat.ItatPanji,              \
              'itat_pune'     : itat.ItatPune,               \
              'itat_vizag'    : itat.ItatVizag,              \
              'itat_hyderabad': itat.ItatHyderabad,          \
              'itat_amritsar' : itat.ItatAmritsar,           \
              'itat_jodhpur'  : itat.ItatJodhpur,            \
              'itat_jaipur'   : itat.ItatJaipur,             \
              'itat_cuttack'  : itat.ItatCuttack,            \
              'itat_gauhati'  : itat.ItatGauhati,            \
              'itat_patna'    : itat.ItatPatna,              \
              'itat_ranchi'   : itat.ItatRanchi,             \
              'itat_allahabad': itat.ItatAllahabad,          \
              'itat_jabalpur' : itat.ItatJabalpur,           \
              'itat_cochin'   : itat.ItatCochin,             \
              'tdsat'         : tdsat.Tdsat,                 \
              'cci'           : cci.Cci,                     \
              'greentribunal' : greentribunal.GreenTribunal, \
              'loksabha'      : loksabha.LokSabha            \
             }

    if not srclist:
        srclist = dldict.keys()

    leveldict = {0: logging.CRITICAL, 1: logging.ERROR, 2: logging.WARNING, \
                 3:logging.INFO, 4: logging.DEBUG}


    logging.basicConfig(\
        level   = leveldict[debuglevel], \
        format  = '%(asctime)s: %(name)s: %(levelname)s %(message)s', \
        datefmt = '%Y-%m-%d %H:%M:%S' \
    )

    if filename:
        logging.basicConfig(filename = os.path.join(statsdir, filename))

    for src in srclist:
        if dldict.has_key(src):
            if src == 'supremecourt':
                srcdir = 'judis.nic.in'
            else:
                srcdir = src

            obj = dldict[src](srcdir, rawdir, metadir, statsdir, updateMeta)
        else:
            print >> sys.stderr, 'Court %s not yet present' % src
            sys.exit(1)
        courtobjs.append(obj)

    for obj in courtobjs:
        dls = obj.sync(fromdate, todate)

        print 'Downloads from %s' % obj.name
        for dl in dls: 
            print dl
