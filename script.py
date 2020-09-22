import os
import sys
import json
import re

# A class that represent a crawler used to find usage of modules in Terraform
# "repoPath" is the full path to the root of the repo. All search happens within the repo
# "listFiles" is the list of files on which the search will be performed. They are represented
# as a path starting from the root of the repo (ex: firstfolder/secondfolder/myfile.tf)
class TerraformCrawler:
    def __init__(self, repoPath, listFiles):
        self.repoPath = repoPath
        self.listFiles = listFiles
        self.rootFolder = os.path.basename(self.repoPath)


    # get a full path of a directory as argument and returns true if
    # a terraform command should be applied from here
    # and false otherwise
    def isRootModule(self, dirPath):
        try:
            filesInDir = os.listdir(dirPath)
            for file in filesInDir:
                filePath = os.path.join(dirPath,file)
                if os.path.isfile(filePath) and file.endswith(".tf"):
                    with(open(filePath, 'r')) as file:
                        for line in file.readlines():
                            if re.match(r"provider \".*\" {",line) or re.match("terraform {",line):
                                return True
            return False
        except FileNotFoundError:
            # error is generated if the parent folder doesn't exist anymore (file and folder were deleted)
            # return false because we are certain this isn't a root module
            return False

    # returns a list of files that are importing the module "filePath"
    # if there is a chain of module imports (i.e. X -> Y import X -> Z import Y)
    # Then this function with return the file that does the last import
    def findModuleUsage(self, filePath):
        parentDirPath = os.path.dirname(filePath) # path to parent folder starting from root of repo
        parentFullPath = os.path.join(self.repoPath,parentDirPath) # full path to parent folder
        listCandidateModules = [parentFullPath]
        listRootFolders = []
        while listCandidateModules:
            parentDirPath = listCandidateModules.pop()
            if self.isRootModule(parentDirPath):
                listRootFolders.append(parentDirPath.replace(self.repoPath + "/", ''))
            else:
                moduleName = os.path.basename(parentDirPath) # the name of the module we are looking for
                parentDirPath = os.path.dirname(parentDirPath)
                parentFullPath = os.path.join(self.repoPath,parentDirPath)
                listCandidateModules += self.findCallingModule(parentFullPath,'',moduleName)
        return listRootFolders

    # crawls up the folders in a breadth-first pattern looking for usage of "moduleRelativePath"
    # at each new level calls the helper function on each unvisited folder
    # search only happens within "self.repoPath"
    # currentDir is formatted as /full/path/to/containing/folder
    # moduleRelative path is initially the name of the module
    # returns the list of all folders (as full path) that contain a file calling "moduleRelativePath"
    def findCallingModule(self, currentDir, ignoreDir, moduleRelativePath, runningList = None):
        if runningList is None:
            runningList = []
        if(os.path.basename(currentDir) == self.rootFolder):
            return runningList + self.findCallingModuleHelper(currentDir, ignoreDir, moduleRelativePath)
        else:
            subList = self.findCallingModuleHelper(currentDir, ignoreDir, moduleRelativePath)
            return self.findCallingModule(os.path.dirname(currentDir),os.path.basename(currentDir),os.path.join(os.path.basename(currentDir),moduleRelativePath),runningList + subList)

    # crawls down a folder looking for usage of "moduleRelativePath"
    # returns the list of all folders calling "moduleRelativePath" within "currentDir"
    def findCallingModuleHelper(self, currentDir, ignoreDir, moduleRelativePath):
        try:
            filesInDir = os.listdir(currentDir)
            for file in filesInDir:
                filePath = os.path.join(currentDir,file)
                if os.path.isfile(filePath) and file.endswith(".tf"):
                    with(open(filePath, 'r')) as file:
                        for line in file.readlines():
                            if moduleRelativePath in line:
                                return [currentDir]
            newList = []
            for folder in os.listdir(currentDir):
                folderPath = os.path.join(currentDir,folder)
                if os.path.isdir(folderPath) and (os.path.basename(folderPath) != ignoreDir) and not os.path.basename(folderPath).startswith('.'):
                    newList = newList + self.findCallingModuleHelper(folderPath,"", "../" + moduleRelativePath)
            return newList
        except FileNotFoundError:
            # if the folder doesn't exist there is no need to crawl down inside it
            return []

def main():
    jsonString = sys.argv[1]
    data = json.loads(jsonString)
    crawler = TerraformCrawler(os.environ['GITHUB_WORKSPACE'],data)
    listTerraformFolders = []
    for value in crawler.listFiles:
        nextListFolders = crawler.findModuleUsage(value)
        for folder in nextListFolders:
            if not folder in listTerraformFolders:
                listTerraformFolders.append(folder)
    print("::set-output name={}::{}".format("target_folders",json.dumps(listTerraformFolders)))

if __name__ == "__main__":
    main()
