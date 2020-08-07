import os
import sys

backendS3FileName = "backend_s3.tf" # this file is always located at the root of a terraform folder
rootFolder = "terraform" # this is the root of all terraform files


# does a "reverse" breadth first search starting from "currentDir"
# and going up until it finds all occurences of a certain file
def crawlUpFolders(currentDir, ignoreDir):
    if(os.path.basename(currentDir) == rootFolder):
        return crawlDownFolders(currentDir, ignoreDir)
    else:
        sourceEnv = crawlDownFolders(currentDir, ignoreDir)
        if sourceEnv is None: # if no backend_s3.tf in current folder then look in parent folder
            return crawlUpFolders(os.path.dirname(currentDir),os.path.basename(currentDir))
        else: # if backend_s3.tf has been found return the folder that contains it
            return sourceEnv



# returns a list of all the folders inside "currentDir" and ignoring "ignoreDir"
# where an occurence backend_s3.tf was found
def crawlDownFolders(currentDir, ignoreDir):
    if backendS3FileName in os.listdir(currentDir):
        return os.path.basename(currentDir)
    else:
        for folder in os.listdir(currentDir):
            folderPath = os.path.join(currentDir,folder)
            if os.path.isdir(folderPath) and (os.path.basename(folderPath) != ignoreDir) and not os.path.basename(folderPath).startswith('.'):
                return crawlDownFolders(folderPath,"")
        return None

def crawlUpFolders2(currentDir, ignoreDir, moduleRelativePath, runningList = None):
    if runningList is None:
        runningList = []
    if(os.path.basename(currentDir) == rootFolder):
        return runningList + crawlDownFolders2(currentDir, ignoreDir, moduleRelativePath)
    else:
        subList = crawlDownFolders2(currentDir, ignoreDir, moduleRelativePath)
        return crawlUpFolders2(os.path.dirname(currentDir),os.path.basename(currentDir),os.path.join(os.path.basename(currentDir),moduleRelativePath),runningList + subList)


def crawlDownFolders2(currentDir, ignoreDir, moduleRelativePath):
    for file in os.listdir(currentDir):
        filePath = os.path.join(currentDir,file)
        if os.path.isfile(filePath) and file.endswith(".tf"):
            with(open(filePath, 'r')) as file:
                for line in file.readlines():
                    if moduleRelativePath in line:
                        print("found an occurence of {} in {}".format(moduleRelativePath,filePath))
                        return [currentDir]
    newList = []
    for folder in os.listdir(currentDir):
        folderPath = os.path.join(currentDir,folder)
        if os.path.isdir(folderPath) and (os.path.basename(folderPath) != ignoreDir) and not os.path.basename(folderPath).startswith('.'):
            newList = newList + crawlDownFolders2(folderPath,"", "../" + moduleRelativePath)
    return newList

# find occurences of a module within the terraform folder
def findModuleUsage(currentFolder, moduleRelativePath):
    # 1. crawl up folders while constructing a relative path of the starting folder
    # 2. look into all tf files for any match of the relative path
    # 3. return the calling folder
    listModuleUsage = crawlUpFolders2(currentFolder,"",moduleRelativePath)
    listEnvironments = []
    # 4. for each usage of the module find the enclosing env from where terrafor should be run
    for moduleUsagePath in listModuleUsage:
        listEnvironments.append(crawlUpFolders(moduleUsagePath,""))
    return listEnvironments

print("::set-output name={}::{}".format("target_folders",findModuleUsage(sys.argv[1],sys.argv[2])))
