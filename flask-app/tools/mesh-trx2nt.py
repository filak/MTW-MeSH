# -*- coding: utf-8 -*-
import os, argparse, datetime, io, gzip, csv, uuid
from timeit import default_timer as timer

appname = 'mesh-trx2nt'
appversion = '0.1 26-9-2023'
appdesc = 'Extracting translation dataset from NLM UMLS text file'
appusage = 'Help:   '+ appname +'.py -h \n'
appauthor = 'Filip Kriz'

mesh_prefix  = 'http://id.nlm.nih.gov/mesh/'
mesht_prefix = 'http://www.medvik.cz/schema/mesh/vocab/#'

custom_concepts = {}
desc_to_concepts = {}

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
    parser.add_argument('inputFile', type=str, help='NLM UMLS text file name (plain or gzipped)')
    parser.add_argument('langcode', type=str, help='Language code')
    parser.add_argument('meshxPrefix', type=str, help='MeSH Translation namespace prefix ie. http://mesh.medvik.cz/link/ ')
    parser.add_argument('--out', type=str, default='mesh-trx', help='Output file name prefix')

    args, unknown = parser.parse_known_args()

    if unknown:
        print('ERROR : Uknown arguments : ', unknown)
        print('Try : '+ appname  +'.py -h')

    else:
        inFile = os.path.normpath(args.inputFile)

        if os.path.isfile(inFile):
            procFile(inFile, args.meshxPrefix, args.out, args.langcode)
        else:
            print('ERROR : Bad input file : ', args.inputFile)


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

    endTime = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d_%H-%M-%S')
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
        recCount += 1
        batch += 1

        docs += getTriples(line, lang_tag, meshx_prefix, startDate)
        #docs += line

        if batch == bsize:
            flushTriples(outputFile, docs)
            batch = 0
            docs = []

    flushTriples(outputFile, docs)
    ##for row in docs:
    ##    print(row)

    result['recordsCount'] = recCount

    print('... DONE!')
    return result


def getTriples(line, lang_tag, meshx_prefix, startDate):
    triples = []

    DescriptorUI, ConceptUI, Language, TermType, Term, TermUI, ScopeNote, Tree, x = line

    csub = mesh_prefix + ConceptUI
    obj  = meshx_prefix + str(uuid.uuid4())  

    # TBD dateCreated 
    dateCrt = None
    if not dateCrt:
        dateCrt = startDate     

    if ConceptUI.startswith('F'):

        if custom_concepts.get(ConceptUI):
            ccid = custom_concepts.get(ConceptUI)
        else:
            ccid = str(uuid.uuid4())
            custom_concepts[ConceptUI] = ccid 

        ccsub = meshx_prefix + ccid       

        if TermType == 'PEP':
            dsub = mesh_prefix + DescriptorUI
            csub = mesh_prefix + desc_to_concepts[DescriptorUI]

            triples.append( getTriple(dsub, 'concept', ccsub) )
            triples.append( getTriple(csub, 'narrowerConcept', ccsub) )
            triples.append( getTriple(ccsub, 'identifier', ConceptUI, literal=True) )
            triples.append( getTriple(ccsub, 'preferredTerm', obj) )

            if ScopeNote:  
                triples.append( getTriple(ccsub, 'scopeNote', ScopeNote, literal=True, lang_tag=lang_tag) ) 

        elif TermType == 'ET':
            triples.append( getTriple(ccsub, 'term', obj) )
        
    else:
        if TermType == 'MH': 
            desc_to_concepts[DescriptorUI] = ConceptUI

        if TermType in ['MH','PEP']:
            triples.append( getTriple(csub, 'preferredTerm', obj) )

            if ScopeNote:  
                triples.append( getTriple(csub, 'scopeNote', ScopeNote, literal=True, lang_tag=lang_tag) )              

        elif TermType == 'ET':
            triples.append( getTriple(csub, 'term', obj) )   

    triples.append( getTriple(obj, 'prefLabel', Term, literal=True, lang_tag=lang_tag) )
    triples.append( getTriple(obj, 'dateCreated', dateCrt, date=True) )                                             

    return triples


def getTriple(sub, pred, obj, literal=False, date=False, lang_tag=None):
    sub = '<' + sub + '>'
    if literal:
        if lang_tag:
            return sub + getMesht(pred) + '"' + sanitize_input(obj) + '"@' + lang_tag
        else: 
            return sub + getMesht(pred) + '"' + sanitize_input(obj) + '"'

    if date:
        return sub + getMesht(pred) + getDate(obj) 

    return sub + getMesht(pred) + '<' + obj + '>'


def getTriplesXML(line, lang_tag, meshx_prefix):
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


def getDate(date):
    return '"' + date + '"^^<http://www.w3.org/2001/XMLSchema#date>'


def readData(input_file):

    fext = os.path.splitext(input_file)[1]
    tsv_file = None
    data = []

    try:
        if fext == '.gz':
            with gzip.open(input_file, mode='rt', encoding='utf-8') as fh:
                tsv_file = csv.reader(fh, delimiter='\t', quotechar=None)
                headers = next(tsv_file)
                for line in tsv_file:
                    data.append(line)                

        if fext == '.txt':
            with open(input_file, mode='r', encoding='utf-8') as fh:
                tsv_file = csv.reader(fh, delimiter='\t', quotechar=None)
                headers = next(tsv_file)
                for line in tsv_file:
                    data.append(line)                 

    except Exception as err:
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
