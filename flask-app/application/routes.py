# -*- coding: utf-8 -*-
"""
Routes & pages
"""
import ast
import base64
import datetime
import functools
import io
import json
import os
import pprint
import re
import subprocess
import sys
import time
import uuid
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from sqlite3 import dbapi2 as sqlite3
from timeit import default_timer as timer
from urllib.parse import quote, urlparse

import bcrypt
import jinja2.ext
import requests
from flask_caching import Cache
from flask_paranoid import Paranoid
from flask_seasurf import SeaSurf
from flask_talisman import Talisman
from requests_futures.sessions import FuturesSession

from application import cache, coll, csrf
from application import database as mdb
from application import paranoid, pp, sess
from application import sparql as sparql
from application import utils as mtu
from flask import Flask, Response, abort
from flask import current_app as app
from flask import (flash, g, make_response, redirect, render_template,
                   render_template_string, request, send_file, send_from_directory, session,
                   url_for)
from flask_session import Session

requests.packages.urllib3.disable_warnings()

def getPath(path):
    customDir = app.config['APP_PATH']
    return(customDir+path)


def login_required(func):
    @functools.wraps(func)
    def secure_function(*args, **kwargs):
        if not session.get('logged_in'):
            session['next'] = request.url
            return redirect(url_for('login'))
        return func(*args, **kwargs)

    return secure_function    


def ref_redirect():
    try:
        purl = urlparse(request.referrer)
        new_url = app.config['HOST_LINK'] + purl.path
        if purl.query:
            new_url += '?' + purl.query
        return new_url
    except:
        return url_for('intro')


def show_elapsed(begin, started=None, tag=''):

    ### TURN OFF:
    return

    elapsed = timer() - begin
    if started:
        process = timer() - started
        print("%.3f" % elapsed, "%.3f" % process, tag)
    else:
        print("%.3f" % elapsed, "0.000", tag)

    return elapsed


###  Pages

@app.route(getPath('/'), methods=['GET'])
@login_required
def intro():

    t0 = timer()

    db = get_db()
    stats_user = []
    stats_user = mdb.getAuditUserStatus(db, userid=session['userid'])

    show_elapsed(t0, tag='stats_user')

    status = []
    events = []
    stats_initial = {}
    stats_actual = {}
    show_stats = False
    worker = app.config['WORKER_HOST']
    endpoint = app.config['SPARQL_HOST'] + app.config['SPARQL_DATASET'] + '/query'

    initial = mtu.getStatsFpath('initial')
    actual  = mtu.getStatsFpath('actual')

    show_elapsed(t0, tag='getStatsFpath finished')
        
    worker_check = checkWorker(worker)
    show_elapsed(t0, tag='worker_check')

    api_check = checkApi(endpoint)
    show_elapsed(t0, tag='api_check')

    if worker_check == 'ERROR':
        msg = 'Background worker is NOT running/available !'
        flash(msg, 'danger')

    elif api_check == 'ERROR':
        msg = 'SPARQL endpoint is NOT running/available !'
        flash(msg, 'warning')             

    else:
        if initial.is_file() and actual.is_file():
            show_stats = True
            stats_initial = mtu.loadJsonFile(initial)
            stats_actual = mtu.loadJsonFile(actual)
            
            show_elapsed(t0, tag='loadJsonFile')
    
            if mtu.fileOld(actual, app.config['REFRESH_AFTER']):
                    
                fsession = FuturesSession()
                future_act = fsession.post(worker+'refresh_stats/get:actual')
        else:
            fsession = FuturesSession()
            future_all = fsession.post(worker+'refresh_stats/get:all')

    if session['ugroup'] in ['admin','manager','editor']:
        status = mdb.getAuditStatus(db)
        events = mdb.getAuditEvent(db)

        show_elapsed(t0, tag='getAudit')

    show_elapsed(t0, tag='ready to render')
    
    return render_template('intro.html', stats_user=stats_user, status=status, events=events, show_stats=show_stats,
                                         initial=stats_initial, actual=stats_actual)


@app.route(getPath('/settings/set_style/'), methods=['POST'])
@login_required
def settings():

    if request.form.get('theme'):
        theme = request.form.get('theme').strip()
        if theme in ['slate','spacelab','flatly']:
            session['theme'] = theme
    else:
        session['theme'] = app.config['DEFAULT_THEME']

    return redirect(ref_redirect())


###  Audit

@app.route(getPath('/todo/'), defaults={'tlist': 'Preferred'}, methods=['GET'])
@app.route(getPath('/todo/list:<tlist>'), methods=['GET'])
@login_required
def todo(tlist):

    hits = None
    tlist_check = tlist.lower()
    if tlist_check in ['preferred','nonpreferred','scopenote','nonprefscopenote','customconcepts','duplicates','duplicates_eng','mesht_predicates']:
        session['tlist'] = tlist
        template = 'reports/todo_' + tlist
        data = sparql.getSparqlData(template)
        if data:
            ##pp.pprint(data)
            hits = sparql.parseSparqlData(data)
            ##pp.pprint(hits)
    else:
        session.pop('tlist', None)
        tlist = 'Select a list'

    return render_template('todo.html', tlist_check=tlist_check, tlist=tlist, hits=hits)


@app.route(getPath('/update_clipboard/'), defaults={'dui':''}, methods=['POST'])
@app.route(getPath('/update_clipboard/dui:<dui>'), methods=['POST'])
@login_required
def update_clipboard(dui):

    if request.form.get('action'):
        db = get_db()
        dui = dui.replace('?','').strip()
        duri = app.config['SOURCE_NS'] + dui
        locked_by = get_locked_by(session['userid'], session['uname'])
        label = request.form.get('label')

        if request.form['action'] == 'clear':
            session.pop('visited',{})
            session.pop('visited_check',[])

            params = get_uparams_skeleton()
            mdb.updateUserParams(db, session['userid'], json.dumps(params))

        elif request.form['action'] == 'add':

            params = get_uparams(session['userid'])
            switch = False

            if dui not in params['selected_check']:
                params['selected'].update({dui: label})
                params['selected_check'].append(dui)
                switch = True

            if len(params['selected_check']) > app.config['CLIPBOARD_SIZE']:
                rem = params['selected_check'].pop(0)
                del params['selected'][rem]

            if switch:
                mdb.updateUserParams(db, session['userid'], json.dumps(params))

        elif request.form['action'] == 'append':

            params = get_uparams(session['userid'])
            dlist = mtu.get_dui_labels(request.form, 'append', with_values=False)
            ddict = mtu.get_dui_labels(request.form, 'append')
            switch = False

            for dui in dlist:
                if dui not in params['selected_check']:
                    params['selected'].update( {dui: ddict[dui]} )
                    params['selected_check'].append(dui)
                    switch = True

                if len(params['selected_check']) > app.config['CLIPBOARD_SIZE']:
                    rem = params['selected_check'].pop(0)
                    del params['selected'][rem]
                    switch = True

            if switch:
                mdb.updateUserParams(db, session['userid'], json.dumps(params))

        elif request.form['action'] == 'remove' and session['ugroup'] != 'admin' :

            dlist = mtu.get_dui_labels(request.form, 'remove', with_values=False)

            if dlist:
                params = get_uparams(session['userid'])
                for dui in dlist:
                    params['selected_check'].remove(dui)
                    del params['selected'][dui]

                mdb.updateUserParams(db, session['userid'], json.dumps(params))

        elif request.form['action'] == 'lock' and dui:
            resp_ok = sparql.updateTriple(template='lock', uri=duri, predicate='lock', value=locked_by, dui=dui, cache=cache)
            if resp_ok:
                mdb.addAudit(db, session['uname'], userid=session['userid'], otype='descriptor', opid=dui, dui=dui, label=label, event='lock', tstate='locked')

        elif request.form['action'] == 'unlock' and dui:
            resp_ok = sparql.updateTriple(template='lock', uri=duri, predicate='unlock', dui=dui, cache=cache)
            if resp_ok:
                audit = mdb.getAuditLocked(db, dui)
                if audit:
                    if audit.get('apid'):
                        mdb.updateAuditResolved(db, audit['apid'], tstate='unlocked', resolvedby=session['uname'])

    else:
        flash('Bad request !', 'danger')

    return redirect(ref_redirect())


@app.route(getPath('/update_concept/dui:<dui>/pref:<pref>'), methods=['POST'])
@login_required
def update_concept(dui, pref):

    if session['ugroup'] in ['viewer','disabled']:
        msg = 'Insufficient priviledges'
        flash(msg, 'warning')
        return render_template('errors/error_page.html', errcode=403, error=msg), 403

    action = request.form['action'].strip()
    ##pp.pprint(request.form)

    if action == 'purge' and session['ugroup'] not in ['admin','manager']:
        return redirect(url_for('search', dui=dui))

    if action == 'delete' and session['ugroup'] not in ['admin','manager','editor']:
        return redirect(url_for('search', dui=dui))

    if request.form.get('concept') and request.form.get('label') and action in ['insert','update','delete','purge']:

        dui = dui.replace('?','').strip()
        pref_concept = app.config['SOURCE_NS'] + pref.replace('?','').strip()
        concept = request.form['concept'].replace('?','').strip()
        cui = mtu.getCui(concept)
        label = request.form['label'].replace('?','').strip()

        if concept == 'NEW':
            concept = app.config['TARGET_NS'] + cui

        cpid = request.form['cpid'].strip()

        form_changed = request.form['form_changed'].strip()
        propose = request.form.get('propose')

        if not propose:
            if action == 'purge':
                propose = 'false'
            else:
                propose = 'true'

        params = {}
        params['cui'] = cui
        params['curi'] = concept
        concept_list = []
        term_list = []
        event = ''

        skip_terms = False

        if action in ['delete','purge'] and app.config['TARGET_NS'] in concept:
            form_changed = 'true'
            event = action + '_concept'

            cd = {}
            cd['concept'] = concept
            cd['operation'] = action
            concept_list.append(cd)
            params['old'] = mtu.getParamsForAudit(dui, concept, cui)

        elif action not in ['delete','purge'] and form_changed == 'true':
            cd = {}

            if action == 'insert':
                event = 'insert_concept'
                params['old'] = {}
            else:
                event = 'update_concept'
                params['old'] = mtu.getParamsForAudit(dui, concept, cui)

            if request.form.get('concept-rel'):
                rel = request.form['concept-rel'].strip()
                if rel in ['narrowerConcept','broaderConcept','relatedConcept']:
                    cd['rel'] = rel
                    if action == 'insert':
                        cd['operation'] = 'insert'
                    else:
                        cd['operation'] = 'upsert'

                    if request.form.get('concept-tnote'):
                        cn = request.form['concept-tnote']
                        cd['cnote'] = mtu.sanitize_input(cn)

            if request.form.get('concept-notrx'):
                event = 'set_notrx'
                cd['operation'] = 'delete_terms'
                cd['notrx'] = 'notrx'
                skip_terms = True
            else:
                cd['notrx'] = 'ok'

            if cd:
                cd['dui'] = dui
                cd['pref_concept'] = pref_concept
                cd['concept'] = concept
                concept_list.append(cd)

            if not skip_terms:
                term_list = mtu.getTermList(request.form, concept, dui)

        ##pp.pprint(concept_list)
        ##pp.pprint(term_list)

        if form_changed == 'true':
            db = get_db()

            ##result_ok = False
            result_ok = sparql.updateSparqlBatch('concept', concept_list=concept_list, term_list=term_list, dui=dui, cache=cache)

            if result_ok:
                params['new'] = mtu.getParamsForAudit(dui, concept, cui)
                ##pp.pprint(params)

                try:
                    detail = mtu.getAuditDetail(event, params)
                except:
                    detail = event

                if propose == 'true':
                    tstate = 'pending'
                elif action == 'delete':
                    tstate = 'deleted'
                elif action == 'purge':
                    tstate = 'purged'
                else:
                    tstate = 'updated'

                mdb.addAudit(db, session['uname'], userid=session['userid'], label=label, detail=detail, opid=cui, dui=dui, event=event, tstate=tstate, params=json.dumps(params))

            if result_ok and event == 'insert_concept':
                msg = 'Concept CREATED : '+label
                flash(msg, 'info')

            elif result_ok and event == 'update_concept':
                msg = 'Concept UPDATED : '+label
                flash(msg, 'success')

            elif result_ok and event == 'set_notrx':
                msg = 'Concept set as NOT Translatable : '+label
                flash(msg, 'warning')

            elif result_ok and event == 'delete_concept':
                msg = 'Concept DELETED : '+label
                flash(msg, 'secondary')

            elif result_ok and event == 'purge_concept':
                msg = 'Concept PURGED : '+label
                flash(msg, 'primary')

            else:
                msg = 'Operation FAILED for Concept : '+concept
                flash(msg, 'danger')
                app.logger.error(msg)

    return redirect(url_for('search', dui=dui))


@app.route(getPath('/add_cpid/dui:<dui>/cui:<cui>'), methods=['GET'])
@login_required
def add_cpid(dui, cui):

    if session['ugroup'] not in ['admin']:
        msg = 'Insufficient priviledges'
        flash(msg, 'warning')
        return render_template('errors/error_page.html', errcode=403, error=msg), 403

    if len(cui) != 36 or not dui.startswith('D'):
        msg = 'Action NOT applicable'
        flash(msg, 'danger')
        return redirect( url_for('search') )

    fpath = app.config['pid_counter_file']
    pid_counter = mtu.loadJsonFile(fpath, default={})
    cnt = pid_counter.get('cpid_count', 0) + 1
    issued = pid_counter.get('issued', [])
    issued_for = pid_counter.get('issued_for', [])

    prefix = app.config['PID_PREFIX_CONCEPT'] + app.config['TARGET_YEAR']
    cpid = prefix + str(cnt).zfill(4)

    if cpid not in issued and cui not in issued_for:
        issued.append(cpid)
        issued_for.append(cui)
        pid_counter['cpid_count'] = cnt
        pid_counter['issued'] = issued
        pid_counter['issued_for'] = issued_for
        curi = app.config['TARGET_NS'] + cui

        check = True
        updated = False
        cpid_result = sparql.getSparqlData('get_cpid', query=cpid, concept=curi)

        if cpid_result:
            if cpid_result.get('results'):
                if cpid_result['results']['bindings']:
                    check = False
                    msg = 'CUI already exist ! '
                    flash(msg, 'danger')
                    app.logger.error(msg + cpid + ' for ' + curi)
                    return redirect(ref_redirect())
        if check:
            updated = sparql.updateTriple(template='set_cpid', insert=True, uri=curi, predicate='mesht:identifier', value=cpid, lang=None, dui=dui, cache=cache)

        if updated:
            mtu.writeJsonFile(fpath, pid_counter)
            msg = 'CUI generated: ' + cpid
            flash(msg, 'info')
            app.logger.info(msg + ' for ' + curi)
        else:
            msg = 'CUI update FAILED ! '
            flash(msg, 'danger')
            app.logger.error(msg + cpid + ' for ' + curi)

    else:
        msg = 'CUI already issued - please try again'
        flash(msg, 'warning')

    return redirect(ref_redirect())


@app.route(getPath('/update_note/dui:<dui>'), methods=['POST'])
@login_required
def update_note(dui):

    if session['ugroup'] in ['viewer','disabled']:
        msg = 'Insufficient priviledges'
        flash(msg, 'warning')
        return render_template('errors/error_page.html', errcode=403, error=msg), 403

    if request.form.get('predicate') and request.form.get('label'):
        dui = dui.replace('?','').strip()
        predicate = request.form['predicate'].replace('?','').strip()
        label = request.form['label'].replace('?','').strip()
        db = get_db()

        if predicate not in app.config['DESC_NOTES']:
            msg = 'Update note: Unknown mesht predicate'
            flash(msg, 'danger')
            app.logger.error(msg)
            return render_template('errors/error_page.html', errcode=403, error=msg), 403

        duri = app.config['SOURCE_NS'] + dui

        if request.form['tnote_changed'] == 'true':
            tnote  = mtu.sanitize_input(request.form['tnote'])
            tnoteo = mtu.sanitize_input(request.form['tnote_original'])

            insert = True
            if tnote == '':
                insert = False

            resp_ok = False
            resp_ok = sparql.updateTriple(template='note', insert=insert, uri=duri, predicate=predicate, value=tnote, dui=dui, cache=cache)
            params = {}
            params['dui'] = dui
            params['duri'] = duri
            params['predicate'] = predicate

            if resp_ok and insert == True:
                params['new'] = tnote

                if not tnoteo:
                    event = 'insert_note'
                    detail = predicate + ' NEW'
                    params['old'] = mtu.sanitize_input(request.form['note_def'])
                else:
                    event = 'update_note'
                    detail = predicate
                    params['old'] = tnoteo

                msg = predicate+' UPDATED : '+dui
                flash(msg, 'success')
                mdb.addAudit(db, session['uname'], userid=session['userid'], otype='descriptor', opid=dui, dui=dui, label=label, detail=detail, event=event, params=json.dumps(params))
            elif resp_ok:
                detail = predicate + ' DELETE'
                params['old'] = tnoteo
                params['new'] = ''

                msg = predicate+' DELETED : '+dui
                flash(msg, 'secondary')
                mdb.addAudit(db, session['uname'], userid=session['userid'], otype='descriptor', opid=dui, dui=dui, label=label, detail=detail, event='delete_note', tstate='deleted', params=json.dumps(params))
            else:
                msg = 'Update note FAILED for : '+dui+' - '+predicate
                flash(msg, 'warning')
                app.logger.warning(msg)

    return redirect(url_for('search', dui=dui, tab='notes'))


@app.route(getPath('/update_scopenote/dui:<dui>'), methods=['POST'])
@login_required
def update_scopenote(dui):

    if session['ugroup'] in ['viewer','disabled']:
        msg = 'Insufficient priviledges'
        flash(msg, 'warning')
        return render_template('errors/error_page.html', errcode=403, error=msg), 403

    if request.form.get('concept') and request.form.get('label'):
        dui = dui.replace('?','').strip()
        concept = request.form['concept'].replace('?','').strip()
        cui = mtu.getCui(concept)
        label = request.form['label'].replace('?','').strip()
        propose = request.form.get('propose')

        if propose == 'true':
            tstate = 'pending'
        else:
            tstate = 'updated'

        predicate = 'scopeNote'

        db = get_db()

        if request.form['scnt_changed'] == 'true':
            scnt  = mtu.sanitize_input(request.form['scnt'])
            scnto = mtu.sanitize_input(request.form['scnt_original'])

            insert = True
            if scnt == '':
                insert = False

            resp_ok = False
            resp_ok = sparql.updateTriple(template='note', insert=insert, uri=concept, predicate=predicate, value=scnt, dui=dui, cache=cache)
            params = {}
            params['cui'] = cui
            params['curi'] = concept
            params['predicate'] = predicate

            if resp_ok and insert == True:
                params['new'] = scnt

                if not scnto:
                    detail = 'scopeNoteTrx NEW'
                    event = 'insert_scopeNoteTrx'
                    params['old'] = mtu.sanitize_input(request.form['scn_def'])
                else:
                    detail = 'scopeNoteTrx'
                    event = 'update_scopeNoteTrx'
                    params['old'] = scnto

                msg = 'ScopeNoteTrx UPDATED'
                flash(msg, 'success')
                mdb.addAudit(db, session['uname'], userid=session['userid'], label=label, detail=detail, opid=cui, dui=dui, event=event, tstate=tstate, params=json.dumps(params))

            elif resp_ok:
                detail = 'scopeNoteTrx DELETE'
                params['old'] = scnto
                params['new'] = ''

                if propose != 'true':
                    tstate = 'deleted'

                msg = 'ScopeNoteTrx DELETED'
                flash(msg, 'secondary')
                mdb.addAudit(db, session['uname'], userid=session['userid'], label=label, detail=detail, opid=cui, dui=dui, event='delete_scopeNoteTrx', tstate=tstate, params=json.dumps(params))

            else:
                msg = 'Update ScopeNoteTrx FAILED for : '+concept
                flash(msg, 'warning')
                app.logger.warning(msg)

            ##pp.pprint(params)

        if request.form['scne_changed'] == 'true':
            scne = mtu.sanitize_input(request.form['scne'])
            scneo = mtu.sanitize_input(request.form['scne_original'])

            insert = True
            if scne == '':
                insert = False

            resp_ok = False
            resp_ok = sparql.updateTriple(template='note', insert=insert, predicate=predicate, uri=concept, value=scne, lang='en', dui=dui, cache=cache)
            params = {}
            params['cui'] = cui
            params['curi'] = concept
            params['lang'] = 'en'
            params['predicate'] = predicate

            if resp_ok and insert == True:
                params['old'] = scneo
                params['new'] = scne

                if not scneo:
                    detail = 'scopeNote NEW'
                    event = 'insert_scopeNote'
                else:
                    detail = 'scopeNote'
                    event = 'update_scopeNote'

                msg = 'English ScopeNote UPDATED'
                flash(msg, 'success')
                mdb.addAudit(db, session['uname'], userid=session['userid'], label=label, detail=detail, opid=cui, dui=dui, event=event, tstate=tstate, params=json.dumps(params) )

            elif resp_ok:
                detail = 'scopeNote DELETE'
                params['old'] = scneo
                params['new'] = ''

                if propose != 'true':
                    tstate = 'deleted'

                msg = 'English ScopeNote DELETED'
                flash(msg, 'secondary')
                mdb.addAudit(db, session['uname'], userid=session['userid'], label=label, detail=detail, opid=cui, dui=dui, event='delete_scopeNote', tstate=tstate, params=json.dumps(params) )

            else:
                msg = 'Update EngScopeNote FAILED : '+concept
                flash(msg, 'warning')
                app.logger.warning(msg)

            ##pp.pprint(params)

    return redirect(url_for('search', dui=dui))


@app.route(getPath('/update_audit/'), methods=['POST'])
@login_required
def update_audit():

    if session['ugroup'] not in ['admin','manager','editor']:
        abort(403)

    if request.form.get('dui') and request.form.get('apid') and request.form.get('approved'):
        dui  = request.form['dui'].replace('?','').strip()
        apid = request.form['apid'].replace('?','').strip()
        appr = request.form['approved'].strip()
        event = request.form['event'].strip()
        cui = request.form.get('cui','')
        note = request.form.get('anote').strip()
        backlink = request.form['backlink'].strip()

        db = get_db()
        audit = mdb.getAuditRecord(db, apid)

        if not audit:
            msg = 'Update FAILED : No Audit record found for : '+apid
            flash(msg, 'danger')
            app.logger.error(msg)
            return redirect(url_for('search', dui=dui))

        if audit.get('resolvedby'):
            msg = 'Update CANCELLED : Audit already updated for : '+event
            flash(msg, 'warning')
            return redirect(url_for('search', dui=dui))

        if appr == 'true':
            tstate = 'approved'
        else:
            tstate = 'rejected'

        upd_err = None
        upd_err = mdb.updateAuditResolved(db, apid, tstate=tstate, resolvedby=session['uname'], note=note)

        if upd_err:
            msg = 'Audit FAILED for : '+ event + ' | cui: ' + cui + ' | tstate: ' + tstate
            flash(msg, 'danger')
            app.logger.error(msg)
            return redirect(url_for('search', dui=dui))

        params = audit.get('params')
        if params:
            params = json.loads(params)

        curi = params.get('curi')
        if curi and tstate == 'rejected':

            if event == 'delete_concept':
                concept_list = []
                cd = {}
                cd['concept'] = curi
                cd['operation'] = 'restore'
                concept_list.append(cd)
                result_ok = sparql.updateSparqlBatch('concept', concept_list=concept_list, term_list=[], dui=dui, cache=cache)

                if result_ok:
                    msg = 'Concept RESTORED : '+cui
                    flash(msg, 'success')
                    return redirect(url_for('search', dui=dui))

            if event == 'insert_concept':
                concept_list = []
                cd = {}
                cd['concept'] = curi
                cd['operation'] = 'delete'
                concept_list.append(cd)
                result_ok = sparql.updateSparqlBatch('concept', concept_list=concept_list, term_list=[], dui=dui, cache=cache)

                if result_ok:
                    msg = 'Concept proposal REJECTED : '+cui
                    flash(msg, 'info')
                    return redirect(url_for('search', dui=dui))

            if event == 'set_notrx':
                concept_list = []
                cd = {}
                cd['concept'] = curi
                cd['notrx'] = 'ok'
                concept_list.append(cd)
                result_ok = sparql.updateSparqlBatch('concept', concept_list=concept_list, term_list=[], dui=dui, cache=cache)

                if result_ok:
                    msg = 'Concept SET as Translatable'
                    flash(msg, 'success')
                    return redirect(url_for('search', dui=dui))

            ###if event in ['update_scopeNote','delete_scopeNote','update_scopeNoteTrx','delete_scopeNoteTrx','insert_scopeNoteTrx']:
            if event in ['delete_scopeNote','delete_scopeNoteTrx']:
                predicate = params.get('predicate')
                #if event == 'insert_scopeNoteTrx':
                #    old = ''
                #else:
                #    old = params.get('old')
                old = params.get('old')
                lang = params.get('lang')
                if not lang:
                    lang = app.config['TARGET_LANG']
                if predicate:
                    result_ok = sparql.updateTriple(template='note', insert=True, uri=curi, predicate=predicate, value=old, lang=lang, dui=dui, cache=cache)
                    if result_ok:
                        msg = 'Concept scopeNote changes REVERTED : '+cui
                        flash(msg, 'success')
                        return redirect(url_for('search', dui=dui))

        if tstate == 'rejected':
            msg = event.upper() + ' marked as REJECTED - revert the changes manually !'
            flash(msg, 'warning')
            return redirect(url_for('search', dui=dui, tab='history'))

        if backlink == 'ref':
            return redirect(ref_redirect())
        else:
            return redirect(url_for('search', dui=dui, tab='history'))


###  Compare

@app.route(getPath('/compare/'), defaults={'dui': ''}, methods=['GET'])
@app.route(getPath('/compare/dui:<dui>'), methods=['GET'])
@login_required
def compare(dui):

    dview = ''
    prev = ''
    dif = ''

    if request.args.get('year'):
        year = request.args.get('year')
        year = mtu.sanitize_input(year)
    else:
        year = app.config['PREV_YEAR_DEF']

    if year not in app.config['PREV_YEARS']:
        year = app.config['PREV_YEAR_DEF']

    if not dui:
        dui = session.get('dui','')

    if dui:
        dui = dui.replace('?','').strip()
        dview_data = sparql.getSparqlData('descriptor_view', query=dui, output='tsv', key=dui+'_diff', cache=cache)
        if dview_data:
            dview = mtu.cleanDescView(dview_data)

        prev_data = sparql.getSparqlDataExt(dui, 'tsv', year=year, key=dui+'_prev_'+year, cache=cache)
        if prev_data:
            prev = mtu.cleanDescView(prev_data)

        if dview and prev:
            dif = mtu.getDiff(prev, dview)

    return render_template('compare.html', dui=dui, year=year, dview=dview, prev=prev, dif=dif)


###  Audit

@app.route(getPath('/audit/'), defaults={'dui': '', 'cui': ''}, methods=['GET'])
@app.route(getPath('/audit/dui:<dui>'), defaults={'cui': ''}, methods=['GET'])
@app.route(getPath('/audit/dui:<dui>/cui:<cui>'), methods=['GET'])
@login_required
def audit(dui, cui):

    if dui:
        dui = dui.replace('?','').strip()
        session['adui'] = dui
    else:
        session.pop('adui', None)

    audit = {}
    db = get_db()
    target_years = mdb.getTargetYears(db)

    year = None
    if request.args.get('year'):
        yr = int(request.args.get('year'))
        if yr in target_years:
            year = yr

    if dui:
        if cui:
            cui = cui.replace('?','').strip()
        dui = dui.replace('?','').strip()
        audit = mdb.getAuditForItem(db, dui, cui=cui, targetyear=year)
        mtu.getAuditDict(audit)
        ##pp.pprint(audit)

    return render_template('audit.html', dui=dui, cui=cui, audit=audit, target_years=target_years, year=year)


###  Approval

@app.route(getPath('/approve/'), defaults={'userid': '', 'username': '', 'status': '', 'event': ''}, methods=['GET'])
@app.route(getPath('/approve/status:<status>'), defaults={'userid': '', 'username': '', 'event': ''}, methods=['GET'])
@app.route(getPath('/approve/event:<event>'), defaults={'userid': '', 'username': '', 'status': ''}, methods=['GET'])
@app.route(getPath('/approve/event:<event>/userid:<userid>/user:<username>'), defaults={'status': ''}, methods=['GET'])
@app.route(getPath('/approve/status:<status>/event:<event>'), defaults={'userid': '', 'username': ''}, methods=['GET'])
@app.route(getPath('/approve/status:<status>/event:<event>/userid:<userid>'), defaults={'username': ''}, methods=['GET'])
@app.route(getPath('/approve/userid:<userid>'), defaults={'username': '', 'status': '', 'event': ''}, methods=['GET'])
@app.route(getPath('/approve/userid:<userid>/user:<username>'), defaults={'status': '', 'event': ''}, methods=['GET'])
@app.route(getPath('/approve/userid:<userid>/user:<username>/status:<status>'), defaults={'event': ''}, methods=['GET'])
@app.route(getPath('/approve/userid:<userid>/user:<username>/status:<status>/event:<event>'), methods=['GET'])
@login_required
def approve(status, event, userid, username):

    if session['ugroup'] not in ['admin','manager','editor','contributor']:
        msg = 'Insufficient priviledges'
        flash(msg, 'warning')
        return render_template('errors/error_page.html', errcode=403, error=msg), 403

    if userid:
        session['auserid'] = userid
    else:
        session.pop('auserid', None)

    if username:
        session['ausername'] = username
    else:
        session.pop('ausername', None)

    if session['ugroup'] not in ['admin','manager','editor']:
        userid = session['userid']
        username = session['uname']

    if status not in ['pending','approved','rejected','deleted','purged','updated','locked','unlocked']:
        status = 'pending'

    statuses = []
    users = []
    db = get_db()

    year = None
    if request.args.get('year'):
        target_years = mdb.getTargetYears(db)
        yr = int(request.args.get('year'))
        if yr in target_years:
            year = yr

    if event:
        if session['ugroup'] not in ['admin','manager','editor']:
            statuses = mdb.getAuditUserStatus(db, userid=userid, targetyear=year)
        else:
            statuses = mdb.getAuditEventStatus(db, event, targetyear=year)
        users = mdb.getAuditUsersEvent(db, event, userid=userid, tstate=status, targetyear=year)
    else:
        statuses = mdb.getAuditUserStatus(db, userid=userid, targetyear=year)
        users = mdb.getAuditUserStatus(db, userid=userid, tstate=status, targetyear=year)

    pending = {}
    if userid:
        pending = mdb.getAuditPending(db, userid=userid)
        mtu.getAuditDict(pending)

    resolved = {}
    if userid and status != 'pending':
        resolved = mdb.getAuditResolved(db, userid, tstate=status, event=event, targetyear=year)
    elif userid:
        resolved = mdb.getAuditResolved(db, userid, event=event, targetyear=year)

    mtu.getAuditDict(resolved)

    return render_template('approve.html', statuses=statuses, users=users, status=status, event=event, userid=userid, username=username,
                                           pending=pending, resolved=resolved, year=year)


@app.route(getPath('/browse/'), defaults={'top': '', 'tn': '', 'action':''}, methods=['GET'])
@app.route(getPath('/browse/do:<action>'), defaults={'top': '', 'tn': ''}, methods=['GET'])
@app.route(getPath('/browse/<top>'), defaults={'tn': '', 'action':''}, methods=['GET'])
@app.route(getPath('/browse/<top>/tree:<tn>'), defaults={'action':''}, methods=['GET'])
@app.route(getPath('/browse/<top>/do:<action>'), defaults={'tn':''}, methods=['GET'])
@app.route(getPath('/browse/<top>/tree:<tn>/do:<action>'), methods=['GET'])
@login_required
def browse(top, tn, action):

    hits_cnt = 0
    tree_query = None
    data = None
    tree = {}

    if action == 'clear':
        session['show'] = 'all'
        session['status'] = 'all'

    if not top:
        session.pop('top', None)
        session.pop('tn', None)

    else:
        if not app.config['MESH_TREE'].get(top):
            msg = 'Browse: Unknown top treeNumber'
            flash(msg, 'warning')
            return render_template('errors/error_page.html', errcode=404, error=msg), 404

        session['top'] = top
        session['tn'] = tn

        if request.args.get('show'):
            show = request.args.get('show').strip()
            if show in ['all','translated','todo','scn','ntx','notpref']:
                session['show'] = show

        if request.args.get('status'):
            status = request.args.get('status').strip()
            if status in ['all','active','revised','deleted','new','notpref']:
                session['status'] = status

        tree_query = mtu.getTreeQuery(top, tn=tn)

        if tree_query:
            data = sparql.getSparqlData('tree-browse', query=tree_query, top=top, tn=tn, show=session.get('show'), status=session.get('status'))
            ##pp.pprint(data)
        else:
            msg = 'Browse: Bad input parameters'
            flash(msg, 'danger')
            app.logger.error(msg)
            return render_template('errors/error_page.html', errcode=500, error=msg), 500

        if data:
            tree = sparql.parseSparqlData(data, sort_tree=True)
            ##pp.pprint(tree)
            if tree:
                hits_cnt = tree['metadata']['hits_cnt']
        else:
            msg = 'No response received from backend'
            flash(msg, 'danger')
            app.logger.error(msg)
            return render_template('errors/error_page.html', errcode=500, error=msg), 500

    if tn:
        subtitle = tn
    elif top:
        subtitle = top
    else:
        subtitle = ''

    return render_template('browse.html', hits_cnt=hits_cnt, top=top, tn=tn, subtitle=subtitle, tree=tree, show=session.get('show'), status=session.get('status'))


@app.route(getPath('/search/'), defaults={'dui':'', 'action':''}, methods=['GET'])
@app.route(getPath('/search/dui:<dui>'), defaults={'action':''}, methods=['GET'])
@app.route(getPath('/search/do:<action>'), defaults={'dui':''}, methods=['GET'])
@login_required
def search(dui, action):

    t0 = timer()

    text_query = None
    hits_key = 'hits_'+str(session['userid'])
    tab = 'concepts'

    if request.args.get('q'):
        tq = request.args.get('q')
        text_query = mtu.sanitize_text_query(tq)
        session['q'] = text_query

    if request.args.get('show'):
        show = request.args.get('show').strip()
        if show in ['all','translated','todo','scn','ntx','notpref']:
            session['sshow'] = show

    if request.args.get('status'):
        status = request.args.get('status').strip()
        if status in ['all','active','revised','deleted','new','notpref']:
            session['sstatus'] = status

    if request.args.get('lang'):
        slang = request.args.get('lang').strip()
        if slang in ['all','source','target']:
            session['slang'] = slang
          
    if request.args.get('scr'):
        scr = request.args.get('scr').strip()
        if scr in ['yes','no']:
            session['scr'] = scr

    if action == 'clear':
        session.pop('q', None)
        session.pop('sshow', None)
        session.pop('sstatus', None)
        session.pop('slang', None)
        session.pop('scr', None)
        session.pop('dui', None)
        session.pop('adui', None)

        text_query = None
        cache.delete(hits_key)

    audit = {}
    descriptor = []
    concepts = {}
    tree = {}
    hits = {}
    hits_cnt = 0
    dview = ''
    dview_query = ''

    if request.args.get('tab'):
        ttab = request.args.get('tab').strip()
        if ttab in ['concepts','notes','details','relations','qualifiers','history']:
            tab = ttab    

    if dui:
        dui = dui.replace('?','').strip()

        started = timer()
        desc_data = sparql.getSparqlData('descriptor', query=dui, key=dui + '_desc', cache=cache)
        show_elapsed(t0, started=started, tag='desc_data')

        desc_started = started

        if not desc_data:
            msg = 'No response received from backend'
            flash(msg, 'danger')
            app.logger.error(msg)
            return render_template('errors/error_page.html', errcode=500, error=msg), 500        

        descriptor = sparql.parseDescriptor(desc_data)

        if descriptor.get('labels'):   
            session['dui'] = dui

            started = timer()
            concepts_data = sparql.getSparqlData('concepts_terms', query=dui, key=dui + '_conc', cache=cache)
            show_elapsed(t0, started=started, tag='concepts_data')

            concepts = sparql.parseConcept(concepts_data)

            started = timer()
            tree_data  = sparql.getSparqlData('tree', query=dui, key=dui + '_tree', cache=cache)
            show_elapsed(t0, started=started, tag='tree_data')

            tree = sparql.parseSparqlData(tree_data)

            started = timer()
            dview = sparql.getSparqlData('descriptor_view_trx', query=dui, output='tsv', key=dui + '_dview', cache=cache)
            show_elapsed(t0, started=started, tag='dview_data')

            dview = mtu.cleanDescView(dview)

            store_visited(dui, descriptor['labels']['en'])
            show_elapsed(t0, started=desc_started, tag='desc_data processed')

            db = get_db()
            audit = mtu.getAuditDict(mdb.getAuditForItem(db, dui))

        else:
            msg = 'Item not found : ' + str(dui)
            flash(msg, 'warning')
            app.logger.warning(msg)
            return render_template('errors/error_page.html', errcode=404, error=msg), 404            

    if text_query:
        data = sparql.getSparqlData('search', query=text_query, show=session.get('sshow'), status=session.get('sstatus'), 
                                              slang=session.get('slang'), scr=session.get('scr'))
        ##pp.pprint(data)

        if data:
            started = timer()
            hits = sparql.parseSparqlData(data)
            ##pp.pprint(hits)
            if hits:
                hits_cnt = hits['metadata']['hits_cnt']
                cache.set(hits_key, hits)
            else:
                msg = 'Nothing found'
                flash(msg, 'warning')

        else:
            msg = 'SEARCH : No response received from backend'
            flash(msg, 'danger')
            app.logger.error(msg)
            return render_template('errors/error_page.html', errcode=500, error=msg), 500

    else:
        cached_hits = cache.get(hits_key)
        if cached_hits:
            hits_cnt = cached_hits['metadata']['hits_cnt']
            hits = cached_hits

    show_elapsed(t0, started=t0, tag='before_render')

    return render_template('search.html', hits_cnt=hits_cnt, hits=hits, dui=dui, tree=tree, descriptor=descriptor, concepts=concepts, tab=tab, 
                                          show=session.get('sshow'), status=session.get('sstatus'), slang=session.get('slang'), scr=session.get('scr'), 
                                          audit=audit, dview=dview)


def store_visited(dui, label):
    dui = dui.replace('?','').strip()

    if not session.get('visited'):
        session['visited'] = {}
        session['visited'].update({dui: label})

        session['visited_check'] = []
        session['visited_check'].append(dui)

    else:
        if dui not in session['visited_check']:
            session['visited'].update({dui: label})
            session['visited_check'].append(dui)

            if len(session['visited_check']) > app.config['CLIPBOARD_SIZE']:
                rem = session['visited_check'].pop(0)
                del session['visited'][rem]


###  Reporting

@app.route(getPath('/report/'), defaults={'userid':'', 'year':''}, methods=['GET'])
@app.route(getPath('/report/userid:<userid>'), defaults={'year':''}, methods=['GET'])
@app.route(getPath('/report/year:<year>'), defaults={'userid':''}, methods=['GET'])
@app.route(getPath('/report/userid:<userid>/year:<year>'), methods=['GET'])
@login_required
def report(userid, year):

    if session['ugroup'] not in ['admin','manager','editor','contributor']:
        msg = 'Insufficient priviledges'
        flash(msg, 'warning')
        return render_template('errors/error_page.html', errcode=403, error=msg), 403

    db = get_db()
    target_years = mdb.getTargetYears(db)

    if not year:
        if request.args.get('year'):
            year = request.args.get('year')
        else:
            year = app.config['TARGET_YEAR']

    if int(year) not in target_years:
        year = app.config['TARGET_YEAR']

    months = mdb.getReportMonth(db, targetyear=year)
    month = None
    if request.args.get('month'):
        mon = request.args.get('month')
        if mon in months:
            month = mon

    report = {}
    resolved = {}

    if session['ugroup'] not in ['admin','manager']:
        userid = session['userid']
        users = mdb.getUsers(db, userid=userid)
    else:
        users = mdb.getUsers(db)

    if request.args.get('report'):
        xrep = request.args.get('report').split('--')
        if len(xrep) == 2:
            fmt = xrep[0]
            rep = xrep[1]
            if rep in ['events','resolved']:
                if rep == 'events':
                    suf = 'created'
                    head = 'Month,Username,Event,Status,Count,TargetYear: ' + str(year)
                elif rep == 'resolved':
                    suf = 'resolved'
                    head = 'Month,ResolvedBy,Event,Status,Count,TargetYear: ' + str(year)
            else:
                abort(403)

            report = mdb.getReport(db, suf, targetyear=year, userid=userid, mon=month)
            if fmt in ['csv','tsv']:
                if fmt == 'csv':
                    resp = make_response(render_template('report-csv.txt', head=head, report=report) )
                    resp.headers["Content-type"] = 'text/csv'
                elif fmt == 'tsv':
                    head_list = head.split(',')
                    head = ('\t').join(head_list)
                    resp = make_response(render_template('report-tsv.txt', head=head, report=report, tab='\t') )
                    resp.headers["Content-type"] = 'text/tab-separated-values'

                resp.headers["Content-Disposition"] = "attachment; filename=mtw-report-"+rep+"."+fmt
                return resp
            else:
                abort(403)
        else:
            abort(400)
    else:
        events = mdb.getReport(db, 'created', targetyear=year, userid=userid, mon=month)
        resolved = mdb.getReport(db, 'resolved', targetyear=year, userid=userid, mon=month)
        ##pp.pprint(report)
        return render_template('report.html', users=users, target_years=target_years, year=year, userid=userid, months=months, month=month, report=events, resolved=resolved )


###  Management

@app.route(getPath('/manage/'), defaults={'action': ''}, methods=['GET'])
@app.route(getPath('/manage/action:<action>'), methods=['POST'])
@login_required
def manage(action):

    if session['ugroup'] not in ['admin','manager']:
        msg = 'Admin or Manager login required'
        flash(msg, 'warning')
        return render_template('errors/error_page.html', errcode=403, error=msg), 403

    if action == 'update_msg' and request.method == 'POST':
        msg_head = request.form['hmsg']
        msg_text = request.form['amsg']
        msg_show = request.form['action']

        if msg_show not in ['hide','show']:
            msg_show = 'hide'

        lockdb = None
        if msg_show == 'show':
            lockdb = request.form.get('lockdb')

        lpath = mtu.getLockFpath('lockdb')
        if lockdb:
            mtu.writeTempLock(lpath, 'lockdb')
        else:
            mtu.delTempLock(lpath)

        msg = {}
        msg['show'] = msg_show
        msg['text'] = msg_text
        msg['head'] = msg_head

        mpath = mtu.getTempFpath('admin-msg', year=False)
        mtu.writeJsonFile(mpath, msg)

        return redirect(ref_redirect())

    users = mdb.getUsers(get_db())

    exports = {}
    exp_files = {}

    ### YYYY_umls.tsv.gz
    exports['umls_tsv'] = mtu.getStatsFpath('umls', ext='tsv.gz')

    ### YYYY_umls_all.tsv.gz
    exports['umls_all_tsv'] = mtu.getStatsFpath('umls_all', ext='tsv.gz')

    ### YYYY_lookups.json.gz
    exports['lookups'] = mtu.getStatsFpath('lookups', ext='json.gz')

    ### YYYY_lookups_rest.json.gz
    exports['lookups_rest'] = mtu.getStatsFpath('lookups_rest', ext='json.gz')

    ### YYYY_js_all.json.gz
    exports['js_all'] = mtu.getStatsFpath('js_all', ext='json.gz')

    ### YYYY_js_parsers.json.gz
    exports['js_parsers'] = mtu.getStatsFpath('js_parsers', ext='json.gz')
    
    ### YYYY_js_elastic.json.gz
    exports['js_elastic'] = mtu.getStatsFpath('js_elastic', ext='json.gz')    

    ### YYYY_xml_desc.xml
    exports['xml_desc'] = mtu.getStatsFpath('xml_desc', ext='xml')

    ### YYYY_xml_qualif.xml
    exports['xml_qualif'] = mtu.getStatsFpath('xml_qualif', ext='xml')

    ### YYYY_marc_mrk.def.txt.gz
    exports['marc_mrk_def'] = mtu.getStatsFpath('marc_mrk', ext='def.txt.gz')

    ### YYYY_marc_mrk.daw.txt.gz
    exports['marc_mrk_daw'] = mtu.getStatsFpath('marc_mrk', ext='daw.txt.gz')

    ### YYYY_marc_line.def.txt.gz
    exports['marc_line_def'] = mtu.getStatsFpath('marc_line', ext='def.txt.gz')

    ### YYYY_marc_line.daw.txt.gz
    exports['marc_line_daw'] = mtu.getStatsFpath('marc_line', ext='daw.txt.gz')

    for f in exports:
        fp = exports[f]
        if fp.is_file():
            exp_files[f] = {}
            exp_files[f]['fname'] = fp.name
            exp_files[f]['fdate'] = mtu.getFpathDate(fp)

    show_lookups_exports = False
    lookups_base = mtu.getTempFpath('lookups')
    if lookups_base.is_file():
        show_lookups_exports = True

    show_marc_exports = False
    lookups_rest = mtu.getTempFpath('lookups_rest')
    if lookups_rest.is_file():
        show_marc_exports = True

    lpath = mtu.getLockFpath('stats')
    if lpath.is_file():
        msg = 'Background worker is RUNNING...'
        flash(msg, 'info')

    return render_template('manage.html', users=users, exports=exp_files, show_lookups=show_lookups_exports, show_marc=show_marc_exports)


@app.route(getPath('/download/<fname>'))
@login_required
def download(fname):

    if session['ugroup'] not in ['admin','manager']:
        msg = 'Admin or Manager login required'
        flash(msg, 'warning')
        return render_template('errors/error_page.html', errcode=403, error=msg), 403
    else:
        return send_from_directory(app.config['EXP_DIR'], fname, as_attachment=True)  


@app.route(getPath('/update_stats/get:<stat>'), methods=['POST'])
@login_required
def update_stats(stat):

    if session['ugroup'] not in ['admin','manager']:
        msg = 'Insufficient priviledges'
        flash(msg, 'warning')
        return render_template('errors/error_page.html', errcode=403, error=msg), 403

    if stat not in ['initial','actual','umls','umls_all','lookups','lookups_rest','js_all','js_parsers','js_elastic','xml_desc','xml_qualif','marc']:
        msg = 'Unknown params for update_stats'
        flash(msg, 'danger')
        return render_template('errors/error_page.html', errcode=404, error=msg), 404

    fpath = mtu.getStatsFpath(stat)
    lpath = mtu.getLockFpath('stats')
    worker = app.config['WORKER_HOST']
    endpoint = app.config['SPARQL_HOST'] + app.config['SPARQL_DATASET'] + '/query'
    
    if lpath.is_file():
        msg = 'Background worker is BUSY - please try again later.'
        flash(msg, 'warning')
        
        return redirect(ref_redirect())
        
    worker_check = checkWorker(worker) 

    if worker_check == 'ERROR':
        msg = 'Background worker is NOT running/available !'
        flash(msg, 'danger')
        
        return redirect(ref_redirect())

    api_check = checkApi(endpoint)

    if api_check == 'ERROR':
        msg = 'SPARQL endpoint is NOT running/available !'
        flash(msg, 'warning')
        
        return redirect(ref_redirect())       
    
    fsession = FuturesSession()

    if stat in ['umls','umls_all','js_all','js_parsers','js_elastic','xml_desc','xml_qualif']:
        future_umls = fsession.post(worker+'export_data/get:'+stat)

    elif stat == 'marc':
        params = {}
        params['marc'] = {}

        line_style = request.form.get('line_style','mrk')
        if line_style in ['mrk','line']:
            params['marc']['line_style'] = line_style

        tree_style = request.form.get('tree_style','def')
        if tree_style in ['def','daw']:
            params['marc']['tree_style'] = tree_style

        anglo_style = request.form.get('anglo_style','no')
        if anglo_style in ['yes','no']:
            params['marc']['anglo_style'] = anglo_style

        future_umls = fsession.post(worker+'export_data/get:'+stat, json=params)

    elif stat in ['initial','actual','all','duplicates','lookups','lookups_rest']:
        future_stat = fsession.post(worker+'refresh_stats/get:'+stat)

    else:
        msg = 'Output stat not defined !'
        flash(msg, 'warning')

        return redirect(ref_redirect())

    msg = 'Process started ...'
    flash(msg, 'success')

    return redirect(ref_redirect())


@app.route(getPath('/user/add'), methods=['POST'])
def add_user():
    if session['ugroup'] not in ['admin','manager']:
        abort(403)
    if request.method == 'POST':
        username = request.form['uname'].replace('_','')
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        passwd = request.form['pswd']
        ugroup = request.form['ugroup']

        if ugroup not in app.config['ROLES']:
            msg = 'Bad role !'
            flash(msg, 'warning')
            return render_template('errors/error_page.html', errcode=403, error=msg), 403

        email = request.form.get('email')
        phone = request.form.get('phone')

        passwd_hashed = bcrypt.hashpw(passwd.encode('utf-8'), bcrypt.gensalt(5))

        params = {}
        params['insert'] = {}
        params['insert'].update( {'firstname': firstname} )
        params['insert'].update( {'lastname': lastname} )
        params['insert'].update( {'role': ugroup} )

        db = get_db()
        res = mdb.addUser(db, username, firstname, lastname, passwd_hashed.decode('utf-8'), ugroup, phone=phone, email=email)

        if res:
            flash(res, 'danger')
            app.logger.error(res+' - uname: '+username)
        else:
            flash('New user successfully added', 'info')
            mdb.addAudit(db, session['uname'], userid=session['userid'], otype='user', opid=username, event='insert', params=json.dumps(params) )

        return redirect(url_for('manage'))


@app.route(getPath('/user/update'), methods=['POST'])
def update_user():
    if session['ugroup'] not in ['admin','manager']:
        abort(403)
    if request.method == 'POST':
        username = request.form['uname'].replace('_','')
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        passwd = request.form['pswdnew']
        id = request.form['userid']
        ugroup = request.form['ugroup']
        action = request.form['action']

        if ugroup not in app.config['ROLES']:
            msg = 'Bad role !'
            flash(msg, 'warning')
            return render_template('errors/error_page.html', errcode=403, error=msg), 403

        email = request.form.get('email')
        phone = request.form.get('phone')

        params = {}
        params['changed'] = []

        if passwd != '':
            passwd = bcrypt.hashpw(passwd.encode('utf-8'), bcrypt.gensalt(5))
            passwd = passwd.decode('utf-8')
            params['changed'].append('password')

        db = get_db()

        if action == 'delete':
            res = mdb.deleteUser(db, id)
        else:
            res = mdb.updateUser(db, username, firstname, lastname, passwd, ugroup, id, phone=phone, email=email)

        opid = str(id) + '_' + username

        if res:
            flash(res, 'danger')
            app.logger.error(res+' - uname: '+username)

        if action in ['delete','update']:
            params[action] = {}
            params[action].update( {'firstname': firstname} )
            params[action].update( {'lastname': lastname} )
            params[action].update( {'role': ugroup} )

        if action == 'delete':
            flash('User '+id+' successfully DELETED ', 'secondary')
            mdb.addAudit(db, session['uname'], userid=session['userid'], otype='user', opid=opid, event=action, params=json.dumps(params) )

        elif action == 'update':
            flash('User '+id+' successfully UPDATED ', 'success')
            mdb.addAudit(db, session['uname'], userid=session['userid'], otype='user', opid=opid, event=action, params=json.dumps(params) )

        return redirect(url_for('manage'))


###  Login | Logout

@app.route(getPath('/login/'), methods=['GET', 'POST'])
def login():
    error = None
    login = False

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        isadmin = request.form['isadmin']
        db = get_db()

        if isadmin == 'yes':
            if username == app.config['ADMINNAME'] and bcrypt.checkpw(password.encode('utf-8'), app.config['ADMINPASS'].encode('utf-8')):
                login = True
            else:
                error = 'Invalid admin login or password'
                app.logger.warning(error+' - uname: '+username)
        else:
            udata = mdb.getUserPwd(db, username)

            if udata:
                if bcrypt.checkpw(password.encode('utf-8'), udata['passwd'].encode('utf-8')):
                    login = True

            if not login:
                error = 'Invalid username or password'
                app.logger.warning(error+' - uname: '+username)

        if error == None and login:
            session['logged_in'] = True
            session['logged_user'] = username

            if isadmin == 'yes':
                userid = 0
                session['uname'] = username
                session['fname'] = 'Admin'
                session['ugroup'] = 'admin'
                session['theme'] = app.config['DEFAULT_THEME']

            else:
                udata = mdb.getUserData(db, username=username)
                userid = udata['id']
                session['uname'] = username
                session['fname'] = udata['firstname']
                session['ugroup'] = udata['ugroup']

                if udata['theme']:
                    session['theme'] = udata['theme']
                else:
                    session['theme'] = app.config['DEFAULT_THEME']

            session['userid'] = userid

            if session['ugroup'] == 'disabled':
                session.pop('logged_in', None)
                flash('Your account has been disabled.', 'warning')
                app.logger.warning('Disabled user login attempt : '+username)

                mdb.addAudit(db, username, userid=userid, otype='user', event='login', tstate='failed')
            else:
                mdb.addAudit(db, username, userid=userid, otype='user', event='login', tstate='success')

                return redirect(url_for('intro'))

        else:
            session.pop('logged_in', None)
            flash('Bad login', 'danger')

    return render_template('login.html')


@app.route(getPath('/logout/'))
def logout():

    if session.get('logged_user') and session['ugroup']:
        username = session['logged_user']
        usergroup = session['ugroup']

        if not session.get('theme'):
            theme = app.config['DEFAULT_THEME']
        else:
            theme = session['theme']

        db = get_db()
        if usergroup not in ['admin']:
            mdb.updateUserTheme(db, session['userid'], theme)

        mdb.addAudit(db, username, userid=session['userid'], otype='user', opid=theme, event='logout', tstate='success')

    session.pop('logged_in', None)
    session.pop('next', None)
    flash('You were logged out', 'info')

    return redirect(url_for('login'))


### Functions, context_processors, etc.

def checkWorker(worker):
    try:
        with closing(requests.get(worker, timeout=10) ) as r:
            if r.status_code == 200:
                return 'SUCCESS'
            else:
                app.logger.warning('Worker: %s \n\n %s', worker, r.status_code )
                return 'ERROR'
                    
    except requests.RequestException as err:
        app.logger.error('Worker: %s \n\n %s', worker, str(err) )
        return 'ERROR'


def checkApi(endpoint):
    headers = {'Content-Type' : 'application/sparql-query; charset=utf-8'}
    sparql  = '''
                SELECT ?subject ?predicate ?object
                WHERE {
                ?subject ?predicate ?object
                } LIMIT 5        
            '''
    with closing(requests.post(endpoint, headers=headers, data=sparql.encode('utf-8'), timeout=10) ) as r:
        if r.status_code == 200:
            return 'SUCCESS'
        else:
            app.logger.warning('API: %s \n\n %s', endpoint, r.status_code )
            return 'ERROR'

    try:
        pass
                    
    except requests.RequestException as err:
        app.logger.error('API: %s \n\n %s', endpoint, str(err) )
        return 'ERROR'        

        
### not used with Flask-Session
'''
@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = datetime.timedelta(minutes=app.config['LOGOUT_AFTER'])
    session.modified = True
'''

@app.context_processor
def utility_processor():
    def random_id():
        return uuid.uuid4().hex[:6].upper()
    return dict(random_id=random_id)


@app.context_processor
def utility_processor():
    def isDbLocked():
        return is_lockdb()
    return dict(isDbLocked=isDbLocked)

def is_lockdb():
    lpath = mtu.getLockFpath('lockdb')
    if lpath.is_file():
        return True
    else:
        return False


@app.context_processor
def utility_processor():
    def getLockedBy(userid, uname):
        return get_locked_by(userid, uname)
    return dict(getLockedBy=getLockedBy)

def get_locked_by(userid, uname):
    return str(userid) + '___' + str(uname)


@app.context_processor
def utility_processor():
    def hash_data(data):
        return str(hash(data))
    return dict(hash_data=hash_data)

@app.context_processor
def utility_processor():
    def app_state():
        if app.debug:
            return 'dev'
        else:
            return ''
    return dict(app_state=app_state)

@app.context_processor
def utility_processor():
    def get_user_params(userid):
        return get_uparams(userid)
    return dict(get_user_params=get_user_params)

def get_uparams(userid):
    uparams = get_uparams_skeleton()
    if userid != 0:
        udata = mdb.getUserData(get_db(), userid=userid)
        params = udata['params']
        if params:
            uparams = json.loads(params)

    return uparams

def get_uparams_skeleton():
    params = {}
    params['selected_check'] = []
    params['selected'] = {}
    return params


@app.context_processor
def utility_processor():
    def get_adminMsg():
        mpath = mtu.getTempFpath('admin-msg', year=False)
        if mpath.is_file():
            return mtu.loadJsonFile(mpath)
        else:
            msg = {}
            msg['show'] = 'hide'
            msg['head'] = ''
            msg['text'] = ''
            return msg
    return dict(get_adminMsg=get_adminMsg)


@app.context_processor
def utility_processor():
    def get_statusRep(status):
        return get_statRep(status)
    return dict(get_statusRep=get_statusRep)


def get_statRep(status):
    status_dict = {
        'pending'  : "info",
        'rejected' : "danger",
        'approved' : "success",
        'updated'  : "secondary",
        'deleted'  : "dark",
        'purged'   : "light",
        'locked'   : "warning",
        'unlocked' : "primary"
    }
    return status_dict.get(status, 'secondary')


@app.context_processor
def utility_processor():
    def get_userBadgeRep(ugroup):
        return get_userRep(ugroup)
    return dict(get_userBadgeRep=get_userBadgeRep)

def get_userRep(ugroup):
    ugroup_dict = {
        'manager'     : "primary",
        'editor'      : "success",
        'contributor' : "info",
        'viewer'      : "secondary",
        'disabled'    : "danger"
    }
    return ugroup_dict.get(ugroup, 'light')


@app.context_processor
def utility_processor():
    def langUmls(lang):
        return mtu.getLangCodeUmls(lang)
    return dict(langUmls=langUmls)


@app.context_processor
def utility_processor():
    def deepGet(dictionary, keys, default=0):
        return mtu.deep_get(dictionary, keys, default=default)
    return dict(deepGet=deepGet)


@app.template_filter()
def numberFormat(value):
    return format(int(value), ',d')


@app.template_filter()
def getListSplit(value, delim='|'):
    return value.split(delim)


###  Database

def connect_db():
        rv = sqlite3.connect(app.config['DATABASE'])
        rv.row_factory = sqlite3.Row
        return rv

def get_db():
    if not hasattr(g, 'sqlite_db'):
        try:
            g.sqlite_db = connect_db()
            ##g.sqlite_db.execute('pragma foreign_keys=on')
        except sqlite3.Error as e:
            error = 'Flask get_db error : '+str(e.args[0])
            flash(error, 'danger')
            app.logger.error(error)
            return None
        else:
            return g.sqlite_db
    else:
        return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()
