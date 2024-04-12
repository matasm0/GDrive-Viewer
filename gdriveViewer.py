from gAPIbackend import AUTHENTICATE as auth
from googleapiclient.http import MediaFileUpload

import os, shutil
import re
import hashlib
from datetime import datetime, timedelta
from math import floor

'''

 A gdrive viewer app! The core of my extensive botnet that will forever
 control my life once I figure out how to code in sentience.

'''


# I LOVE GLOBAL VARIABLES!

# TEST VARIABLES #

debug = 1
armed = 0   
filePageSize = 1000
folderPageSize = 100

##################

driveFilePath = ["/home", "user", "gdrive"]
# Add an update directory function that will go through all files and folders and change
# the directory (self.directory[0]) to the new directory

DRIVE = None

class GDrive:
    root = None

gDrive = GDrive()

# Theres probs more, add as I find.
mime_types = {
    "xls":'application/vnd.ms-excel',
    "xlsx":'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    "xml": 'text/xml',
    "ods": 'application/vnd.oasis.opendocument.spreadsheet',
    "csv": 'text/plain',
    "tmpl": 'text/plain',
    "pdf": 'application/pdf',
    "php": 'application/x-httpd-php',
    "jpg": 'image/jpeg',
    "png": 'image/png',
    "gif": 'image/gif',
    "bmp": 'image/bmp',
    "txt": 'text/plain',
    "doc": 'application/msword',
    "js": 'text/js',
    "swf": 'application/x-shockwave-flash',
    "mp3": 'audio/mpeg',
    "zip": 'application/zip',
    "rar": 'application/rar',
    "tar": 'application/tar',
    "arj": 'application/arj',
    "cab": 'application/cab',
    "html": 'text/html',
    "htm": 'text/html',
    "default": 'application/octet-stream',
    "folder": 'application/vnd.google-apps.folder',
    "webm": "video/webm",
    "mp4": "video/mp4",
}

class Folder:
    def __init__(self, meta):
        self.metadata = {
            'name'     : "",
            'id'       : "",
            'mimeType' : 'application/vnd.google-apps.folder',
            'parents'  : [],
        }
        # List of subfolders
        self.children = []
        # List of files
        self.contents = []
        self.directory = [x for x in driveFilePath]
        for x in self.metadata:
            if x in meta:
                self.metadata[x] = meta[x]

        self.orig_name = self.metadata['name']

        if len(self.orig_name) >= 100:
            self.metadata["name"] = self.orig_name[:101]

    def toString(self, indent = 0):
        toReturn = ""
        for x, y in self.metadata.items():
            if not y: continue
            if type(y) == list:
                toReturn += " " * indent + x + " : " + "[" +  ", ".join(y) + "]"
            else: toReturn += " " * indent + x + " : " + y
            toReturn += "\n"

        return toReturn

    def addSelfToParent(self):
        if not self.metadata['parents']: return
        parent = foldersMap[self.metadata['parents'][0]]
        if self.metadata['id'] not in parent.children:
            parent.children.append(self.metadata['id'])

    def getMetadata(self):
        return {
            'name' : self.metadata['name'],
            'parents' : self.metadata['parents'],
            'mimeType' : self.metadata['mimeType'],
        }
            

foldersMap = {}
localFoldersMap = {}

class File:
    def __init__(self, meta):
        self.metadata = {
            'name'     : "",
            'id'       : "",
            'mimeType' : 'application/octet-stream',
            'parents'  : [],
            'md5Checksum' : "",
            'modifiedTime' : "",
        }
        self.directory = [x for x in driveFilePath]
        for x in self.metadata:
            if x in meta:
                self.metadata[x] = meta[x]

        self.orig_name = self.metadata['name']

        if len(self.orig_name) >= 100:
            ext = None
            try: ext = self.orig_name.rindex(".")
            except:
                print ("Can't find file extension for file %s", self.orig_name)
                self.metadata['name'] = self.orig_name[:100]
            else:
                self.metadata['name'] = self.orig_name[:100 - (len(self.orig_name) - ext) - 2] + ".." + self.orig_name[ext:]


    def toString(self, indent = 0):
        toReturn = ""
        for x, y in self.metadata.items():
            if not y: continue
            if type(y) == list:
                toReturn += " " * indent + x + " : " + "[" + ", ".join(y) + "]"
            else: 
                toReturn += " " * indent + x + " : " + y
            toReturn += "\n"

        return toReturn

    def addSelfToParent(self):
        if not self.metadata['parents']: return
        parent = foldersMap[self.metadata['parents'][0]]
        if self.metadata['id'] not in parent.contents:
            parent.contents.append(self.metadata['id'])

    def getMetadata(self):
        return {
            'name' : self.metadata['name'],
            'parents' : self.metadata['parents'],
            'mimeType' : self.metadata['mimeType']
        }


filesMap = {}
localFilesMap = {}

def getRoot():
    test = DRIVE.files().get(fileId="root").execute()
    gDrive.root = test['id']

def getFolders():
    if debug: print("Getting folders")
    pToken = ""
    files = []
    while 1:
        temp = DRIVE.files().list(
            q="mimeType='application/vnd.google-apps.folder' and 'me' in owners and trashed=false", 
            fields='files(name, id, mimeType, parents), nextPageToken', 
            pageSize=folderPageSize, 
            pageToken=pToken,
            ).execute()
        files += [x for x in temp["files"]]
        if "nextPageToken" not in temp: break
        if debug: print("Got %s folders" %len(files))
        pToken = temp["nextPageToken"]
    if debug: print("Finished getting %s folders" %len(files))
    return files

def getFiles():
    if debug: print("Getting files")
    pToken = ""
    files = []
    
    while 1:
        temp = DRIVE.files().list(
            q="not mimeType contains 'application/vnd.google-apps' and 'me' in owners and trashed=false", 
            fields='files(id, name, mimeType, parents, md5Checksum, modifiedTime), nextPageToken', 
            pageSize=filePageSize, 
            pageToken=pToken,
            ).execute()
        files += [x for x in temp['files']] 
        if "nextPageToken" not in temp: break
        if debug: print("Got %s files" %len(files))
        pToken = temp["nextPageToken"]

    if debug: print("Finished getting %s files" %len(files))
    return files

def orderFolders(_foldersMap = foldersMap):
    if debug: print("Ordering folders")

    # Some folders will not have correct parents or may otherwise be invalid. Keep track of them and remove them.
    toRemove = []

    for x in _foldersMap:
        for y in _foldersMap[x].metadata['parents']:
            try: _foldersMap[y].children.append(x) 
            except Exception as e:
                print(_foldersMap[x].metadata['name'], y)
                toRemove.append(x)
                _foldersMap[x] = 'x'
                # _foldersMap.pop(x)
                continue
        if _foldersMap[x] == 'x': continue
        dir = [_foldersMap[x].metadata['name']]
        currFolderID = _foldersMap[x].metadata['id']
        while currFolderID != gDrive.root: # This is probably a dangerous check that can break under certain circumstances if we reach a dead end somehow
            if not len(_foldersMap[currFolderID].metadata['parents']): break
            currFolderID = _foldersMap[currFolderID].metadata['parents'][0]
            dir.append(_foldersMap[currFolderID].metadata['name'])
        _foldersMap[x].directory += dir[::-1]


    if debug: print("Removing %s invalid folders" %len(toRemove))
    for x in toRemove:
        _foldersMap.pop(x)

    if debug: print("Finished ordering folders")
        


def addFilesToFolders(_filesMap = filesMap, _foldersMap = foldersMap, _fileList = []):
    if debug: print("Adding files to folders")
    if not len(_filesMap): _fileList = getFiles() if not len(_fileList) else _fileList
    if debug: print("Map files to parent folders and populate directory")

    toRemove = []
    for x in _fileList:
        _filesMap[x['id']] = File(x)
        directoryToAdd = []
        curr = None
        if _filesMap[x['id']].metadata['parents']:
            try: _foldersMap[x['parents'][0]].contents.append(x['id'])
            except:
                print(x['name'], x['parents'][0])
                toRemove.append(x['id'])
                _filesMap[x['id']] = 'x'
                continue
            curr = _foldersMap[x['parents'][0]]
            directoryToAdd.append(_filesMap[x['id']].metadata['name']) # Name gets shortened if it is too long
            directoryToAdd.append(curr.metadata['name'])
            while curr:
                if curr.metadata['parents']:
                    curr = _foldersMap[curr.metadata['parents'][0]]
                    directoryToAdd.append(curr.metadata['name'])
                else: break
            _filesMap[x['id']].directory += directoryToAdd[::-1]
    
    if debug: print("Removing %s invalid files" %len(toRemove))

    for x in toRemove:
        _filesMap.pop(x)

    if debug: print("Finished adding files to folders")

def createFolderTree(_foldersMap = foldersMap, _foldersList = []):
    if debug: print("Creating folder tree")
    if not len(_foldersMap): foldersList = getFolders() if not len(_foldersList) else _foldersList
    if debug: print("Mapping folders to foldersMap")

    rootFile = gDrive.root

    _foldersMap[rootFile] = Folder({'name' : "My Drive", 'id' : rootFile})
    for x in foldersList:
        _foldersMap[x['id']] = Folder(x)

    orderFolders(_foldersMap)
    # printFolders() 
    if debug: print("Finished creating folder tree")
    
def printFoldersPartial():
    if debug: print("Printing partial folders list, %s folders" %len(foldersMap))
    toPrint = ""
    for x in foldersMap:
        toAdd = ""
        q = [x]
        while len(q):
            toAdd = "/" + foldersMap[q[0]].metadata['name'] + toAdd
            if foldersMap[q[0]].metadata['parents'] and foldersMap[q[0]].metadata['parents'][0] in foldersMap:  
                q.append(foldersMap[q[0]].metadata['parents'][0])
            q.pop(0)
        toPrint += toAdd + "\n" 

    if debug: print("Opening file to write")
    e = open("/home/jeffrey/Desktop/testing.txt", 'w')
    e.write(toPrint)
    e.close()
    if debug: print("Finished printing partial folders list")


def printFolders():
    if debug: print("Printing folders")
    # CHECK IF ROOT IS HERE
    visited = {gDrive.root : 1}
    stack = [[gDrive.root, 0, 3]]
    toPrint = "%s" %foldersMap[gDrive.root].metadata['name']

    while len(stack):
        currFolder = foldersMap[stack[len(stack) - 1][0]]
        childPos = stack[len(stack) - 1][1]
        offset = stack[len(stack) - 1][2]
        toAdd = "\n"

        if len(currFolder.children) <= childPos:
            stack.pop(len(stack) - 1)
            continue

        if currFolder.children[childPos] not in visited:
            nextFolder = foldersMap[currFolder.children[childPos]]
            visited[nextFolder.metadata['id']] = 1 
            while len(toAdd) <= offset:
                toAdd += " "
            toAdd += nextFolder.metadata['name']
            stack[len(stack) - 1][1] += 1
            stack.append([nextFolder.metadata['id'], 0, offset + 3])

            toPrint += toAdd



    file = open("/home/jeffrey/Desktop/testing2.txt", 'w')
    file.write(toPrint)
    file.close()
    if debug: print("Finished printing folders")

def upload(file = None, dir = None, id = None, parentId = None):

    directory = "/".join(dir) if dir else "/".join(file.directory)
    fileId = None
    if (id):
        fileId = id
    elif (file and file.metadata['id']):
        fileId = file.metadata['id']
    else:
        fileId = generateIds()

    fileName = dir[-1] if dir else file.metadata['name']
    parent = [parentId] if parentId else file.metadata['parents']
    if not parent: parent = [gDrive.root]
    mimeType = None

    if file:
        mimeType = file.metadata['mimeType']
    else:
        mimeType = getMimetype(fileName)

    modTime = None

    if file and "modifiedTime" in file.metadata and file.metadata['modifiedTime']:
        modTime = file.metadata['modifiedTime']
    else:
        tempTime = os.path.getmtime(directory)
        modTime = epoch2utc(tempTime)

    metadata = {
        'id' : fileId,
        'name' : fileName,
        'parents' : parent,
        'modifiedTime' : modTime,
        'mimeType' : mimeType,
    }

    if type(file) == Folder:
        response = DRIVE.files().create(body=metadata).execute()
    else:
        mediaBody = MediaFileUpload(directory, mimeType, resumable=True)
        
        request = DRIVE.files().create(body=metadata, media_body=mediaBody)
        response = None
        while response is None:
            status, response = request.next_chunk()
            # Print status if want
    return response

def download(id = None, name = None, dir = None, modTime = None, file = None):
    # Epoch times differ on windows and unix
    if (not name or not id) and not file: return


    temp = None
    directory = dir if dir else "/".join(file.directory)
    fileId = id if id else file.metadata['id']
    modDateEpoch = None
    if (modTime): modDateEpoch = utc2epoch(modTime)
    elif (file and "modifiedTime" in file.metadata and file.metadata["modifiedTime"]):
        modDateEpoch = utc2epoch(file.metadata["modifiedTime"])

    if os.path.exists(directory) and os.stat(directory).st_size > 0: return # BANDAID
    try:
        temp = DRIVE.files().get_media(fileId = fileId).execute()
    except Exception as e:
        print(e)
        return
    with open(directory, "wb") as f:
        f.write(temp)
    if modDateEpoch: os.utime(directory, (modDateEpoch, modDateEpoch))

def deleteCloud(file = None, dir = None, id = None):
    if file:
        try: DRIVE.files().delete(fileId = file.metadata['id']).execute()
        except Exception as e: 
            print("In deleteCloud: %s for file %s" %(e, file.metadata['name']))
    elif dir:
        return
    elif id:
        try: DRIVE.files().delete(fileId = id).execute()
        except Exception as e: 
            print("In deleteCloud: %s for file %s" %(e, id))
    else:
        print("Nothing provided to delete")


def deleteLocal(dir, isFolder=0):
    if isFolder:
        try: os.rmdir(dir)
        except Exception as e:
            print("In deleteLocal: %s for directory %s" %(e, dir))
    else:
        try: os.remove(dir)
        except Exception as e:
            print("In deleteLocal: %s for directory %s" %(e, dir))

def createLocalFolder(dir):
    os.mkdir(dir)

def createLocalFolders():
    if debug: print("Creating local folders")
    visited = {gDrive.root : 1} # Add this at some point
    stack = [[gDrive.root, 0]]
    currDirectory = [x for x in driveFilePath]

    iter = 0
    while len(stack) and iter < len(foldersMap) * 5:
        iter += 1
        currId = stack[len(stack) - 1][0]
        currFolder = foldersMap[currId]
        currChildCount = stack[len(stack) - 1][1]

        if currChildCount == 0:
            try: 
                os.makedirs("/".join(currDirectory + [currFolder.metadata['name']]))
                currFolder.directory = currDirectory
            except FileExistsError:
                pass
            except:
                print("Shits bugged dog")
            currDirectory.append(currFolder.metadata['name'])

        if currChildCount >= len(currFolder.children):
            stack.pop(len(stack) - 1)
            if len(currDirectory) > 1: currDirectory.pop(len(currDirectory) - 1)
            continue

        stack[len(stack) - 1][1] += 1
        stack.append([currFolder.children[currChildCount], 0])
        
    if debug: print("Finished creating local folders with %s iterations" %iter)


def populateLocalFoldersEmpty():
    if debug: print("Adding empty files to local folders")

    for x in filesMap:
        currFile = None
        try: currFile = open("/".join(filesMap[x].directory + [filesMap[x].metadata['name']]), 'w')
        except OSError:
            currFile = open("/".join(filesMap[x].directory + [filesMap[x].metadata['name'][:10]]), 'w')
        currFile.close()

    if debug: print("Finishing adding empty files to local folders")


def populateLocalFolders():
    if debug: print("Adding files to local folders")

    iter = 0
    for x in filesMap:
        download(file=filesMap[x])
        iter += 1
        if debug and iter % 50 == 0: print("Downloaded %s of %s files" %(iter, len(filesMap)))

    if debug: print("Finishing adding %s files to local folders" %iter)

def toLocal():
    createLocalFolders()
    populateLocalFolders()


# Make a json-esque file with all the folders/files
def writeLocalReference():
    # Gonna assume that no other folder other than My Drive have no parents
    if debug: print("Making local reference file")

    # CHECK IF ROOT IS HERE

    indent = 3

    visited = {gDrive.root : 1}
    stack = [[gDrive.root, 0, 0]]
    toPrint = ""


    maxIterations = (len(foldersMap) * 3)
    currIterations = 0
    while (len(stack) and currIterations < maxIterations):
        currIterations += 1

        currFolder = foldersMap[stack[len(stack) - 1][0]]
        currChildPos = stack[len(stack) - 1][1]
        offset = stack[len(stack) - 1][2]

        toAdd = ""

        # Print itself
        if currChildPos == 0:
            toAdd += " " * offset + "{\n"
            offset += indent
            stack[len(stack) - 1][2] = offset
            toAdd += " " * offset + "type : folder\n"
            toAdd += currFolder.toString(offset)

        # Finished printing all other subfolders, add files
        if currChildPos >= len(currFolder.children):
            for x in currFolder.contents:
                toAdd += " " * (offset) + "{\n"
                toAdd += " " * (offset + indent) + "type : file\n"
                toAdd += filesMap[x].toString(offset + indent)
                toAdd += " " * (offset) + "}\n"
                
            toAdd += " " * (offset - indent) + "}\n" 
            stack.pop(len(stack) - 1)
            
        # Add subfolders to stack
        elif currFolder.children[currChildPos] not in visited:
            nextFolder = foldersMap[currFolder.children[currChildPos]]
            stack[len(stack) - 1][1] += 1
            stack.append([nextFolder.metadata['id'], 0, offset + indent])
            visited[nextFolder.metadata['id']] = 1
            

        toPrint += toAdd


    file = open("/home/jeffrey/Desktop/testing2.txt", 'w')
    file.write(toPrint)
    file.close()
    if debug: print("Finished local reference")


def readLocalReference():
    if debug: print("Reading from local reference file")



    with open("/home/jeffrey/Desktop/testing2.txt", 'r') as file:
        iter = 0
        directoryToAdd = [x for x in driveFilePath]

        making = []
        current = None

        # switches
        makeNew = False
        writing = False

        count = 0
        for f in file:
            count += 1
            currLine = f.lstrip().rstrip()

            if currLine == "{":
                makeNew = True
                continue

            if currLine == "}":
                writing = False
                
                making[len(making) - 1].addSelfToParent()
                making[-1].directory = [x for x in directoryToAdd]
                if type(making[-1]) == File:
                    making[-1].directory += [making[-1].metadata['name']]

                elif type(making[-1]) == Folder:
                    directoryToAdd.pop()
                making.pop()
                continue

            if makeNew:
                key, val = re.findall("(.*) : (.*)", currLine)[0]
                if val == "file":
                    making.append(File(meta=[]))
                elif val == "folder":
                    making.append(Folder(meta=[]))
                else:
                    print ("We got some problemos! File type was: %s" %val)

                makeNew = False
                writing = True
                continue

            if writing:
                key, val = re.findall("(.*) : (.*)", currLine)[0]

                if key == "id":
                    if type(making[len(making) - 1]) == Folder:
                        foldersMap[val] = making[len(making) - 1]
                    else:
                        filesMap[val] = making[len(making) - 1]
                if val[0] == '[' and key != "name": # Name should be the only thing thats not a list that can have '['s in it, so we need to check for it specifically
                    val = val[1:len(val) - 1].split(",")

                # Check for contents and children for folders

                making[len(making) - 1].metadata[key] = val
                if type(making[-1]) == Folder and key == "name":
                    directoryToAdd += [val]

        print(len(filesMap), len(foldersMap))

def checkmd5(dir):
    md5 = ""
    with open(dir, 'rb') as f:
        data = f.read()
        md5 = hashlib.md5(data).hexdigest()
    return md5


def update():
    # Call pollCloud, then poll. Merge the toDeletes, and also pass it all into the backup method


    pass

def pollLocal():
    if debug: print("Polling local files for changes")

    # visited = {}
    toDelete = []
    toUpload = []
    toModify = {}

    toDeleteFolders = []
    toCreateFolders = []
     
    dir = [x for x in driveFilePath] + ["My Drive"]
    stack = [[
        "My Drive",   # name of directory
        "0ALJkVcguqfY-Uk9PVA",  # ID of folder (empty if folder is new)
        # [],         # list of subdirectories
        # 0,          # position in subdir list
        ]]

    iter = 0
    while len(stack):
        dirName = stack[len(stack) - 1][0]
        dirID = stack[len(stack) - 1][1]

        # If the list only has 2 entries, it needs initializing and analyzing. See above (stack) for info
        if len(stack[len(stack) - 1]) == 2:
            contents = os.listdir("/".join(dir))
            fileList = []
            folderList = []

            for x in contents:
                if os.path.isdir("/".join(dir + [x])):
                    folderList.append(x)
                else: fileList.append(x)

            # Analyze subdirectories and files, see if they are all there (Do this by looping through all of the folder's children, and see if they match. If not, add to delete or upload)

            currFolderFiles = {}
            for x in foldersMap[dirID].contents:
                currFolderFiles[filesMap[x].metadata["name"]] = x

            # Go through fileList and check if it is in the currFolder's filelist. If it is, check the md5 (and maybe if that fails, check the date modified/size) 
            # and if it doesn't match, add to toUpload (toModify). Pop the file off of currFolderFiles. If it isnt in the fileList, add it to toUpload. At the end,
            # add any leftover files in currFolderFiles to toDelete

            for x in fileList:
                if x in currFolderFiles:
                    # Check if modified dates are the same.

                    if floor(os.path.getmtime("/".join(dir + [x]))) != floor(utc2epoch(filesMap[currFolderFiles[x]].metadata["modifiedTime"])):
                        # toModify.append(filesMap[currFolderFiles[x]])
                        tempFile = File({
                            'name' : x,
                            'id' : generateIds(),
                            'mimeType' : getMimetype(x),
                            'parents' : [dirID],
                            'modifiedTime' : epoch2utc(os.path.getmtime("/".join(dir + [x])))
                        })
                        tempFile.directory = dir + [x]
                        # tempFile.addSelfToParent()
                        foldersMap[dirID].contents.append(tempFile.metadata['id'])
                        toUpload.append(tempFile)
                        # filesMap[tempFile.metadata['id']] = tempFile # Issue
                        toDelete.append(filesMap[currFolderFiles[x]])

                    currFolderFiles.pop(x)
                    fileList[fileList.index(x)] = -1

                else:
                    tempFile = File({
                        'name' : x,
                        'id' : generateIds(),
                        'mimeType' : getMimetype(x),
                        'parents' : [dirID],
                        'modifiedTime' : epoch2utc(os.path.getmtime("/".join(dir + [x])))
                    })
                    tempFile.directory = dir + [x]
                    # tempFile.addSelfToParent()
                    foldersMap[dirID].contents.append(tempFile.metadata['id'])
                    toUpload.append(tempFile)
                    # filesMap[tempFile.metadata['id']] = tempFile
                    fileList[fileList.index(x)] = -1

            for x in currFolderFiles:
                toDelete.append(filesMap[currFolderFiles[x]])

            currFolderFolders = {}
            for x in foldersMap[dirID].children:
                # try: 
                currFolderFolders[foldersMap[x].metadata["name"]] = x
                # except KeyError: continue # Since we are adding new children that are not yet created, skip them

            nextFoldersList = []
            for x in folderList:
                if x in currFolderFolders:
                    nextFoldersList.append(currFolderFolders[x])
                    folderList[folderList.index(x)] = -1
                    currFolderFolders.pop(x)
                else:
                    tempFolder = Folder({
                        'name' : x,
                        'id' : generateIds(),
                        'mimeType' : mime_types['folder'],
                        'parents' : [dirID]
                    })
                    tempFolder.directory = dir + [x]
                    # tempFolder.addSelfToParent()
                    foldersMap[dirID].children.append(tempFolder.metadata['id'])
                    # foldersMap[tempFolder.metadata['id']] = tempFolder
                    toCreateFolders.append(tempFolder) # We need to add all of the items inside of directory to the lists
                    tempStack = [[tempFolder, 0, []]]
                    while tempStack:
                        currTempFolder = tempStack[-1][0]
                        tempDir = currTempFolder.directory
                        if not len(tempStack[-1][2]):
                            contents = os.listdir("/".join(tempDir))
                            for y in contents:
                                if os.path.isdir("/".join(tempDir + [y])):
                                    tempFolder = Folder({
                                        'name' : y,
                                        'id' : generateIds(),
                                        'mimeType' : mime_types['folder'],
                                        'parents' : [currTempFolder.metadata['id']]
                                    })
                                    tempFolder.directory = tempDir + [y]
                                    # tempFolder.addSelfToParent()
                                    # foldersMap[tempFolder.metadata['id']] = tempFolder
                                    currTempFolder.children.append(tempFolder.metadata['id'])
                                    toCreateFolders.append(tempFolder)
                                    tempStack[-1][2].append(tempFolder)
                                else:
                                    tempFile = File({
                                        'name' : y,
                                        'id' : generateIds(),
                                        'mimeType' : getMimetype(y),
                                        'parents' : [currTempFolder.metadata['id']],
                                        'modifiedTime' : epoch2utc(os.path.getmtime("/".join(tempDir + [y])))
                                    })
                                    tempFile.directory = tempDir + [y]
                                    # tempFile.addSelfToParent()
                                    # filesMap[tempFile.metadata['id']] = tempFile
                                    currTempFolder.contents.append(tempFile.metadata['id'])
                                    toUpload.append(tempFile)
                        if len(tempStack[-1][2]) > tempStack[-1][1]:
                            tempStack[-1][1] += 1
                            tempStack.append([tempStack[-1][2][tempStack[-1][1] - 1], 0, []])
                        else:
                            tempStack.pop()

                            
            for x in currFolderFolders:
                # toDeleteFolders.append("/".join(dir) + x)
                toDeleteFolders.append(foldersMap[currFolderFolders[x]])

                tempStack = [[foldersMap[currFolderFolders[x]], 0, []]]
                while tempStack:
                    currTempFolder = tempStack[-1][0]
                    if not len(tempStack[-1][2]):
                        for y in currTempFolder.contents:
                            toDelete.append(filesMap[y])
                        for y in currTempFolder.children:
                            tempStack[-1][2].append(foldersMap[y])
                            toDeleteFolders.append(foldersMap[y])
                    if len(tempStack[-1][2]) > tempStack[-1][1]:
                        tempStack[-1][1] += 1
                        tempStack.append([tempStack[-1][2][tempStack[-1][1] - 1], 0, []])
                    else:
                        tempStack.pop()

                

            stack[len(stack) - 1].append(nextFoldersList)
            stack[len(stack) - 1].append(0)

        if len(stack[len(stack) - 1][2]) <= stack[len(stack) - 1][3]:
            stack.pop()
            dir.pop()
            continue

        iter += 1
        if not iter % 10 and debug: print("Polled %s directories" %iter)

        nextChildID = stack[len(stack) - 1][2][stack[len(stack) - 1][3]]
        dir.append(foldersMap[nextChildID].metadata["name"])
        stack[len(stack) - 1][3] += 1
        stack.append([foldersMap[nextChildID].metadata["name"], nextChildID])
        
    if debug: print("Uploading changes to drive")

    # with open("local_changes.txt", "w") as f:
    #     toWrite = [x for x in toUpload]
    #     toWrite += ["\n\n\nTO DELETE\n\n\n"]
    #     toWrite += [x.metadata['name'] for x in toDelete]
    #     toWrite += ["\n\n\nFOLDERS\n\nTO CREATE\n\n\n"]
    #     toWrite += [x for x in toCreateFolders]
    #     toWrite += ["\n\n\nTO DELETE\n\n\n"]
    #     toWrite += [x.metadata['name'] for x in toDeleteFolders]
    #     f.write("FILES\n\nTO UPLOAD\n\n\n" + "\n".join(toWrite))

    return toDelete, toUpload, toDeleteFolders, toCreateFolders
    

def pollCloud():
    if (debug): print("Polling the cloud\n")
    # tempFolders, tempFiles = dict(), dict()
    # createFolderTree(tempFolders)
    # addFilesToFolders(tempFiles, tempFolders)

    toDownload = []
    toDelete = []

    toCreateFolders = []
    toDeleteFolders = []

    cloudFiles = getFiles()
    cloudFolders = getFolders()

    tempFolders = {}
    tempFiles = {}
    createFolderTree(tempFolders, cloudFolders)
    addFilesToFolders(tempFiles, tempFolders, cloudFiles)

    refFiles = {}
    for x in filesMap:
        refFiles[x] = 1

    refFolders = {}
    for x in foldersMap:
        refFolders[x] = 1

    # for x in range(len(cloudFiles)):
    #     if cloudFiles[x]['id'] in filesMap:
    #         try: 
    #             # if cloudFiles[x]['md5Checksum'] == filesMap[cloudFiles[x]['id']].metadata['md5Checksum']:
    #             if (floor(utc2epoch(cloudFiles[x]['modifiedTime']))
    #                 == floor(utc2epoch(filesMap[cloudFiles[x]['id']].metadata['modifiedTime']))):
    #                 refFiles.pop(cloudFiles[x]['id'])
    #                 cloudFiles[x] = -1
    #         except KeyError:
    #             refFiles.pop(cloudFiles[x]['id'])
    #             cloudFiles[x] = -1

    for x in tempFiles:
        if x in filesMap:
            try:
                if (floor(utc2epoch(tempFolders[x].metadata['modifiedTime']))
                    == floor(utc2epoch(filesMap[x].metadata['modifiedTime']))):
                    refFiles.pop(x)
                    tempFiles[x] = -1
            except KeyError:
                refFiles.pop(x)
                tempFiles[x] = -1
    
    for x in tempFolders:
        if x in foldersMap:
            if tempFolders[x].metadata['name'] == foldersMap[x].metadata['name']:
                refFolders.pop(x)
                tempFolders[x] = -1

    # for x in cloudFiles:
    #     if x != -1:
    #         # try: 
    #         toDownload.append(tempFiles[x['id']])
    #         # except: continue # Make it so that these damn invalid files are disappeared somewhere
    for x in tempFiles:
        if tempFiles[x] != -1: 
            toDownload.append(tempFiles[x])

    for x in refFiles:
        # try: toDelete.append(tempFiles[x['id']])
        # except: continue
        toDelete.append(filesMap[x])

    # for x in cloudFolders:
    #     if x != -1:
    #         try: 
    #             toCreateFolders.append(tempFolders[x['id']])
    #         except: continue
    for x in tempFolders:
        if tempFolders[x] == -1: continue 
        try: toCreateFolders.append(tempFolders[x])
        except: continue


    for x in refFolders:
        # try: toDeleteFolders.append(tempFolders[x['id']])
        # except: continue
        toDeleteFolders.append(foldersMap[x])

    if debug: print("Finished polling cloud\n")

    # with open("cloud_changes.txt", "w") as f:
    #     toWrite = [x.metadata['name'] for x in toDownload]
    #     toWrite += ["\n\n\nTO DELETE\n\n\n"]
    #     toWrite += [x.metadata['name'] for x in toDelete]
    #     toWrite += ["\n\n\nFOLDERS\n\nTO CREATE\n\n\n"]
    #     toWrite += [x.metadata['name'] for x in toCreateFolders]
    #     toWrite += ["\n\n\nTO DELETE\n\n\n"]
    #     toWrite += [x.metadata['name'] for x in toDeleteFolders]
    #     f.write("FILES\n\nTO DOWNLOAD\n\n\n" + "\n".join(toWrite))

    return toDelete, toDownload, toDeleteFolders, toCreateFolders

def poll():
    localToDelete, localToUpload, localToDeleteFolders, localToUploadFolders = pollLocal()
    cloudToDelete, cloudToDownload, cloudToDeleteFolders, cloudToCreateFolders = pollCloud()
    
    localToDelete = localToDelete[::-1]
    localToDeleteFolders = localToDeleteFolders[::-1]

    sort = lambda x : len(x.directory)
    cloudToDelete.sort(key = sort, reverse=True)
    cloudToDownload.sort(key = sort)
    cloudToDeleteFolders.sort(key = sort, reverse=True)
    cloudToCreateFolders.sort(key = sort)
    

    # Since os can only delete empty directories, delete files first, then folders
    # And since we need folders to put files in, make new directories before downloading files

    toWrite = "-- LOCAL --\n\nTo Delete\n\n"
    # Delete files
    for x in localToDelete:
        toWrite += "/".join(x.directory) + "\n"
        print("localDelete", x.metadata['id'], x.metadata['name'])
        if armed:
            deleteCloud(x)
            filesMap.pop(x.metadata['id']) 
            tempParent = foldersMap[x.metadata['parents'][0]]
            tempParent.contents.pop(tempParent.contents.index(x.metadata['id']))
        
        

    toWrite += "\n\nTo Delete Folders\n\n"
    # Delete folders
    for x in localToDeleteFolders:
        print("localDeleteFolder", x.metadata['id'], x.metadata['name'])
        toWrite += "/".join(x.directory) + "\n"
        if armed:
            deleteCloud(x)
            foldersMap.pop(x.metadata['id'])
            tempParent = foldersMap[x.metadata['parents'][0]]
            tempParent.children.pop(tempParent.children.index(x.metadata['id']))

    toWrite += "\n\nTo Upload Folders\n\n"
    # Upload folders
    for x in localToUploadFolders:
        print("localUploadFolder", x.metadata['id'], x.metadata['name'])
        toWrite += "/".join(x.directory) + "\n"
        if armed:
            upload(x)
            foldersMap[x.metadata['id']] = x

    toWrite += "\n\nTo Upload Files\n\n"
    # Upload files
    for x in localToUpload:
        print("localUpload", x.metadata['id'], x.metadata['name'])
        toWrite += "/".join(x.directory) + "\n"
        if armed:
            upload(x)
            filesMap[x.metadata['id']] = x

    toWrite += "\n\n-- CLOUD --\n\nTo Delete\n\n"
    # Delete local files
    for x in cloudToDelete:
        print("cloudDelete", x.metadata['id'], x.metadata['name'])
        toWrite += "/".join(x.directory) + "\n"
        if armed:
            try: 
                deleteLocal("/".join(x.directory))
                filesMap.pop(x.metadata['id'])
                tempParent = foldersMap[x.metadata['parents'][0]]
                tempParent.contents.pop(tempParent.contents.index(x.metadata['id']))
            except: continue


    toWrite += "\n\nTo Delete Folders\n\n"
    # Delete local folders
    for x in cloudToDeleteFolders:
        print("cloudDeleteFolder", x.metadata['id'], x.metadata['name'])
        toWrite += "/".join(x.directory) + "\n"
        if armed:
            deleteLocal("/".join(x.directory))
            foldersMap.pop(x.metadata['id'])
            tempParent = foldersMap[x.metadata['parents'][0]]
            tempParent.children.pop(tempParent.children.index(x.metadata['id']))

    toWrite += "\n\nTo Create Folders\n\n"
    # Create local folders
    for x in cloudToCreateFolders:
        print("cloudCreateFolder", x.metadata['id'], x.metadata['name'])
        toWrite += "/".join(x.directory) + "\n"
        if armed:
            createLocalFolder("/".join(x.directory))
            foldersMap[x.metadata['id']] = x
            x.addSelfToParent()

    toWrite += "\n\nTo Create Files\n\n"
    # Create local files
    for x in cloudToDownload:
        print("cloudCreate", x.metadata['id'], x.metadata['name'])
        toWrite += "/".join(x.directory) + "\n"
        if armed:   
            download(file=x)
            filesMap[x.metadata['id']] = x
            x.addSelfToParent()

    with open("changes.txt", "w") as f:
        f.write(toWrite)

    if armed: writeLocalReference()

def checkDiff():
    pass


def temp():


    pass

def downloadByName(name):
    file = DRIVE.files().list(q="name='%s'" %name, fields="files(id)").execute()
    fileID = file["files"][0]["id"]
    print(fileID)
    contents = DRIVE.files().get_media(fileId=fileID).execute()
    save = open("/home/jeffrey/Desktop/%s" %name, 'wb')
    save.write(contents)
    save.close()

def test():
    deleteCloud(id="11mNV9GAamTZCv-Qdgpk9rbLHNCXOUXNh")


# Need try catch for all of these calls to the API
def generateIds(count = 1):
    toReturn =  DRIVE.files().generateIds(count=count).execute()['ids']
    return toReturn if count > 1 else toReturn[0]

def getExtension(name):
    return name.split(".")[-1]

def getMimetype(name):
    try: return mime_types[getExtension(name)]
    except Exception as e:
        return mime_types["default"]
    
def epoch2utc(epoch):
    # Changes based on os I think
    dt = datetime(1970, 1, 1) + timedelta(seconds=epoch)
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

def utc2epoch(utc):
    dt = datetime.strptime(utc, '%Y-%m-%dT%H:%M:%S.%f%z')
    return dt.timestamp()



def arm():
    # for x in range(5): print("ARMING\n\n\n")
    global armed
    print("Arm program? 1 for yes, anything else for no")
    if input() == "1": armed = 1
    else: armed = 0

def main():
    # Do error catching
    global DRIVE

    DRIVE = auth()
    getRoot()

    # arm()
    # init()
    # getFiles()
    # download()
    # upload()
    # delete()
    # temp()
    # test()
    createFolderTree()
    addFilesToFolders()
    toLocal()
    writeLocalReference()
    # readLocalReference()
    # pollLocal()
    # pollCloud()
    # poll()

if __name__ == "__main__":
    main()
