#!/usr/bin/python3.4

import time
import requests
import sys
import os
import argparse
import datetime
from gi.repository import Gtk, GObject, GdkPixbuf
from gi import require_version 
require_version("Gtk", "3.0")
import threading


class STDetective(threading.Thread):
    def __init__(self, gui, servers):
        super(STDetective, self).__init__()
        self.gui = gui
        self.isOver = False #flag for terminating this thread when icon terminates

        self.server_names = servers
        self.server_ids =[]

        self.isDownloading = False
        self.isUploading = False
        self.isSTAvailable = False
        
        while True:
            try:
                c = requests.get('http://localhost:8384/rest/system/config')
                self.devices = c.json()["devices"]
                self.a,self.b,self.c,self.d= self.request_local_completion()
                self.pa,self.pb,self.pc,self.pd= self.a,self.b,self.c,self.d #previous values, stored to calculate dl speed
                self.isSTAvailable = True
                break
            except:
                #~ raise
                self.isSTAvailable = False
                self.gui.update_icon() 
                time.sleep(3)

        self.DlCheckTime = datetime.datetime.today()
        self.UlCheckTime = self.DlCheckTime
        self.pDlCheckTime = self.DlCheckTime
        self.pUlCheckTime = self.UlCheckTime
        
        self.QuickestServerID=''

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

        try:
            c = requests.get('http://localhost:8384/rest/system/connections')
            self.connected_ids = list(c.json()["connections"].keys())
            self.connected_server_ids = [s for s in self.server_ids if s in self.connected_ids]

            for s in self.connected_server_ids: self.server_completion[s] =  self.request_remote_completion(s)
            if self.connected_server_ids: self.isSTAvailable = True
        except:
            #~ raise
            self.isSTAvailable = False
        
        GObject.idle_add(lambda :self.gui.update_icon(self)) 

        if not self.a == self.b or not self.c == self.d: isDownloading = True
        if all((not p == 100) for p in self.server_completion.values()): self.isUploading = True
        GObject.idle_add(lambda :self.gui.update_icon(self)) 


    def DlCheck(self):
        if not self.isDownloading or (datetime.datetime.today()-self.DlCheckTime).total_seconds() <2: return False
        self.pa, self.pb,self.pc, self.pd =  self.a,self.b,self.c,self.d
        self.a,self.b,self.c,self.d= self.request_local_completion()
        self.pDlCheckTime = self.DlCheckTime
        self.DlCheckTime = datetime.datetime.today() 
        self.update_DLState()

    def UlCheck(self):
        if not self.QuickestServerID or not self.isUploading or (datetime.datetime.today()-self.UlCheckTime).total_seconds() <2: return False
        self.server_completion[self.QuickestServerID] = self.request_remote_completion(self.QuickestServerID)
        self.pUlCheckTime = self.UlCheckTime
        self.UlCheckTime = datetime.datetime.today() 
        self.update_ULState()

    def request_local_completion(self):
        c = requests.get('http://localhost:8384/rest/db/status?folder=default')
        return c.json()["inSyncFiles"], c.json()["globalFiles"],  c.json()["inSyncBytes"], c.json()["globalBytes"]

    def request_remote_completion(self,devid):
        c = requests.get('http://localhost:8384/rest/db/completion?device='+devid+'&folder=default')
        return c.json()["completion"]   

    def update_ULState(self):
        if all((not p == 100) for p in self.server_completion.values()): 
            self.isUploading = True
            self.QuickestServerID =max(self.server_completion.keys(), key = lambda x: self.server_completion[x])
            print(self.QuickestServerID)
        else:
            self.isUploading = False
            self.QuickestServerID=''
    
    def update_DLState(self):
        if not self.a == self.b or not self.c == self.d: isDownloading = True
        else: 
            self.isDownloading = False

    def run(self):
        next_event=1
        while not self.isOver:
            try:
                c = requests.get('http://localhost:8384/rest/system/connections')
                self.connected_ids = list(c.json()["connections"].keys())
                self.connected_server_ids = [s for s in self.server_ids if s in self.connected_ids]

                c = requests.get('http://localhost:8384/rest/events?since='+str(next_event), timeout=(2 if self.isDownloading or self.isUploading else 65))
                events = c.json()
                self.isSTAvailable = True
            except:
                if not self.isDownloading and not self.isUploading:
                    self.isSTAvailable = False
                    GObject.idle_add(lambda :self.gui.update_icon(self)) 
                    time.sleep(3)
                    continue
                else: pass
            for v in events:
                print(v["type"]+str(v["id"]))
                if v["type"] == "LocalIndexUpdated": 
                    self.isUploading = True

                elif v["type"] == "RemoteIndexUpdated":
                    self.isDownloading = True
                elif str(v["type"]) == "FolderSummary": 
                    w = v["data"]["summary"]
                    self.a,self.b,self.c,self.d = w["inSyncFiles"], w["globalFiles"],  w["inSyncBytes"], w["globalBytes"]
                    self.update_DLState()

                if v["type"] == "FolderCompletion":
                    if v["data"]["device"] in self.connected_server_ids: 
                        self.server_completion[v["data"]["device"]] = v["data"]["completion"]
                    self.update_ULState()

            GObject.idle_add(lambda :self.gui.update_icon(self)) #we do it twice because DL/UL check might take ~1s, so this way icon update is quicker.
            self.DlCheck()
            self.UlCheck()            
            GObject.idle_add(lambda :self.gui.update_icon(self)) 
            next_event = events[len(events)-1]["id"]

        sys.exit()

class StikoGui(Gtk.StatusIcon):
    def __init__ (self, iconDir):
        super(StikoGui, self).__init__()

        try:
            self.px_good = GdkPixbuf.Pixbuf.new_from_file(os.path.join(iconDir,'stiko-ok.png'))
            self.px_noST = GdkPixbuf.Pixbuf.new_from_file(os.path.join(iconDir,'stiko-notok.png'))
            self.px_noServer = GdkPixbuf.Pixbuf.new_from_file(os.path.join(iconDir,'stiko-inactive.png'))
            self.px_sync = [GdkPixbuf.Pixbuf.new_from_file(os.path.join(iconDir,'stiko-sync0.png')), 
                        GdkPixbuf.Pixbuf.new_from_file(os.path.join(iconDir,'stiko-sync1.png'))]
        except:
            #~ raise
            print("I coudn't open icon files.")
            sys.exit()  

        self.set_from_pixbuf(self.px_noServer)
        self.connect('activate', self.on_left_click)
        #self.connect('query-tooltip', self.ask_detective) def callback(widget, x, y, keyboard_mode, tooltip, user_param1, ...)
        while Gtk.events_pending(): Gtk.main_iteration() 
        
        self.animation_counter = 1
        self.isAnimated = False   #for controlling animation only

    def on_left_click(event, icon):
        icon.set_visible(False)
        Gtk.main_quit()
   
    def update_icon(self,t):
        print([t.isSTAvailable, len(t.connected_server_ids), t.isDownloading, t.isUploading])
        if t.QuickestServerID: print(str(round((t.d-t.server_completion[t.QuickestServerID]*t.d/100)/1000000,2)))
    
        info_str =''
        if not t.isSTAvailable: 
            info_str += "No contact with syncthing"
            self.set_from_pixbuf(self.px_noST)
            self.isAnimated=False
        elif not t.connected_server_ids:
            info_str += "No servers"
            self.set_from_pixbuf(self.px_noServer)
            self.isAnimated=False

        elif t.isDownloading or t.isUploading:
            info_str +=  str(len(t.connected_server_ids))+" Server" +('s' if len(t.connected_server_ids) >1 else '')
            if t.isDownloading:
                if not t.a==t.b:
                    info_str += "\nDownloading "+str(t.b-t.a)+" file" +('s (' if t.b-t.a>1 else ' (')+str(round((t.d-t.c)/1000000,2))+'MB)'
                else:
                    info_str += "\nChecking remote indices"

            if t.isUploading:
                if t.QuickestServerID:
                    info_str += "\nUploading to "+t.id_dict[t.QuickestServerID] + ' ('+str(round((t.d-t.server_completion[t.QuickestServerID]*t.d/100)/1000000,2))+'MB)'
                else:
                    info_str += "\nChecking local indices"

            if not self.isAnimated: 
                self.isAnimated = True
                self.set_from_pixbuf(self.px_sync[0])
                self.animation_counter = 1
                GObject.timeout_add(600, self.update_icon_animate,t)
        else:
            info_str +=  str(len(t.connected_server_ids))+" Server" +('s' if len(t.connected_server_ids) >1 else '')+"\nUp to Date"            
            self.set_from_pixbuf(self.px_good)
            self.isAnimated=False

        self.set_tooltip_text(info_str)
        while Gtk.events_pending(): Gtk.main_iteration_do(True)

    def update_icon_animate(self,t):
        print("update icon animate")
        print ([t.isDownloading, t.isUploading,t.isSTAvailable, len(t.connected_server_ids), self.isAnimated])
        if (t.isDownloading or t.isUploading) and t.isSTAvailable and t.connected_server_ids and self.isAnimated:
            print("inside")
            self.set_from_pixbuf(self.px_sync[self.animation_counter])
            self.animation_counter = (self.animation_counter + 1) % 2
            return True
        else: 
            return False
        


parser = argparse.ArgumentParser(description = 'This is stiko, an icon for syncthing.',epilog='', usage='stiko.py [options]')
parser.add_argument('--servers', nargs = '+', default ='',help = 'List of names of devices treated as servers, space separated. If empty then all connected devices will be treated as servers.',metavar='')
parser.add_argument('--icons',  default ='',help = 'Path to the directory with icons. If empty then use this script\'s directory ('+os.path.dirname(os.path.abspath(__file__))+')', action="store", metavar='')
args = parser.parse_args(sys.argv[1:])
iconDir = os.path.dirname(__file__) if not args.icons else args.icons[0]

GObject.threads_init()

gui = StikoGui(iconDir)

t = STDetective(gui,args.servers)
t.start()

Gtk.main()
t.isOver = True
