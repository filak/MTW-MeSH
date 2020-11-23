# MTW Flask web-app

## Development - Run with Python

Prerequisites: Python 3.7+, Git, Java8 JRE

> Tip: You can use [Visual Studio Code](https://code.visualstudio.com/docs/python/python-tutorial)

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

7. Create database - run:

       $ cd instance/db
       $ sqlite3 mtw.db < mtw_schema.sql
       $ cd ../..

8. Run set-mtw-admin tool: 

       $ python set-mtw-admin.py --login <ADMIN_LOGIN> --pwd <ADMIN_PASSWD>

9. Run worker &amp; server apps: 

    ```
    $ python run-worker-dev.py
    $ python run-server-dev.py
    ```

10. Enjoy:   http://127.0.0.1:5900/mtw/

## Deploy on Linux

https://flask.palletsprojects.com/en/1.1.x/deploying/#deployment

## Building for Windows

1. Activate virtualenv

       $ venv\Scripts\activate.bat
       
3. Install Pyinstaller and Pywin32 (pywin32_postinstall.py MUST be run as Admin)

       $ pip install pyinstaller 
       $ pip install pywin32
       $ python venv/Scripts/pywin32_postinstall.py -install       

3. Run all !build_*.bat files

    ```
    $ !!build__mtw-server.bat
    $ !!build__mtw-tools.bat
    $ !!build__mtw-worker.bat
    $ !!build__set-mtw-admin.bat
    ```

4. Check *dist* folder

5. Follow the [Docs](https://github.com/filak/MTW-MeSH/wiki/Installation-on-Windows#install-mtw-server-and-mtw-worker-as-windows-service) to install MTW-Server and MTW-Worker as Windows services

