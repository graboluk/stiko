servernames=a,b,c

set isDownloading, isUploading, isSTAvailable isServerPresent to false

loop with breaks of 5s to get
    foldercompletion, 
    known hosts with keys, 
    connected-hosts
on success set isAnsweringST to true.


loop with breaks of 5s to get
    foldersummary for names in servernames \cap connected-hosts
    if at least one answers then set isServerPresent to True

Based on the foldersummaries and foldercompletions set isDownloading and isUploading

main loop
    get new events
    go through events
        if IndexUpdated set isUploading or isDownloading true
        if foldersummaries of foldercopletions set isDownloading/ isUploading to true or false
        if connect/disconnect -> update list of servers.

    if isUploading of isDownloading for some time, say 3min, then query if any servers are present.

-jesli nie moge sie polaczyc z syncthing to czekam dalej bo moze dopiero wystartowal?
-poza tym mozemy ominac RemoteIndexUpdated i LocalIndexUpdated, wiec na poczatek robimy query "FolderCompletion" oraz "FolderSummary" wszystkich serwerow (do momentu gdy zobaczymy jeden ktory ma FolderSummary "100".

-jesli widze "LocalIndexUpdated" po lokalnej zmianie, to mam pewnosc, ze ktos ma moja lokalna zmiane dopiero gdy widze "FolderCompletion" z completion=100

-jesli widze "RemoteIndexUpdated" to moge zaczac pytac o FolderSummary dopoki pokazuje, ze cos trzeba sciagnac, to ikonka pokazuje, ze konieczny download.

-co jakis czas trzeba patrzyc czy jestesmy z kimkolwiek polaczeni - jesli nie to rpzestajemy pokazywac cokolwiek.
    gdy nic sie nie dzieje to nie patrzymy
    gdy jestesmy w trakcie to patrzymy co powiedzmy 4s.

-jesli dostaniemy FolderSummary ktory pokazuje ze cos trzeba sciagnac to przechodzimy tak czy inaczej (niezaleznie czy widzialem RemoteIndexUpdated) w tryb "Downloading"

issues (why would it be better if syncthing did it): 
-this depends on seeing all "LocalIndexUdated". 
-at the beginning we might miss something
-if webapp is part of st, why icon can't be - the same problems need to be solved.
-if st config changed ping time then this might not work


-would be nice to have st feature to allow stopping upload to servers if at least one server has it. Or simply a rule as to whom to speak (like: if platon is present don't talk to archimedes)
