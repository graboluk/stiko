#!/usr/bin/python3.4

import time
import requests
import sys
import os
import argparse
import datetime
from gi import require_version 
require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, GdkPixbuf
import threading
import collections


class STDetective(threading.Thread):
    def __init__(self, gui, servers):
        super(STDetective, self).__init__()
        self.gui = gui

        #flag for terminating this thread when icon terminates
        self.isOver = False 

        self.server_names = servers
        self.server_ids =[]
        self.server_completion = {}
        self.connections = {}
        self.pconnections = {}
        self.id_dict = {}

        # current and previous inSyncFiles, globalFiles, inSyncBytes, globalBytes
        self.a,self.b,self.c,self.d, self.pa,self.pb,self.pc,self.pd = [0,0,0,0,0,0,0,0]

        self.isDownloading = False
        self.isUploading = False
        self.isSTAvailable = False

        self.DlCheckTime = datetime.datetime.today()
        self.UlCheckTime = self.DlCheckTime
        self.pDlCheckTime = self.DlCheckTime
        self.pUlCheckTime = self.UlCheckTime
        
        self.UlSpeeds = collections.deque(maxlen=5)
        self.DlSpeeds = collections.deque(maxlen=5)

        self.QuickestServerID=''
    
        config = self.request_config()
        while not self.isOver and not config:
            time.sleep(3)
            config = self.request_config()
    
        # A thread-safe way to demand gui updates. We do it here 
        # because request_config() hopefully changed isSTAvailable to True
        self.update_gui()

        for a in config["devices"]:
            self.id_dict[a["deviceID"]] =  a['name']

        if any([not (a in self.id_dict.values()) for a in self.server_names]):
            print("Some provided server names are wrong.")
            Gtk.main_quit()
            sys.exit()
        if any([not (a in id_dict.keys()) for a in self.server_ids]):
            print("Some provided server ids are wrong.")
            Gtk.main_quit()
            sys.exit()

        if not self.server_names and not self.server_ids: 
            self.server_ids = self.id_dict.keys()
        else:  
            self.server_ids = [a for a in self.id_dict.keys() if (self.id_dict[a] in self.server_names or a in self.server_ids)]

        self.get_base_state()
        self.update_gui()

    def get_base_state():
        self.a,self.b,self.c,self.d = self.request_local_completion()

        self.connections = request_connections()
        self.connected_ids = list(self.connections.keys())
        self.connected_server_ids = [s for s in self.server_ids if s in self.connected_ids]
    
        # the following call doesn't really belong here, but 
        # the call afterwards can take long time, so better update gui now
        self.update_gui()

        self.server_completion = self.request_server_completion()

        self.update_states()



    def update_gui(self):
        GObject.idle_add(lambda :self.gui.update_icon(self)) 

    def DlCheck(self):
        if (datetime.datetime.today()-self.DlCheckTime).total_seconds() <2: 
            time.sleep(1)
            return False
        self.pa, self.pb,self.pc, self.pd =  self.a,self.b,self.c,self.d
        self.a,self.b,self.c,self.d= self.request_local_completion()
        self.pDlCheckTime = self.DlCheckTime
        self.DlCheckTime = datetime.datetime.today() 
        self.update_states()

        self.DlSpeeds.append((self.c-self.pc)/(self.DlCheckTime-self.pDlCheckTime).total_seconds())


    def UlCheck(self):
        if not self.QuickestServerID or not self.isUploading or (datetime.datetime.today()-self.UlCheckTime).total_seconds() <2: return False
        self.server_completion[self.QuickestServerID] = self.request_remote_completion(self.QuickestServerID)
        self.pUlCheckTime = self.UlCheckTime
        self.UlCheckTime = datetime.datetime.today() 
        self.update_states()

        try:
            self.pconnections = self.connections
            self.connections = requests.get('http://localhost:8384/rest/system/connections').json()["connections"]
        except:
            self.isSTAvailable = False
        
        try:
            byte_delta = self.connections[self.QuickestServerID]["outBytesTotal"] - self.pconnections[self.QuickestServerID]["outBytesTotal"]
            time = datetime.datetime.strptime(self.connections[self.QuickestServerID]["at"][:-9], '%Y-%m-%dT%H:%M:%S.%f')
            ptime = datetime.datetime.strptime(self.pconnections[self.QuickestServerID]["at"][:-9], '%Y-%m-%dT%H:%M:%S.%f')
            self.UlSpeeds.append(byte_delta/(time-ptime).total_seconds())
        except:
            self.UlSpeeds.append(0)

    def request_config(self):
        if self.isOver: sys.exit()
        try:
            c = requests.get('http://localhost:8384/rest/system/config').json()
            self.isSTAvailable = True
            return c
        except:
            #~ raise
            self.isSTAvailable = False
            return False

    def request_connections(self):
        if self.isOver: sys.exit()
        try:
            connections = requests.get('http://localhost:8384/rest/system/connections').json()["connections"]
            self.isSTAvailable = True
            return connections
        except:
            #~ raise
            self.isSTAvailable = False
            return {}

    def request_local_completion(self):
        if self.isOver: sys.exit()
        try:
            c = requests.get('http://localhost:8384/rest/db/status?folder=default')
            self.isSTAvailable = True
            return c.json()["inSyncFiles"], c.json()["globalFiles"],  c.json()["inSyncBytes"], c.json()["globalBytes"]
        except:
            self.isSTAvailable = False
            return self.a,self.b,self.c,self.d

    def request_remote_completion(self,devid):
        if self.isOver: sys.exit()
        try:
            c = requests.get('http://localhost:8384/rest/db/completion?device='+devid+'&folder=default')
            self.isSTAvailable = True
            return c.json()["completion"]   
        except:
            self.isSTAvailable = False
            return 0

    def request_server_completion(self)
        for s in self.connected_server_ids: 
            self.server_completion[s] =  self.request_remote_completion(s)

    def request_events(self,since, Timeout):
        if self.isOver: sys.exit()
        try:
            events = requests.get('http://localhost:8384/rest/events?since='+str(since), timeout=Timeout).json()
            events = c.json()
            self.isSTAvailable = True
            return events
        except requests.exceptions.Timeout
            return []
        except:
            #~ raise
            self.isSTAvailable = False
            time.sleep(2)
            return []

    def update_states()
        if all((not p == 100) for p in self.server_completion.values()): 
            self.isUploading = True
            try:
                self.QuickestServerID =max(self.server_completion.keys(), key = lambda x: self.server_completion[x])
            except: 
                self.QuickestServerID=''
        else:
            self.isUploading = False
            self.QuickestServerID=''
    
        if not self.a == self.b or not self.c == self.d: 
            isDownloading = True
        else: 
            self.isDownloading = False

    def run(self):
        next_event=1
        while not self.isOver:
            
            self.DlCheck()
            self.update_gui()
            self.UlCheck()
            self.update_gui()

            # the above calls should give correct answers as to whether 
            # we are uploading, etc. We use also the event loop, in order to 
            # 1) react to things quicker, 2) to know that something is happening 
            # so that we have to run the calls above (request_events() is blocking)
            
            events = self.request_events(next_event, 2 if self.isDownloading or self.isUploading else 65)
            for v in events:
                #print(v["type"]+str(v["id"]))
                if v["type"] == "LocalIndexUpdated": 
                    self.isUploading = True

                elif v["type"] == "RemoteIndexUpdated":
                    self.isDownloading = True
                elif str(v["type"]) == "FolderSummary": 
                    w = v["data"]["summary"]
                    self.a,self.b,self.c,self.d = w["inSyncFiles"], w["globalFiles"],  w["inSyncBytes"], w["globalBytes"]

                elif v["type"] == "FolderCompletion":
                    if v["data"]["device"] in self.connected_server_ids: 
                        self.server_completion[v["data"]["device"]] = v["data"]["completion"]
                    
            self.update_states()
            self.update_gui() 
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
        #~ print([t.isSTAvailable, len(t.connected_server_ids), t.isDownloading, t.isUploading])
        #~ if t.QuickestServerID: print(str(round((t.d-t.server_completion[t.QuickestServerID]*t.d/100)/1000000,2)))
    
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
                    info_str += "\nDownloading "+str(t.b-t.a)+" file" +('s' if t.b-t.a>1 else '')
                    info_str += ' ('+str(round((t.d-t.c)/1000000,2))+'MB @ '
                    info_str += ('%.0f' % max(0,sum(list(t.DlSpeeds))/5000)) +'KB/s)'
                else:
                    info_str += "\nChecking indices"

            if t.isUploading:
                if t.QuickestServerID:
                    info_str += "\nUploading to "+t.id_dict[t.QuickestServerID]
                    info_str +=' ('+str(round((t.d-t.server_completion[t.QuickestServerID]*t.d/100)/1000000,2))+'MB'
                    try:
                        info_str +=' @ '+ ('%.0f' % max(0,sum(list(t.UlSpeeds))/5000)) +'KB/s)'
                    except:
                        info_str +=')'
                else:
                    info_str += "\nUploading..."

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
        #~ print("update icon animate")
        #~ print ([t.isDownloading, t.isUploading,t.isSTAvailable, len(t.connected_server_ids), self.isAnimated])
        if (t.isDownloading or t.isUploading) and t.isSTAvailable and t.connected_server_ids and self.isAnimated:
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
