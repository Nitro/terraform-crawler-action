import os
import sys
import json

# A class that represent a crawler used to find usage of modules in Terraform
# "repoPath" is the full path to the root of the repo. All search happens within the repo
# "listFiles" is the list of files on which the search will be performed. They are represented
# as a path starting from the root of the repo (ex: firstfolder/secondfolder/myfile.tf)
# "targetFile" is a key file which indicates the location from which terraform commands should be applied
class TerraformCrawler:
    def __init__(self, repoPath, listFiles, targetFile):
        self.repoPath = repoPath
        self.listFiles = listFiles
        self.targetFile = targetFile
        self.rootFolder = os.path.basename(self.repoPath)


    # get a full path of a directory as argument and returns true if
    # a terraform command should be applied from here
    # and false otherwise
    def isRootModule(self, dirPath):
        for file in os.listdir(dirPath):
            filePath = os.path.join(dirPath,file)
            if os.path.isfile(filePath) and os.path.basename(filePath) == self.targetFile:
                return True
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
        for file in os.listdir(currentDir):
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

def main():
    jsonString = sys.argv[1]
    data = json.loads(jsonString)
    crawler = TerraformCrawler(os.environ['GITHUB_WORKSPACE'],data,'backend_s3.tf')
    listTerraformFolders = []
    for value in crawler.listFiles:
        nextListFolders = crawler.findModuleUsage(value)
        for folder in nextListFolders:
            if not folder in listTerraformFolders:
                listTerraformFolders.append(folder)
    print("::set-output name={}::{}".format("target_folders",json.dumps(listTerraformFolders)))

if __name__ == "__main__":
    main()
