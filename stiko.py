#!/usr/bin/python3.4

import time
import requests
import sys
import os
import argparse
from gi.repository import Gtk, GObject, GdkPixbuf
from gi import require_version 
require_version("Gtk", "3.0")
import threading


class STDetective(threading.Thread):
    def __init__(self, gui, servers):
        super(STDetective, self).__init__()
        self.gui = gui
        self.isOver = False #flag for terminating when icon terminated

        self.server_names = servers
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
                #~ raise
                self.isSTAvailable = False
                self.gui.update_icon() 
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

        if not a is  b or not c is  d: self.isDownloading = True
        if all((not p == 100) for p in self.server_completion.values()): self.isUploading = True
        GObject.idle_add(lambda :self.gui.update_icon(self)) 



    def request_local_completion(self):
        c = requests.get('http://localhost:8384/rest/db/status?folder=default')
        return c.json()["inSyncFiles"], c.json()["globalFiles"],  c.json()["inSyncBytes"], c.json()["globalBytes"]

    def request_remote_completion(self,devid):
        c = requests.get('http://localhost:8384/rest/db/completion?device='+devid+'&folder=default')
        return c.json()["completion"]   


    def run(self):
        next_event=1
        while not self.isOver:
            try:
                c = requests.get('http://localhost:8384/rest/system/connections')
                self.connected_ids = list(c.json()["connections"].keys())
                self.connected_server_ids = [s for s in self.server_ids if s in self.connected_ids]

                c = requests.get('http://localhost:8384/rest/events?since='+str(next_event))
                events = c.json()
                self.isSTAvailable = True
            except:
                #~ raise
                self.isSTAvailable = False
                GObject.idle_add(lambda :self.gui.update_icon(self)) 
                time.sleep(3)
                continue
            for v in events:
                #~ print(v["type"])
                if v["type"] == "LocalIndexUpdated": 
                    self.isUploading = True

                elif v["type"] == "RemoteIndexUpdated": 
                    self.isDownloading = True
                elif str(v["type"]) == "FolderSummary": 
                    w = v["data"]["summary"]
                    a,b,c,d = w["inSyncFiles"], w["globalFiles"],  w["inSyncBytes"], w["globalBytes"]
                    if not a == b or not c == d: isDownloading = True
                    else: 
                        self.isDownloading = False
                GObject.idle_add(lambda :self.gui.update_icon(self)) 

                if v["type"] == "FolderCompletion":
                    if v["data"]["device"] in self.connected_server_ids: 
                        self.server_completion[v["data"]["device"]] = v["data"]["completion"]
                    if all((not p == 100) for p in self.server_completion.values()): self.isUploading = True
                    else: self.isUploading = False
                GObject.idle_add(lambda :self.gui.update_icon(self)) 

            next_event = events[len(events)-1]["id"]


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
        while Gtk.events_pending(): Gtk.main_iteration() 
        
        self.animation_counter = 0
        self.isAnimated = False   #for controlling animation only

    def on_left_click(event, icon):
        icon.set_visible(False)
        Gtk.main_quit()
   
    def update_icon(self,t):
        if not t.isSTAvailable: 
            self.set_tooltip_text("No contact with syncthing")
            self.set_from_pixbuf(self.px_noST)
            self.isAnimated=False
            return False
        if not t.connected_server_ids:
            self.set_tooltip_text("No servers")
            self.set_from_pixbuf(self.px_noServer)
            self.isAnimated=False
            return False
        if t.isDownloading or t.isUploading:
            self.set_tooltip_text(str(len(t.connected_server_ids))+" Server(s)"+
                ("\nDownloading..." if t.isDownloading else '')+
                ("\nUploading..." if t.isUploading else ''))
            self.set_from_pixbuf(self.px_sync[0])
            self.animation_counter = 1
            if not self.isAnimated: GObject.timeout_add(800, self.update_icon_animate,t)
            self.isAnimated=True
        else:
            self.set_tooltip_text(str(len(t.connected_server_ids))+" Server(s)"+ "\nUp to Date")            
            self.set_from_pixbuf(self.px_good)
            self.isAnimated=False
        return False
    
    def update_icon_animate(self,t):
        #~ print("update icon animate")
        if (t.isDownloading or t.isUploading) and t.isSTAvailable and t.connected_server_ids:
            self.set_from_pixbuf(self.px_sync[self.animation_counter])
            self.animation_counter = (self.animation_counter + 1) % 2
            return True
        else:
            #self.update_icon(t)
            self.animation_counter = 0
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
