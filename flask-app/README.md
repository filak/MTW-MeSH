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

       $ pip install -r mtw_requirements.txt       

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

## Upgrade Python version in your virtual env

    ```
    $ cd MTW-MeSH\flask-app
    $ venv\Scripts\deactivate.bat
    $ python -m venv --upgrade venv
    $ venv\Scripts\activate.bat
    ```

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

4. Open *dist* folder and test run (and check the logs for any errors)

    ```
    $ mtw-worker.exe --debug
    $ set-mtw-admin.exe --login mtwdev --pwd test
    $ mtw-server.exe --debug
    ```
    
5. Enjoy MTW: http://127.0.0.1:55930/mtw/  

6. Follow the [Docs](https://github.com/filak/MTW-MeSH/wiki/Installation-on-Windows) how to deploy MTW as Windows service for production.

