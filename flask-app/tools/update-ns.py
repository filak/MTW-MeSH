# -*- coding: utf-8 -*-
import os
import argparse
import datetime
import io
import gzip
from timeit import default_timer as timer

appname = 'mesh-nt-update-ns'
appversion = '1.0.1 22-1-2025'
appdesc = 'Update MeSH namespace'
appusage = 'Help:   ' + appname + '.py -h \n'
appauthor = 'Filip Kriz'

# mesh_ns_prefix = 'http://id.nlm.nih.gov/mesh/'


def main():

    print('\n')
    print('********************************************')
    print('*  ', appname, appversion)
    print('********************************************')
    print('*  ', appdesc)
    print('*  ', appusage)
    print('*   Author:  ', appauthor)
    print('********************************************\n')

    parser = argparse.ArgumentParser(description=appdesc, prog=appname, usage='%(prog)s inputFile')
    parser.add_argument('inputFile', type=str, help='MeSH N-Triples input file')
    parser.add_argument("ns_old", help="Namespace URI")
    parser.add_argument("ns_new", help="New namespace URI")
    parser.add_argument('outputFile', type=str, help='Output file')
    # parser.add_argument('--add-active', help='Add status active=true triples', action='store_true')

    args, unknown = parser.parse_known_args()

    if unknown:
        print('ERROR : Uknown arguments : ', unknown)
        print('Try : ' + appname + '.py -h')

    else:
        inFile = os.path.normpath(args.inputFile)

        if os.path.isfile(inFile):
            getOutput(inFile, args.ns_old, args.ns_new, args.outputFile)
        else:
            print('ERROR : Input file NOT found : ', args.inputFile)


def getOutput(inputFile, ns_old, ns_new, outputFile):

    t0 = timer()
    startTime = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d_%H-%M-%S')
    startDate = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')

    print('Started     : ', startTime, '\n')
    print('Input file  : ', inputFile)
    print('NS Old      : ', ns_old)
    print('NS New      : ', ns_new)
    print('Output file : ', outputFile)
    print('\n')

    head = f'### Replaced {ns_old} with {ns_new} ###\n'
    writeOutputGzip(outputFile, head)

    result = updateNS(inputFile, ns_old, ns_new, outputFile)
    print('\n', result)

    # endTime = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d_%H-%M-%S')
    et = ('\nElapsed time : ' + str((timer() - t0) / 60) + ' min\n')
    print(et)


def updateNS(inputFile, ns_old, ns_new, outputFile):
    result = {}
    mesh_ns_old = '<' + ns_old
    mesh_ns_new = '<' + ns_new

    count = 0
    batch = 0
    bsize = 64000

    ext = os.path.splitext(inputFile)[1]
    fext = ext.lower()

    print('Processing ... ')

    if fext == '.gz':
        fh = gzip.open(inputFile, mode='rt', encoding='utf-8')
    else:
        fh = open(inputFile, mode='r', encoding='utf-8')

    s = io.StringIO()

    for line in fh:
        count += 1
        batch += 1
        s.write(line.replace(mesh_ns_old, mesh_ns_new))

        if batch == bsize:
            writeOutputGzip(outputFile, s.getvalue())
            batch = 0
            s.close()
            s = io.StringIO()

    fh.close()

    if s.getvalue():
        writeOutputGzip(outputFile, s.getvalue())

    s.close()

    result['triplesCount'] = count

    print('... DONE!')
    return result


def writeOutputGzip(outputFile, fdata, mode='wt'):

    with gzip.open(outputFile, mode=mode, encoding='utf-8') as ft:
        ft.write(fdata)

if __name__ == '__main__':
    main()

