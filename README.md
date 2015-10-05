### **stiko** - a systray icon for [syncthing](https://github.com/syncthing/syncthing) with server support

---

##### Installation and usage
stiko is written in python 3 using  gtk3 so it should run on a wide variety of platforms. I personally run it on debian testing (openbox with tint2 panel). To install copy all the files to your folder of preference. If you wish you can copy the icons to a separate folder.

To run it, execute `python3 stiko.py` or make sure that the file stiko.py is executable and excute `stiko.py`

Currently stiko.py assumes that the URL of syncthing is localhost:8384. The command line options are: `--icons ICON_DIR` (defaults to the same directory in which the file stiko.py is) and `--servers S`, where S is a space separated list of names of devices which should be treated as servers (defaults to all connected devices).

Once stiko is running you can left-click it to quit. If you hover over the icon, useful info will appear - number of connected servers, current state (Up to Date, Uploading, Downloading, No Servers...), as well as download/upload progress:

![Example screenshot](/../screenshots/screenshots/1.png?raw=true)
![Example screenshot](/../screenshots/screenshots/2.png?raw=true)
![Example screenshot](/../screenshots/screenshots/4.png?raw=true)
![Example screenshot](/../screenshots/screenshots/6.png?raw=true)


##### Example
Suppose you have a cheap VPS (syncthing device name CHEAPO). The price is great but uptime is at 95%. But you also have a computer at work (syncthing device name OFFICEMATE) which you keep on almost all the time. Together their uptime is pretty much 100%. It would be nice to use both of them in combination as a server to/from which you syncronize all your other devices, for example your laptop. 

Stiko allows you to use syncthing this way. Just setup syncthing on all your devices (including CHEAPO and OFFICEMATE) in the standard way. Now on your laptop run `stiko.py --servers CHEAPO OFFICEMATE`. Stiko will inform you if at least one of the devices CHEAPO and OFFICEMATE are in sync with your laptop.

##### Meaning of icons
1. If local files are Up to Date, and **at least one server** is Up to Date, then the icon is blue.
2. If no servers are connected then the icon is grey.
3. If syncthing instance can't be contacted then the icon is red.
4. the icon wiggles if either local files are not up to date  or none of the servers are up to date. Hover the cursor over the icon to find out the details.

##### License
Licensed under GPL3. But in case you would like to contribute I require all contribution to be dual licensed MPL2/GPL3, so that it's easy to change the license to another free software license if ever need be.
