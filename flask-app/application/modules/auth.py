from functools import wraps
from itsdangerous import URLSafeTimedSerializer
from secrets import compare_digest

from flask import abort, request, session, redirect, url_for, has_app_context, has_request_context
from flask import current_app as app

WORKER_TOKEN_HEADER = 'x-mdv-api-token'


def login_required(f):
    @wraps(f)
    def secure_function(*args, **kwargs):
        if not session.get('logged_in'):
            session['next'] = request.url
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return secure_function 


def public_api_only():
    def decorator(f):
        @wraps(f)
        def check_public(*args, **kwargs):

            if app.config.get('API_STATUS') == 'private':
                if not app.config.get('APP_RELAXED'):

                    if not validateBasicAuth():
                        abort(403)

                    code, msg = validateRequest()

                    if app.debug:
                        print(code, msg)

                    if code != 200:
                        app.logger.error(msg)
                        abort(403)
            
            return f(*args, **kwargs)  

        return check_public
    return decorator


def validateBasicAuth():
    if has_request_context():
        if app.config.get('API_AUTH_BASIC'): 
            user, pwd = app.config.get('API_AUTH_BASIC')
            if user and pwd:
                auth = request.authorization
                if (auth is not None
                    and auth.type == "basic"
                    and auth.username == user
                    and compare_digest(auth.password, pwd)
                ):
                    return True
        else:
            return True
        
    if has_app_context():
        app.logger.error('Basic Auth failed')   

 
def getReqHost():
    if has_request_context():
        return str(request.host).strip().split(':')[0]


def getReqOrigin():
    if has_request_context():
        if request.origin:
            origin = str(request.origin).strip().replace('https://','').replace('http://','').strip()
            return origin.split(':')[0] 
        return getReqHost()    
  

def validateRequest(token=None):

    if not has_app_context():
        return (418, 'No app context') 

    if not has_request_context():
        return (418, 'No request context')

    if not token:
        if request.method == 'GET':
            token = request.args.get('token')

        if not token:
            token = request.headers.get(WORKER_TOKEN_HEADER)    
        
    if not token:
        errmsg = 'Missing token'
        return (403, errmsg)  

    token_data = decodeApiToken(token, app.config.get('API_KEY'), 
                                        salt=app.config.get('API_SCOPE'),  
                                        max_age=app.config.get('API_MAX_AGE') )

    if not token_data:
        errmsg = 'Invalid token'
        return (403, errmsg)

    host = getReqHost()
    host_token = str(token_data).strip().split(':')[0]

    errmsg = check_hostnames(host, host_token, ttype='request')

    if errmsg:
        return (403, errmsg)
    else:
        return (200, 'OK')


def check_hostnames(host, host_token, ttype='request'):

    if host_token not in ['localhost','127.0.0.1']:
        
        app_host = app.config.get('SERVER_NAME', app.config.get('APP_HOST'))

        if app_host and host_token != app_host:
            errmsg = 'Invalid ' + ttype + ' from : ' + host
            if ttype == 'request':
                errmsg += ' : ' + get_headers_log() 
            return errmsg


def get_headers_log():
    headers = ''
    try:
        headers = request.headers.environ     
    except:
        headers = 'NO_HEADERS'
    return str(headers)       


def decodeApiToken(token, secret, salt=None, max_age=10):
    s = URLSafeTimedSerializer(secret, salt=salt)

    try:
        return s.loads(token, max_age=max_age)
    except:
        return False
    

def genApiToken(secret, salt='', data=''):
    s = URLSafeTimedSerializer(secret, salt=salt)
    return s.dumps(data) 


def genApiHeaders(data='check'):
    api_token = genApiToken(app.config['API_KEY'], 
                            salt=app.config['API_SCOPE'],
                            data=data)
    headers = {WORKER_TOKEN_HEADER: api_token}    

    return headers
    
