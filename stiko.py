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

DEBUG=False

class STDetective(threading.Thread):
    def __init__(self, gui, servers):
        super(STDetective, self).__init__()
        self.gui = gui

        #flag for terminating this thread when icon terminates
        self.isOver = False 

        self.server_names = servers
        self.server_ids = []
        self.connected_server_ids = []
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
        self.pUlCheckTime = self.DlCheckTime
        self.local_index_stamp =  self.DlCheckTime      

        self.UlSpeeds = collections.deque(maxlen=5)
        self.DlSpeeds = collections.deque(maxlen=5)

        self.QuickestServerID=''
        self.config = {}

    def basic_init(self):
        # we add basic_init() (instead of calling everything from init()) 
        # because otherwise if the basic checks below fail gui is unresponsive
        # (because main_loop isn't working yet). This will be ran from self.run() 
   
        self.config = self.request_config()

        # A thread-safe way to demand gui updates. We do it here 
        # because request_config() hopefully changed isSTAvailable to True
        self.update_gui()

        while not self.config:
            time.sleep(3)
            config = self.request_config()
            self.update_gui()
            if self.isOver: sys.exit()

        for a in self.config["devices"]:
            self.id_dict[a["deviceID"]] =  a['name']

        if any([not (a in self.id_dict.values()) for a in self.server_names]):
            print("Some provided server names are wrong.")
            Gtk.main_quit()
            sys.exit()

        if any([not (a in id_dict.keys()) for a in self.server_ids]):
            print("Some provided server ids are wrong.")
            Gtk.main_quit()
            sys.exit()

        if all([not f["id"] == STFolder for f in self.config["folders"]]):
            print("No such folder reported by syncthing")
            Gtk.main_quit()
            sys.exit()

        if not self.server_names and not self.server_ids: 
            self.server_ids = self.id_dict.keys()
        else:  
            self.server_ids = [a for a in self.id_dict.keys() if (self.id_dict[a] in self.server_names or a in self.server_ids)]


    def get_base_state(self):
        self.a,self.b,self.c,self.d = self.request_local_completion()

        self.connections = self.request_connections()
        self.connected_ids = list(self.connections.keys())
        self.connected_server_ids = [s for s in self.server_ids if s in self.connected_ids]
    
        # the following call doesn't really belong here, but 
        # the call afterwards can take long time, so better update gui now
        self.update_gui()

        self.request_server_completion()

        self.update_dl_state()
        self.update_ul_state()

    def update_gui(self):
        GObject.idle_add(lambda :self.gui.update_icon(self)) 
        #while Gtk.events_pending(): Gtk.main_iteration_do(True)
        GObject.idle_add(lambda :self.gui.menu.update_menu(self)) 


    def DlCheck(self):
        if DEBUG: print("DLCheck()")
        if (datetime.datetime.today() -self.pDlCheckTime).total_seconds() <3: return

        self.pa, self.pb,self.pc, self.pd =  self.a,self.b,self.c,self.d
        self.a,self.b,self.c,self.d= self.request_local_completion()
        self.pDlCheckTime = self.DlCheckTime
        self.DlCheckTime = datetime.datetime.today() 
        self.update_dl_state()

        self.DlSpeeds.append((self.c-self.pc)/(self.DlCheckTime-self.pDlCheckTime).total_seconds())


    def UlCheck(self):
        if DEBUG: print("ULCheck()")
        if (datetime.datetime.today() -self.pUlCheckTime).total_seconds() <3: return

        # this is a dirty hack - we give ourselves 7 seconds of hope 
        # that all servers will report their FolderCompletions. Otherwise 
        # the icon will go "OK" and only after FolderCompletions arrive will it go to "Sync" again
        if (datetime.datetime.today() - self.local_index_stamp).total_seconds() <7:return

        self.pconnections = self.connections 
        self.connections = self.request_connections()
        self.connected_ids = list(self.connections.keys())
        self.connected_server_ids = [s for s in self.server_ids if s in self.connected_ids]
    
        self.request_server_completion()

        self.update_ul_state()

        self.pUlCheckTime = self.UlCheckTime
        self.UlCheckTime = datetime.datetime.today() 
    
        if self.QuickestServerID in self.pconnections.keys() and self.QuickestServerID in self.connections.keys():
            byte_delta = self.connections[self.QuickestServerID]["outBytesTotal"] - self.pconnections[self.QuickestServerID]["outBytesTotal"]
            time = datetime.datetime.strptime(self.connections[self.QuickestServerID]["at"][:-9], '%Y-%m-%dT%H:%M:%S.%f')
            ptime = datetime.datetime.strptime(self.pconnections[self.QuickestServerID]["at"][:-9], '%Y-%m-%dT%H:%M:%S.%f')
            self.UlSpeeds.append(byte_delta/(time-ptime).total_seconds())
            #~ print(byte_delta)
            #~ print(self.UlSpeeds)

    def request_config(self):
        if self.isOver: sys.exit()
        try:
            c = requests.get(STUrl+'/rest/system/config').json()
            self.isSTAvailable = True
            return c
        except:
            #~ raise
            self.isSTAvailable = False
            return False

    def request_connections(self):
        if self.isOver: sys.exit()
        try:
            connections = requests.get(STUrl+'/rest/system/connections').json()["connections"]
            self.isSTAvailable = True
            return connections
        except:
            #~ raise
            self.isSTAvailable = False
            return {}

    def request_local_completion(self):
        if self.isOver: sys.exit()
        try:
            c = requests.get(STUrl+'/rest/db/status?folder='+STFolder)
            self.isSTAvailable = True
            return c.json()["inSyncFiles"], c.json()["globalFiles"],  c.json()["inSyncBytes"], c.json()["globalBytes"]
        except:
            #~ raise
            self.isSTAvailable = False
            return self.a,self.b,self.c,self.d

    def request_remote_completion(self,devid):
        if self.isOver: sys.exit()
        try:
            c = requests.get(STUrl+'/rest/db/completion?device='+devid+'&folder='+STFolder)
            self.isSTAvailable = True
            return c.json()["completion"]   
        except:
            self.isSTAvailable = False
            return 0

    def request_server_completion(self):
        for s in self.connected_server_ids: 
            self.server_completion[s] =  self.request_remote_completion(s)

    def request_events(self,since, Timeout):
        if DEBUG: print("request_events() "+str(Timeout))
        if self.isOver: sys.exit()
        try:
            events = requests.get(STUrl+'/rest/events?since='+str(since), timeout=Timeout).json()
            self.isSTAvailable = True
            return events
        except:
            # there seems to be a bug in requests. As a workaround 
            # we will just ignore error when Timeout is 2. If this is 
            # genuine then it will be caught soon (in request_connections for example)
            if Timeout >3:
                self.isSTAvailable = False
            return []

    def update_ul_state(self):
        if all((not p == 100) for p in self.server_completion.values()): 
            self.isUploading = True
            try:
                self.QuickestServerID =max(self.server_completion.keys(), key = lambda x: self.server_completion[x])
            except: 
                self.QuickestServerID=''
        else:
            self.isUploading = False
            self.QuickestServerID=''
    
    def update_dl_state(self):
        if not self.a == self.b or not self.c == self.d: 
            self.isDownloading = True
        else: 
            self.isDownloading = False

    def run(self):
        if DEBUG: print("run()")
        
        self.basic_init()
        next_event=1

        self.get_base_state()
        self.update_gui()

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
                if DEBUG: print(v["type"]+str(v["id"]))
                
                # The "stamp" is heuristic, we are giving ourselves better chances 
                # to report events picked-up in the event loop
                if v["type"] == "StateChanged" and v["data"]["to"] == "scanning": 
                    self.isUploading = True
                    self.local_index_stamp = datetime.datetime.today()
                if v["type"] == "LocalIndexUpdated": 
                    self.isUploading = True
                    self.local_index_stamp = datetime.datetime.today()
            
                elif v["type"] == "RemoteIndexUpdated":
                    self.isDownloading = True

                elif str(v["type"]) == "FolderSummary": 
                    w = v["data"]["summary"]
                    self.pa, self.pb,self.pc, self.pd =  self.a,self.b,self.c,self.d
                    self.a,self.b,self.c,self.d = w["inSyncFiles"], w["globalFiles"],  w["inSyncBytes"], w["globalBytes"]
                    self.pDlCheckTime = self.DlCheckTime
                    self.DlCheckTime = datetime.datetime.today() 
                    self.DlSpeeds.append((self.c-self.pc)/(self.DlCheckTime-self.pDlCheckTime).total_seconds())
                    self.update_dl_state()

                elif v["type"] == "FolderCompletion":
                    if v["data"]["device"] in self.connected_server_ids: 
                        self.server_completion[v["data"]["device"]] = v["data"]["completion"]
                    self.update_ul_state()

            self.update_gui() 
            if events: next_event = events[len(events)-1]["id"]

        sys.exit()


class StikoMenu(Gtk.Menu):
    def __init__ (self):
        super(StikoMenu,self).__init__()
        self.is_visible = False

        self.close_item = Gtk.MenuItem("Close App")
        self.append(self.close_item)
        self.close_item.connect_object("activate", lambda x : self.on_left_click(self), "Close App")
        self.close_item.show()

        self.connect("deactivate", self.deactivate_callback)     

    def deactivate_callback(self, menu):
        self.is_visible = False 

    def update_menu(self, t):
        self.updater(t)
        if self.is_visible: GObject.timeout_add(1000, self.updater,t)

    def updater(self,t):
        info_str = ''
        info_str += "\nDownloading "+str(t.b-t.a)+" file" +('s' if t.b-t.a>1 else '')
        info_str += ' ('+str(round((t.d-t.c)/1000000,2))+'MB @ '
        info_str += ('%.0f' % max(0,sum(list(t.DlSpeeds))/5000)) +'KB/s)'
        self.close_item.set_label(info_str)

        return self.is_visible


class StikoGui(Gtk.StatusIcon):
    def __init__ (self, iconDir):
        super(StikoGui, self).__init__()

        try:
            self.px_good = GdkPixbuf.Pixbuf.new_from_file(os.path.join(iconDir,'stiko-ok.png'))
            self.px_noST = GdkPixbuf.Pixbuf.new_from_file(os.path.join(iconDir,'stiko-notok.png'))
            self.px_noServer = GdkPixbuf.Pixbuf.new_from_file(os.path.join(iconDir,'stiko-inactive.png'))
            self.px_sync = [GdkPixbuf.Pixbuf.new_from_file(os.path.join(iconDir,'stiko-sync1.png')), 
                        GdkPixbuf.Pixbuf.new_from_file(os.path.join(iconDir,'stiko-sync0.png'))]
        except:
            #~ raise
            print("I coudn't open icon files.")
            sys.exit()  

        self.set_from_pixbuf(self.px_noServer)
        self.connect('activate', self.on_left_click)
        self.connect('popup-menu', self.on_right_click)
        
        self.animation_counter = 1
        self.isAnimated = False   #for controlling animation only

        self.menu = StikoMenu()

    def on_left_click(self,icon):
        icon.set_visible(False)
        Gtk.main_quit()

    def on_right_click(self, data, event_button, event_time):
        self.menu.popup(None,None,None,None,event_button,event_time)
        self.menu.is_visible = True
   
    def update_icon(self,t):
        if DEBUG: print([t.isSTAvailable, len(t.connected_server_ids), t.isDownloading, t.isUploading])
   
        info_str = ''
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
                    info_str += ' ('+str(round((t.d-t.server_completion[t.QuickestServerID]*t.d/100)/1000000,2))+'MB'
                    try:
                        info_str += ' @ '+ ('%.0f' % max(0,sum(list(t.UlSpeeds))/5000)) +'KB/s)'
                    except:
                        info_str += ')'
                else:
                    info_str += "\nUploading..."

            if not self.isAnimated: 
                self.isAnimated = True
                self.set_from_pixbuf(self.px_sync[0])
                self.animation_counter = 1
                GObject.timeout_add(600, self.update_icon_animate,t)
        else:
            info_str += str(len(t.connected_server_ids))+" Server" +('s' if len(t.connected_server_ids) >1 else '')+"\nUp to Date"            
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



parser = argparse.ArgumentParser(description = 'This is stiko, a systray icon for syncthing.',epilog='', usage='stiko.py [options]')
parser.add_argument('--servers', nargs = '+', default ='',help = 'List of names of devices treated as servers, space separated. If empty then all connected devices will be treated as servers.',metavar='')
parser.add_argument('--icons',  default ='', help = 'Path to the directory with icons. Defaults to this script\'s directory ('+os.path.dirname(os.path.abspath(__file__))+')', action="store", metavar='')
parser.add_argument('--sturl',  default ='', help = 'URL of a syncthing instance. Defaults to  "http://localhost:8384"', action="store", metavar='')
parser.add_argument('--stfolder',  default ='', help = 'Name of the syncthing folder to monitor. Defaults to "default"', action="store", metavar='')

args = parser.parse_args(sys.argv[1:])
iconDir = os.path.dirname(__file__) if not args.icons else args.icons
STUrl = "http://localhost:8384" if not args.sturl else args.sturl
STFolder = 'default' if not args.stfolder else args.stfolder

GObject.threads_init()

gui = StikoGui(iconDir)

t = STDetective(gui,args.servers)
t.start()

Gtk.main()
t.isOver = True
