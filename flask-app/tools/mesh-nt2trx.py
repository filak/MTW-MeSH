# -*- coding: utf-8 -*-
import os, sys, argparse, string, datetime, time, io, gzip
from timeit import default_timer as timer

appname = 'mesh-nt2trx'
appversion = '1.4 13-3-2019'
appdesc = 'Extracting translation dataset from Fuseki backup dump'
appusage = 'Help:   '+ appname +'.py -h \n'
appauthor = 'Filip Kriz'

mesht_prefix = 'http://www.medvik.cz/schema/mesh/vocab/#'

def main():

    print('\n')
    print('********************************************')
    print('*  ', appname, appversion)
    print('********************************************')
    print('*  ', appdesc)
    print('*  ', appusage)
    print('*   Author:  ', appauthor)
    print('********************************************\n')

    parser = argparse.ArgumentParser(description=appdesc, prog=appname, usage='%(prog)s inputFile [options]')
    parser.add_argument('inputFile', type=str, help='MTW dump file name (plain or gzipped)')
    parser.add_argument('--out', type=str, default='mtw-trx', help='Output file name')

    args, unknown = parser.parse_known_args()

    if unknown:
        print('ERROR : Uknown arguments : ', unknown)
        print('Try : '+ appname  +'.py -h')

    else:
        inFile = os.path.normpath(args.inputFile)

        if os.path.isfile(inFile):
            getSubset(inFile, args.out)
        else:
            print('ERROR : Bad input file : ', args.inputFile)


def getSubset(inputFile, outputFile):

    t0 = timer()
    startTime = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d_%H-%M-%S')
    startDate = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')

    outputFile = outputFile + '_' + startDate + '.nt.gz'

    print('Started     : ', startTime, '\n')
    print('Input file  : ', inputFile)
    print('mesht       : ', mesht_prefix)
    print('Output file : ', outputFile)
    print('\n')

    head = '### MeSH translation dataset extracted from Fuseki backup dump ###\n'
    writeOutputGzip(outputFile, head)

    result = getSubsetFrom(inputFile, outputFile)
    print('\n', result)

    endTime = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d_%H-%M-%S')
    et = ('\nElapsed time : ' + str((timer() - t0) / 60) + ' min\n')
    print(et)


def getSubsetFrom(inputFile, outputFile):

    result = {}
    mesht_pred = ' <' + mesht_prefix

    count = 0
    found = 0
    batch = 0

    bsize = 64000

    ext = os.path.splitext(inputFile)[1]
    fext = ext.lower()

    print('Processing ...')

    if fext == '.gz':
        fh = gzip.open(inputFile, mode='rt', encoding='utf-8')
    else:
        fh = open(inputFile, mode='r', encoding='utf-8')

    s = io.StringIO()

    for line in fh:
        count += 1

        if mesht_pred in line:
            found += 1
            batch += 1
            s.write(line)

        if batch == bsize:
            writeOutputGzip(outputFile, s.getvalue(), mode='at')
            batch = 0
            s.close()
            s = io.StringIO()

    fh.close()
    writeOutputGzip(outputFile, s.getvalue(), mode='at')
    s.close()

    result['triplesCount'] = count
    result['triplesFound'] = found

    print('... DONE!')
    return result


def writeOutputGzip(outputFile, fdata, mode='wt'):

    with gzip.open(outputFile, mode=mode, encoding='utf-8') as ft:
        ft.write(fdata)


if __name__ == '__main__':
    main()
