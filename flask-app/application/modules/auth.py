from functools import wraps
from itsdangerous import URLSafeTimedSerializer

from flask import abort, render_template, request, session, redirect, url_for
from flask import current_app as app


def login_required(func):
    @wraps(func)
    def secure_function(*args, **kwargs):
        if not session.get('logged_in'):
            session['next'] = request.url
            return redirect(url_for('login'))
        return func(*args, **kwargs)

    return secure_function 


def public_api_only(func):
    @wraps(func)
    def check_public(*args, **kwargs):

        if app.config.get('API_STATUS') == 'private':
            if not app.debug and not app.config.get('APP_RELAXED'):
                code, msg = validateRequest(app, request)
                if code != 200:
                    app.logger.error(msg)
                    abort(403)
        
        return func(*args, **kwargs)  

    return check_public


def validateRequest(app, request):

    errmsg  = ''
    token = request.headers.get('x-mdv-api-token')

    if not token:
        errmsg = 'Missing token'

    token_data = decodeApiToken(token, app.config.get('API_KEY'), 
                                        salt=app.config.get('API_SALT'), 
                                        max_age=app.config.get('API_MAX_AGE'), 
                                        debug=False)

    if not token_data:
        errmsg = 'Invalid token'

    host_check = str(token_data).strip().split(':')[0]

    if host_check not in ['localhost', '127.0.0.1']:
        hostname = request.host.strip().split(':')[0]
        mtw_host = app.config.get('APP_HOST')

        if host_check != mtw_host:
            headers = None
            try:
                headers = request.headers.environ
            except:
                pass
                
            errmsg = 'Invalid request from : ' + hostname + ' : ' + str(headers)

    if errmsg:
        return(403, errmsg)
    else:
        return(200, 'OK')    


def decodeApiToken(token, secret, salt='', max_age=5, debug=False):
    s = URLSafeTimedSerializer(secret, salt=salt)

    try:
        return s.loads(token, max_age=max_age)
    except:
        return False
    

def genApiToken(secret, salt='', data='check'):
    s = URLSafeTimedSerializer(secret, salt=salt)
    return s.dumps(data) 


def genApiHeaders():
    api_token = genApiToken(app.config['API_KEY'], 
                            salt=app.config['API_SALT'],
                            data=str(request.host)) 
    headers = {'x-mdv-api-token': api_token}  

    return headers
    