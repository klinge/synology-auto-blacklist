# synology-auto-blacklist
Python script to download and add IPs to the Synologys blacklist database

## Info
Downloads blacklisted IPs from AbuseIpDB and Blocklist.de and adds them to the blacklist database for your Synology NAS

Mostly developed for my personal use, but should work for anyone :) 

## Getting the script
You can get the script in two ways.. 
1) clone the repository https://github.com/klinge/synology-auto-blacklist.git
2) download the latest release https://github.com/klinge/synology-auto-blacklist/releases

## Installation
1. AbuseIpDb requires an api key. So first register there to get your personal api key
2. Rename the file config.ini.ORG to config.ini
3. Add your AbuseIpDb api key to the config.ini file
4. Move the files "blockupdate.py" and "config.ini" to a folder on your NAS
5. Install python3 on your NAS using Package Center
6. ssh to the NAS, change to the folder you put the script in and create a virtual environment, then activate it
```bash
python3 -m venv venv
. venv/bin/activate
```
7. Install the needed dependencies 
```bash
pip install -r requirements.txt
```
8. Use Task Scheduler on the NAS to run the script with the periodicity you want

It it strongly recommended that you backup your database file first! You can do this with the command: 
```bash
python3 blockupdate.py -b [backup-folder]
```

## Usage of the script
Not written yet.. You can see available options by running
```bash
python3 blockupdate.py -h
```

## Inspired by
The script borrows (heavily in parts) from https://github.com/kichetof/AutoBlockIPList