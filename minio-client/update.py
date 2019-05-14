import pandas as pd
from bs4 import BeautifulSoup
import os
import re
import subprocess
import requests
import urllib.request
import json
import hashlib
import untangle
from distutils.version import StrictVersion
from xml.etree import ElementTree as et

def sha256sum(filename):
    h  = hashlib.sha256()
    b  = bytearray(128*1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        for n in iter(lambda : f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()

nuspecfile = './minio-client/minio-client.nuspec'
ps1file = './minio-client/tools/chocolateyinstall.ps1'
tmpfile = './minio-client/tmp.file'
dlurl = 'https://dl.minio.io/client/mc/release/windows-amd64/mc.exe'

print('Searching for minio-client update')

# Get latest version information an download url from JSON
url = 'https://dl.minio.io/client/mc/release/windows-amd64/'
data = requests.get(url).text
soup = BeautifulSoup(data, 'lxml')
table = soup.find_all('table')[0] 
latestversion = ''
for row in table.find_all('tr'):
    if latestversion != '':
        break
    columns = row.find_all('td')
    for column in columns:
        val = column.get_text()
        if len(val) == 16:
            latestversion = val[:10].replace('-', '.')
            break

print('Latest version from minio download page: ' + latestversion)

# Get last committed chocolatey version from nuspec
obj = untangle.parse(nuspecfile)
mcvercion = obj.package.metadata.version.cdata
print('Chocolatey Version: ' + mcvercion)

if StrictVersion(latestversion) > StrictVersion(mcvercion):
    print('We have an update')
    print('Downloading file')
    print('Download URL: ' + dlurl)
    urllib.request.urlretrieve(dlurl, tmpfile)
    print('Calculating sha256 checksum')
    shachecksum = sha256sum(tmpfile)
    print('Deleting downloaded file')
    os.remove(tmpfile)
    print('Replacing version in ' + nuspecfile)
    with open(nuspecfile, 'r') as f:
        content = f.read()
        content_new = re.sub(pattern="<version>\d\.\d\.\d</version>", repl="<version>" + latestversion + "</version>", string=content)
    print('Writing new ' + nuspecfile)
    with open(nuspecfile, 'w') as f:
        f.write(content_new)            
    print('Replacing checksum in ' + ps1file)
    with open(ps1file, 'r') as f:
        content = f.read()
        content_new = re.sub(pattern="checksum64\s*=\s*'.*'", repl="checksum64    = '" + shachecksum + "'", string=content)
    print('Writing new ' + ps1file)
    with open(ps1file, 'w') as f:
        f.write(content_new)            
    print('Chocolatey pack')
    subprocess.call(['choco.exe', 'pack'], cwd='./minio-client')
    print('Chocolatey push')
    subprocess.call(['choco.exe', 'push'], cwd='./minio-client')
    print('Git commit')
    subprocess.call(['git.exe', 'commit', '-m "Minio client automatic update"', "--author=<autoupdate>"], cwd='./minio-client')
    subprocess.call(['git.exe', 'push'], cwd='./minio-client')
else:
    print('No update available')