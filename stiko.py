#!/usr/bin/python3

import time
import requests
import sys
from gi.repository import Gtk, GObject, GdkPixbuf
import threading


class STDetective(threading.Thread):
    def __init__(self, icon):
        super(STDetective, self).__init__()
        self.icon = icon
        self.quit = False
        self.server_names = ['platon', 'archimedes']
        self.server_ids =[]

        self.isDownloading = False
        self.isUploading = False
        self.isSTAvailable = False

        while True:
            try:
                c = requests.get('http://localhost:8384/rest/system/config')
                self.devices = c.json()["devices"]
                a,b,c,d= self.request_local_completion()
                self.isSTAvailable = True
                break
            except:
                self.isSTAvailable = False
                GObject.idle_add(self.update_icon)
                time.sleep(3)

        self.id_dict = {}
        for a in self.devices:
            self.id_dict[a["deviceID"]] =  a['name']

        if any([not (a in self.id_dict.values()) for a in self.server_names]):
            print("Some provided server names are wrong.")
            sys.exit()
        if any([not (a in id_dict.keys()) for a in self.server_ids]):
            print("Some provided server ids are wrong.")
            sys.exit()

        if not self.server_names and not self.server_ids: 
            self.server_ids = self.id_dict.keys()
        else:  
            self.server_ids = [a for a in self.id_dict.keys() if (self.id_dict[a] in self.server_names or a in self.server_ids)]


        self.server_completion = {}
        while True:
            try:
                c = requests.get('http://localhost:8384/rest/system/connections')
                self.connected_ids = list(c.json()["connections"].keys())
                self.connected_server_ids = [s for s in self.server_ids if s in self.connected_ids]

                for s in self.connected_server_ids: self.server_completion[s] =  self.request_remote_completion(s)
                if self.connected_server_ids: 
                    self.isSTAvailable = True
                    break
                time.sleep(3)
            except:
                self.isSTAvailable = False
                GObject.idle_add(self.update_icon)
                time.sleep(3)

        if not a is  b or not c is  d: self.isDownloading = True
        if any((not p == 100) for p in self.server_completion.values()): self.isUploading = True
        GObject.idle_add(self.update_icon)


    def update_icon(self):
        #~ GObject.idle_add(self.update_label, counter)
        #print([len(self.connected_server_ids),self.isSTAvailable,self.isUploading, self.isDownloading])
        self.icon.set_tooltip_text(str([len(self.connected_server_ids),self.isSTAvailable,self.isUploading, self.isDownloading]))

        return False

    def request_local_completion(self):
        c = requests.get('http://localhost:8384/rest/db/status?folder=default')
        return c.json()["inSyncFiles"], c.json()["globalFiles"],  c.json()["inSyncBytes"], c.json()["globalBytes"]

    def request_remote_completion(self,devid):
        c = requests.get('http://localhost:8384/rest/db/completion?device='+devid+'&folder=default')
        return c.json()["completion"]   


    def run(self):
        next_event=1
        while not self.quit:
            try:
                c = requests.get('http://localhost:8384/rest/system/connections')
                self.connected_ids = list(c.json()["connections"].keys())
                self.connected_server_ids = [s for s in self.server_ids if s in self.connected_ids]

                c = requests.get('http://localhost:8384/rest/events?since='+str(next_event))
                events = c.json()
                self.isSTAvailable = True
            except:
                self.isSTAvailable = False
                GObject.idle_add(self.update_icon)
                time.sleep(3)
                continue
            for v in events:
                print(v["type"])
                if v["type"] == "LocalIndexUpdated": self.isUploading = True
                if v["type"] == "RemoteIndexUpdated": self.isDownloading = True
                if str(v["type"]) == "FolderSummary": 
                    w = v["data"]["summary"]
                    a,b,c,d = w["inSyncFiles"], w["globalFiles"],  w["inSyncBytes"], w["globalBytes"]
                    if not a == b or not c == d: isDownloading = True
                    else: 
                        self.isDownloading = False
                if v["type"] == "FolderCompletion":
                    if v["data"]["device"] in self.connected_server_ids: 
                        self.server_completion[v["data"]["device"]] = v["data"]["completion"]
                if any((not p == 100) for p in self.server_completion.values()): self.isUploading = True
                else: self.isUploading = False
            GObject.idle_add(self.update_icon)
            next_event = events[len(events)-1]["id"]


def on_left_click(event, icon):
    icon.set_visible(False)
    Gtk.main_quit()


GObject.threads_init()

px_good = GdkPixbuf.Pixbuf.new_from_file('icon-red.png')
#px_good = px_good.add_alpha(True,255,255,255)

icon = Gtk.StatusIcon()
icon.set_from_pixbuf(px_good)
#~ icon.connect('popup-menu', on_right_click)
icon.connect('activate', on_left_click,icon)
icon.set_has_tooltip(True)

def  update_icon_watchdog():
    icon.set_tooltip_text("HAHA!")
    return True

GObject.timeout_add_seconds(1, update_icon_watchdog)

t = STDetective(icon)
t.start()

Gtk.main()
t.quit = True









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
