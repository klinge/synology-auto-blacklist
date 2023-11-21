# synology-auto-blacklist
Python script to download and add IPs to the Synologys blacklist database

## Info
Downloads blacklisted IPs from AbuseIpDB and Blocklist.de and adds them to the blacklist database for your Synology NAS

## Installation
1. AbuseIpDb requires an api key. So first register there to get your personal api key
2. Rename the file config.ini.ORG to config.ini
3. Add your AbuseIpDb api key to the config.ini file
4. Move the files blockupdate.py and config.ini to a folder on your NAS
5. Install python3 on your NAS using Package Center
6. Use cron to schedule run the script with the periodicity you want

## Usage of the script
<TODO>

## Inspired by
The script borrows (heavily in parts) from https://github.com/kichetof/AutoBlockIPList