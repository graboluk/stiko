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
import webbrowser

# pango markup
black = '<span foreground="black" font_family="monospace" size="large">'
green = '<span foreground="green" font_family="monospace" size="large">'
gray = '<span foreground="gray" font_family="monospace" size="large">'
blue = '<span foreground="blue" font_family="monospace" size="large">'
red =  '<span foreground="red" font_family="monospace" size="large">'
span  = '</span>'
sgray = '<span foreground="gray" font_family="monospace" size="small">'



class STDetective(threading.Thread):
    def __init__(self, gui, servers):
        super(STDetective, self).__init__()
        self.gui = gui

        #flag for terminating this thread when icon terminates
        self.isOver = False 

        self.server_names = servers
        self.server_ids = []
        self.connected_ids = []
        self.connected_server_ids = []

        # server_completion really lists all peers. 
        # We only get cached values from st so it's 
        # not expensive to query for all of them
        self.server_completion = {} 


        # p as a prefix to a variable name means 
        # that this is the previously checked value
        self.connections = {}
        self.pconnections = {}

        #dictionary for translating device ids to syncthing names
        self.id_dict = {}

        # current and previous inSyncFiles, globalFiles, inSyncBytes, globalBytes
        self.a,self.b,self.c,self.d, self.pa,self.pb,self.pc,self.pd = [0,0,0,0,0,0,0,0]

        self.isDownloading = False
        self.isUploading = False
        self.isSTAvailable = False

        self.DlCheckTime = datetime.datetime.today()
        self.pDlCheckTime = self.DlCheckTime
        self.local_index_stamp =  self.DlCheckTime      

        self.UlSpeeds = collections.deque(maxlen=2)
        self.DlSpeeds = collections.deque(maxlen=2)

        self.QuickestServerID=''
        self.config = {}

        self.peer_ulspeeds = {}
        self.peer_dlspeeds = {}
        self.peer_completion = {}

    def basic_init(self):
        # we add basic_init() (instead of calling everything from __init__()) 
        # because otherwise if the basic checks below fail gui is unresponsive
        # (because main_loop wouldn't be working yet). This will be ran from self.run() 
   
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

    def update_gui(self):
        GObject.idle_add(lambda :self.gui.update_icon(self)) 
        GObject.idle_add(lambda :self.gui.menu.update_menu(self)) 
        GObject.idle_add(lambda :self.gui.peer_menu.update_menu(self)) 

    def DlCheck(self):
        #~ print("DLCheck()")
        #if (datetime.datetime.today() -self.pDlCheckTime).total_seconds() <3: return

        self.pa, self.pb,self.pc, self.pd =  self.a,self.b,self.c,self.d
        self.a,self.b,self.c,self.d= self.request_local_completion()
        self.pDlCheckTime = self.DlCheckTime
        self.DlCheckTime = datetime.datetime.today() 
        self.update_dl_state()
        self.DlSpeeds.append((self.c-self.pc)/(self.DlCheckTime-self.pDlCheckTime).total_seconds())

    def UlCheck(self):
        #~ print("ULCheck()")

        # this is a dirty hack - we give ourselves 7 seconds of hope 
        # that all servers will report their FolderCompletions less than 100. Otherwise 
        # the icon will go "OK" and only after FolderCompletions arrive will it go to "Sync" again
        if (datetime.datetime.today() - self.local_index_stamp).total_seconds() >7:
            self.update_ul_state()

    
    def update_connection_data(self):
        self.pconnections = self.connections 
        self.connections = self.request_connections()

        self.connected_ids = list(self.connections.keys())
        self.connected_server_ids = [s for s in self.server_ids if s in self.connected_ids]

        self.request_server_completion()

        for a in  self.pconnections.keys():
            if a in self.connections.keys():
                if not a in self.peer_ulspeeds.keys(): self.peer_ulspeeds[a] = collections.deque(maxlen=2)
                if not a in self.peer_dlspeeds.keys(): self.peer_dlspeeds[a] = collections.deque(maxlen=2)
                byte_delta = self.connections[a]["outBytesTotal"] - self.pconnections[a]["outBytesTotal"]
                time = datetime.datetime.strptime(self.connections[a]["at"][:19], '%Y-%m-%dT%H:%M:%S')
                ptime = datetime.datetime.strptime(self.pconnections[a]["at"][:19], '%Y-%m-%dT%H:%M:%S')
                self.peer_ulspeeds[a].append(byte_delta/(time-ptime).total_seconds())
                byte_delta = self.connections[a]["inBytesTotal"] - self.pconnections[a]["inBytesTotal"]
                self.peer_dlspeeds[a].append(byte_delta/(time-ptime).total_seconds())

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
        for s in self.connected_ids: 
            self.server_completion[s] =  self.request_remote_completion(s)

    def request_events(self,since, Timeout):
        #~ print("request_events() "+str(Timeout))
        if self.isOver: sys.exit()
        try:
            events = requests.get(STUrl+'/rest/events?since='+str(since), timeout=Timeout).json()
            self.isSTAvailable = True
            return events
        except:
            # there seems to be a bug in requests. As a workaround 
            # we will just ignore error when Timeout is 2. If syncthing really is not
            # accessible then it will be caught soon (in request_connections for example)
            if Timeout >3:
                self.isSTAvailable = False
            return []

    def update_ul_state(self):

        # this seems to be the only place where server_completion 
        # should really mean that we look only at the servers,
        # so s below is server_completion restricted to servers
        s = {}
        for a in self.server_completion.keys(): 
            if a in self.connected_server_ids: s[a] = self.server_completion[a] 

        if all((not p == 100) for p in s.values()): 
            self.isUploading = True
            try:
                self.QuickestServerID =max(s.keys(), key = lambda x: s[x])
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
        #~ print("run()")
        
        self.basic_init()
        next_event=1

        self.a,self.b,self.c,self.d = self.request_local_completion()
        self.update_gui()
    
        while not self.isOver:
            self.update_connection_data()

            self.DlCheck()
            self.UlCheck()
            self.update_gui()

            # the above calls should give correct answers as to whether 
            # we are uploading, etc. We use also the event loop, in order to 
            # 1) react to things quicker, 2) to know that something is happening 
            # so that we have to run the calls above (request_events() is blocking)

            be_quick = self.isDownloading or self.isUploading or any([ not t.server_completion[a] ==100 for a in self.connected_ids])
            events = self.request_events(next_event, 2 if be_quick else 65)
            for v in events:
                #~ print(v["type"]+str(v["id"]))
                
                # The "stamp" is heuristic, we are giving ourselves better chances 
                # to report events picked-up in the event loop
                #~ if v["type"] == "StateChanged" and v["data"]["to"] == "scanning": 
                    #~ self.isUploading = True
                    #~ self.local_index_stamp = datetime.datetime.today()
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


class PeerMenu(Gtk.Menu):
    def __init__ (self,gui):
        super(PeerMenu,self).__init__()
        self.set_reserve_toggle_size(False)

        self.gui = gui
        self.is_visible = False
        self.peer_info = Gtk.MenuItem('')
        info_str = gray+ " "*25+span
        self.peer_info.get_children()[0].set_markup(info_str)
        self.peer_info.set_sensitive(False)

        self.append(self.peer_info)
        self.peer_info.show()

    def update_menu(self, t): 
        all_str = gray + 'name          status        UL / DL'+span+sgray+' (KB/s)' +span
        info_str = ''
        for a in t.connected_ids: 
            info_str = '\n'
            info_str += black + t.id_dict[a][:10] + span
            try:
                if t.server_completion[a] == 100: 
                    miss ='OK'
                    info_str += green + ' '*(4+ 10-len(t.id_dict[a]))+ miss + span 
                else:
                    miss = str(round((t.d-t.server_completion[a]*t.d/100)/1000000,2))+'MB'
                    info_str += blue +' '*(4+ 10-len(t.id_dict[a])) +miss+span
                ustr = ('%.0f' % max(0,sum(list(t.peer_ulspeeds[a]))/5000))
                info_str += black +' '*(10-len(miss))+ ' '*(6-len(ustr))+ ustr +  ' / ' 
                info_str += ('%.0f' % max(0,sum(list(t.peer_dlspeeds[a]))/5000))+span
            except: pass
            all_str +=info_str

        self.peer_info.get_children()[0].set_markup(all_str)

class StikoMenu(Gtk.Menu):
    def __init__ (self,gui):
        super(StikoMenu,self).__init__()
        self.gui = gui
        self.is_visible = False

        self.server_item = Gtk.MenuItem('\n\n\n\n\n\n\n\n\n\n\n')
        self.sep = Gtk.SeparatorMenuItem()
        self.progress_item = Gtk.MenuItem('')
        self.sep2 = Gtk.SeparatorMenuItem()
        self.all_peers_item = Gtk.MenuItem('')
        self.close_item = Gtk.MenuItem('')

        self.append(self.server_item)
        self.append(self.sep)
        self.append(self.progress_item)
        self.append(self.sep2)
        self.append(self.all_peers_item)
        self.append(self.close_item)

        self.all_peers_item.set_submenu(gui.peer_menu)
        self.all_peers_item.connect_object("select", self.select_peer_menu_callback,None)
        self.all_peers_item.connect_object("deselect", self.deselect_peer_menu_callback,None)

        self.close_item.connect_object("activate", lambda x: Gtk.main_quit(),None)

        self.server_item.show()
        self.sep.show()
        self.progress_item.show()
        self.sep2.show()
        self.all_peers_item.show()
        self.close_item.show()
    
        self.connect("deactivate", self.deactivate_callback)     
        self.set_reserve_toggle_size(False)

        self.close_item.get_children()[0].set_markup(black+"Close stiko"+span)
        self.all_peers_item.get_children()[0].set_markup(black+"Peer info"+span)

    def select_peer_menu_callback(self,x):
        self.gui.peer_menu.is_visible = True 

    def deselect_peer_menu_callback(self,x):
        self.gui.peer_menu.is_visible = False 

    def deactivate_callback(self, menu):
        self.is_visible = False 

    def update_menu(self, t):
        self.updater(t)
        #if self.is_visible: GObject.timeout_add(1000, self.updater,t)

    def updater(self,t):
        if not t.isSTAvailable:
            info_str = red+"No contact with syncthing"+span

        elif not t.connected_server_ids:
            info_str = gray+"No servers"+span

        else:
            info_str =gray+  "Connected Servers ("+str(len(t.connected_server_ids))+'/'+str(len(t.server_ids))+')'+span
            for a in t.connected_server_ids:
                info_str += black+  '\n '+t.id_dict[a][:10] +span
                if a in t.server_completion.keys() and t.server_completion[a] == 100: 
                    info_str += green + ' '*(6+ 10-len(t.id_dict[a]))+ 'OK'+ span 
                elif a in t.server_completion.keys():
                    info_str += blue +' '*(4+ 10-len(t.id_dict[a])) +str(round((t.d-t.server_completion[a]*t.d/100)/1000000,2))+'MB'+span
                else:
                    info_str += blue +' '*(4+ 10-len(t.id_dict[a])) +"..."+span
        

        # Apparently this is te only way of accessing  the label of a GTk.MenuItem
        self.server_item.get_children()[0].set_markup(info_str)
        
        self.server_item.set_sensitive(False)

        info_str =gray+ "Local Status"+span
        if t.isDownloading:
            if not t.a==t.b:
                info_str += blue  +' '*3+ str(round((t.d-t.c)/1000000,2)) + 'MB'+span
                info_str +=  black+ '\n('+str(t.b-t.a)+" file" +('s' if t.b-t.a>1 else '')+span
                #info_str += black + str(round((t.d-t.c)/1000000,2))+'MB @ '+span
                info_str +=black + ' @ '+ ('%.0f' % max(0,sum(list(t.DlSpeeds))/5000)) +'KB/s)'+span
            else:
                info_str += black +"\nChecking indices..."+span

        if t.isUploading:
            if not t.isDownloading: info_str +=black+'\n'+span
            if t.QuickestServerID:
                info_str += blue + "\nUL to "+t.id_dict[t.QuickestServerID] +span 
                info_str += black +'\n('+str(round((t.d-t.server_completion[t.QuickestServerID]*t.d/100)/1000000,2))+'MB'
                try:
                    info_str += ' @ '+ ('%.0f' % max(0,sum(list(t.peer_ulspeeds[t.QuickestServerID]))/5000)) +'KB/s)' +span
                except:
                    info_str += ')'+span
            else:
                info_str += blue+"\nUploading... \n "+span
    
        if t.isSTAvailable and len(t.connected_server_ids) and not t.isDownloading and not t.isUploading:
            info_str += green+' '*5+"OK\n\n\n"+span
        info_str += '\n'*(3-info_str.count('\n'))

        self.progress_item.get_children()[0].set_markup(info_str)
        self.progress_item.set_sensitive(False)



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

        self.peer_menu = PeerMenu(self)
        self.menu = StikoMenu(self)

    def on_left_click(self,icon):
        #icon.set_visible(False)
        webbrowser.open_new_tab(STUrl)

    def on_right_click(self, data, event_button, event_time):
        self.menu.popup(None,None,None,None,event_button,event_time)
        self.menu.is_visible = True
   
    def update_icon(self,t):
        #print([t.isSTAvailable, len(t.connected_server_ids), t.isDownloading, t.isUploading])
   
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
                        info_str += ' @ '+ ('%.0f' % max(0,sum(list(t.peer_ulspeeds[t.QuickestServerID]))/5000)) +'KB/s)'
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
            self.animation_counter = (self.animation_counter +  1) % 2
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


# we make t a daemon because http requests are 
# blocking, so otherwise we hae to wait for 
# termination up to 60s (or whatever the syncthing 
# ping interval is)
t.daemon = True

t.start()

Gtk.main()
t.isOver = True
