#!/usr/bin/python3

import time
import requests
import sys

server_names = ['platon', 'archimedes']
server_ids =[]

isDownloading = False
isUploading = False
isBusy = True  
isSTAvailable = False
#isServerPresent = False 

def request_local_completion():
    c = requests.get('http://localhost:8384/rest/db/status?folder=default')
    return c.json()["inSyncFiles"], c.json()["globalFiles"],  c.json()["inSyncBytes"], c.json()["globalBytes"]

def request_remote_completion(devid):
    c = requests.get('http://localhost:8384/rest/db/completion='+devid+'?folder=default')
    return c.json()["completion"]   

while True:
    try:
        c = requests.get('http://localhost:8384/rest/system/config')
        devices = c.json()["devices"]
        a,b,c,d= request_local_completion()
        isSTAvailable = True
        break
    except:
        isSTAvailable = False
        print("No response from Syncthing")
        time.sleep(3)

id_dict = {}
for a in devices:
    id_dict[a["deviceID"]] =  a['name']

if any([not (a in id_dict.values()) for a in server_names]):
    print("Some provided server names are wrong.")
    sys.exit()
if any([not (a in id_dict.keys()) for a in server_ids]):
    print("Some provided server ids are wrong.")
    sys.exit()

if not server_names and not server_ids: 
    server_ids = id_dict.keys()
else:  
    server_ids = [a for a in id_dict.keys() if (id_dict[a] in server_names or a in server_ids)]


server_completion = {}
while True:
    Try:
        c = requests.get('http://localhost:8384/rest/system/connections')
        connected_ids = list(c.json()["connections"].keys())
        connected_server_ids = [s for s in server_ids if s in connected_ids]

        for s in connected_server_ids: server_completion[s] =  request_remote_completion(s)
        if connected_server_ids: break
        time.sleep(3)
    Except:
        isSTAvailable = False
        print("No response from Syncthing")
        time.sleep(3)

if a is not b or c is not d: isDownloading = True
if all((p is not 100) for p in server_completion.values()): isUploading = True

print(server_ids)
print(connected_ids)

last_event = -1



#~ loop with breaks of 5s to get
    #~ foldercompletion, 
    #~ known hosts with keys, 
    #~ connected-hosts
#~ on success set isAnsweringST to true.


#~ loop with breaks of 5s to get
    #~ foldersummary for names in servernames \cap connected-hosts
    #~ if at least one answers then set isServerPresent to True

#~ Based on the foldersummaries and foldercompletions set isDownloading and isUploading

#~ main loop
    #~ get new events
    #~ go through events
        #~ if not isServerPresent then only look on connect/disconnect
        #~ if IndexUpdated set isUploading or isDownloading true
        #~ if foldersummaries of foldercopletions set isDownloading/ isUploading to true or false
        #~ if connect/disconnect -> update list of servers.

    #~ if isUploading of isDownloading for some time, say 3min, then query if any servers are present and reset isServerPresent.
    
    #~ if icon_state need be changed then 
        #~ reset_icon
        #~ save icon_state

#~ -jesli nie moge sie polaczyc z syncthing to czekam dalej bo moze dopiero wystartowal?
#~ -poza tym mozemy ominac RemoteIndexUpdated i LocalIndexUpdated, wiec na poczatek robimy query "FolderCompletion" oraz "FolderSummary" wszystkich serwerow (do momentu gdy zobaczymy jeden ktory ma FolderSummary "100".

#~ -jesli widze "LocalIndexUpdated" po lokalnej zmianie, to mam pewnosc, ze ktos ma moja lokalna zmiane dopiero gdy widze "FolderCompletion" z completion=100

#~ -jesli widze "RemoteIndexUpdated" to moge zaczac pytac o FolderSummary dopoki pokazuje, ze cos trzeba sciagnac, to ikonka pokazuje, ze konieczny download.

#~ -co jakis czas trzeba patrzyc czy jestesmy z kimkolwiek polaczeni - jesli nie to rpzestajemy pokazywac cokolwiek.
    #~ gdy nic sie nie dzieje to nie patrzymy
    #~ gdy jestesmy w trakcie to patrzymy co powiedzmy 4s.

#~ -jesli dostaniemy FolderSummary ktory pokazuje ze cos trzeba sciagnac to przechodzimy tak czy inaczej (niezaleznie czy widzialem RemoteIndexUpdated) w tryb "Downloading"

#~ issues (why would it be better if syncthing did it): 
#~ -this depends on seeing all "LocalIndexUdated". 
#~ -at the beginning we might miss something
#~ -if webapp is part of st, why icon can't be - the same problems need to be solved.
#~ -if st config changed ping time then this might not work


#~ -would be nice to have st feature to allow stopping upload to servers if at least one server has it. Or simply a rule as to whom to speak (like: if platon is present don't talk to archimedes)
