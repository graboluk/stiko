# stiko
A systray icon for syncthing. Allows to designate some devices as servers. Great for dropbox aficionados which need just one look to know if they can turn off computer/start working.

#### Installation and usage
stiko is written in python3 using  gtk3 so it should run on a wide variety of platforms. I personally run it on debian testing. To install copy all the files to your folder of preference. If you wish you can copy the icons to a separate folder.

To run it, execute `python stiko.py` or make sure that the file stiko.py is executable and excute `stiko.py`

Currently stiko.py assumes that the URL of syncthing is locahost:8384. The command line options are: `--icons ICON_DIR` (defaults to the same directory in which the file stiko.py is) and `--servers S`, where S is a space separated list of names of devices which should be treated as servers (defaults to all connected devices).

Once stiko is running you can left-click it to quit. If you hover over the icon, useful info will appear - number of connected servers, current sate (Up to Date, Uploading, Downloading Checking Indices), as well as download/upload progress.

#### Meaning of icons.
1. If local files are Up to Date, and **at least one server** is Up to Date, then the icon is blue.
2. If no servers are connected then the icon is grey.
3. If syncthing instance can't be contacted then the icon is red.
4. the icon wiggles if either local files are not up to date (and hence data is being downloaded) or none of the servers are up to data (and hence data is being uplaoded). Hover the cursr over the icon to find out the details.

#### License
Licensed under GPL3. But in case you would like to contribute I require all contribution to be dual licensed MPL3/GPL3, so that it's easy to change the license to another free software license if ever need be.
