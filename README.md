### **stiko** - systray icon for [syncthing](https://github.com/syncthing/syncthing) with server support

---

##### Installation and usage
stiko is written in python 3 using gtk3 and tested on openbox with tint2 panel from debian jessie. It should run on a variety of other platforms.  To install copy all the files to your folder of preference. In debian you will need the  packages `python3`, `python3-requests`, `python3-gi` and `gir1.2-gtk-3.0`.

To run it, execute `python3 stiko.py` (command line options are described below). An icon should appear in your systray. If you hover over it, useful info will appear in a tooltip - number of connected servers, current state (Up to Date, Uploading, Downloading, No Servers...), as well as download/upload progress:

![Example screenshot](/../screenshots/screenshots/1.png?raw=true)
![Example screenshot](/../screenshots/screenshots/2.png?raw=true)
![Example screenshot](/../screenshots/screenshots/4.png?raw=true)
![Example screenshot](/../screenshots/screenshots/6.png?raw=true)

Even more info is accessible via right-click menu:

![Example screenshot](/../screenshots/screenshots/menu1.png?raw=true)
![Example screenshot](/../screenshots/screenshots/menu2.png?raw=true)

Left-clicking will open a new brwoser tab with syncthing web gui.

##### Command line options

|||
|---|---|
| `--servers server1 server2 ...`| Space separated list of devices which should be treated as servers (defauts to all connected devices). Stiko will report "Up to Date" only if the local files are up to date and at least one of the servers is up to date |
| `--icons ICON_FOLDER`| Folder containing the icons. Defaults to the directory containing `stiko.py`|
| `--sturl SYNCTHING_URL`| Complete URL  of a syncthing instance. Defaults to `http://localhost:8384`|
| `--stfolder FOLDER_NAME`| Name of the sycthing folder to monitor. Defaults to `default`. Currently stiko works correctly only if one folder is present|


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
