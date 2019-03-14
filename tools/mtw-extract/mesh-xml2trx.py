# -*- coding: utf-8 -*-
import os, sys, argparse, string, datetime, time, io, gzip
from timeit import default_timer as timer
import xml.etree.ElementTree as ET

appname = 'mesh-xml2trx'
appversion = '1.4 14-3-2019'
appdesc = 'Extracting translation dataset from MeSH XML'
appusage = 'Help:   '+ appname +'.py -h \n'
appauthor = 'Filip Kriz'

mesh_prefix  = 'http://id.nlm.nih.gov/mesh/'
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

    parser = argparse.ArgumentParser(description=appdesc, prog=appname, usage='%(prog)s inputFile meshxPrefix [options]')
    parser.add_argument('inputFile', type=str, help='MeSH XML file name (plain or gzipped)')
    parser.add_argument('meshxPrefix', type=str, help='MeSH Translation namespace prefix ie. http://mesh.medvik.cz/link/ ')
    parser.add_argument('--out', type=str, default='mesh-trx', help='Output file')

    args, unknown = parser.parse_known_args()

    if unknown:
        print('ERROR : Uknown arguments : ', unknown)
        print('Try : '+ appname  +'.py -h')

    else:
        inFile = os.path.normpath(args.inputFile)

        if os.path.isfile(inFile):
            getSubset(inFile, args.meshxPrefix, args.out)
        else:
            print('ERROR : Bad input file : ', args.inputFile)


def getSubset(inputFile, meshxPrefix, outputFile):

    t0 = timer()
    startTime = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d_%H-%M-%S')
    startDate = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')

    meshx_prefix = meshxPrefix

    outputFile = outputFile + '_' + startDate + '.nt.gz'

    print('Started     : ', startTime, '\n')
    print('Input file  : ', inputFile)
    print('mesht       : ', mesht_prefix)
    print('meshx       : ', meshx_prefix)
    print('Output file : ', outputFile)
    print('\n')

    head = '### MeSH translation dataset extracted from MeSH XML ###\n'
    writeOutput(outputFile, head)

    result = parse_xml(inputFile, outputFile, meshx_prefix)
    print('\n', result)

    endTime = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d_%H-%M-%S')
    et = ('\nElapsed time : ' + str((timer() - t0) / 60) + ' min\n')
    print(et)



def parse_xml(inputFile, outputFile, meshx_prefix):
    result = {}

    recCount = 0
    batch = 0
    bsize = 1000

    docs = []

    print('Processing ...')
    try:
        root = getRoot(inputFile)
    except:
        raise

    lang_code = root.attrib['LanguageCode']
    lang_tag = getLangTag(lang_code)
    result['LanguageCode'] = lang_code
    result['LanguageTag'] = lang_tag

    for rec in root.findall('DescriptorRecord'):
        recCount += 1
        batch += 1

        docs += getTriples(rec, lang_code, lang_tag, meshx_prefix)

        rec.clear()

        if batch == bsize:
            flushTriples(outputFile, docs)
            batch = 0
            docs = []

    flushTriples(outputFile, docs)
    ##for row in docs:
    ##    print(row)

    root.clear()

    result['recordsCount'] = recCount

    print('... DONE!')
    return result


def getTriples(rec, lang_code, lang_tag, meshx_prefix):
    triples = []

    dui = rec.find('DescriptorUI').text.strip()
    dsub = '<' + mesh_prefix + dui + '>'

    for concept in rec.findall('ConceptList/Concept'):

        cui = concept.find('ConceptUI').text.strip()
        cpref = concept.attrib['PreferredConceptYN']

        cui = concept.find('ConceptUI').text.strip()
        if cui.startswith('F'):
            csub = '<' + meshx_prefix + cui + '>'
            triples.append(dsub + getMesht('concept') + csub)
            triples.append(csub + getMesht('identifier') + '"' + cui + '"')

            rels = concept.find('ConceptRelationList/ConceptRelation')
            rel = rels.attrib['RelationName']

            if rel == 'NRW':
                relPred = 'narrowerConcept'
            elif rel == 'BRD':
                relPred = 'narrowerConcept'
            elif rel == 'REL':
                relPred = 'relatedConcept'
            else:
                relPred = ''

            if relPred:
                sub = '<' + mesh_prefix + rels.find('Concept1UI').text.strip() + '>'
                pred = getMesht(relPred)
                obj = '<' + meshx_prefix + rels.find('Concept2UI').text.strip() + '>'
                triples.append(sub + pred + obj)

        else:
            csub = '<' + mesh_prefix + cui + '>'

        trxScn = concept.find('TranslatorsScopeNote')
        if trxScn is not None:
            scn = sanitize_input(trxScn.text)
            triples.append(csub + getMesht('scopeNote') + '"' + scn + '"@' + lang_tag)

        for term in concept.findall('TermList/Term'):

            prefTerm = term.attrib['ConceptPreferredTermYN']

            tui = term.find('TermUI').text.strip()
            if tui.startswith(lang_code):
                tsub = '<' + meshx_prefix + tui + '>'

                if prefTerm == 'Y':
                    triples.append(csub + getMesht('preferredTerm') + tsub)
                else:
                    triples.append(csub + getMesht('term') + tsub)

                label_raw = term.find('String').text
                label = sanitize_input(label_raw)
                triples.append(tsub + getMesht('prefLabel') + '"' + label + '"@' + lang_tag)

                if term.attrib['LexicalTag'] != 'NON':
                    row = tsub + getMesht('lexicalTag') + '"' + term.attrib['LexicalTag'] + '"'
                    triples.append(row)

                dateCrt = term.find('DateCreated')
                row = tsub + getMesht('dateCreated') + getDate(dateCrt)
                triples.append(row)

                dateRev = term.find('DateRevised')
                if dateRev:
                    row = tsub + getMesht('dateUpdated') + getDate(dateRev)
                    triples.append(row)

                triples.append(tsub + getMesht('identifier') + '"' + tui + '"')

    return triples


def getMesht(predicate):
    return ' <' + mesht_prefix + predicate + '> '


def sanitize_input(text):
    t = text.strip()
    t = " ".join(t.split())
    t = t.replace('?','')
    t = t.replace('"','\\"')
    return t


def getDate(node):
    year  = node.find('Year').text.strip()
    month = node.find('Month').text.strip()
    day  = node.find('Day').text.strip()
    return '"' + year +'-'+ month +'-'+ day + '"^^<http://www.w3.org/2001/XMLSchema#date>'


def getLangTag(lang_code):
    lang_dict = {
        'cze' : 'cs',
        'fre' : 'fr',
        'ger' : 'de',
        'ita' : 'it',
        'nor' : 'no',
        'por' : 'pt',
        'scr' : 'hr',
        'spa' : 'es'
    }
    return lang_dict.get(lang_code.lower(), 'xx')


def getRoot(input_file):

    fext = os.path.splitext(input_file)[1]
    tree = None

    try:
        if fext == '.gz':
            with gzip.open(input_file, mode='rt', encoding='utf-8') as fh:
                tree = ET.parse(fh)

        if fext == '.xml':
            with open(input_file, mode='r', encoding='utf-8') as fh:
                tree = ET.parse(fh)

    except Exception as err:
        logging.error(' reading file : %s', input_file)
        raise

    finally:
        if tree:
            root = tree.getroot()
            return root


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
