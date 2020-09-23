# MTW Flask web-app

## Development - Run with Python

Prerequisites: Python 3.7+, Git, Java8 JRE

> Tip: You can run in [Visual Studio Code](https://code.visualstudio.com/docs/python/python-tutorial)

1. Install: 

    - Apache Jena/Fuseki, SQLite and load some MeSH datasets - see the [wiki](https://github.com/filak/MTW-MeSH/wiki)

2. Clone the repo: 

       $ git clone https://github.com/filak/MTW-MeSH

3. Adjust the config file: [mtw.ini](https://github.com/filak/MTW-MeSH/blob/master/flask-app/instance/conf/mtw.ini) in *MTW-MeSH\\flask-app\\instance\\conf* folder 

4. Create virtualenv &amp; activate it:

    ```
    $ cd MTW-MeSH\flask-app
    $ py -3 -m venv venv
    $ venv\Scripts\activate.bat

    ($ venv\Scripts\deactivate.bat)
    ```

5. Upgrade the environment tools - run:

    ```
    $ python -m pip install --upgrade pip
    $ pip install setuptools --force
    $ pip install wheel --force
    ```
    
6. Install dependencies - run:

       $ pip install -r *_requirements.txt

7. Run set-mtw-admin tool: 

       $ python set-mtw-admin.py --login <ADMIN_LOGIN> --pwd <ADMIN_PASSWD>

8. Run worker &amp; server apps: 

    ```
    $ python run-worker-dev.py
    $ python run-server-dev.py
    ```

9. Enjoy:   http://127.0.0.1:5900/mtw/

## Build for Windows

1. Activate virtualenv

       $ venv\Scripts\activate.bat

2. Run all !build_*.bat files

    ```
    $ !!build__mtw-server.bat
    $ !!build__mtw-tools.bat
    $ !!build__mtw-worker.bat
    $ !!build__set-mtw-admin.bat
    ```

3. Check *dist* folder

## Install MTW-Server and MTW-Worker as a Windows service

1. Install [NSSM](https://nssm.cc) service manager

2. Go to *dist* folder and run for both services:

       $ nssm install <SERVICE_NAME>-<PORT>

    - Application - Path:

          C:\Programs\...\dist\*-server.exe

    - Application - Startup dir:

           C:\Programs\...\dist   

    - Application - Arguments - leave empty or check the [Docs](https://github.com/filak/MTW-MeSH/wiki/Installation-on-Windows#install-mtw-server)

3. Adjust the config file: [mtw-dist.ini](https://github.com/filak/MTW-MeSH/blob/master/flask-app/dist/instance/conf/mtw-dist.ini)

    - and copy the file to *dist\\instance\\conf* folder

4. Create the production database - go to *dist\\db* folder and run: 

       $ sqlite3 mtw.db < mtw_schema.sql

5. Run set-mtw-admin tool: 

       $ set-mtw-admin.exe --login <ADMIN_LOGIN> --pwd <ADMIN_PASSWD>     

6. Start the service using Win Services manager or run:

       $ nssm start <SERVICE_NAME>-<PORT>

7. Follow the [Deployment](https://github.com/filak/MTW-MeSH/wiki#deployment) instructions   

