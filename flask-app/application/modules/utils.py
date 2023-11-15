# -*- coding: utf-8 -*-
"""
MeSH Traslation Workflow (MTW) - utils
"""
import csv
import datetime
import gzip
import html
import io
import json
import os
import sys
import time
import uuid
from configparser import ConfigParser
from functools import reduce
from requests_futures.sessions import FuturesSession
from pathlib import Path
from urllib import parse as uparse

import arrow
import diff_match_patch as dmp_module

from flask import abort, url_for
from flask import current_app as app

from application.main import coll, pp 
from application.modules import sparql
from application.modules.auth import genApiHeaders, getReqHost

fsession = FuturesSession()


def get_instance_dir(app, file_path):
    if getattr(sys, 'frozen', False):
        datadir = os.path.normpath(os.path.join(os.path.dirname(sys.executable), 'instance') )
    else:
        datadir = os.path.normpath(app.instance_path)
    if file_path:
        return os.path.normpath(os.path.join(datadir, file_path) )
    else:
        return datadir


### Config loading
def getConfig(cfg_file):
    cpath = Path( cfg_file )
    if not cpath.is_file():
        return
    try:
        config = ConfigParser()
        config.read(cpath, encoding='utf-8')
        return config
    except:
        return


def getAdminConfValue(conf, worker_only=False):
    d = {}
    try:
        if worker_only:
            d['API_KEY'] = conf.get('worker', 'API_KEY')
        else:    
            d['ADMINNAME']  = conf.get('adminconf', 'ADMINNAME')
            d['ADMINPASS']  = conf.get('adminconf', 'ADMINPASS')
            d['SECRET_KEY'] = conf.get('adminconf', 'SECRET_KEY')
            d['API_KEY']    = conf.get('worker', 'API_KEY')         

    except:
        error = 'Error parsing admin config : '+app.config['admin_config_file']
        app.logger.error(error)
        abort(500)
    return d


def getLocalConfValue(conf):
    d = {}
    try:
        section = 'appconf'
        for key, val in json.loads( conf.get(section, 'CACHING', fallback={}) ).items():
            d[key] = val

        for key, val in json.loads( conf.get(section, 'SESSIONS', fallback={}) ).items():
            d[key] = val

        d['SERVER_NAME'] = conf.get(section, 'SERVER_NAME', fallback=None)
        d['DATABASE_NAME'] = conf.get(section, 'DATABASE_NAME', fallback='mtw.db')
        d['DATABASE'] = get_instance_dir( app, 'db/'+d['DATABASE_NAME'] )
        d['DEFAULT_THEME'] = conf.get(section, 'DEFAULT_THEME', fallback='slate')
        d['SRC_DIR'] = conf.get(section, 'SRC_DIR', fallback=get_instance_dir(app, '_data/in') )
        d['EXP_DIR'] = conf.get(section, 'EXP_DIR', fallback=get_instance_dir(app, '_data/out') )
        d['TARGET_YEAR'] = conf.get(section, 'TARGET_YEAR')
        d['PREV_YEAR_DEF'] = conf.get(section, 'PREV_YEAR_DEF')
        d['PREV_YEARS'] = conf.get(section, 'PREV_YEARS').strip().split(',')
        d['REVISED_AFTER'] = conf.get(section, 'REVISED_AFTER')
        d['CREATED_AFTER'] = conf.get(section, 'CREATED_AFTER')
        d['MARC_LIBCODE']  = conf.get(section, 'MARC_LIBCODE', fallback='LIB')
        d['MARC_CATCODE']  = conf.get(section, 'MARC_CATCODE', fallback='CAT')
        d['MARC_MESHCODE'] = conf.get(section, 'MARC_MESHCODE', fallback='xxmesh')
        d['MARC_LINE'] = conf.get(section, 'MARC_LINE', fallback='mrk')
        d['MARC_TREE'] = conf.get(section, 'MARC_TREE', fallback='def')
        d['MARC_ANGLO'] = conf.get(section, 'MARC_ANGLO', fallback='no')
        d['REFRESH_AFTER'] = int( conf.get(section, 'REFRESH_AFTER', fallback=30) )
        d['LOGOUT_AFTER']  = int( conf.get(section, 'LOGOUT_AFTER', fallback=30) )
        d['CLIPBOARD_SIZE'] = int( conf.get(section, 'CLIPBOARD_SIZE', fallback=20) )
        d['AUT_LINK'] = conf.get(section, 'AUT_LINK', fallback='/mtw/search/dui:')
        d['PID_PREFIX_CONCEPT'] = conf.get(section, 'PID_PREFIX_CONCEPT', fallback='F')
        d['CSRF_COOKIE_SECURE'] = conf.getboolean(section, 'CSRF_COOKIE_SECURE', fallback=True)
        d['CSRF_DISABLE'] = conf.getboolean(section, 'DEV_DISABLE_CSRF', fallback=False)
        d['GCSP'] = json.loads(conf.get(section, 'GCSP'))
        d['CHAR_NORM_FILE'] = conf.get(section, 'CHAR_NORM_FILE', fallback='norm_chars_table.tsv.txt')

        section = 'sparqlconf'
        d['SPARQL_HOST'] = conf.get(section, 'SPARQL_HOST', fallback='http://127.0.0.1:3030/')
        d['SPARQL_DATASET'] = conf.get(section, 'SPARQL_DATASET', fallback='mesh')
        d['MESH_RDF'] = conf.get(section, 'MESH_RDF', fallback='https://id.nlm.nih.gov/mesh/sparql')
        d['MESH_WEB'] = conf.get(section, 'MESH_WEB', fallback='https://id.nlm.nih.gov/mesh/')
        d['SOURCE_NS'] = conf.get(section, 'SOURCE_NS', fallback='http://id.nlm.nih.gov/mesh/')
        d['SOURCE_NS_VOCAB'] = conf.get(section, 'SOURCE_NS_VOCAB', fallback='http://id.nlm.nih.gov/mesh/vocab#')
        d['TARGET_LANG'] = conf.get(section, 'TARGET_LANG')
        d['TARGET_NS'] = conf.get(section, 'TARGET_NS')
        d['TRX_NS_VOCAB'] = conf.get(section, 'TRX_NS_VOCAB', fallback='http://www.medvik.cz/schema/mesh/vocab/#')

        section = 'flowconf'
        d['ROLES'] = conf.get(section, 'ROLES').replace('\n','').strip().split(',')
        d['DESC_NOTES'] = conf.get(section, 'DESC_NOTES').replace('\n','').strip().split(',')
        d['TRX_NOTES'] = conf.get(section, 'TRX_NOTES').replace('\n','').strip().split(',')

        section = 'worker'
        d['WORKER_HOST'] = conf.get(section, 'WORKER_HOST', fallback='http://127.0.0.1:55933/')  
        d['API_STATUS'] = conf.get(section, 'API_STATUS', fallback='private')
        d['API_MAX_AGE'] = int( conf.get(section, 'API_TOKEN_MAX_AGE', fallback=10) )
        d['API_TIMEOUT'] = int( conf.get(section, 'API_TIMEOUT', fallback=10) )
        if conf.get(section, 'API_AUTH_BASIC_USER', fallback=None) and conf.get(section, 'API_AUTH_BASIC_PWD', fallback=None):
            d['API_AUTH_BASIC'] = (conf.get(section, 'API_AUTH_BASIC_USER'), conf.get(section, 'API_AUTH_BASIC_PWD'))


        d['MESH_TREE'] = loadJsonFile(get_instance_dir(app, 'conf/mesh_tree_top_'+ d['TARGET_LANG'] +'.json'))
        d['CHAR_NORM_PATH'] = get_instance_dir(app, 'conf/'+ d['CHAR_NORM_FILE'])

        char_list = readDataTsv(d['CHAR_NORM_PATH'])
        d['CHAR_NORM_MAP'] = getCharMap(char_list)

    except:
        error = 'Error parsing local config : '+app.config['local_config_file']
        app.logger.error(error)
        abort(500)
    return d


def refreshStats(stat, force=False):
    interval = None
    lpath = getLockFpath('stats')

    if stat == 'all':
        for s in ['initial','actual']:
            fpath = getStatsFpath(s)
            if s == 'initial':
                if not fpath.is_file() and not lpath.is_file():
                    startStats(s, fpath, lpath)

            elif s == 'actual':
                if not lpath.is_file():
                    startStats(s, fpath, lpath, interval=app.config['REFRESH_AFTER'])
    else:
        fpath = getStatsFpath(stat)
        if stat == 'actual':
            interval = app.config['REFRESH_AFTER']
        if not lpath.is_file():
            startStats(stat, fpath, lpath, interval=interval, force=force)


def exportData(export):
    lpath = getLockFpath('stats')
    ext = 'json'
    if export in ['umls','umls_all','umls_raw']:
        ext = 'tsv'  

    if export in ['umls_all','umls_raw']:
        fpath = getTempFpath('umls', ext=ext)
        epath = getStatsFpath(export, ext=ext)
        exportTsvFile(export, fpath, epath)
    else:
        fpath = getTempFpath(export, ext=ext)
        if not lpath.is_file():
            resp = startStats(export, fpath, lpath)

        if resp and fpath.is_file():
            epath = getStatsFpath(export, ext=ext)
            exportTsvFile(export, fpath, epath)


def startStats(stat, fpath, lpath, interval=None, force=False):
    start = True
    if interval and not force:
        if not fileOld(fpath, interval):
            start = False

    if start:
        writeTempLock(lpath, stat)
        bad_resp = backStatsProcess(fpath, lpath, stat)

        if bad_resp:
            start = False

        delTempLock(lpath)

    return start


def exportLookup(export, params={}):

    lookups = getTempFpath('lookups', ext='json')
    if not lookups.is_file():
        return

    output = ''
    gzip = False
        
    if export.startswith('js_'):
        output = 'json'
        gzip = True

    elif export.startswith('xml_'):
        output = 'xml'

    elif export == 'marc':
        output = 'marc'
        gzip = True
    else:
        return

    locked = False
    lpath = getLockFpath('stats')
    if not lpath.is_file():
        locked = writeTempLock(lpath, export)

    if not locked:
        return

    fpath = getStatsFpath(export, ext=output, params=params)
    
    if output == 'json' and export == 'js_elastic':
        data = getLookupJson(lookups, export)
        jdata = getElasticData(data) 
        writeJsonFile(fpath, jdata, comp=gzip)           

    elif output == 'json':
        data = getLookupJson(lookups, export)        
        writeJsonFile(fpath, data, comp=gzip)
        
    elif output == 'xml':
        data = getLookupXml(lookups, export)
        writeTextFile(fpath, data, comp=gzip)

    elif output == 'marc':
        data = getMarc(lookups, export, params)
        writeTextFile(fpath, data, comp=gzip)

    return delTempLock(lpath)


def getLookupJson(lookups, export):
    data = {}

    lookup = loadJsonFile(lookups)
    if not lookup:
        return data

    xterms = {}
    if export in ['js_elastic', 'js_parsers', 'marc']:
        xdata = getBaseTerms()
        xterms = xdata.get('desc_terms',{})

    data['mesh_year'] = lookup.get('mesh_year', app.config['TARGET_YEAR'])
    data['trx_lang']  = lookup.get('trx_lang',  app.config['TARGET_LANG'])
    utc = arrow.utcnow()
    ts = lookup.get('fdate', utc.timestamp)
    data['timestamp'] = str(arrow.get(ts) )

    qualifiers = {}
    qualifiers_eng = {}
    qualifiers_trx = {}

    descriptors = {}
    descriptors_eng = {}
    descriptors_trx = {}

    desc_cnt = 0
    qual_cnt = 0

    for item in lookup.get('lookups_base',[]):
        dui = item['dui']
                
        d = {}
        if item.get('active','') == 'false':
            d['active'] = False
            d['eng'] = item.get('den','').replace('[OBSOLETE]','').strip()
        else:
            d['active'] = True
            d['eng'] = item.get('den','')

        if item.get('notrx','') != '':
            d['notrx'] = True
            d['trx'] = item.get('den','').replace('[OBSOLETE]','').strip()
        else:
            d['trx'] = item.get('trx','')

        dtype = item.get('dtype','')
        d['dc'] = getDescClass(dtype)

        if item.get('pa'):
            d['pa'] = []
            for pa in item.get('pa','').split('~'):
                if pa:
                    d['pa'].append(pa)

        terms = []
        terms_all = []
        
        if export in ['js_elastic','js_parsers']:
            if xterms.get(dui):
                ### terms termsx nterms ntermsx
                for termtype in ['terms','termsx','nterms','ntermsx']:
                    if xterms[dui].get(termtype):
                        terms_all += xterms[dui].get(termtype).split('~')
                terms = list(set(terms_all))
            
            
        if export == 'marc':
            if xterms.get(dui):
                if xterms[dui].get('active') == 'true':
                    ### terms termsx nterms ntermsx
                    for termtype in ['terms','termsx','nterms','ntermsx']:
                        if xterms[dui].get(termtype):
                            terms_all += xterms[dui].get(termtype).split('~')
                    terms = list(set(terms_all))
                    
            d['terms'] = []
            for t in terms:
                if t:
                    d['terms'].append(t.replace('[OBSOLETE]','').strip())                    
                    
                                                    
        if export in ['js_elastic','js_parsers', 'marc']:
            d['cat'] = []
            d['trn'] = []
            trees = item.get('trn','').split('~')
            for trn in trees:
                if item.get('active','') == 'false':
                    trn = trn.replace('[OBSOLETE]','').strip()
                    if 'x' not in d['cat']:
                        d['cat'].append('x')    
                    
                d['trn'].append(trn)
                cat = trn[:1].lower()
                if cat not in d['cat']:
                    d['cat'].append(cat)

            d['xtr'] = []
            cui = item.get('cui')
            if cui:
                d['cui'] = cui
                d['xtr'].append(cui)

            nlm = item.get('nlm')
            if nlm:
                d['nlm'] = nlm
                d['xtr'].append(nlm)

            rn = item.get('rn','0')
            if rn != '0':
                d['rn'] = rn
                d['xtr'].append(rn)

            cas = item.get('cas')
            if cas:
                d['cas'] = cas
                d['xtr'].append(cas)

            crt = item.get('crt')
            if crt:
                d['crt'] = crt

            est = item.get('est')
            if est:
                d['est'] = est                

            for t in terms:
                if t:
                    d['xtr'].append( t.replace('[OBSOLETE]','').strip() )
                    

        if export in ['marc','js_elastic']:

            d['btd'] = []
            for t in item.get('btd','').split('~'):
                if t:
                    d['btd'].append(t)

            d['ntd'] = []
            for t in item.get('ntd','').split('~'):
                if t:
                    d['ntd'].append(t)

            d['rtd'] = []
            for t in item.get('rtd','').split('~'):
                if t:
                    d['rtd'].append(t)


        if export in ['js_elastic']:
            terms_en = []
            terms_cs = []
            if xterms.get(dui):
                ###  terms nterms    => xtr_en
                for termtype in ['terms','nterms']:
                    if xterms[dui].get(termtype):
                        terms_en += xterms[dui].get(termtype).split('~')
                terms_en = list(set(terms_en))

                ###  termsx ntermsx  => xtr_cs
                for termtype in ['termsx','ntermsx']:
                    if xterms[dui].get(termtype):
                        terms_cs += xterms[dui].get(termtype).split('~')
                terms_cs = list(set(terms_cs))

            terms_en_clean = []
            for t in terms_en:
                terms_en_clean.append( t.replace('[OBSOLETE]','').strip() )

            if terms_en:
                d['xtr_en'] = []

            for t in sorted(terms_en_clean):
                if t:
                    d['xtr_en'].append( t )

            if terms_cs:
                d['xtr_cs'] = []

            for t in sorted(terms_cs, key=coll.sort_key):
                if t:
                    d['xtr_cs'].append( t )


        if dui.startswith('D'):
            desc_cnt += 1
            descriptors[dui] = d
            lookup = d['eng']
            descriptors_eng[lookup] = dui
            if d.get('trx'):
                descriptors_trx[d['trx']] = dui

        elif dui.startswith('Q'):
            qual_cnt += 1
            qualifiers[dui] = d
            d['id'] = dui
            lookup = d['eng']
            qualifiers_eng[lookup] = d
            if d.get('trx'):
                qualifiers_trx[d['trx']] = d
  
    if export == 'js_elastic':
         data['qualifiers'] = dict(sorted(qualifiers.items()))
         data['descriptors'] = dict(sorted(descriptors.items()))
         
         xdata = getBaseRest()
         data['desc_qualifs'] = xdata.get('desc_qualifs',{})
         data['desc_notes'] = xdata.get('desc_notes',{})
         data['desc_use'] = xdata.get('desc_use',{})
    
    else:
        data['desc_cnt'] = desc_cnt
        data['qual_cnt'] = qual_cnt
        
        data['qualifiers'] = dict(sorted(qualifiers.items()))
        data['qualifiers_eng'] = dict(sorted(qualifiers_eng.items()))
        data['qualifiers_trx'] = dict(sorted(qualifiers_trx.items()))
        
        data['descriptors'] = dict(sorted(descriptors.items()))
        data['descriptors_eng'] = dict(sorted(descriptors_eng.items()))
        data['descriptors_trx'] = dict(sorted(descriptors_trx.items()))

    return data
    
    
def getElasticData(data):    

    descriptors = data.get('descriptors',{})
    qualifiers = data.get('qualifiers',{})
    qualifs = data.get('desc_qualifs',{})
    notes = data.get('desc_notes',{})
    use_instead = data.get('desc_use',{})
    
    resp = []
    
    for dui in qualifiers:
        item = qualifiers[dui]
        item['db'] = 'mesh'
        item['id'] = dui
        item['heading'] = []
        item['heading'].append(item['eng'])
        item['heading'].append(item['trx'])
        
        for trn in item.get('trn',[]):
            ### Add later by running:  grind-data elastic mesh ... 
            ##resp.append( {'index': {'_id': trn, '_index': 'mesht'}} )
            resp.append( {'id': dui, 'db': 'mesht', 'trn': trn.replace('.','-'), 'eng': item.get('eng',''), 'trx': item.get('trx',''), 'active': item.get('active')} ) 
        
        ### Add later by running:  grind-data elastic mesh ...          
        ##resp.append( {'index': {'_id': dui, '_index': 'mesh'}} )
                
        xnote = notes.get(dui, {})            
        resp.append( getElasticDoc(dui, item, qualifiers, xnote) )  
        
                
    for dui in descriptors:
        item = descriptors[dui]
        item['db'] = 'mesh'
        item['id'] = dui
        item['heading'] = []
        item['heading'].append(item['eng'])
        item['heading'].append(item['trx'])
        
        for trn in item.get('trn',[]):
            ### Add later by running:  grind-data elastic mesh ...   
            ##resp.append( {'index': {'_id': trn, '_index': 'mesht'}} )
            resp.append( {'id': dui, 'db': 'mesht', 'trn': trn.replace('.','-'), 'eng': item.get('eng',''), 'trx': item.get('trx',''), 'active': item.get('active')} )             
                
        if qualifs.get(dui):
            qa = []
            qlist = qualifs.get(dui).split('~')
            for q in qlist:
                rel = qualifiers.get(q)
                eng = rel.get('eng')                
                r = rel.get('trx', eng) + '~' + eng + '|' + q            
                qa.append(r)
                
            if qa:
                item['qa'] = qa    
        
        ### Add later by running:  grind-data elastic mesh ...               
        ##resp.append( {'index': {'_id': dui, '_index': 'mesh'}} )

        qua_use = []
        usein = use_instead.get(dui, {})
        if usein:
            ecin = usein.get('qn')
            for qd in sorted( ecin.split('|') ):
                parts = qd.split('~')
                q = parts[0]
                qen = qualifiers[q].get('eng','EMPTY')
                qtr = qualifiers[q].get('trx','MISSING')

                d = parts[1]
                den = descriptors[d].get('eng','EMPTY')
                dtr = descriptors[d].get('trx','MISSING')

                qout = {}
                qout['qtr'] = qtr + '~' + qen + '|' + q
                qout['dtr'] = dtr + '~' + den + '|' + d

                qua_use.append( qout )

        if qua_use:
            item['qua_use'] = qua_use
                
        xnote = notes.get(dui, {})            
        resp.append( getElasticDoc(dui, item, descriptors, xnote) ) 
                              
    return resp
    
    
def getElasticDoc(dui, item, lookup, xnote=None):

    for key in ['pa','ntd','btd','rtd']:
        if item.get(key):
            rels = []
            for d in item.get(key,[]):
                rel = lookup.get(d)
                eng = rel.get('eng')                
                r = rel.get('trx', eng) + '~' + eng + '|' + d
                rels.append(r)
            if rels:
                item[key] = rels

    if xnote:
        del xnote['dui']
        del xnote['cui']
        item['notes'] = xnote
        
    return item         
    

def getBaseTerms():
    data = {}

    npath = getTempFpath('lookups_rest', ext='json')
    xrest = loadJsonFile(npath)
    if not xrest:
        return data

    data['mesh_year'] = xrest.get('mesh_year', app.config['TARGET_YEAR'])
    data['trx_lang']  = xrest.get('trx_lang', app.config['TARGET_LANG'])

    ##lookups_terms
    desc_terms = {}

    for item in xrest.get('lookups_terms',[]):
        dui = item['dui']
        desc_terms[dui] = {}
        for k in item:
            desc_terms[dui][k] = item[k]

    data['desc_terms'] = dict( sorted( desc_terms.items() ))
    return data


def getBaseRest():
    data = {}

    npath = getTempFpath('lookups_rest', ext='json')
    xrest = loadJsonFile(npath)
    if not xrest:
        return data

    data['mesh_year'] = xrest.get('mesh_year', app.config['TARGET_YEAR'])
    data['trx_lang']  = xrest.get('trx_lang', app.config['TARGET_LANG'])

    ## lookups_notes
    ## lookups_use_instead
    ## lookups_qualifs

    desc_notes = {}
    desc_use = {}
    desc_qualifs = {}

    for item in xrest.get('lookups_notes',[]):
        dui = item['dui']
        desc_notes[dui] = {}
        for k in item:
            desc_notes[dui][k] = item[k]

    for item in xrest.get('lookups_use_instead',[]):
        dui = item['dui']
        desc_use[dui] = {}
        for k in item:
            desc_use[dui][k] = item[k]

    for item in xrest.get('lookups_qualifs',[]):
        dui = item['dui']
        desc_qualifs[dui] = item['qa']

    data['desc_qualifs'] = dict( sorted( desc_qualifs.items() ))
    data['desc_use'] = dict( sorted( desc_use.items() ))
    data['desc_notes'] = dict( sorted( desc_notes.items() ))
    return data


def getLookupXml(lookups, export, as_string=True):
    data = getLookupJson(lookups, export)

    mesh_year = data.get('mesh_year')
    trx_lang = data.get('trx_lang','')
    timestamp = data.get('timestamp','')
    desc_cnt = data.get('desc_cnt',0)
    qual_cnt = data.get('qual_cnt',0)

    if not mesh_year:
        return ''

    xml = io.StringIO()

    header = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml.write(header)

    if export == 'xml_desc':
        root = 'descriptors'
        tag = 'd'

    elif export == 'xml_qualif':
        root = 'qualifiers'
        tag = 'q'

    head = '<%s trx_lang="%s" mesh_year="%s" desc_cnt="%d" qual_cnt="%d" timestamp="%s">\n' % (root, trx_lang, mesh_year, desc_cnt, qual_cnt, timestamp)
    xml.write(head)

    items = data.get(root)

    for k in sorted(items):
        eng = html.escape(items[k].get('eng','') )
        trx = html.escape(items[k].get('trx','') )
        dclass = items[k].get('dc','-1')

        if items[k].get('active') == False:
            line = '<%s id="%s" eng="%s" trx="%s" dclass="%s" active="0" />\n' % (tag, k, eng, trx, dclass)
        else:
            line = '<%s id="%s" eng="%s" trx="%s" dclass="%s" />\n' % (tag, k, eng, trx, dclass)
        xml.write(line)

    xml.write('</'+root+'>\n')

    if as_string:
        return xml.getvalue()
    else:
        return xml  


def getMarc(lookups, export, params, as_string=True):
    data = getLookupJson(lookups, export)

    mesh_year = data.get('mesh_year')
    if not mesh_year:
        return ''

    descriptors = data.get('descriptors',{})
    qualifiers = data.get('qualifiers',{})
    xdata = getBaseRest()
    qualifs = xdata.get('desc_qualifs',{})
    notes = xdata.get('desc_notes',{})

    timestamp = data.get('timestamp','')
    
    if timestamp:
        tsa = arrow.get(timestamp)
    else:
        tsa = arrow.get()   

    gen_date = tsa.format('YYYYMMDDHHmmss.S')    

    line_pref = '='
    ldr_pref = 'LDR  '
    code_pref = '  '
    fw = ''

    treetype = params.get('tree_style')
    ecin = params.get('anglo_style')  

    if params.get('line_style') == 'line':
        line_pref = ''
        ldr_pref = ''
        code_pref = ' '
        fw = ' '

    marc = io.StringIO()

    leader = line_pref + ldr_pref + '00000nz##a2200000n##4500\n'
    cnt = 0
    items = data.get('descriptors')

    if ecin == 'yes':
        d_items = data.get('descriptors') 
        q_items = data.get('qualifiers')
        items = {**d_items, **q_items}
    else:
        items = data.get('descriptors')    

    for mid in sorted(items):

        item = items[mid]
                
        if item.get('active') == True:
            cnt += 1
            marc.write(leader)
            marc.write(line_pref + '001' + code_pref + mid + '\n')
            marc.write(line_pref + '003' + code_pref + app.config['MARC_LIBCODE'] + '\n')
            marc.write(line_pref + '005' + code_pref + gen_date + '\n')        
                        
            xnote = notes.get(mid, {})
    
            fields = getMarcFields(mid, item, descriptors, qualifiers, qualifs, xnote, 
                                   lp=line_pref, cp=code_pref, fw=fw, treetype=treetype, ecin=ecin)
            if fields:
                marc.write(fields + '\n')
    
            bas = line_pref + 'BAS    $a' + fw + 'MeSH' + str(mesh_year)
            marc.write(bas + '\n')
    
            if item.get('trx'):
                translated = 'Y'
            elif item.get('notrx'):
                translated = 'X'
            else:
                translated = 'N'
    
            msh = line_pref + 'MSH    $a' + fw + str(item.get('dc')) + fw + '$b' + fw + item.get('cui') + fw + '$d' + fw + translated
    
            if item.get('nlm'):
                msh += fw + '$h' + fw + item.get('nlm')
    
            if xnote.get('pi'):
                for p in xnote.get('pi').split('~'):
                    msh += fw + '$i' + fw + p
    
            if xnote.get('on'):
                msh += fw + '$o' + fw + xnote.get('on')
    
            if xnote.get('pm'):
                msh += fw + '$p' + fw + xnote.get('pm')
    
            if item.get('rn'):
                if item.get('rn','0') != 0:
                    msh += fw + '$r' + fw + item.get('rn')
    
            if item.get('cas'):
                msh += fw + '$s' + fw + item.get('cas')
    
            marc.write(msh + '\n')
            marc.write('\n')
    
        qa = qualifs.get(mid)
        if item.get('active') == True and qa and ecin == 'yes':
            for qui in qa.split('~'):
                cnt += 1
                marc.write(leader)
                marc.write(line_pref + '001' + code_pref + mid + qui + '\n')
                marc.write(line_pref + '003' + code_pref + app.config['MARC_LIBCODE'] + '\n')
                marc.write(line_pref + '005' + code_pref + gen_date + '\n')    

                ecin_rec = getEcinRecord(item, mid, qui, qualifiers, lp=line_pref, cp=code_pref, fw=fw)

                marc.write(ecin_rec + '\n')
                marc.write('\n')
            
        ### Testing only   
        ''' 
        if cnt >= 50:
            if as_string:
                return marc.getvalue()
            else:
                return marc
        '''        

    if as_string:
        return marc.getvalue()
    else:
        return marc    


def getMarcFields(dui, item, descriptors, qualifiers, qualifs, xnote, lp='=', cp='  ', fw='', treetype='def', ecin='no'):
    rows = []

    htag, dt, crt = getMarcCommons(item)

    rows.append(lp + '008' + cp + crt + '#n#ancnnbab'+ dt + '##########||#ana#####d')
    rows.append(lp + '035    $a' + fw + '(DNLM)' + dui )
    rows.append(lp + '040    $a' + fw + app.config['MARC_CATCODE'] + fw + '$b' + fw + getLangCodeUmls(app.config['TARGET_LANG'], lower=True) )

    if treetype == 'def':
        for trn in item.get('trn',[]):
            trx = '$a' + fw + trn.replace('.', '.' + fw + '$x' + fw)
            rows.append(lp + '072    ' + trx)

    heading = item.get('trx', '')
    if heading == '':
        heading = item.get('eng', '')

    if ecin == 'yes':
        fx = ''
    else:
        fx = getQualifSubfield(dui, qualifiers, qualifs, fw)

    rows.append(lp + '1' + htag + '    $a' + fw + heading + fx + fw + '$2' + fw + app.config['MARC_MESHCODE'] )

    if xnote.get('cx'):
        rows.append(lp + '360    $i' + fw + xnote.get('cx') )

    ## "$wi" & "$a" & descname & "$iUF"
    terms = item.get('terms',[])
    for xt in sorted(terms, key=coll.sort_key):
        xtr = '$w' + fw + 'i' + fw + '$a' + fw + xt + fw + '$i' + fw + 'UF'
        rows.append(lp + '4' + htag + '    ' + xtr)

    btd = {}
    btdx = []
    for d in item.get('btd',[]):
        des = descriptors.get(d)
        if des.get('active') == True:  
            trx = des.get('trx')
            if not trx:
                trx = des.get('eng')
            
            btd[trx] = d
            btdx.append(trx)
        
    for x in sorted(btdx, key=coll.sort_key):        
        xtr = '$w' + fw + 'g' + fw + '$a' + fw + x + fw + '$7' + fw + btd[x]
        rows.append(lp + '5' + htag + '    ' + xtr)
        
    ntd = {}
    ntdx = []        
    for d in item.get('ntd',[]):
        des = descriptors.get(d)
        if des.get('active') == True:       
            trx = des.get('trx')
            if not trx:
                trx = des.get('eng')
            
            ntd[trx] = d
            ntdx.append(trx)
            
    for x in sorted(ntdx, key=coll.sort_key):
        xtr = '$w' + fw + 'h' + fw + '$a' + fw + x + fw + '$7' + fw + ntd[x]
        rows.append(lp + '5' + htag + '    ' + xtr)
        
    rtd = {}
    rtdx = []         
    for d in item.get('rtd',[]):
        des = descriptors.get(d)
        if des.get('active') == True: 
            trx = des.get('trx')
            if not trx:
                trx = des.get('eng')
                
            rtd[trx] = d
            rtdx.append(trx)
            
    for x in sorted(rtdx, key=coll.sort_key):            
        xtr = '$w' + fw + 'i' + fw + '$a' + fw + x + fw + '$i' + fw + 'RT' + fw + '$7' + fw + rtd[x]
        rows.append(lp + '5' + htag + '    ' + xtr)
        
    pa = {}
    pax = []         
    for d in item.get('pa',[]):
        des = descriptors.get(d)
        if des.get('active') == True: 
            trx = des.get('trx')
            if not trx:
                trx = des.get('eng')
                
            pa[trx] = d
            pax.append(trx)
            
    for x in sorted(pax, key=coll.sort_key):             
        xtr = '$w' + fw + 'i' + fw + '$a' + fw + x + fw + '$i' + fw + 'PA' + fw + '$7' + fw + pa[x]
        rows.append(lp + '5' + htag + '    ' + xtr)
        
    an = xnote.get('an')
    if not an:
        an = xnote.get('an')
    if an:
        anot = '$a' + fw + an + fw
        rows.append(lp + '667    ' + anot )

    scn = xnote.get('scnt')
    if not scn:
        scn = xnote.get('scn')
    if scn:
        scnf = '$i' + fw + scn + fw
        rows.append(lp + '680    ' + scnf )

    if treetype == 'daw':
        for trn in item.get('trn',[]):
            trx = '$a' + fw + trn + fw
            rows.append(lp + '686    ' + trx )

    hn = xnote.get('hn')
    if not hn:
        hn = xnote.get('hn')

    if hn:
        hist = '$a' + fw + hn + fw
        rows.append(lp + '688    ' + hist )

    #=750  /2$aCalcimycin$7D000001
    # 750 /2 $a Calcimycin $7 D000001

    rows.append(lp + '7' + htag + cp + ' 2' + fw + '$a' + fw + item.get('eng', '') + fw + '$7' + fw + dui)

    return '\n'.join(rows)


def getQualifSubfield(dui, qualifiers, allowed_qualifs, fw):
    qa = allowed_qualifs.get(dui)
    if not qa:
        return ''   

    qui_list = qa.split('~')
    qn_list = []
    qualifs = ''
       
    for qui in qui_list:
        qualif = qualifiers.get(qui)
        qn = qualif.get('trx','')
        if qn == '':
            qn = qualif['eng']
    
        qn_list.append(qn)
        
    for qn in sorted(qn_list, key=coll.sort_key):
        qualifs += fw + '$x' + fw + qn

    return qualifs


def getEcinRecord(item, dui, qui, qualifiers, lp='=', cp='  ', fw=''):
    rows = []

    htag, dt, crt = getMarcCommons(item)

    rows.append(lp + '008' + cp + crt + '#n#ancnnbab'+ dt + '##########||#ana#####d')
    rows.append(lp + '040    $a' + fw + app.config['MARC_CATCODE'] + fw + '$b' + fw + getLangCodeUmls(app.config['TARGET_LANG'], lower=True) )

    heading = item.get('trx', '')
    if heading == '':
        heading = item.get('eng', '')

    qualif = qualifiers.get(qui)
    qn = qualif.get('trx', qualif['eng'] )

    rows.append(lp + '1' + htag + '    $a' + fw + heading + fw + '$x' + fw + qn + fw + '$2' + fw + app.config['MARC_MESHCODE'] )

    if item.get('eng'):
        rows.append(lp + '7' + htag + cp + ' 2' + fw + '$a' + fw + item['eng'] + fw + '$x' + fw + qualif['eng'] + fw + '$7' + fw + dui + qui)

    return '\n'.join(rows)


def getMarcCommons(item):
    htag = '50'
    dt = 'a'

    if item.get('dc')   == '1': ## 150 - topical
        htag = '50'
    elif item.get('dc') == '2': ## 155 - publ
        htag = '55'
        dt = 'b'
    elif item.get('dc') == '3': ## 150 - checktag
        htag = '50'
    elif item.get('dc') == '4': ## 151 - geo
        htag = '51'
        dt = 'd'
    elif item.get('dc') == '0': ## 150 - qualifiers
        htag = '50'

    crt = item.get('crt','000000')
    crt = crt.replace('-','')
    crt = crt[2:8]        

    return (htag, dt, crt)                


def getFpathDate(fpath):
    return datetime.datetime.fromtimestamp(fpath.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')


def getStatsFpath(stat, ext='json', params={}, target_year=None):

    if ext == 'marc':
        ext = params.get('tree_style','') + '.txt'
        stat += '_' +  params.get('line_style')

    if not target_year:
        target_year = app.config['TARGET_YEAR']

    return Path( app.config['EXP_DIR'], target_year + '_' + stat + '.' + ext )


def getLockFpath(stat):
    return Path( app.config['TEMP_DIR'], '_' + stat + '.lock' )


def getTempFpath(fname, ext='json', subdir='', year=True):

    if year:
        target_year = app.config['TARGET_YEAR'] + '_'
    else:
        target_year = ''

    return Path( app.config['TEMP_DIR'], subdir, target_year + fname + '.' + ext )


def backStatsProcess(fpath, lpath, stat):
    now = time.time()

    data = {}
    data['fdate'] = now
    data['date'] = datetime.datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M')
    data['stat'] = stat
    data['mesh_year'] = app.config['TARGET_YEAR']
    data['trx_lang'] = app.config['TARGET_LANG']

    templates = []
    output = 'json'
    gzip = False
    data_text = ''

    if stat == 'initial':
        template_subdir = 'stats/'
        templates = ['descriptor','meshv_pref','meshv_nonPref','meshv_scopeNote','mesht_pref','mesht_nonPref','mesht_concept','mesht_concept_terms','mesht_scopeNote','mesht_concept_scopeNote']

    elif stat == 'actual':
        template_subdir = 'stats/'
        templates = ['mesht_pref','mesht_nonPref','mesht_concept','mesht_concept_terms','mesht_scopeNote','mesht_concept_scopeNote']

    elif stat == 'duplicates':
        template_subdir = 'stats/'
        templates = ['check_duplicates']

    elif stat == 'umls':
        output = 'tsv'
        template_subdir = 'exports/'
        templates = ['umls']

    elif stat == 'lookups':
        template_subdir = 'exports/'
        templates = ['lookups_base']
        gzip = True

    elif stat == 'lookups_rest':
        template_subdir = 'exports/'
        templates = ['lookups_notes','lookups_qualifs','lookups_terms','lookups_use_instead']
        gzip = True

    for t in templates:
        resp = sparql.getSparqlData(template_subdir+t, output=output)

        if resp:
            if stat == 'umls':
                data_text = resp
            else:
                parsed = sparql.parseSparqlStats(resp, t)
                if parsed.get('data'):
                    data[t] = parsed.get('data')
                else:
                    return 'PARSER_ERROR'
        else:
            return 'NORESPONSE'

    if output == 'json':
        writeJsonFile(fpath, data, comp=gzip)
    else:
        writeTextFile(fpath, data_text, comp=gzip)

    if stat in ['lookups','lookups_rest']:
        tpath = getTempFpath(stat)
        writeJsonFile(tpath, data)


def fileOld(fpath, interval_min):
    if fpath.is_file():
        updated = fpath.stat().st_mtime

        if updated:
            now = time.time()
            elapsed_min = (now - updated) / 60

            if elapsed_min >= interval_min :
                return True
    else:
        return True


def writeTempLock(lpath, stat):
    ##print('writing lock')
    try:
        with open(str(lpath), mode='w', encoding='utf-8') as ft:
            ft.write(stat)
        return True
    except:
        return False


def delTempLock(lpath):
    ##print('removing lock')
    try:
        lpath.unlink()
        return True
    except:
        return False


def writeJsonFile(fpath, data, comp=False):
    if comp:
        with gzip.open(str(fpath)+'.gz', mode='wt', encoding='utf-8') as ft:
            ft.write(json.dumps(data))
    else:
        with open(str(fpath), mode='w', encoding='utf-8') as ft:
            ft.write(json.dumps(data))


def writeTextFile(fpath, data, comp=False, stream=False):
    if comp:
        with gzip.open(str(fpath)+'.gz', mode='wt', encoding='utf-8') as ft:
            if stream:
                #TBD
                data.close()
            else:    
                ft.writelines(data)
                data = {}
    else:
        with open(str(fpath), mode='w', encoding='utf-8') as ft:
            if stream:
                #TBD
                data.close()
            else:    
                ft.writelines(data)
                data = {}
            

def writeNDJson(fpath, data, comp=False):
    err_msg = ''
    s = io.StringIO()
    try:        
        for o in data:
            s.write(json.dumps(o, sort_keys=True) + '\n')
        s.write('\n')

    except Exception as err:
        err_msg = '  Dumping data to JSON : ' + fpath + ' : ' + str(err) 

    try:
        if comp:
            with gzip.open(str(fpath)+'.gz', mode='wt', encoding='utf-8') as ft:
                ft.write(s.getvalue())
        else:
            with open(str(fpath), mode='w', encoding='utf-8') as ft:
                ft.write(s.getvalue())
    
    except Exception as err:
        err_msg += '  Writing file (NDJson) : ' + fpath + ' : ' + str(err)        
        
    finally:
        s.close()
        data = {} 
        return err_msg  
        
        

def writeOutputGzip(fpath, data, mode='wt'):
    with gzip.open(str(fpath)+'.gz', mode=mode, encoding='utf-8') as ft:
        ft.write(data)


def writeOutputGzipTsv(fpath, lines, mode='wt'):
    with gzip.open(str(fpath)+'.gz', mode=mode, encoding='utf-8', newline='') as ft:
        writer = csv.writer(ft, delimiter='\t', doublequote=True, quoting=1)
        writer.writerows(lines)       


def loadJsonFile(fpath, default=None):
    try:
        with open(str(fpath), mode='r', encoding='utf-8') as json_file:
            return json.load(json_file)
    except:
        return default


def loadTextFile(fpath):
    try:
        with open(str(fpath), mode='r', encoding='utf-8') as text_file:
            return text_file.read()
    except:
        return ''


def deep_get(dictionary, keys, default=None):
    return reduce(lambda d, key: d.get(key, default) if isinstance(d, dict) else default, keys.split("."), dictionary)


def sanitize_input(text, normalize=True):
    t = text.strip()
    if t:
        t = ' '.join(t.split())
        t = t.replace('?','')
        if normalize:
            t = normalize_str(t, clear_escaping=True)
        t = t.replace('"','\\"')
    return t


def sanitize_text_query(text):
    t = text.strip()
    if t:    
        t = ' '.join(t.split())
        t = t.replace('\\','')
    return t


def normalize_str(text, skip_normalization=False, clear_escaping=False):
    if text:
        if not skip_normalization:
            for src, trg in app.config['CHAR_NORM_MAP']:
                text = text.replace(src, trg)
        if clear_escaping:
            text = text.replace('\\"','"')     
    return text    


def getCui(concept):
    if concept == 'NEW':
        new_cui = str(uuid.uuid4())
        return new_cui
    else:
        con = concept.replace(app.config['SOURCE_NS'],'')
        con = con.replace(app.config['TARGET_NS'],'')
        return con


def get_dui_labels(f, action, with_values=True):
    if with_values:
        result = {}
    else:
        result = []

    for key in f.keys():
        for value in f.getlist(key):
            items = key.split('___')

            if len(items) > 1:
                it = items[0]
                sub = items[1]

                if sub == action:
                    if with_values:
                        result.update({it: value})
                    else:
                        result.append(it)
    return result


def getParamsForAudit(dui, concept, cui):
    par = {}
    con = concept.replace(app.config['SOURCE_NS'],'mesh:')
    con = con.replace(app.config['TARGET_NS'],'meshx:')

    concept_data = sparql.getSparqlData('concepts_terms', query=dui, concept=con)
    concept_orig = sparql.parseConcept(concept_data)

    ##pp.pprint(concept_orig)

    citem = concept_orig['concepts'].get(cui)

    par['cui'] = cui

    if citem:
        par['active'] = citem['active']
        par['label'] = citem['label']
        par['rel'] = citem['rel']
        par['terms'] = citem['terms']['target']

        if citem.get('cpid'):
            par['cpid'] = citem['cpid']

        if citem.get('ntx'):
            par['ntx'] = True
        else:
            par['ntx'] = False

        if citem.get('dateDeleted'):
            par['dateDeleted'] = citem.get('dateDeleted')

        if citem.get('scne'):
            par['scne'] = citem.get('scne')
        if citem.get('scnt'):
            par['scnt'] = citem.get('scnt')
        if citem.get('tnote'):
            par['tnote'] = citem.get('tnote')

    return par


def getAuditDict(audit_list):
    con_dict = {}

    for item in audit_list:
        cui = item['opid']

        if not con_dict.get(cui):
            con_dict[cui] = []

        if item['params'] != '':
            params = json.loads(item['params'])
            item.pop('params', None)
            item['params'] = params
        else:
            item['params'] = {}

        con_dict[cui].append(item)

    return con_dict


def getAuditDetail(event, params):
    detail = ''

    if event == 'insert_concept':
        detail = params['new']['terms'][0].get('prefLabel')

    elif event == 'update_concept':
        label_old = params['old'].get('label')
        label_new = params['new'].get('label')

        if label_old and label_old != label_new:
            detail = label_new
        else:
            if params['old'].get('rel') == 'preferredConcept':
                pref_label_old = ''

                if params['old'].get('terms'):
                    pref_label_old = params['old']['terms'][0].get('prefLabel')

                pref_label_new = params['new']['terms'][0].get('prefLabel')

                if not pref_label_old:
                    detail = 'NEW => ' + pref_label_new
                elif pref_label_old != pref_label_new:
                    detail = pref_label_new
                else:
                    detail = 'nonPref/trxNote updated'
            else:
                detail = 'nonPref/rel/trxNote updated'

    elif event == 'set_notrx':
        detail = 'NOT_TRX'

    elif event == 'delete_concept':
        detail = 'DELETED'

    elif event == 'purge_concept':
        detail = 'PURGED'

    return detail


def getTermList(f, concept, dui):
    dform = {}
    tlist = []
    term_list = []

    for key in f.keys():
        for value in f.getlist(key):
            items = key.split('___')

            if len(items) > 1:
                it = items[0]
                sub = items[1].replace('?','')

                if dform.get(it):
                    dform[it][sub] = sanitize_input(value)
                else:
                    tlist.append(it)
                    dform[it] = {}
                    dform[it][sub] = sanitize_input(value)
            else:
                dform[key] = sanitize_input(value)

    for it in tlist:

        dterm = dform[it]
        dterm['concept'] = concept

        if not dform.get('prefTermNew'):
            pass

        else:
            if dform['prefTermNew'] == dterm['rowid']:
                dterm['rel'] = 'preferredTerm'
            else:
                dterm['rel'] = 'term'

            if dterm['prefLabel'] == '':
                dterm['operation'] = 'delete'
            else:
                dterm['operation'] = 'upsert'

            if dterm['lexicalTag'] == 'NON':
                dterm.pop('lexicalTag')

            if dterm.get('turi'):
                dterm.pop('rowid')
                term_list.append(dterm)

            elif dterm['prefLabel'] != '':
                    dterm['turi'] = app.config['TARGET_NS'] + str(uuid.uuid4())
                    dterm['operation'] = 'insert'
                    dterm.pop('rowid')
                    term_list.append(dterm)

    return term_list


def encodeMeshRdfQuery(query):
    return uparse.quote_plus(query, safe='<>')


def getTreeQuery(top, tn=None):

    query = []
    roots = app.config['MESH_TREE']

    if top in ('B','E','H'):
        query.append(top+'0?')
    else:
        query.append(top+'0?')
        query.append(top+'1?')
        query.append(top+'2?')

    if top in ('K','L','M','Z'):
        query.append(top+'01.???')

    if tn:
        query.append(tn)
        query.append(tn+'.???')

        parts = tn.split('.')
        branch = []
        for p in parts:
            if len(p) != 3:
                return
            branch.append(p)
            query.append(('.').join(branch)+'.???')

    if query:
        q = (' OR ').join(query)
        return q


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
    return lang_dict.get(lang_code, 'xx')


def getLangCodeUmls(lang_tag, lower=False):
    lang_dict = {
        'cs' : 'CZE',
        'fr' : 'FRE',
        'de' : 'GER',
        'it' : 'ITA',
        'no' : 'NOR',
        'pt' : 'POR',
        'hr' : 'HRV',
        'es' : 'SPA'
    }
    if lower:
        return lang_dict.get(lang_tag, 'XXX').lower()
    else:
        return lang_dict.get(lang_tag, 'XXX')


### meshv:TopicalDescriptor,meshv:GeographicalDescriptor,meshv:PublicationType,meshv:CheckTag,meshv:Qualifier
def getDescClass(dtype):
    dtype_dict = {
        'Qualifier': '0',
        'TopicalDescriptor': '1',
        'PublicationType': '2',
        'CheckTag': '3',
        'GeographicalDescriptor': '4'
    }
    return dtype_dict.get(dtype, '-1')


def exportTsvFile(export, inputFile, outputFile):

    ext = os.path.splitext(inputFile)[1]
    fext = ext.lower()
    tab = '\t'

    if export == 'umls':
        ###    ?dui  ?cui  ?lang  ?tty  ?str  ?tui  ?scn
        cols = 'DescriptorUI,ConceptUI,Language,TermType,String,TermUI,ScopeNote'.split(',')

    elif export in ['umls_all','umls_raw']:
        ###    ?status ?tstatus  ?dui  ?cui  ?lang  ?tty  ?str  ?tui  ?scn
        cols = 'Dstatus,Tstatus,DescriptorUI,ConceptUI,Language,TermType,String,TermUI,ScopeNote'.split(',')

    writeOutputGzipTsv(outputFile, [cols], mode='wt')

    if fext == '.gz':
        fh = gzip.open(str(inputFile), mode='rt', encoding='utf-8')
    else:
        fh = open(str(inputFile), mode='r', encoding='utf-8')

    docs = []
    count = 0

    for line in fh:
        if count > 0:
            line = line.replace('@'+app.config['TARGET_LANG'], '')
            line = line.replace('^^xsd:boolean', '')

            row  = line.strip().split(tab)

            if export in ['umls_all','umls_raw']:
                if row[1] == 'false':
                    #print(line)
                    pass
                else:
                    clean_row = (tab).join( clearQuotes(row) )

                    if export == 'umls_raw':
                        docs.append( normalize_str( clean_row, clear_escaping=True, skip_normalization=True ).split(tab) )
                    else:    
                        docs.append( normalize_str( clean_row, clear_escaping=True ).split(tab) )

            elif export == 'umls':
                if row[0] == 'false' or row[1] == 'false':
                    #print(line)
                    pass
                else:
                    clean_row = (tab).join( clearQuotes(row[2:]) )
                    docs.append( normalize_str( clean_row, clear_escaping=True ).split(tab) )            

        count += 1                

    writeOutputGzipTsv(outputFile, docs, mode='at')


def clearQuotes(row):
    cleaned = []
    for item in row:
        if item.startswith('"'):
            cleaned.append(item[1:-1])
        else:
            cleaned.append(item)
    return cleaned        


def cleanDescView(dview):
    out = ''
    count = 0

    if not dview:
        return 'Error in the view'

    for line in dview.split('\n'):
        count += 1
        if count > 1:
            line = line.replace('http://id.nlm.nih.gov/mesh/vocab#','').replace('http://www.w3.org/2000/01/rdf-schema#','').replace('http://www.w3.org/1999/02/22-rdf-syntax-ns#','')
            line = line.replace('http://www.medvik.cz/schema/mesh/vocab/#','*** ')
            line = line.replace('http://aaa','')
            line = line.replace('"','')
            line = line.replace('<','')
            line = line.replace('>',':')
            line = line.strip()

            if line.startswith('type:'):
                if 'MeSH TopicalDescriptor' in line:
                    pass
                elif 'MeSH GeographicalDescriptor' in line:
                    pass
                elif 'MeSH PublicationType' in line:
                    pass
                elif 'MeSH CheckTag' in line:
                    pass
                elif 'MeSH Qualifier' in line:
                    pass
                elif line:
                    out += line + '\n'
            else:
                if line:
                    out += line + '\n'
    return out


def getDiff(old, new):
    dmp = diff_match_patch()
    diff = dmp.diff_main(old, new, checklines=True)
    return dmp.diffHtml(diff)


class diff_match_patch(dmp_module.diff_match_patch):
    def diffHtml(self, diffs):
        """Convert a diff array into a pretty HTML report.
        Args:
          diffs: Array of diff tuples.
        Returns:
          HTML representation.
        """
        html = []
        for (op, data) in diffs:
          text = (data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>"))
          if op == self.DIFF_INSERT:
            html.append("<span class=\"text-success\"><ins>%s</ins></span>" % text)
          elif op == self.DIFF_DELETE:
            html.append("<span class=\"text-warning\"><del>%s</del></span>" % text)
          elif op == self.DIFF_EQUAL:
            html.append("<span>%s</span>" % text)

        return ''.join(html)
    

def readDataTsv(input_file):

    fext = os.path.splitext(input_file)[1]
    tsv_file = None
    data = []

    try:
        if fext == '.gz':
            with gzip.open(input_file, mode='rt', encoding='utf-8') as fh:
                tsv_file = csv.reader(fh, delimiter='\t', quotechar=None)
                for line in tsv_file:
                    if len(line):
                        if line[0].startswith('#') or line[0].startswith('Code'):
                            pass
                        else:
                            data.append(line)                

        if fext == '.txt':
            with open(input_file, mode='r', encoding='utf-8') as fh:
                tsv_file = csv.reader(fh, delimiter='\t', quotechar=None)
                for line in tsv_file:
                    if len(line):
                        if line[0].startswith('#') or line[0].startswith('Code'):
                            pass
                        else:
                            data.append(line)                

    except Exception as err:
        print('ERROR reading file : ', input_file)
        raise

    return data


def getChar(code):
    return chr( int(code[2:], 16) )


def getCharMap(char_list):
    char_map = []
    for item in char_list:
        Code, CharName, ReplCode, ReplChar = item
        src = getChar(Code)
        trg = None        
        if ReplCode == 'None':
            trg = ''
        elif ReplCode == 'str':
            trg = ReplChar
        else:
            trg = getChar(ReplCode)
        char_map.append((src, trg)) 

    return char_map   


def callWorker(export=None, stat=None, force=False):
    worker = app.config['WORKER_HOST'].strip('/')
    endpoint = None

    # future_all = fsession.post(worker+'refresh_stats/get:all')
    if stat:
        endpoint = worker + '/refresh_stats/' + stat
    elif export:
        endpoint = worker + '/export_data/' + export

    if force:
        endpoint += '?force=1'  

    bauth = app.config.get('API_AUTH_BASIC', None)      

    if endpoint:
        fsession.post(endpoint, headers=genApiHeaders(data=getReqHost()), auth=bauth)                

