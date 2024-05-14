# -*- coding: utf-8 -*-
import os
import argparse
import datetime
import io
import gzip
import csv
import uuid
from timeit import default_timer as timer

appname = 'mesh-trx2nt'
appversion = '1.1.1 14-5-2024'
appdesc = 'Extracting translation dataset from NLM UMLS text file [trans_only_2023_expanded.txt]'
appusage = 'Help:   ' + appname + '.py -h \n'
appauthor = 'Filip Kriz'

mesh_prefix = 'http://id.nlm.nih.gov/mesh/'
mesht_prefix = 'http://www.medvik.cz/schema/mesh/vocab/#'

custom_concepts = {}


def main():

    print('\n')
    print('********************************************')
    print('*  ', appname, appversion)
    print('********************************************')
    print('*  ', appdesc)
    print('*  ', appusage)
    print('*   Author:  ', appauthor)
    print('********************************************\n')

    parser = argparse.ArgumentParser(description=appdesc, prog=appname, usage='%(prog)s inputFile langCode meshxPrefix [options]')
    parser.add_argument('inputFile', type=str, help='NLM UMLS text file name (plain or gzipped)')
    parser.add_argument('langCode', type=str, help='Language code')
    parser.add_argument('meshxPrefix', type=str, help='MeSH Translation namespace prefix ie. http://my.mesh.com/id/ ')
    parser.add_argument('--out', type=str, default='mesh-trx', help='Output file name prefix')

    args, unknown = parser.parse_known_args()

    if unknown:
        print('ERROR : Uknown arguments : ', unknown)
        print('Try : ' + appname + '.py -h')

    else:
        inFile = os.path.normpath(args.inputFile)

        if os.path.isfile(inFile):
            procFile(inFile, args.meshxPrefix, args.out, args.langCode)
        else:
            print('ERROR : Input file NOT found : ', args.inputFile)


def procFile(inputFile, meshxPrefix, outputFile, lang_tag):

    t0 = timer()
    startTime = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d_%H-%M-%S')
    startDate = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')

    meshx_prefix = meshxPrefix

    outputFile = outputFile + '-' + lang_tag + '_' + startDate + '.nt.gz'

    print('Started     : ', startTime, '\n')
    print('Input file  : ', inputFile)
    print('Lang code   : ', lang_tag)
    print('mesht       : ', mesht_prefix)
    print('meshx       : ', meshx_prefix)
    print('Output file : ', outputFile)
    print('\n')

    head = '### MeSH translation dataset extracted from NLM UMLS text file ###\n'
    writeOutputGzip(outputFile, head)

    result = parse_file(inputFile, outputFile, meshx_prefix, lang_tag, startDate)
    print('\n', result)

    # endTime = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d_%H-%M-%S')
    et = ('\nElapsed time : ' + str((timer() - t0) / 60) + ' min\n')
    print(et)


def parse_file(inputFile, outputFile, meshx_prefix, lang_tag, startDate):
    result = {}

    recCount = 0
    batch = 0
    bsize = 1000

    docs = []

    print('Processing ...')

    result['LanguageTag'] = lang_tag

    for line in readData(inputFile):

        if recCount == 0 and line[0] == 'DescriptorUI':
            # Skip headers if present
            pass
        else:
            recCount += 1
            batch += 1

            docs += getTriples(line, lang_tag, meshx_prefix, startDate)
            # docs += line

            if batch == bsize:
                flushTriples(outputFile, docs)
                batch = 0
                docs = []

    flushTriples(outputFile, docs)
    # for row in docs:
    #     print(row)

    result['rowCount'] = recCount

    print('... DONE!')
    return result


def getTriples(line, lang_tag, meshx_prefix, startDate):
    triples = []

    DescriptorUI, ConceptUI, Language, TermType, Term, TermUI, ScopeNote, Tree, Created, Relation, ParentCUI = line

    csub = mesh_prefix + ConceptUI
    obj = meshx_prefix + str(uuid.uuid4())

    if not Created:
        Created = startDate

    if ConceptUI.startswith('F'):

        if custom_concepts.get(ConceptUI):
            ccid = custom_concepts.get(ConceptUI)
        else:
            ccid = str(uuid.uuid4())
            custom_concepts[ConceptUI] = ccid

        ccsub = meshx_prefix + ccid

        if TermType == 'PEP':
            dsub = mesh_prefix + DescriptorUI
            csub = mesh_prefix + ParentCUI

            triples.append(getTriple(dsub, 'concept', ccsub))
            triples.append(getTriple(csub, getRelationPredicate(Relation), ccsub))
            triples.append(getTriple(ccsub, 'identifier', ConceptUI, literal=True))
            triples.append(getTriple(ccsub, 'preferredTerm', obj))

            if ScopeNote:
                triples.append(getTriple(ccsub, 'scopeNote', ScopeNote, literal=True, lang_tag=lang_tag))

        elif TermType == 'ET':
            triples.append(getTriple(ccsub, 'term', obj))

    else:
        if TermType in ['MH', 'PEP']:
            triples.append(getTriple(csub, 'preferredTerm', obj))

            if ScopeNote:
                triples.append(getTriple(csub, 'scopeNote', ScopeNote, literal=True, lang_tag=lang_tag))

        elif TermType == 'ET':
            triples.append(getTriple(csub, 'term', obj))

    triples.append(getTriple(obj, 'prefLabel', Term, literal=True, lang_tag=lang_tag))
    triples.append(getTriple(obj, 'dateCreated', Created, date=True))

    return triples


def getRelationPredicate(Relation):
    if Relation == 'RB':
        return 'broaderConcept'
    elif Relation == 'RN':
        return 'narrowerConcept'
    elif Relation == 'RO':
        return 'relatedConcept'
    else:
        return 'narrowerConcept'


def getTriple(sub, pred, obj, literal=False, date=False, lang_tag=None):
    sub = '<' + sub + '>'
    if literal:
        if lang_tag:
            return sub + getMesht(pred) + '"' + sanitize_input(obj) + '"@' + lang_tag
        else:
            return sub + getMesht(pred) + '"' + sanitize_input(obj) + '"'

    if date:
        return sub + getMesht(pred) + '"' + obj + '"^^<http://www.w3.org/2001/XMLSchema#date>'

    return sub + getMesht(pred) + '<' + obj + '>'


def getMesht(predicate):
    return ' <' + mesht_prefix + predicate + '> '


def sanitize_input(text):
    t = text.strip()
    t = ' '.join(t.split())
    t = t.replace('?', '')
    t = t.replace('"', '\\"')
    return t


def readData(input_file):

    fext = os.path.splitext(input_file)[1]
    tsv_file = None
    data = []

    try:
        if fext == '.gz':
            with gzip.open(input_file, mode='rt', encoding='utf-8') as fh:
                tsv_file = csv.reader(fh, delimiter='\t', quotechar=None)
                for line in tsv_file:
                    if len(line):
                        if line[0].startswith('#'):
                            pass
                        else:
                            data.append(line)

        if fext == '.txt':
            with open(input_file, mode='r', encoding='utf-8') as fh:
                tsv_file = csv.reader(fh, delimiter='\t', quotechar=None)
                for line in tsv_file:
                    if len(line):
                        if line[0].startswith('#'):
                            pass
                        else:
                            data.append(line)

    except:  # noqa: E722
        print('ERROR reading file : ', input_file)
        raise

    return data


def flushTriples(outputFile, docs):
    s = io.StringIO()

    for line in docs:
        s.write(line+' .\n')

    writeOutputGzip(outputFile, s.getvalue(), mode='at')
    s.close()


def writeOutputGzip(outputFile, fdata, mode='wt'):
    with gzip.open(outputFile, mode=mode, encoding='utf-8') as ft:
        ft.write(fdata)


if __name__ == '__main__':
    main()
