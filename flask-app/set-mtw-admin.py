# -*- coding: utf-8 -*-
import os, argparse, configparser
import bcrypt
from pathlib import Path

appname = 'set-mtw-admin'
appversion = '1.3.1'
appdesc = '(re)Set Admin credentials and SecKeys in MTW Admin Config'
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
    parser.add_argument('--worker', help='Reset Worker section only', action='store_true')

    args, unknown = parser.parse_known_args()

    if unknown:
        print('ERROR : Uknown arguments : ', unknown)
        print('Try : ', appname ,' -h')

    elif args.worker or (args.login and args.pwd):
        procFile(args)

    else:
        print('ERROR : missing params !')


def procFile(args):

    configFile = Path('instance/conf/mtw-admin.tmp')
    config = configparser.RawConfigParser()

    if args.login and args.pwd and not args.worker:
    
        section = 'adminconf'
        config.add_section(section)
        config.set(section, 'SECRET_KEY', str(os.urandom(24) ).replace('%','%%') )
        config.set(section, 'ADMINNAME', args.login)

        pwd = args.pwd
        pwd_hashed = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt(5))
        config.set(section, 'ADMINPASS', pwd_hashed.decode('utf-8') )

        section = 'worker'
        config.add_section(section)
        config.set(section, 'API_KEY', str(os.urandom(24) ).replace('%','%%') )

        with open(str(configFile), 'w', encoding='utf-8') as configfile:
            config.write(configfile)        

    elif args.worker and configFile.exists():

        config.read(configFile)

        section = 'worker'
        config.remove_section(section)
        config.add_section(section)
        config.set(section, 'API_KEY', str(os.urandom(24) ).replace('%','%%') )

        with open(str(configFile), 'w', encoding='utf-8') as configfile:
            config.write(configfile)


    if configFile.exists():
        print('\nAdmin Config updated: ', str(configFile), '\n')
        print('\nYou MUST restart the App for changes to take effect ! \n')

    else:
        print('ERROR: Cannot write config file: ', str(configFile))


if __name__ == '__main__':
    main()

