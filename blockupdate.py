# pylint: disable=missing-function-docstring,line-too-long,unspecified-encoding,logging-fstring-interpolation
'''
A command line tool that downloads lists of blacklisted IPs from the internet and
updates the database in a Synology server that holds blocked IP addresses. 

Intended use is to schedule running the tool with cron/Task Scheduler and running it to keep
constantly updated list of IPs to block

    Usage: 
        run blockupdate.py 
    Options: 
        -u - download and update blocklist
        -e - set expire time (in days) on the new posts
        -v - verbose
        -b [backup-path] - backup database to backup-path
        --dry-run - only test 
        --clear-database - deletes all rows from blocklist

        To see all options run blockupdate.py -h

    Results:
        when run with the -u option updates the database synoautoblock.db 
'''

import os
import argparse
import logging
import configparser
import shutil
from datetime import datetime
import time
import sqlite3
import json
import ipaddress
import requests


## FETCH values from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

VERSION = config.get('APP', 'version')
ABUSE_KEY = config.get('APP', 'abuseipkey')
ENV = config.get('APP', 'env')
LOGLEVEL = getattr(logging, config.get('LOGGING', 'loglevel'))
USECERT = config['APP'].getboolean('use-extra-cert')
if USECERT:
    CERT = config.get('APP', 'cert-path')

logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.ERROR,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger.setLevel(LOGLEVEL)

db = config.get('DATABASE', 'dbfile')

def create_connection(db_file):
    try:
        return sqlite3.connect(db_file)
    except sqlite3.Error as e:
        raise e

def download_blocklist():
    data = ""
    url = "https://lists.blocklist.de/lists/all.txt"

    try:
        if USECERT:
            response = requests.get(url=url, verify=CERT, timeout=10)
        else:
            response = requests.get(url=url, timeout=10)
        data = response.text.split("\n")
    except requests.exceptions.RequestException as e:
        logger.warning(f"WARNING: unable to connect to blocklist.de. Error was: {e}")

    return data

def download_abuseipdb(key):
    data = ""
    test_file = ""

    if ENV != 'PROD':
        #FOR TESTING: use a file with the json test data since AbuseIpDb only allows 5 daily calls to the API..
        test_file = "test-data/abuseip.json"

    url = 'https://api.abuseipdb.com/api/v2/blacklist'
    querystring = {
        'confidenceMinimum':'90'
    }
    headers = {
        'Accept': 'application/json',
        'Key': key
    }
    try:
        # check if test file exists - if so use it instead of calling api
        if ENV != 'PROD':
            logger.info("-abuseipdb: reading test data from file..")
            with open(test_file) as data:
                decoded_response = json.load(data)
                data.close()
        else:
            logger.info("-abuseipdb: getting data from API..")
            if USECERT:
                response = requests.get(url=url, headers=headers, params=querystring, verify=CERT, timeout=10)
            else:
                response = requests.get(url=url, headers=headers, params=querystring, timeout=10)
            decoded_response = json.loads(response.text)

        # Extract IP addresses from json
        resp_data = decoded_response['data'] #select only the data part of the json
        data = [item['ipAddress'] for item in resp_data] # create data using list comprehension

    except requests.exceptions.RequestException as e:
        logger.warning("WARNING: unable to connect to AbuseIpDB. Error was: %s", e)

    return data

def process_ip(ip_list, expire):
    processed = []
    invalid = []
    for i in ip_list:
        try:
            ip = ipaddress.ip_address(i)
            if ip.version == 4:
                ipstd = ipv4_to_ipstd(i)
            elif ip.version == 6:
                ipstd = ipv6_to_ipstd(i)
            else:
                ipstd = ""
            processed.append([i, ipstd, expire])
        except ValueError:
            if i != "":
                invalid.append(i)
    return processed, invalid

def ipv4_to_ipstd(ipv4):
    # pylint: disable=consider-using-f-string
    numbers = [int(bits) for bits in ipv4.split('.')]
    return '0000:0000:0000:0000:0000:ffff:{:02x}{:02x}:{:02x}{:02x}'.format(*numbers).upper()

def ipv6_to_ipstd(ipv6):
    return ipaddress.ip_address(ipv6).exploded.upper()

def folder(attr='r'):
    def check_folder(path):
        if os.path.isdir(path):
            if attr == 'r' and not os.access(path, os.R_OK):
                raise argparse.ArgumentTypeError(f'"{path}" is not readable.')
            if attr == 'w' and not os.access(path, os.W_OK):
                raise argparse.ArgumentTypeError(f'"{path}" is not writable.')
            return os.path.abspath(path)
        raise argparse.ArgumentTypeError(f'"{path}" is not a valid path.')
    return check_folder

def parse_args():
    parser = argparse.ArgumentParser(prog='blockupdate')
    parser.add_argument("-u", "--update", action='store_true', help="Update the database")
    parser.add_argument("-e", "--expire-in-day", type=int, default=0,
                        help="Expire time in day. Default 0: no expiration")
    parser.add_argument("--remove-expired", action='store_true',
                        help="Remove expired entry")
    parser.add_argument("-b", "--backup-to", type=folder('w'),
                        help="Folder to store a backup of the database")
    parser.add_argument("--clear-db", action='store_true',
                        help="Clear ALL deny entry in database before filling")
    parser.add_argument("--dry-run", action='store_true',
                        help="Perform a run without any modifications")
    parser.add_argument("-v", "--verbose", action='store_true',
                        help="Increase output verbosity")
    parser.add_argument('--version', action='version', version=f'%(prog)s version {VERSION}')

    a = parser.parse_args()

    if a.clear_db and a.backup_to is None:
        # pylint: disable=raising-bad-type
        raise parser.error("backup folder should be set for clear db")
    if a.dry_run:
        a.verbose = True

    return a

if __name__ == '__main__':

    start_time = time.time()
    args = parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)

    ## CONNECT TO DATABASE
    #Sqlite3 just silently creates an empty database file is none is found so check that it exists first..
    if not os.path.isfile(db):
        raise FileNotFoundError(f"No such file or directory: '{db}'")
    if not os.access(db, os.R_OK):
        raise FileExistsError("Unable to read database. Run this script with sudo or root user.")

    conn = create_connection(db)
    c = conn.cursor()

    ## DATABASE BACKUP
    if args.backup_to is not None:
        filename = datetime.now().strftime("%Y%m%d_%H%M%S") + "_backup_synoautoblock.db"
        shutil.copy(db, os.path.join(args.backup_to, filename))
        logger.info("Database backup successful")

    ## SET EXPIRE DATE
    if args.expire_in_day > 0:
        args.expire_in_day = int(start_time) + args.expire_in_day * 60 * 60 * 24
        logger.info(f'Expire time set to: {args.expire_in_day}')

    ## REMOVE EXPIRED ROWS IN DATABASE
    if args.remove_expired:
        COUNT_SQL = "SELECT COUNT(*) from AutoBlockIP WHERE Deny = 1 AND ExpireTime > 0 AND ExpireTime < strftime('%s','now')"
        DELETE_SQL = "DELETE FROM AutoBlockIP WHERE Deny = 1 AND ExpireTime > 0 AND ExpireTime < strftime('%s','now')"

        count = c.execute(COUNT_SQL).fetchone()[0]
        logger.info(f'Remove expired: ready to delete {count} expired posts in the database')

        if not args.dry_run:
            c.execute(DELETE_SQL)
            conn.commit()
            logger.info("All expired entries were successfully removed")

    ## REMOVE ALL POSTS IN DATABASE
    if args.clear_db:
        count = c.execute("SELECT COUNT(*) from AutoBlockIP").fetchone()[0]
        logger.info(f'Clear DB: ready to delete {count} rows in the database')

        if not args.dry_run:
            c.execute("DELETE FROM AutoBlockIP WHERE Deny = 1")
            conn.commit()
            logger.info("All deny entries were successfully removed")

    ## DOWNLOAD NEW LISTS AND UPDATE DATABASE
    if args.update:
        # save results in a set to make sure there are no duplicates
        ip_blacklist = set()

        ## DOWNLOAD FROM BLOCKLIST.DE
        logger.info("Downloading blacklist from blocklist.de...")

        blocklist_blacklist = download_blocklist()
        logger.info(f"-blocklist.de: Successfully downloaded {len(blocklist_blacklist)} IPs.")

        result, failed = process_ip(blocklist_blacklist, args.expire_in_day)
        logger.info(f"--Processed IP list. Adding: {len(result)} items. Failed: {len(failed)}")

        result_set = { tuple(s) for s in result } #convert the list in result to a set
        ip_blacklist.update(result_set)

        ## DOWNLOAD FROM ABUSEIP
        logger.info("Downloading blacklist from abuseipdb.com...")

        abuseipdb_blacklist = download_abuseipdb(ABUSE_KEY)
        logger.info(f"-abuseipdb.com: Successfully downloaded {len(abuseipdb_blacklist)} IPs.")

        result, failed = process_ip(abuseipdb_blacklist, args.expire_in_day)
        logger.info(f"--Processed IP list. Adding: {len(result)} items. Failed: {len(failed)}")

        result_set = { tuple(s) for s in result } #convert the list in result to a set
        ip_blacklist.update(result_set)

        logger.info(f"Blacklist total: {len(ip_blacklist)}")

        count_ip = c.execute("SELECT COUNT(IP) FROM AutoBlockIP WHERE Deny = 1")
        count_ip_before = count_ip.fetchone()[0]
        logger.info(f"Number of IPs in database before update: {count_ip_before}")

        # UPDATE DATABASE
        if not args.dry_run:
            logger.info("Updating database...")
            c.executemany("REPLACE INTO AutoBlockIP (IP, IPStd, ExpireTime, Deny, RecordTime, Type, Meta) "
                            "VALUES(?, ?, ?, 1, strftime('%s','now'), 0, NULL);", ip_blacklist)
            conn.commit()
        else:
            logger.warning("Dry run - no update of the database done..")

        count_ip = c.execute("SELECT COUNT(IP) FROM AutoBlockIP WHERE Deny = 1")
        count_ip_after = count_ip.fetchone()[0]
        logger.info(f"Number of IPs in database after update: {count_ip_after}")

    logger.info("Closing DB...")
    conn.close()

    elapsed = round(time.time() - start_time, 2)
    logger.info(f"Elapsed time: {elapsed} seconds")
