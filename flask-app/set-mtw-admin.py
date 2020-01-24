# -*- coding: utf-8 -*-
import os, sys, argparse, string, io, configparser
import bcrypt
from pathlib import Path

appname = 'set-mtw-admin'
appversion = '1.2'
appdesc = '(re)Set Admin credentials and SecKey in MTW Admin Config'
appusage = 'Help:   '+ appname +' -h '

def main():

    print('\n')
    print('********************************************')
    print('*  ', appname, appversion)
    print('********************************************')
    print('*  ', appdesc)
    print('*  ', appusage)
    print('********************************************\n')

    parser = argparse.ArgumentParser(description=appdesc, prog=appname, usage='%(prog)s --login ... -pwd ... ')
    parser.add_argument('--login', type=str, help='Admin login')
    parser.add_argument('--pwd', type=str, help='Admin password')

    args, unknown = parser.parse_known_args()

    if unknown:
        print('ERROR : Uknown arguments : ', unknown)
        print('Try : ', appname ,' -h')

    elif not args.login or not args.pwd:
        print('ERROR : missing params !')

    else:
        configFile = Path('instance/conf/mtw-admin.tmp')
        procFile(configFile, args)


def procFile(fpath, args):

    config = configparser.RawConfigParser()

    section = 'adminconf'
    config.add_section(section)
    config.set(section, 'SECRET_KEY', str(os.urandom(24) ).replace('%','%%') )
    config.set(section, 'ADMINNAME', args.login)

    pwd = args.pwd
    pwd_hashed = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt(5))
    config.set(section, 'ADMINPASS', pwd_hashed.decode('utf-8') )

    with open(str(fpath), 'w', encoding='utf-8') as configfile:
        config.write(configfile)

    if fpath.exists():
        print('\nAdmin Config updated: ', str(fpath), '\n')
        print('\nYou MUST restart the App for changes to take effect ! \n')

    else:
        print('ERROR: Cannot write config file: ', str(fpath))


if __name__ == '__main__':
    main()

