# -*- coding: utf-8 -*-
"""
MeSH Traslation Workflow (MTW) - SPARQL ops
"""
import datetime
import requests
import pprint
from contextlib import closing
from timeit import default_timer as timer

from flask import render_template
from flask import current_app as app

from application.modules import utils as mtu

pp = pprint.PrettyPrinter(indent=2)


def clear_cached(dui=None, cache=None):

    if dui and cache:
        keys = ['_desc', '_conc', '_tree', '_dview', '_diff']
        for key in keys:
            cache.delete(dui + key)


def show_elapsed(begin, tag=''):

    # TURN OFF:
    return

    elapsed = timer() - begin
    print("    %.3f" % elapsed, tag)

    return elapsed


def getSparqlData(template, query='', show='', status='', top='', tn='', concept='', otype='Descriptor',
                  output='json', slang=None, lang=None, scr=None, key=None, cache=None):

    t0 = timer()

    if key and cache:
        if cache.get(key):
            return cache.get(key)

    toptn = ''
    if tn:
        toplist = tn.split('.')
        if len(toplist) > 1:
            toptn = ('.').join(toplist[:-1])
        else:
            toptn = toplist[0]

    lang_umls = ''
    if not lang:
        lang = app.config['TARGET_LANG']

    lang_umls = mtu.getLangCodeUmls(lang)

    sparql = render_template('sparql/' + template + '.sparql', query=cleanQuery(query), otype=otype,
                             show=show, status=status, top=top, tn=tn, toptn=toptn, concept=concept,
                             lang=lang, lang_umls=lang_umls, slang=slang, scr=scr)

    if app.debug:
        print(sparql)

    endpoint = app.config['SPARQL_HOST'] + app.config['SPARQL_DATASET'] + '/query'

    if output in ['tsv', 'csv', 'json']:
        endpoint += '?format=' + output

    headers = {'Content-Type': 'application/sparql-query; charset=utf-8'}
    # headers = {'Content-Type': 'application/sparql-query; charset=utf-8', 'Connection': 'close'}
    # headers = {'Content-Type': 'application/sparql-query; charset=utf-8', 'Connection': 'keep-alive'}

    try:
        with closing(requests.post(endpoint, headers=headers, data=sparql.encode('utf-8'), timeout=600)) as r:
            show_elapsed(t0, tag='result ready: ' + template)
            if r.status_code == 200:
                if output == 'json':
                    resp = r.json()
                    if key:
                        cache.set(key, resp)
                    return resp
                else:
                    resp = r.text
                    if key:
                        cache.set(key, resp)
                    return resp

    except requests.exceptions.RequestException as err:
        app.logger.error('%s \n\n %s \n\n %s \n\n %s', endpoint, template, query, str(err))


def getSparqlDataExt(dui, output, year='', key=None, cache=None, otype='Descriptor'):

    if key and cache:
        if cache.get(key):
            return cache.get(key)

    endpoint = app.config['MESH_RDF']

    dview_ext_query = render_template('sparql/descriptor_view.sparql', query=dui, official=True, year=year, otype=otype)
    # print(dview_ext_query)

    query = mtu.encodeMeshRdfQuery(dview_ext_query)

    url = endpoint + '?query=' + query

    if output in ['tsv', 'csv', 'json']:
        url += '&format=' + output
    else:
        return

    headers = {'Connection': 'close'}

    try:
        with closing(requests.get(url, headers=headers, timeout=600)) as r:
            if r.status_code == 200:
                if output == 'json':
                    resp = r.json()
                    if key:
                        cache.set(key, resp)
                    return resp
                else:
                    resp = r.text
                    if key:
                        cache.set(key, resp)
                    return resp

    except requests.exceptions.RequestException as err:
        app.logger.error('%s \n\n %s \n\n %s \n\n %s', endpoint, query, str(err))


def updateSparqlBatch(template, concept_list=None, term_list=None, lang=None, dui=None, cache=None):

    if not template:
        return False

    if not concept_list:
        concept_list = []

    if not term_list:
        term_list = []

    template = 'sparql/updates/' + template + '.sparql'

    curDate = datetime.datetime.today().strftime('%Y-%m-%d')

    if not lang:
        lang = app.config['TARGET_LANG']

    sparql = render_template(template, concept_list=concept_list, term_list=term_list, lang=lang, tdate=curDate)
    # print(sparql)

    endpoint = app.config['SPARQL_HOST'] + app.config['SPARQL_DATASET'] + '/update'
    headers = {'Accept': 'application/json', 'Content-Type': 'application/sparql-update; charset=utf-8', 'Connection': 'close'}

    try:
        with closing(requests.post(endpoint, headers=headers, data=sparql.encode('utf-8'), timeout=60)) as r:
            stat = r.status_code

            if stat == 200 or stat == 204:
                clear_cached(dui=dui, cache=cache)
                return True

    except requests.exceptions.RequestException as err:
        app.logger.error('%s \n\n %s \n\n %s', endpoint, template, str(err))


def updateTriple(template='', insert=True, uri='', predicate=None, value='', lang=None, dui=None, cache=None):

    if not template:
        return False

    if not uri:
        return False

    if not predicate:
        return False

    template = 'sparql/updates/' + template + '.sparql'

    if not lang:
        lang = app.config['TARGET_LANG']

    sparql = render_template(template, insert=insert, uri=uri, predicate=predicate, value=cleanQuery(value), lang=lang)
    # pp.pprint(sparql)

    endpoint = app.config['SPARQL_HOST'] + app.config['SPARQL_DATASET'] + '/update'
    headers = {'Accept': 'application/json', 'Content-Type': 'application/sparql-update; charset=utf-8', 'Connection': 'close'}

    try:
        with closing(requests.post(endpoint, headers=headers, data=sparql.encode('utf-8'), timeout=60)) as r:
            stat = r.status_code

            if stat == 200 or stat == 204:
                clear_cached(dui=dui, cache=cache)
                return True

    except requests.exceptions.RequestException as err:
        app.logger.error('%s \n\n %s \n\n %s', endpoint, template, str(err))


def parseSparqlData(data, sort_tree=None):

    hits_cnt = 0
    metadata = {}

    if sort_tree:
        result = {}
        tree_cat = {}

    for row in data['results']['bindings']:
        hits_cnt += 1
        for item in row:
            val = row[item]['value']
            val = val.replace(app.config['SOURCE_NS'], '').replace('vocab#', '').replace('http://www.w3.org/2000/01/rdf-schema#', '')
            row[item]['repr'] = val

            if sort_tree:
                if item == 'tn':
                    cat = row[item]['repr'][:1]
                    if tree_cat.get(cat):
                        tree_cat[cat].append(row)
                    else:
                        tree_cat[cat] = []
                        tree_cat[cat].append(row)

    metadata['hits_cnt'] = hits_cnt

    if sort_tree and hits_cnt > 0:
        for cat in tree_cat:
            hits = len(tree_cat[cat])
            metadata[cat] = {}
            metadata[cat]['hits_cnt'] = hits

        result = tree_cat
        result['metadata'] = metadata
        return result

    if hits_cnt > 0:
        data['metadata'] = metadata
        return data


def clearPredicateUri(p):
    p = p.replace(app.config['SOURCE_NS'], '')
    p = p.replace('vocab#', '')
    p = p.replace('http://www.w3.org/2000/01/rdf-schema#', '')
    p = p.replace('http://www.w3.org/1999/02/22-rdf-syntax-ns#', '')
    p = p.replace(app.config['TRX_NS_VOCAB'], '')
    return p


def parseSparqlStats(data, template):
    metadata = {}
    hits_cnt = 0

    if template in ['check_duplicates']:
        metadata['data'] = []
        for row in data['results']['bindings']:
            hits_cnt += 1
            vals = []
            vals.append(row['trx'].get('value', ''))
            vals.append(row['ttype'].get('value', ''))
            vals.append(row['cnt'].get('value', ''))
            metadata['data'].append(vals)

        metadata['hits_cnt'] = hits_cnt

    elif template in ['lookups_base', 'lookups_terms', 'lookups_notes', 'lookups_qualifs', 'lookups_use_instead']:
        metadata['data'] = []
        items = data['head']['vars']
        for row in data['results']['bindings']:
            hits_cnt += 1
            vals = {}
            for item in items:
                if row.get(item):
                    val = row[item].get('value', '')
                    if row[item].get('type') == 'uri':
                        val = clearPredicateUri(val)
                    if item in ['trx', 'scnt', 'tan', 'tcx', 'thn', 'termsx', 'ntermsx']:
                        vals[item] = mtu.normalize_str(val)
                    else:
                        vals[item] = val
            metadata['data'].append(vals)

        metadata['hits_cnt'] = hits_cnt

    else:
        metadata['data'] = {}
        for row in data['results']['bindings']:
            if row.get('p'):
                p = row['p']['value']
                if row['p']['type'] == 'uri':
                    p = clearPredicateUri(p)
            else:
                p = 'count'

            metadata['data'][p] = int(row['count']['value'])

    return metadata


def parseDescriptor(descriptor):

    result = {}
    result['labels'] = {}
    notes = {}
    details = []
    relations = []
    qualifiers = []

    # pp.pprint(descriptor)

    for row in descriptor['results']['bindings']:

        p = row['p']['value']
        if row['p']['type'] == 'uri':
            p = clearPredicateUri(p)

        if p == 'preferredConcept':
            # if row.get('label'):
            #     result['labels']['en'] = row['label']['value']
            if row.get('tlabel'):
                result['labels']['target'] = row['tlabel']['value']

            result['labels']['prefCui'] = row['o']['value'].replace(app.config['SOURCE_NS'], '')

            if row.get('cas'):
                details.append({'p': 'CAS N1', 'val': row['cas'].get('value', '')})

            if row.get('rn'):
                details.append({'p': 'RN', 'val': row['rn'].get('value', '')})

            if row.get('rrn'):
                details.append({'p': 'RN Related', 'val': row['rrn'].get('value', '').replace('~', '<br>')})

        elif p == 'allowableQualifier':
            ui = row['o']['value']
            ui = ui.replace(app.config['SOURCE_NS'], '')
            val = row['label']['value']
            qualifiers.append({'ui': ui, 'val': val})

        elif p in ['broaderDescriptor', 'broaderQualifier', 'seeAlso', 'pharmacologicalAction', 'preferredTerm']:
            if p == 'preferredTerm':
                result['labels']['prefTerm'] = row['o']['value'].replace(app.config['SOURCE_NS'], '')
            else:
                ui = row['o']['value']
                ui = ui.replace(app.config['SOURCE_NS'], '')
                val = row['label']['value']
                relations.append({'p': p, 'ui': ui, 'val': val})

        elif p == 'label':
            lang = row['o']['xml:lang']
            val = row['o']['value']
            details.append({'p': p, 'val': val, 'lang': lang})
            if lang == 'en':
                result['labels']['en'] = val

        elif p in app.config['DESC_NOTES']:
            note = {}
            val = row['o']['value']
            lang = row['o']['xml:lang']

            if lang == 'en':
                note['note'] = val
            else:
                note['tnote'] = val

            if notes.get(p):
                notes[p].update(note)
            else:
                notes[p] = {}
                notes[p] = note

        else:
            val = row['o']['value']
            val = val.replace(app.config['SOURCE_NS'], '').replace('vocab#', '').replace('http://www.w3.org/2000/01/rdf-schema#', '')
            lang = ''
            if row['o'].get('xml:lang'):
                lang = row['o']['xml:lang']
            details.append({'p': p, 'val': val, 'lang': lang})

            if p == 'type':
                result['labels']['dtype'] = val

            if p == 'lockedBy':
                result['lockedBy'] = val

    result['notes'] = notes
    result['details'] = sorted(details, key=lambda item: item['p'])
    result['relations'] = sorted(relations, key=lambda item: item['p'])
    result['qualifiers'] = sorted(qualifiers, key=lambda item: item['val'])

    return result


def parseConcept(concepts):

    result = {}
    con_list = []
    con_dict = {}

    # pp.pprint(concepts)

    if concepts:
        for row in concepts['results']['bindings']:
            rc = row['c']['value']
            c = rc.replace(app.config['SOURCE_NS'], '')
            c = c.replace(app.config['TARGET_NS'], '')

            if c not in con_list:
                con_list.append(c)

            if not con_dict.get(c):
                con_dict[c] = {}
                con_dict[c]['terms'] = {}
                con_dict[c]['terms']['en'] = []
                con_dict[c]['terms']['target'] = []
                con_dict[c]['cui'] = c
                con_dict[c]['rc'] = rc
                if row.get('cpid'):
                    con_dict[c]['cpid'] = row['cpid']['value']

                con_dict[c]['status'] = row['status']['value']
                if row.get('rel'):
                    con_dict[c]['rel'] = row['rel']['value']

                con_dict[c]['type'] = row['ctype']['value']
                con_dict[c]['label'] = row['label']['value']
                con_dict[c]['lang'] = row['label']['xml:lang']
                if row.get('cactive'):
                    con_dict[c]['active'] = row['cactive']['value']
                else:
                    con_dict[c]['active'] = 'true'

                if row.get('scn'):
                    con_dict[c]['scn'] = row['scn']['value']
                if row.get('scnt'):
                    con_dict[c]['scnt'] = row['scnt']['value']
                if row.get('scne'):
                    con_dict[c]['scne'] = row['scne']['value']
                if row.get('cnote'):
                    con_dict[c]['tnote'] = row['cnote']['value']
                if row.get('ntx'):
                    con_dict[c]['ntx'] = 'notrx'

                if row.get('dateDeleted'):
                    con_dict[c]['dateDeleted'] = row['dateDeleted']['value']

            td = {}
            rt = row['t']['value']
            t = rt.replace(app.config['SOURCE_NS'], '')
            t = t.replace(app.config['TARGET_NS'], '')
            td['tui'] = t
            td['rt'] = rt
            if row.get('tpid'):
                td['tpid'] = row['tpid']['value']

            ttype = row['ttype']['value']

            if ttype == 'NT':
                ttype = 'N'

            td['ttype'] = ttype

            td['prefLabel'] = row['tlabel']['value']

            if row.get('ltag'):
                td['lexicalTag'] = row['ltag']['value']
            else:
                td['lexicalTag'] = ''

            if row.get('dateCreated'):
                td['dateCreated'] = row['dateCreated']['value']

            if row.get('dateUpdated'):
                td['dateUpdated'] = row['dateUpdated']['value']

            td['lang'] = row['tlabel']['xml:lang']

            target = 'en'
            if td['lang'] != 'en':
                target = 'target'

            if row.get('tactive'):
                td['active'] = row['tactive']['value']
            else:
                td['active'] = 'true'

            if row.get('altlabel'):
                td['altLabel'] = row['altlabel']['value']

            if row.get('tnote'):
                td['tnote'] = row['tnote']['value']

            con_dict[c]['terms'][target].append(td)

    result['con_list'] = con_list
    result['concepts'] = con_dict

    return result


def cleanQuery(query):
    query = query.replace('\\', '')
    query = query.replace('"', '\\"')
    return query
