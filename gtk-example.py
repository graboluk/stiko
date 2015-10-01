#!/usr/bin/python3 
import threading
import time
from gi.repository import Gtk as gtk, GObject as gobject
#import gtk

gobject.threads_init()

class MyThread(threading.Thread):
    def __init__(self, label):
        super(MyThread, self).__init__()
        self.label = label
        self.quit = False

    def update_label(self, counter):
        self.label.set_text("Counter: %i" % counter)
        return False

    def run(self):
        counter = 0
        while not self.quit:
            counter += 1
            gobject.idle_add(self.update_label, counter)
            time.sleep(0.1)

w = gtk.Window()
l = gtk.Label()
w.add(l)
w.show_all()
w.connect("destroy", lambda _: gtk.main_quit())
t = MyThread(l)
t.start()

gtk.main()
t.quit = True
