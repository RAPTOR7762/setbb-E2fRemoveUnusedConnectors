#!/usr/bin/env python3

# Various support routines for processing Fritzing's fzp and svg files. 

from __future__ import print_function   # for eprint.

# Change this from 'no' to 'yes' to cause 0 length/width terminal definitions
# to be warned about but not modified, to being changed (which will cause them
# to move in the svg and need repositioning) to a length/width of 10 (which 
# depending on scaling may or may not be .01in). The default is warn but not
# change, but I use modify as it is much easier converting 0 width parts with
# Inkscape like that.

ModifyTerminal = 'y'

# Set to 'n' (or anything not 'y') to supress Warning 28: (dup id in 
# description field) which is all of common, annoying and harmless.
# However by default the warning is issued ...

IssueNameDupWarning = 'n'

# If RemoveTspans is n, then if we see a tag of value 'tspan', toss an error
# because Qt objects to Fritzing's method of rendering tspans. If RemoveTspans
# is 'y' (or any other value than 'n') then convert the tspan in to a standard
# text element and note the modification as an error to be manually checked.

RemoveTspans = 'y'

ChangeConnectorAsGroup = 'y'

Version = '0.0.4'  # Version number of this file. 

# Import copyfile

from shutil import copyfile

# Import os and sys to get file rename and the argv stuff, re for regex,
# logging to get logging support and PPTools for the parse routine

import os, sys, re, logging, math, PPToolsw as PP

# and the lxml library for the xml

from lxml import etree

# Establish a local logger instance.

logger = logging.getLogger(__name__)

def eprint(*args, **kwargs):

    # https://stackoverflow.com/questions/5574702/how-to-print-to-stderr-in-python

    print(*args, file=sys.stderr, **kwargs)

# End of def eprint(*args, **kwargs):

def EprintBanner(Elem, Level, InFile, Debug):

    if Debug > 1:

        # If debugging is enabled at 2 or higher output the Source line 
        # number on the left margin to make it easily visable via this
        # print statement (eprint because it is going to stderr where
        # logger is writing rather than stdout as print does)

        eprint('*** XML source line {0:d} Tree Level {1:d}  File\n\n    \'{2:s}\'\n'.format(Elem.sourceline, Level, InFile))

    # End of if Debug > 1:

# End of def EprintBanner(Elem, Level, InFile, Debug):

def OutputSplashScreen(InFile, Debug):

    # Write a splash screen to separate file processing between files 
    # to be able to find a particular point in the debug log easier.

    if Debug > 1:

        # If debug is enabled output an easily spotable banner
        # to detect the start of a debug run on the console.

        eprint ('\n\n\n\n********************************************************************************\n********************************************************************************\n********************************************************************************\n********************************************************************************\n********************************************************************************\n\n               FritzingCheckPart.py: Starting to process file\n\n   {0:s}\n\n********************************************************************************\n********************************************************************************\n********************************************************************************\n********************************************************************************\n********************************************************************************\n\n\n'.format(str(InFile)))

    else:

        print('\n**** Starting to process file {0:s}\n\n'.format(str(InFile)))

    # End of if Debug > 1:

# End of def OutputSplashScreen(FileName):




def InitializeAll():

    # Initialize all of the global variables

    Errors = []

    Warnings = []

    Info = []

    FzpDict = {}

    FzpDict['connectors.fzp.breadboardView'] = []

    FzpDict['connectors.fzp.iconView'] = []

    FzpDict['connectors.fzp.pcbView'] = []

    FzpDict['connectors.fzp.schematicView'] = []

    FzpDict['views'] = []

    CurView = None

    TagStack = [['empty', 0]]

    State={'lasttag': 'none', 'nexttag': 'none', 'lastvalue': 'none', 'image': 'none', 'noradius': [], 'KeyErrors': [], 'InheritedAttributes': []}

    State['InheritedAttributes'] = None

    return Errors, Warnings, Info, FzpDict, CurView, TagStack, State

# End of def InitializeAll():

def InitializeState():

    # Initialize only the state related global variables (not the PrefixDir, 
    # Errors, Warnings or dictionary) to start processing a different file 
    # such as an svg linked from a fzp. 

    TagStack = [['empty', 0]]

    State={'lasttag': 'none', 'nexttag': 'none', 'lastvalue': 'none', 'image': 'none', 'noradius': [], 'KeyErrors': [], 'InheritedAttributes': []}

    State['InheritedAttributes'] = None

    return TagStack, State

# End of def InitializeState():

def ProcessArgs(Argv, Errors):

    # Process the input arguments on the command line. 

    logger.info ('Entering ProcessArgs\n')

    # Regex to match '.svg' to find svg files

    SvgExtRegex = re.compile(r'\.svg$', re.IGNORECASE)

    # Regex to match .fzp to find fzp files

    FzpExtRegex = re.compile(r'\.fzp$', re.IGNORECASE)

    # Regex to match 'part. to identify an unzipped fzpz file'

    PartRegex = re.compile(r'^part\.', re.IGNORECASE)

    # Regex to match 'part.filename' for substitution for both unix and windows.

    PartReplaceRegex = re.compile(r'^part\..*$|\/part\..*$|\\part\..*$', re.IGNORECASE)

    # Set the return values to the error return (really only FileType needs
    # to be done, but do them all for consistancy. Set PrefixDir and Path
    # to striing constants (not None) for the dir routines. 

    FileType = None

    DirProcessing = 'N'

    PrefixDir = ""

    Path = ""

    File = None

    SrcDir = None

    DstDir = None

    if len(sys.argv) == 3:

        # If we have two directories, one empty, process all the fzp files in 
        # the first directory in to the empty second directory, creating 
        # subdirectories as needed (but no backup files!) 

        DirProcessing, PrefixDir, Path, File, SrcDir, DstDir = ProcessDirArgs(Argv, Errors)

        if DirProcessing == 'Y':

            # Success, so set FileType to 'dir' from None to indicate no
            # error is present and to continue processing. 
    
            FileType = 'dir'

        # End of if (DirProcessing == 'Y':

        logger.info ('Exiting ProcessArgs\n')

        return FileType, DirProcessing, PrefixDir, Path, File, SrcDir, DstDir

    elif len(sys.argv) != 2:

        # No input file or too many arguments so print a usage message and exit.

        Errors.append('Usage: {0:s} filename.fzp or filename.svg or srcdir dstdir\n'.format(str(sys.argv[0])))

        logger.info ('Exiting ProcessArgs\n')

        return FileType, DirProcessing, PrefixDir, Path, File, SrcDir, DstDir

    else:

        # only a single file is present so arrange to process it.

        InFile = sys.argv[1]

        logger.debug ('ProcessArgs\n    Input filename\n     \'%s\'\n    isfile \'%s\'\n    svg    \'%s\'\n    fzp    \'%s\'\n', InFile, os.path.isfile(InFile), SvgExtRegex.search(InFile), FzpExtRegex.search(InFile))

        if (not os.path.isfile(InFile) or 
                (SvgExtRegex.search(InFile) == None and
                FzpExtRegex.search(InFile) == None)):

            # Input file isn't valid, return a usage message.

            Errors.append('Usage: {0:s} filename.fzp or filename.svg or srcdir dstdir\n\n\'{1:s}\'\n\neither isn\'t a file or doesn\'t end in .fzp or .svg\n'.format(str(sys.argv[0]),  str(InFile)))

            logger.info ('Exiting ProcessArgs\n')

            return FileType, DirProcessing, PrefixDir, Path, File, SrcDir, DstDir

        # End of if not os.path.isfile(InFile) and not SvgExtRegex.search(InFile) and not FzpExtRegex.search(InFile):

        Path = ''

        # First strip off the current path if any

        Path = os.path.dirname(InFile)

        if not Path:

            # No path present so set that

            Path = ''

        # End of if not Path:

        # and then get the filename 

        File = os.path.basename(InFile)

        if SvgExtRegex.search(File):

            # process a single svg file.

            FileType = 'SVG'

            logger.debug ('ProcessArgs\n    Found svg input file\n    \'%s\'\n    set FileType \'%s\'\n', InFile, FileType)

        else:

            # this is an fzp file of some kind so figure out which kind and 
            # set the appropriate path.

            Pat = PartRegex.search(File)

            logger.debug ('ProcessArgs\n    Found svg input file\n     \'%s\'\n    match \'%s\'\n', InFile, Pat)
    
            if PartRegex.search(File):
    
                # It is a part. type fzp, thus the svgs are in this same
                # directory named svg.image_type.filename so set FileType 
                # to fzpPart to indicate that.
    
                FileType = 'FZPPART'

                logger.debug ('ProcessArgs\n    Set filetype \'FZPPART\'\n')
    
            else:
    
                # This is a Fritzing internal type fzp and thus the svgs are in
                # svg/PrefixDir/image_type/filename.svg. So make sure we have a 
                # prefix directory on the input file. 

                # get the path from the input file. 

                Path = os.path.dirname(InFile)

                # and the file name

                File =  os.path.basename(InFile)
    
                SplitDir = os.path.split(Path)
    
                if SplitDir[1] == '' or SplitDir[1] == '.' or SplitDir[1] == '..':
    
                    Errors.append('Error 10: There must be a directory that is not \'.\' or \'..\' in the input name for\na fzp file in order to find the svg files.\n')
    
                    logger.info ('Exiting ProcessArgs no prefix dir error\n')
    
                    return FileType, DirProcessing, PrefixDir, Path, File, SrcDir, DstDir
    
                # End of if SplitDir[1] == '' or SplitDir[1] == '.' or SplitDir[1] == '..':
        
                Path = SplitDir[0]
        
                PrefixDir =  SplitDir[1]

                if PrefixDir == None:

                    # Make sure PrefixDir has a string value not None for the
                    # path routines.

                    PrefixDir = ""

                # End of if PrefixDir == None:
        
                # then so set FileType to fzpFritz to indicate that. 
    
                FileType = 'FZPFRITZ'
    
                logger.debug ('ProcessArgs\n    Set filetype \'FZPFRITZ\'\n')

            # End of if PartRegex.search(File):
    
        # End of if SvgExtRegex.search(File):

    # End of if len(sys.argv) == 3:

    logger.debug ('ProcessArgs\n    return\n     FileType \'%s\'\n     PrefixDir\n      \'%s\'\n     Path\n      \'%s\'\n     File\n      \'%s\'\n', FileType, PrefixDir, Path, File)

    logger.info ('Exiting ProcessArgs\n')

    return FileType, DirProcessing, PrefixDir, Path, File, SrcDir, DstDir

# End of def ProcessArgs(Argv, Errors):

def ProcessDirArgs(argv, Errors):

    logger.info ('Entering ProcessDirArgs\n')

    # Clear the return variables in case of error. 

    DirProcessing = 'N'

    PrefixDir = ''

    Path = ''

    File = None

    # Get the 2 directories from the input arguments.

    SrcDir = argv[1]

    DstDir = argv[2]

    # Check that the source is a directory

    if not os.path.isdir(SrcDir):

        Errors.append('Usage: {0:s} src_dir dst_dir\n\nsrc_dir {1:s} isn\'t a directory\n'.format(sys.argv[0], SrcDir))

        logger.info ('Exiting ProcessDirArgs src dir error\n')

        return DirProcessing, PrefixDir, Path, File, SrcDir, DstDir

    # End of if not os.path.isdir(SrcDir):

    # then that the dest dir is a directory

    if not os.path.isdir(DstDir):

        Errors.append('Usage: {0:s} src_dir dst_dir\n\ndst_dir {1:s} Isn\'t a directory\n'.format(sys.argv[0], DstDir))

        logger.info ('Exiting ProcessDirArgs dst dir error\n')

        return DirProcessing, PrefixDir, Path, File, SrcDir, DstDir

    # End of if not os.path.isdir(DstDir):

    # Both are directories so make sure the dest is empty

    if os.listdir(DstDir) != []:

        Errors.append('Error 13: dst dir\n\n{0:s}\n\nmust be empty and it is not\n'.format(str(DstDir)))

        logger.info ('Exiting ProcessDirArgs dst dir not empty error\n')

        return DirProcessing, PrefixDir, Path, File, SrcDir, DstDir

    # End of if os.listdir(DstDir) != []:

    # Now get the last element of the src path to create the fzp and svg
    # directories under the destination directory.

    SplitDir = os.path.split(SrcDir)

    logger.debug  ('ProcessDirArgs\n    SplitDir\n    \'%s\'\n', SplitDir)

    if SplitDir[1] == '' or SplitDir[1] == '.' or SplitDir[1] == '..':

        Errors.append('Error 10: There must be a directory that is not \'.\' or \'..\' in the input name for\na fzp file in order to find the svg files.\n')

        logger.info ('Exiting ProcessDirArgs no prefix dir error\n')

        return DirProcessing, PrefixDir, Path, File, SrcDir, DstDir

    else:
    
        Path = SplitDir[0]
    
        PrefixDir =  SplitDir[1]

        if PrefixDir == None:

            # Insure PrefixDir has a string value for the directory routines. 

            PrefixDir = ''

        # End of if PrefixDir == None:

        DstFzpDir = os.path.join(DstDir,PrefixDir) 

        try:    

            os.makedirs(DstFzpDir)

        except os.error as e:

            Errors.append('Error 14: Creating dir\n\n{0:s} {1:s} \({2:s}\)\n'.format(DstFzpDir), e.strerror, str(e.errno))

            logger.info ('Exiting ProcessDirArgs dir on error \'%s\'\n',e.strerror)

            return DirProcessing, PrefixDir, Path, File, SrcDir, DstDir

        # End of try:
    
        logger.debug ('ProcessDirArgs\n    mkdir\n     \'%s\'\n',DstFzpDir)
        
        # The fzp directory was created so create the base svg directory
        
        DstSvgDir = os.path.join(DstDir, 'svg')
    
        try:    
    
            os.makedirs(DstSvgDir)

        except os.error as e:

            Errors.append('Error 14: Creating dir\n\n{0:s} {1:s} \({2:s}\)\n'.format(DstFzpDir), e.strerror, str(e.errno))

            logger.info ('Exiting ProcessDirArgs dir on error\n    \'%s\'\n', e.strerror)

            return DirProcessing, PrefixDir, Path, File, SrcDir, DstDir

        # End of try:
    
        logger.debug ('ProcessDirArgs\n    mkdir\n     \'%s\'\n',DstSvgDir)
        
        DstSvgDir = os.path.join(DstSvgDir, PrefixDir)
    
        try:    
        
            os.makedirs(DstSvgDir)

        except os.error as e:

            Errors.append('Error 14: Creating dir\n\n{0:s} {1:s} \({2:s}\)\n'.format(DstFzpDir), e.strerror, str(e.errno))

            logger.info ('Exiting ProcessDirArgs dir on error\n    \'%s\'\n', e.strerror)

            return DirProcessing, PrefixDir, Path, File, SrcDir, DstDir

        # End of try:
    
        logger.debug ('ProcessDirArgs\n    mkdir\n     \'%s\'\n', DstSvgDir)
        
        # then the four svg direcotries
        
        SvgDir = os.path.join(DstSvgDir, 'breadboard')
    
        try:    
        
            os.makedirs(SvgDir)

        except os.error as e:

            Errors.append('Error 14: Creating dir\n\n{0:s} {1:s} \({2:s}\)\n'.format(DstFzpDir), e.strerror, str(e.errno))

            logger.info ('Exiting ProcessDirArgs dir on error\n    \'%s\'\n', e.strerror)

            return DirProcessing, PrefixDir, Path, File, SrcDir, DstDir

        # End of try:
    
        logger.debug('ProcessDirArgs\n     mkdir\n      \'%s\'\n', SvgDir)
        
        SvgDir = os.path.join(DstSvgDir, 'icon')
    
        try:    
        
            os.makedirs(SvgDir)

        except os.error as e:

            Errors.append('Error 14: Creating dir\n\n{0:s} {1:s} \({2:s}\)\n'.format(DstFzpDir), e.strerror, str(e.errno))

            logger.info ('Exiting ProcessDirArgs dir on error\n    \'%s\'\n', e.strerror)

            return DirProcessing, PrefixDir, Path, File, SrcDir, DstDir

        # End of try:
    
        logger.debug('ProcessDirArgs\n     mkdir\n      \'%s\'\n', SvgDir)
        
        SvgDir = os.path.join(DstSvgDir, 'pcb')
    
        try:    
        
            os.makedirs(SvgDir)

        except os.error as e:

            Errors.append('Error 14: Creating dir\n\n{0:s} {1:s} \({2:s}\)\n'.format(DstFzpDir), e.strerror, str(e.errno))

            logger.info ('Exiting ProcessDirArgs dir on error\n    \'%s\'\n', e.strerror)

            return DirProcessing, PrefixDir, Path, File, SrcDir, DstDir

        # End of try:
    
        logger.debug('ProcessDirArgs\n     mkdir\n      \'%s\'\n', SvgDir)
        
        SvgDir = os.path.join(DstSvgDir, 'schematic')
    
        try:    
        
            os.makedirs(SvgDir)

        except os.error as e:

            Errors.append('Error, Creating dir {0:s} {1:s} ({2:s})\n'.format(DstFzpDir), e.strerror, str(e.errno))

            logger.info ('Exiting ProcessDirArgs dir on error\n    \'%s\'\n', e.strerror)

            return DirProcessing, PrefixDir, Path, File, SrcDir, DstDir

        # End of try:
    
        logger.debug('ProcessDirArgs\n     mkdir\n      \'%s\'\n', SvgDir)

    # End of if SplitDir[1] == '' or SplitDir[1] == '.' or SplitDir[1] == '..':
        
    # If we get here we have a src and dst directory plus all the required new
    # dst directories so return all that to the calling routine. Set
    # DirProcessing  to 'Y' to indicate success.

    DirProcessing,  = 'Y'

    # Then set FileType to 'dir' from None to not cause a silent error exit
    # on return. 

    FileType = 'dir'

    logger.debug ('ProcessDirArgs\n     return\n      DirProcessing \'%s\'\n      PrefixDir\n       \'%s\'\n       Path\n       \'%s\'\n      File\n       \'%s\'\n      SrcDir\n        \'%s\'\n      DstDir\n        \'%s\'\n', DirProcessing, PrefixDir, Path, File, SrcDir, DstDir)

    logger.info ('Exiting ProcessDirArgs\n')

    return DirProcessing, PrefixDir, Path, File, SrcDir, DstDir

# End of def ProcessDirArgs(Argv, Errors):

def PopTag(Elem, TagStack, Level):

    # Determine from the current level if the value on the tag stack is still
    # in scope. If it is not, then remove the value from the stack.

    logger.info ('Entering PopTag XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug('PopTag\n    TagStack\n     %s\n', TagStack)

    Tag, StackLevel = TagStack[len(TagStack) - 1]

    # Because we may have exited several recusion levels before calling this
    # delete all the tags below the current level. 

    while Level != 0 and StackLevel >= Level:

        # Pop the last item from the stack.

        logger.debug('PopTag\n    popped Tag \'%s\'\n    StackLevel \'%s\'\n', Tag, StackLevel )

        TagStack.pop(len(TagStack) - 1)

        Tag, StackLevel = TagStack[len(TagStack) - 1]

    # End of while Level != 0 and StackLevel >= Level:

    logger.debug('PopTag exit\n    TagStack\n     %s\n', TagStack)

    logger.info ('Exiting PopTag XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def PopTag(Elem, TagStack, Level):

def BackupFilename(InFile, Errors):

    logger.info ('Entering BackupFilename\n')

    # First set the appropriate output file name None for an error condition.

    OutFile = None

    try:

        # Then try and rename the input file to InFile.bak

        os.rename (InFile, InFile + '.bak')

    except os.error as e:

        Errors.append('Error 15: Can not rename\n\n\'{0:s}\'\n\nto\n\n\'{1:s}\'\n\n\'{2:s}\'\n\n{3:s} ({4:s})\n'.format(str(InFile), str(InFile + '.bak'), str( e.filename), e.strerror, str(e.errno)))

        return InFile, OutFile

    # End of try:

    # If we get here, then the file was successfully renamed so change the 
    # filenames and return.

    OutFile = InFile

    InFile = InFile + '.bak'

    return InFile, OutFile

    logger.info ('Exiting BackupFilename\n')

# End of def BackupFilename(InFile, Errors):

def DupNameError(InFile, Id, Elem, Errors):

    logger.info ('Entering DupNameError XML source line %s\n', Elem.sourceline)

    logger.debug ('DupNameError Entry\n     InFile\n      \'%s\'\n     Id \'%s\'\n     Elem\n      %s\n      Errors\n       %s\n', InFile, Id, Elem, Errors)

    # Log duplicate name error 

    Errors.append('Error 16: File\n\'{0:s}\'\nAt line {1:s}\n\nId {2:s} present more than once (and should be unique)\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

    logger.info ('Exiting DupNameError XML source line %s\n', Elem.sourceline)

#End of def DupNameError(InFile, Id, Elem, Errors):

def DupNameWarning(InFile, Id, Elem, Warnings):

    logger.info ('Entering DupNameWarning XML source line %s\n', Elem.sourceline)

    logger.debug ('DupNameWarning Entry\n    InFile\n     \'%s\'\n    Id \'%s\'\n    Elem\n     %s\n    Errors\n     %s\n', InFile, Id, Elem, Warnings)

    # Log duplicate name warning

    Warnings.append('Warning 28: File\n\'{0:s}\'\nAt line {1:s}\n\nname {2:s} present more than once (and should be unique)\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

    logger.info ('Exiting DupNameWarning XML source line %s\n', Elem.sourceline)

#End of def DupNameWarning(InFile, Id, Elem, Warnings):

def CheckGroupConnector(InFile, Elem, Tag, Id, State, Errors):

    logger.info ('Entering CheckGroupConnector XML source line %s\n', Elem.sourceline)

    logger.debug ('CheckGroupConnector Entry\n   Tag      \'%s\'\n   Id      \'%s\'\n    attrib     \'%s\'\n', Tag, Id, Elem.attrib)

    LeadingConnectorRegex = re.compile(r'connector|pin',  re.IGNORECASE)

    AlreadyDoneConnectorRegex = re.compile(r'---')

    if Tag == 'g' and LeadingConnectorRegex.search(str(Id)) != None and not AlreadyDoneConnectorRegex.search(str(Id)) != None:

            # If the connector is a group and the name doesn't contain '---'
            # (indicating we have already converted it earlier) set up 
            # to change the group to the next circle drawing element. 

            logger.debug ('CheckGroupConnector detected\n   Tag      \'%s\'\n    Id     \'%s\'\n', Tag, Id)

            if ChangeConnectorAsGroup == "y":

                # Change the id and schedule a swap to the next drawing 
                # circle drawing element.

                State['ChangeGroupId'] = Id

                # then append a "---" to the current id attribute to make it 
                # unique (and identifiable so this is only done once!)

                Id += '---'

                logger.debug ('CheckGroupConnector Id modified\n    Id     \'%s\'\n', Id)

                Elem.set('id', Id)

            else:

                # Correction is not enabled, toss an Error.

                Errors.append('Error ?: File\n\'{0:s}\'\n\nAt line {1:s}\n\nId {2:s} is associated with a group, not a drawing element\n'.format(str(InFile), str(Elem.sourceline), str(Id)))


            #End of if ChangeConnectorAsGroup == "y":

    #End of if Tag == 'g' and LeadingConnectorRegex.search(str(Id)) != None:

    logger.info ('Exiting CheckGroupConnector XML source line %s\n', Elem.sourceline)

#End of def CheckGroupConnector(InFile, Elem, Tag, Id, State, Errors):

def ProcessTree(FzpType, FileType, InFile, OutFile, CurView, PrefixDir, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Debug, Level=0):

    # Potentially recursively process the element nodes of an lxml tree to 
    # aquire the information we need to check file integrity. This routine gets
    # called recursively to process child nodes (other routines get called for
    # leaf node processing). 

    # print the banner giving XML line number and input file. 

    EprintBanner(Elem, Level, InFile, Debug)

    logger.info ('Entering ProcessTree XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    # Start by checking for non whitespace charactes in tail (which is likely
    # an error) and flag the line if present. 

    Tail = Elem.tail

    logger.debug ('ProcessTree\n    Elem len \'%s\'\n    Tag \'%s\'\n    attributes\n     %s\n    text\n     \'%s\'\n    FzpType   \'%s\'\n    FileType  \'%s\'\n    InFile\n     \'%s\'\n    OutFile\n     \'%s\'\n    CurView \'%s\'\n    PrefixDir\n     \'%s\'\n    Errors\n     %s\n    Warnings\n     %s\n    Info\n     %s\n    TagStack\n     %s\n    State\n     %s\n    Tail\n     \'%s\'\n', len(Elem), Elem.tag, Elem.attrib, Elem.text, FzpType, FileType, InFile, OutFile, CurView, PrefixDir, Errors, Warnings, Info, TagStack, State, Tail)

    if Tail != None and not Tail.isspace(): 

        Warnings.append('Warning 2: File\n\'{0:s}\'\nAt line {1:s}\n\nText \'{2:s}\' isn\'t white space and may cause a problem\n'.format(str(InFile), str(Elem.sourceline), str(Tail)))
        
    # End of if not Elem.tail.isspace(): 

    if len(Elem):

        logger.debug ('ProcessTree\n    calling ProcessLeafNode\n     Tree Level %s\n     XML Source line %s\n     len \'%s\'\n     tag \'%s\'\n', Level, Elem.sourceline, len(Elem), Elem.tag)

        ProcessLeafNode(FzpType, FileType, InFile, OutFile, CurView, PrefixDir, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Debug, Level)

        logger.debug ('ProcessTree\n    process child nodes\n     Source line %s\n     len \'%s\'\n     Level %s\n     tag \'%s\'\n', Elem.sourceline, len(Elem), Level, Elem.tag)

        # This node has children so recurse down the tree to deal with them.

        for Elem in Elem:

            if len(Elem):

                # this node has children so process them (the attributes of 
                # this node will be processed by the recursion call and the 
                # level will be increased by one.) 

                ProcessTree(FzpType, FileType, InFile, OutFile, CurView, PrefixDir, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Debug, Level+1)

            else: # This particular element in the for loop is a leaf node.

                # As this is a leaf node proecess it again increasing the 
                # level by 1 before doing the call. 

                ProcessLeafNode(FzpType, FileType, InFile, OutFile, CurView, PrefixDir, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Debug, Level+1)

            # End of if len(Elem):

        # End of for Elem in Elem:

    else:

        # This is a leaf node and thus the level needs to be increased by 1
        # before we process it.  

        ProcessLeafNode(FzpType, FileType, InFile, OutFile, CurView, PrefixDir, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Debug, Level+1)

    # end of if len(Elem):

    logger.info ('Exiting ProcessTree XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def ProcessTree(FzpType, FileType, InFile, OutFile, CurView, PrefixDir, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Debug, Level=0):

def ProcessLeafNode(FzpType, FileType, InFile, OutFile, CurView, PrefixDir, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Debug, Level):

    # Process a leaf node.

    # print the banner giving XML line number and input file. 

    EprintBanner(Elem, Level, InFile, Debug)

    logger.info ('Entering ProcessLeafNode XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    # Start by checking for non whitespace charactes in tail (which is likely
    # an error) and flag the line if present. 

    Tail = Elem.tail

    logger.debug ('ProcessLeafNode\n    FzpType  \'%s\'\n    FileType \'%s\'\n    InFile\n     \'%s\'\n    CurView \'%s\'\n    Errors\n     %s\n    Tag \'%s\'\n    Attributes\n     \'%s\'\n    Tail\n     \'%s\'\n', FzpType, FileType, InFile,CurView, Errors, Elem.tag, Elem.attrib, Tail)

    if Tail != None and not Tail.isspace(): 

        Warnings.append('Warning 2: File\n\'{0:s}\'\nAt line {1:s}\n\nText  \'{2:s}\' isn\'t white space and may cause a problem\n'.format(str(InFile), str(Elem.sourceline), str(Tail)))
        
    # End of if not Elem.tail.isspace(): 

    # Select the appropriate leaf node processing routing based on the FileType
    # variable. 

    if FileType == 'FZPFRITZ' or  FileType == 'FZPPART':

        # If this is a fzp file do the leaf node processing for that. 

        ProcessFzpLeafNode(FzpType, FileType, InFile, CurView, PrefixDir, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)
        
    elif FileType == 'SVG':

        ProcessSvgLeafNode(FzpType, FileType, InFile, CurView, PrefixDir, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)

    else:

        if not 'SoftwareError' in State:

            # Report the software error once, then set 'SoftwareError' in State
            # to supress more messages and just return. It won't work right 
            # but the problem will at least be reported. 

            Errors.append('Error 19: File\n\'{0:s}\'\n\nFile type {1:s} is an unknown format (software error)\n'.format(str(InFile), str(FileType)))

            State['SoftwareError'] = 'y'

        # End of if not 'SoftwareError' in State:

    # End of if FileType == 'FZPFRITZ' or  FileType == 'FZPPART':

    logger.info ('Exiting ProcessLeafNode XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def ProcessLeafNode(FzpType, InFile, OutFile, CurView, PrefixDir, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Debug, Level):

def ProcessFzp(DirProcessing, FzpType, FileType, InFile, OutFile, CurView, PrefixDir, Errors, Warnings, Info, FzpDict, FilesProcessed, TagStack, State, Debug):

    logger.info ('Entering ProcessFzp\n')

    logger.debug ('ProcessFzp\n    FzpType  \'%s\'\n    FileType \'%s\'\n    InFile\n     \'%s\'\n    OutFile\n     \'%s\'\n    CurView \'%s\'\n    PrefixDir\n     \'%s\'\n    Errors:\n     %s\n    Warnings:\n     %s\n    Info:\n     %s\n    FzpDict:\n     %s\n    TagStack:\n     %s\n    State:\n     %s\n    Debug %s\n', FzpType, FileType, InFile, OutFile, CurView, PrefixDir, Errors, Warnings, Info, FzpDict, TagStack, State, Debug)

    # Parse the input document.

    Doc, Root = PP.ParseFile (InFile, Errors)

    logger.debug ('ProcessFzp\n    Return from parse\n    Doc:\n     \'%s\'\n', Doc)

    if Doc != None:

        # We have successfully parsed the input document so process it. Since
        # We don't yet have a CurView, set it to None.

        logger.debug ('ProcessFzp\n    Calling ProceesTree\n    Doc:\n     \'%s\'\n', Doc)

        # Set the local output file to a value in case we don't use it but 
        # do test it. 

        FQOutFile = None

        if OutFile == None:

            if Debug == 0:
    
                # No output file indicates we are processing a single fzp file
                # so rename the src file to .bak and use the original src file
                # as the output file (assuming the rename is successfull).
                # Use FQOutFile as the new file name to preserve the value
                # of OutFile for svg processing later. 
    
                InFile, FQOutFile = BackupFilename(InFile, Errors)
    
                logger.debug ('ProcessFzp\n    after BackupFilename\n    InFile\n      \'%s\'\n    FQOutFile\n      \'%s\'\n', InFile, FQOutFile)
    
                if FQOutFile == None:
    
                    # An error occurred, so just return to indicate that without
                    # writing the file (as there is no where to write it to).
    
                    logger.info ('Exiting ProcessFzp after rename error\n')
    
                    return
    
                # End of if FQOutFile == None:
    
            # End of if Debug == 0:

        else:

            # OutFile wasn't none, so set FQOutFile

            FQOutFile = OutFile
    
            logger.debug ('ProcessFzp\n    set output filename\n     FQOutFile\n      \'%s\'\n', InFile, FQOutFile)

        # End of if OutFile == None:

        # Now that we have an appropriate input file name, process the tree.
        # (we won't get here if there is a file rename error above!)

        logger.debug ('ProcessFzp\n    before ProcessTree\n    FileType \'%s\'\n    FQOutFile\n     \'%s\'\n', FileType, FQOutFile)

        ProcessTree(FzpType, FileType, InFile, FQOutFile, None, PrefixDir, Root, Errors, Warnings, Info, FzpDict, TagStack, State, Debug)

        # We are at the end of processing the fzp file so check that the
        # connector numbers are contiguous.

        FzpCheckConnectors(InFile, Root, FzpDict, Errors, Warnings, Info, State)        
        # We have an output file name so write the fzp file to it (or the 
        # console if Debug is > 0.)

        logger.debug ('ProcessFzp\    prettyprint\n    FileType \'%s\'\n    FQOutFile\n     \'%s\'\n', FileType, FQOutFile)

        PP.OutputTree(Doc, Root, FileType, InFile, FQOutFile, Errors, Warnings, Info, Debug)

        # Then process the associatted svg files from the fzp.

        logger.debug ('ProcessFzp\n    calling ProcessSvgsFromFzp\n     DirProcessing \'%s\'\n     FzpType \'%s\'\n     FileType \'%s\'\n     InFile\n      \'%s\'\n     OutFile     \'%s\'\n     PrefixDir\n      \'%s\'\n     Errors\n      %s\n     Warnings\n      %s\n     Info\n      %s\n     Debug %s\n', DirProcessing, FzpType, FileType, InFile, OutFile, PrefixDir, Errors, Warnings, Info, Debug)


        # Use the original value of OutFile to process the svgs. 

        ProcessSvgsFromFzp(DirProcessing, FzpType, FileType, InFile, OutFile, PrefixDir, Errors, Warnings, Info, FzpDict, FilesProcessed, Debug)

    # End of if Doc != None:
    
    logger.info ('Exiting ProcessFzp\n')

# End of def ProcessFzp(DirProcessing, FzpType, FileType, InFile, OutFile, CurView, PrefixDir, Errors, Warnings, Info, FzpDict, FilesProcessed, TagStack, State, Debug):

def ProcessSvgsFromFzp(DirProcessing, FzpType, FileType, InFile, OutFile, PrefixDir, Errors, Warnings, Info, FzpDict, FilesProcessed, Debug):

    # Process the svg files referenced in the FzpDict created from a Fritzing
    # .fzp file.

    logger.info ('Entering ProcessSvgsFromFzp\n')

    logger.debug ('ProcessSvgsFromFzp\n    DirProcessing \'%s\'\n    FzpType \'%s\'\n    FileType \'%s\'\n    InFile\n     \'%s\'\n    Outfile\n     \'%s\'\n    PrefixDir\n     \'\%s\'\n    FzpDict\n     %s\n', DirProcessing,  FzpType, FileType, InFile, OutFile, PrefixDir, FzpDict)

    # First we need to determine the directory structure / filename for the 
    # svg files as there are several to choose from: uncompressed parts which 
    # are all in the same directory but with odd prefixes of 
    # svg.layer.filename or in a Fritzing directory which will be 
    # ../svg/PrefixDir/layername/filename in 4 different directories. In
    # addition we may be processing a single fzp file (in which case the input
    # file needs a '.bak' appended to it), or directory of fzp files in which
    # case the '.bak' isn't needed. We will form appropriate file names from 
    # the InFile, OutFile and PrefixDir arguments to feed to the svg 
    # processing routine. 

    # Insure FQOutFile has a value

    FQOutFile = None

    # Get the path from the input and output files (which will be the fzp file 
    # at this point.) 

    InPath = os.path.dirname(InFile)

    # Record in FilesProcessed that we have processed this file name in case 
    # this is a directory operation. Get just the file name.

    BaseFile = os.path.basename(InFile)

    if 'processed.' + InFile in FilesProcessed:

        # If we have already processed it, flag an error (should not occur).

        Errors.append('Error 87: File\n\'{0:s}\'\n\nFile has already been processed (software error)\n'.format(str(InFile)))

        logger.info ('Exiting ProcessSvgsFromFzp on already processed error\n')

        return
        
    else:

        # Mark that we have processed this file. 

        FilesProcessed['processed.' + InFile] = 'y'

        logger.debug ('ProcessSvgsFromFzp\n    InFile\n     \'%s\'\n    marked as processed\n', InFile)

    # End of if 'processed.' + InFile in FilesProcessed:

    logger.debug ('ProcessSvgsFromFzp\n    InPath\n     \'%s\'\n    InFile\n     \'%s\'\n', InPath, InFile)

    if OutFile == None:

        OutPath = ''

    else:

        OutPath = os.path.dirname(OutFile)

    # End of if OutFile == None:

    logger.debug ('ProcessSvgsFromFzp\n    OutPath\n     \'%s\'\n    OutFile\n     \'%s\'\n', OutPath, OutFile)

    for CurView in FzpDict['views']:

        logger.debug ('ProcessSvgsFromFzp\n    Process View \'%s\'\n    FileType \'%s\'\n    FzpDict[views]\n     %s\n', CurView, FileType, FzpDict['views'])

        # Extract just the image name as a string from the list entry.

        Image = ''.join(FzpDict[CurView + '.image'])

        logger.debug ('ProcessSvgsFromFzp\n    CurView \'%s\'\n    Image\n     \'%s\'\n    FzpType \'%s\'\n    FileType \'%s\'\n    OutFile\n     \'%s\'\n', CurView, Image, FzpType, FileType, OutFile)

        # indicate we haven't seen an output file rename error. 

        OutFileError = 'n'

        if FzpType == 'FZPPART':

            # The svg is of the form svg.layer.filename in the directory 
            # pointed to by Path. So append a svg. to the file name and 
            # convert the '/' to a '.' to form the file name for processing. 

            Image = Image.replace(r"/", ".")

            if OutFile == None:

                # Single file processing so set the output filename and use 
                # FQOutFile.bak as the input. Again preserve the original 
                # value of OutFile for processing later svg files. 

                Image = Image.replace(r"/", ".")

                FQOutFile = os.path.join(InPath, 'svg.' + Image)

                # Set the input file from the output file in case debug is non
                # zero and we don't set a backup file. 

                FQInFile = FQOutFile

                if Debug == 0:

                    # If Debug isn't set then rename the input file and
                    # change the input file name. Otherwise leave it alone 
                    # (in this case OutFile is unused and output goes to the
                    # console for debugging.)

                    FQInFile, FQOutFile = BackupFilename(FQInFile, Errors)

                    if FQOutFile == None:

                        # an error occurred renaming the input file so set an
                        # an OutFileError so we don't try and process this 
                        # file as we have no valid output file to write it to. 

                        OutFileError = 'n'

                    # End of if FQOutFile == None:

                    logger.debug ('ProcessSvgsFromFzp\n    FQInFile\n     \'%s\'\n    FQOutFile\n     \'%s\'\n    OutFileError \'%s\'\n', FQInFile, FQOutFile, OutFileError)
                    
                # End of if Debug == 0:

            else:

                # dir to dir processing so set appropriate file names
                # (identical except for path)

                FQInFile = os.path.join(InPath, 'svg.' + Image)

                FQOutFile = os.path.join(OutPath, 'svg.' + Image)

            # End of if OutFile == None:

        elif FzpType == 'FZPFRITZ':

            # The svg is of the form path../svg/PrefixDir/layername/filename, 
            # so prepend the appropriate path and use that as the file name. 

            # First create the new end path as NewFile 
            # (i.e. '../svg/PrefixDir/Image') once, ready to append as needed.

            NewFile = '..'

            NewFile = os.path.join(NewFile, 'svg')

            logger.debug ('ProcessSvgsFromFzp\n    after add svg\n    NewFile\n     \'%s\'\n    PrefixDir\n     \'%s\'\n', NewFile, PrefixDir)

            NewFile = os.path.join(NewFile, PrefixDir)

            logger.debug ('ProcessSvgsFromFzp\n    after add PrefixDir\n    NewFile\n     \'%s\'\n', NewFile)

            NewFile = os.path.join(NewFile, Image)

            logger.debug ('ProcessSvgsFromFzp\n    after add Image\n    NewFile\n     \'%s\'\n', NewFile)

            # add the new end path to the end of the source path

            FQInFile = os.path.join(InPath, NewFile)

            if OutFile == None:

                if Debug == 0:

                    # If Debug isn't set then rename the input file and
                    # change the input file name. Otherwise leave it alone 
                    # (in this case OutFile is unused and output goes to the
                    # console for debugging.)

                    FQInFile, FQOutFile = BackupFilename(FQInFile, Errors)

                    logger.debug ('ProcessSvgsFromFzp\n    after rename\n    FQInfile\n     \'%s\'\n    FQOutFile\n     \'%s\'\n', FQInFile, FQOutFile)

                    if FQOutFile == None:

                        # an error occurred renaming the input file so set an
                        # an OutFileError so we don't try and process this 
                        # file as we have no valid output file to write it to. 

                        OutFileError = 'y'

                    # End of if FQOutFile == None:

                else:

                    # Insure FQOutFile has a value

                    FQOutFile = None

                # End of if Debug == 0:

            else:

                # dir to dir processing 

                FQInFile = os.path.join(InPath, NewFile)

                FQOutFile = os.path.join(OutPath, NewFile)


            # End of if OutFile == None:

        else:

            # Software error! Shouldn't ever get here.

            Errors.append('Error 19: File\n\'{0:s}\'\n\nFile type {1:s} is an unknown format (software error)\n'.format(str(InFile), str(FzpType)))

            # Don't try and process further as will likely crash due to unset
            # variables.

            continue

        # End of if FzpType == 'FZPPART':

        logger.debug ('ProcessSvgsFromFzp\n    FileType \'%s\'\n    Process\n    \'%s\'\n    to\n      \'%s\'\n', FileType, FQInFile, FQOutFile)

        if not os.path.isfile(FQInFile):

            # The file doesn't exist so flag an error,

            Errors.append('Error 20: File\n\'{0:s}\'\n\nDuring processing svgs from fzp, svg file doesn\'t exist\n'.format(str(FQInFile)))

        else:

            # Check for identical case in the filename (Windows doesn't care
            # but Linux and probably MacOS do)

            TmpPath = os.path.dirname(FQInFile)

            TmpFile = os.path.basename(FQInFile)

            # get the path from the input file

            logger.debug('ProcessSvgsFromFzp\n    TmpPath\n     \'%s\'\n    TmpFile\n     \'%s\'\n', TmpPath, TmpFile)

            if TmpPath == '':

                # Change an empty path to current directory to prevent os error

                TmpPath = './'

            # End of if TmpPath == '':

            if not TmpFile in os.listdir(TmpPath):

                # File system case mismatch error. 

                logger.debug('ProcessSvgsFromFzp\n    dir names\n     \'%s\'\n    InFile\n     \'%s\'\n    OutFile\n     \'%s\'\n    FzpType \'%s\'\n', os.listdir(TmpPath), InFile, OutFile, FzpType)

                if OutFile == None or DirProcessing == 'Y':

                    # Then InFile is the fzp file.

                    Errors.append('Error 21: Svg file\n\n\'{0:s}\'\n\nHas a different case in the file system than in the fzp file\n\n\'{1:s}\'\n'.format(str(FQInFile), str(InFile)))

                else:

                    # Then OutFile is the fzp file (InFile will have .bak 
                    # appended which we don't want.)

                    Errors.append('Error 21: Svg file\n\n\'{0:s}\'\n\nHas a different case in the file system than in the fzp file\n\n\'{1:s}\'\n'.format(str(FQInFile), str(OutFile)))

                # End of if OutFile == None or DirProcessing == 'Y':

            # End of if not TmpFile in os.listdir(TmpPath):

            if OutFileError == 'n':

                if CurView == 'iconView':

                    # If this is iconview, don't do processing as we aren't 
                    # going to check anything and sometimes the breadboard 
                    # svg is reused which will cause a warning and replace 
                    # the .bak file (which is undesirable). We do however
                    # want to have the output file even though we didn't
                    # do anything to it, so do copy the infile to the outfile
                    # (so as to leave both the input file and a new outfile)
                    # if FQOutFile isn't None.

                    if FQOutFile != None and Debug == 0:

                        # If Debug isn't 0, the file names are the same and 
                        # will cause an exception during the copy. 

                        copyfile(FQInFile, FQOutFile)

                    # End of if FQOutFile != None:

                    logger.debug ('ProcessSvgsFromFzp\n    Process View \'%s\' skipping iconview\n', CurView)

                    continue

                # End of if CurView == 'iconview':

                # Mark that we have processed this file in case this is 
                # directory processing of part.files to avoid double 
                # processing the svg files.

                if 'processed.' + FQInFile in FilesProcessed:

                    # Already seen, may occur if svgs are shared, so warn as 
                    # the .bak file will be overwritten and the user needs to 
                    # know that 

                    logger.debug('ProcessSvgsFromFzp\n    FQInFile\n     \'%s\'\n    Warning 29 issued. FilesProcessed \'%s\'\n', FQInFile, FilesProcessed)

                    Warnings.append('Warning 29: File\n\'{0:s}\'\n\nProcessing view {1:s}, File {2:s}\nhas already been processed\nbut will be processed again as part of this fzp file in case of new warnings.\n'.format(str(InFile), str(CurView), str(FQInFile)))

                else:

                    logger.debug('ProcessSvgsFromFzp\n    FQInFile\n     \'%s\'\n     marked as processed.\n', FQInFile)

                    FilesProcessed['processed.' + FQInFile] = 'y'

                # End of if 'processed.' + FQInFile in FilesProcessed:

                # If the file exists and there was not a file rename error then
                # go and try and process the svg (set the FileType explicitly 
                # to svg), but first reset the state variables for the new 
                # file (but not Errors, Warnings, FzpDict or CurView).

                TagStack, State = InitializeState()

                ProcessSvg(FzpType, 'SVG', FQInFile, FQOutFile, CurView, PrefixDir,  Errors, Warnings, Info, FzpDict, FilesProcessed, TagStack, State, Debug)

                # We are finished processing this file from an fzp, and it 
                # isn't the icon file (which doesn't have connectors) because
                # that was caught above, so check the connectors on this svg 
                # file to make sure they are all present.

                logger.debug  ('ProcessSvgsFromFzp\n    Checking connectors for file\n     \'%s\'\n', InFile)

                for Connector in FzpDict['connectors.fzp.' + CurView]:

                    # Check that the connector is in the svg and error if not. 

                    logger.debug  ('ProcessSvgsFromFzp\n    Checking connector \'%s\'\n', Connector)

                    if not 'connectors.svg.' + CurView in FzpDict:

                        logger.debug  ('ProcessSvgsFromFzp\n    no connectors found\n')

                        if not 'pcbnoconnectorwarning' in State:

                            Errors.append('Error 17: File\n\'{0:s}\'\n\nNo connectors found for view {1:s}.\n'.format(str(InFile), str(CurView)))

                            # Only output the message once.

                            State['pcbnoconnectorwarning'] = 'y'

                        # End of if not 'pcbnoconnectorwarning' in State:

                    elif not Connector in FzpDict['connectors.svg.' + CurView]:

                        logger.debug  ('ProcessSvgsFromFzp\n    Connector \'%s\' missing\n', Connector)

                        Errors.append('Error 18: File\n\'{0:s}\'\n\nConnector {1:s} is in the fzp file but not the svg file. (typo?)\n\nsvg {2:s}\n'.format(str(InFile), str(Connector), str(FQInFile)))

                    # End of if not 'connectors.svg.' + CurView in FzpDict:
                
                # End of `for Connector in FzpDict['connectors.fzp.' + CurView]:

                if CurView == 'schematicView' and 'subparts' in FzpDict:

                    # We have subparts, so now having processed the entire svg
                    # make sure we have found all the connectors we should have.

                    logger.debug('ProcessSvgsFromFzp\n    Subpart start\n    FzpDict[\'subparts\']\n      %s\n',FzpDict['subparts'])

                    for SubPart in FzpDict['subparts']:

                        # Get the list of subparts from the fzp.

                        logger.debug('ProcessSvgsFromFzp\n    Subpart before loop\n    SubPart\n     \'%s\'\n    FzpDict[SubPart + \'.subpart.cons\']\n     \'%s\'\n    FzpDict[SubPart + \'.svg.subparts\']\n     \'%s\'\n',SubPart, FzpDict[SubPart + '.subpart.cons'], FzpDict[SubPart + '.svg.subparts'])

                        for SubpartConnector in FzpDict[SubPart + '.subpart.cons']:

                            logger.debug('ProcessSvgsFromFzp\n    processing SubpartConnector \'%s\'\n',SubpartConnector)

                            if not SubPart + '.svg.subparts' in FzpDict:

                                # No connectors in svg error. 

                                logger.debug('ProcessSvgsFromFzp\n    no connectors in svg\n    SubPart\n     \'%s\'\n   SubpartConnector \'%s\'\n',SubPartConnector, SubPart)

                                Errors.append('Error 78: Svg file\n\n\'{0:s}\'\n\nWhile looking for {1:s}, Subpart {2:s} has no connectors in the svg\n'.format(str(FQInFile), str(OutFile), str(SubpartConnector), str(SubPart)))

                            elif not SubpartConnector in FzpDict[SubPart + '.svg.subparts']:

                                # Throw an error if one of the connectors we 
                                # should have isn't in the svg. 

                                logger.debug('ProcessSvgsFromFzp\n    Error 79 no connector\n     \'%s\'\n    in svg\n    Subpart \'%s\'\n     SubpartConnector\n     \'%s\'\n', SubPart, SubpartConnector)

                                Errors.append('Error 79: Svg file\n\n\'{0:s}\'\n\nSubpart {1:s} is missing connector {2:s} in the svg\n'.format(str(FQInFile), str(SubPart), str(SubpartConnector)))

                            # if not SubPart + '.svg.subparts' in FzpDict:

                        # End of for SubpartConnector in FzpDict[SubPart + '.subpart.cons']:

                    # End of for SubPart in FzpDict['subparts']:

                # End of if CurView == 'schematicView' and 'subparts' in FzpDict:

            # End of if OutFileError == 'n':

        # End of if not os.path.isfile(FQInFile):

    # End of for CurView in FzpDict['views']:

    logger.info ('Exiting ProcessSvgsFromFzp\n')

#End of def ProcessSvgsFromFzp(FzpType, FileType, InFile, OutFile, PrefixDir, Errors, Warnings, Info, FzpDict, FilesProcessed, Debug):

def ProcessFzpLeafNode(FzpType, FileType, InFile, CurView, PrefixDir, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    # We are processing an fzp file so do the appropiate things for that. 

    logger.info ('Entering ProcessFzpLeafNode XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug ('ProcessFzpLeafNode\n    FileType \'%s\'\n    Infile\n     \'%s\'\n', FzpType, InFile)

    # Regex to detect comment lines (ignoring case)

    CommentRegex = re.compile(r'^<cyfunction Comment at',re.IGNORECASE)

    # Mark in the dictionary that we have processed the fzp file so when we 
    # process an associated svg we know if the fzp data is present in the dict.

    if not 'fzp' in FzpDict:

        # not here yet so set it. 

        FzpDict['fzp'] = 'y'

    # End of if not 'fzp' in FzpDict:

    # Check for a comment line and return if so. 

    Tag = Elem.tag

    logger.debug ('ProcessFzpLeafNode\n    Tag \'%s\'\n', Tag)

    if CommentRegex.match(str(Tag)):

        # Ignore comment lines so as to not complain about lack of tags.

        logger.debug ('ProcessFzpLeafNode\n    Comment line ignored\n ')

        return

    # End of if CommentRegex.match(str(Tag)):

    # Then check for any of Fritzing's tags.

    FzpTags(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, Level)

    StackTag, StackLevel = TagStack[len(TagStack) - 1]
 
    logger.debug ('ProcessFzpLeafNode\n    StackTag\n     \'%s\'\n    StackLevel \'%s\'\n', StackTag, StackLevel)

    if len(TagStack) == 2 and StackTag == 'module':

        # If the tag stack is only 'module' check for a moduleid if this
        # is a dup that will be caught in FzpmoduleId via the dictionary.

        FzpmoduleId(FzpType, InFile, Elem, Errors, Warnings, Info, FzpDict, State, Level)
   
        # Set where we are and what we expect to see next.
 
        State['lasttag'] = 'module'

        State['nexttag'] = 'views'

    elif len(TagStack) == 2:

        Errors.append('Error 22: File\n\'{0:s}\'\n\nAt line {1:s}\n\nNo ModuleId found in fzp file\n'.format(str(InFile), str(Elem.sourceline)))

    # End of if len(TagStack) == 2 and StackTag == 'module':

    # If TagStack is 3 or more and is 'module', 'views' (i.e. TagStack[2] is
    # 'views', so first get TagStack[2] in to BaseTag.)

    if len(TagStack) > 2:

        BaseTag, StackLevel = TagStack[2]

    else:

        # We aren't yet that far in the file so set BaseTag to ''

        BaseTag = ''

    # End of If len TagStack > 2:
 
    logger.debug ('ProcessFzpLeafNode\n    moduleid BaseTag \'%s\'\n    TagStack len \'%s\'\n', BaseTag, len(TagStack))

    if len(TagStack) > 2 and BaseTag == 'views':

        logger.debug ('ProcessFzpLeafNode\n    start processing views\n')

        # As long as we haven't cycled to 'connectors' as the primary tag,
        # keep processing views tags.
   
        if not 'views' in FzpDict:

            # If we don't have a views yet create an empty one. 

            logger.debug ('ProcessFzpLeafNode\n    create \'views\' in dictionary\n')

            FzpDict['views'] = []

        # End of if not 'views' in FzpDict:

        if State['lasttag'] == 'module':

            # Note that we have seen the 'views' tag now. 

            State['lasttag'] = 'views'

            # notw we are looking for a viewname next.

            State['nexttag'] = 'viewname'

        # End of if State['lasttag'] == 'module':

        # We are currently looking for file and layer names so do that. 

        if len(TagStack) > 3:

            # We have already dealt with the TagStack 3 ('views') case above 
            # so only call FzpProcessViewsTs3 for 4 or higher 
            # (viewname, layers and layer). 

            FzpProcessViewsTs3(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)

        # End of len(TagStack) > 3:

    # End of if len(TagStack) > 2 and BaseTag == 'views':

    # Again BaseTag is TagStack[2] (the current tag may be different.)

    if len(TagStack) == 3 and BaseTag == 'connectors':

        # process the connectors

        logger.debug ('ProcessFzpLeafNode\n    Start processing connectors\n')

        # By the time we get here we should have all the views present so check
        # and make sure we have at least one view and warn about any that are
        # missing or have unexpected names (no views is an error!). 

        if not 'FzpCheckViews' in State:

            logger.debug ('ProcessFzpLeafNode\n    Set State[\'FzpCheckViews\'] = []\n    then call FzpCheckViews\n     XML Source line %s\n     State \'%s\'\n ', Elem.sourceline, State)

            # Indicate we have executed the check so it is only done once.

            State['FzpCheckViews'] = []

            FzpCheckViews(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)

        # End of if not FzpCheckViews in State:

        # Set the appropriate states for connectors.

        State['lasttag'] = 'connectors'

        State['nexttag'] = 'connector'

    # End of if len(TagStack) == 3 and BaseTag == 'connectors':

    # Again BaseTag is TagStack[2] (the current tag may be different.)

    if len(TagStack) > 3 and  BaseTag == 'connectors':

        logger.debug ('ProcessFzpLeafNode\n    TagStack > 3 continue processing connectors\n')

        # We have dealt with TagStack = 3 'connectors' above so only do 
        # 4 and higher by calling FzpProcessConnectorsTs3.

        FzpProcessConnectorsTs3(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)

    # End of if len(TagStack) > 3 and  BaseTag == 'connectors':

    # If TagStack is 3 and is 'module', 'buses' 

    # Again BaseTag is TagStack[2] (the current tag may be different.)

    if len(TagStack) == 3 and BaseTag == 'buses':

        logger.debug ('ProcessFzpLeafNode\n    start processing buses\n')

        # Since some parts have an empty bus tag at the end of the fzp
        # don't check the previous state (but do set the new state in case
        # this really is a bus definition.)

        State['lasttag'] = 'buses'

        State['nexttag'] = 'bus'

        if not 'buses' in FzpDict:

            # If we don't have a buses yet create an empty one. 

            logger.debug ('ProcessFzpLeafNode\n    create \'buses\' in dictionary\n')

            FzpDict['buses'] = []

        # End of if not 'buses' in FzpDict:

        logger.debug ('ProcessFzpLeafNode\n    TagStack len \'%s\'\n', len(TagStack))

    # End of if len(TagStack) == 3 and BaseTag == 'buses':

    # Again BaseTag is TagStack[2] (the current tag may be different.)

    if len(TagStack) > 3 and  BaseTag == 'buses':

        logger.debug ('ProcessFzpLeafNode\n    TagStack > 3, continue processing buses\n')

        # Go and process the bus tags

        FzpProcessBusTs3(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)

    # End of if len(TagStack) > 3 and  BaseTag == 'buses':

    logger.debug ('ProcessFzpLeafNode\n    before subparts processing\n    TagStack len \'%s\'\n    TagStack\n     %s\n', len(TagStack), TagStack)

    # Again BaseTag is TagStack[2] (the current tag may be different.)

    if len(TagStack) == 3 and BaseTag == 'schematic-subparts':

        logger.debug ('ProcessFzpLeafNode\n    start sub parts processing\n')

        if 'buses' in FzpDict:

            # A bus has already been defined and won't allow schematic parts.

            logger.debug ('ProcessFzpLeafNode\n    subparts found but bus defined\n')

            if 'bus_defined' in FzpDict:

                if 'bus_defined' == 'n':

                    Errors.append('Error 23: File\n\'{0:s}\'\nAt line {1:s}\n\nA bus is already defined, schematic parts won\'t work with busses\n'.format(str(InFile), str(Elem.sourceline)))

                    # Mark that we have flagged the error so we don't repeat it.

                    FzpDict['bus_defined'] = 'y'

                # End of if 'bus_defined' == 'n':

            # End of if 'bus_defined' in FzpDict:
    
        else:
    
            if not 'schematic-subparts' in FzpDict:
    
                # If we don't have a schematic-subparts yet create an empty one. 
                logger.debug ('ProcessFzpLeafNode\n    create \'schematic-subparts\' in dictionary\n')
    
                FzpDict['schematic-subparts'] = []
    
            # End of if not 'schematic-subparts' in FzpDict:

        # End of if 'buses' in FzpDict:

        # Set State for where we are and what we expect next.

        State['lasttag'] = 'schematic-subparts'

        State['nexttag'] = 'subpart'

    # End of if len(TagStack) == 3 and BaseTag == 'schematic-subparts':

    # Again BaseTag is TagStack[2] (the current tag may be different.)

    if len(TagStack) > 3 and  BaseTag == 'schematic-subparts':

        logger.debug ('ProcessFzpLeafNode\n    len TagStack > 3 continue processing subparts\n    TagStack\n     %s\n',TagStack)

        # Process the schematic-subparts section of the fzp.

        if not 'bus_defined' in FzpDict:

            # But only if there isn't a bus already defined.
    
            FzpProcessSchematicPartsTs3(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)

        else:

            logger.debug ('ProcessFzpLeafNode\n    Skipped subpart processing due to bus defined\n')

        # End of if not 'bus_defined' in FzpDict:

    # End of if len(TagStack) > 3 and  BaseTag == 'schematic-subparts':
    
    logger.debug ('ProcessFzpLeafNode\n    exiting\n    State\n     %s\n', State)

    logger.info ('Exiting ProcessFzpLeafNode XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def ProcessFzpLeafNode(FzpType, FileType, InFile, CurView, PrefixDir, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def FzpTags(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, Level):

    # Looks for and log any of the Fritzing tags. We will check the dictionary
    # to make sure the appropriate tag has been seen when processing layer and
    # pin information later. 

    logger.info ('Entering FzpTags XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    Tag = Elem.tag

    if Tag != None:

        # If we have a tag go and adjust the tag stack if needed. 

        PopTag(Elem, TagStack, Level)

    # End of if Tag != None:

    logger.debug ('FzpTags\n    Tag \'%s\'\n    attributes\n     %s\n    TagStack\n     %s\n',Elem.tag, Elem.attrib, TagStack)

    # Check the single per file tags (more than one is an error)

    if Tag in ['module', 'version', 'author', 'title', 'label', 'date', 'tags', 'properties', 'taxonomy', 'url', 'schematic-subparts', 'buses']:

        logger.debug ('FzpTags\n    XML Source line %s\n    Level %s\n    Tag \'%s\'\n', Elem.sourceline, Level, Tag)

        # Record the tag in the dictionary (and check for more than one!)

        if Tag in FzpDict:

            logger.debug ('FzpTags\n    Dup Tag value\n    Source line %s\n    Level %s\n    tag \'%s\'\n', Elem.sourceline, Level, Tag)

            # If its already been seen flag an errror.

            Errors.append('Error 24: File\n\'{0:s}\'\nAt line {1:s}\n\nMore than one copy of Tag {2:s}\n'.format(str(InFile), str(Elem.sourceline), str( Tag)))
        
        # End of if Tag in FzpDict:
        
        FzpDict[Tag] = [Tag]

    # End of if Tag in ['module', 'version', 'author', 'title', 'label', 'date', 'tags', 'properties', 'taxonomy', 'url', 'schematic-subparts', 'buses']:

    # For the repeating tags: views, iconView, layers, breadboardView,
    # schematicView, pcbView, connector, subpart, bus and the non repeating 
    # tags connectors, schematic-subparts, buses stick them in a stack
    # so we know where we are when we come across an attribute.

    if Tag in ['module', 'version', 'author', 'title', 'label', 'date', 'tags', 'tag', 'properties', 'property', 'spice', 'taxonomy', 'description', 'url', 'line', 'model', 'views', 'iconView', 'layers', 'layer', 'breadboardView', 'schematicView', 'pcbView', 'connectors', 'connector', 'p', 'buses', 'bus', 'nodeMember', 'schematic-subparts', 'subpart']:

        # Push the Id and Level on to the tag stack.

        TagStack.append([Tag, Level])

        logger.debug ('FzpTags End\n    found  Tag \'%s\'\n    XML source line %s\n    Level %s\n    TagStack len \'%s\'\n    TagStack\n     %s\n', Tag, Elem.sourceline, Level, len(TagStack), TagStack)

    else:
        
        logger.debug ('FzpTags End\n    didn\'t find  Tag \'%s\'\n    XML source line %s\n    Level %s\n   TagStack len \'%s\'\n    TagStack %s\n', Tag, Elem.sourceline, Level, len(TagStack), TagStack)

    # End of if Tag in ['module', 'version', 'author', 'title', 'label', 'date', 'tags', 'tag', 'properties', 'property', 'spice', 'taxonomy', 'description', 'url', 'line', 'model', 'views', 'iconView', 'layers', 'layer', 'breadboardView', 'schematicView', 'pcbView', 'connectors', 'connector', 'p', 'buses', 'bus', 'nodeMember', 'schematic-subparts', 'subpart']:

    logger.info ('Exiting FzpTags XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def FzpTags(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, Level):

def FzpmoduleId(FzpType, InFile, Elem, Errors, Warnings, Info, FzpDict, State, Level):

    logger.info ('Entering FzpmoduleId XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    LeadingPartRegex = re.compile(r'^part\.', re.IGNORECASE)

    TrailingFzpRegex = re.compile(r'\.fzp$', re.IGNORECASE)

    # Check to see if we have a moduleId and flag an error if not, because 
    # one is required. 
    
    ModuleId =  Elem.get('moduleId')

    logger.debug('FzpmoduleId\n    ModuleId \'%s\'\n',ModuleId)

    # Make a local copy of the base file name (without its path if any)
    # as we may make changes to it that we don't want to propigate. 

    File = os.path.basename(InFile)

    # Remove the trailing .bak if it is present.

    File = re.sub(r'\.bak$','', File)

    if ModuleId == None:

        if not 'moduleId' in FzpDict:

            Errors.append('Error 22: File\n\'{0:s}\'\n\nAt line {1:s}\n\nNo ModuleId found in fzp file\n'.format(str(InFile), str(Elem.sourceline)))

        # End of if not 'moduleId' in FzpDict:

        logger.debug('FzpmoduleId\n    no moduleId\n')

    else:
            
        # We have found a moduleId so process it. Check that it matches the 
        # input filename without the fzp, and there is only one of them. Look 
        # for (and warn if absent) a referenceFile and fritzingVersion as well.

        # Check if this is a breadboard file and mark that in State if so.

        if File in ['breadboard.fzp', 'breadboard2.fzp']:

            State['breadboardfzp'] = 'y'

        # End of if File in ['breadboard.fzp', 'breadboard2.fzp']:

        logger.debug('FzpmoduleId\n    FzpType \'%s\'\n    InFile\n     \'%s\'\n    File\n     \'%s\'\n', FzpType, InFile,  File)

        if FzpType == 'FZPPART':

            # This is a part. type file so remove the "part." from the
            # file name before the compare.

            File = LeadingPartRegex.sub('', File)

            logger.debug('FzpmoduleId\n    removed \'part.\' to leave\n     \'%s\'\n', File)

        # End of if FzpType == 'FZPPART':

        # Then remove the trailing ".fzp"

        File = TrailingFzpRegex.sub('', File)

        logger.debug('FzpmoduleId\n    removed \'.fzp\' to leave\n     \'%s\'\n', File)

        if File != ModuleId:

            Warnings.append('Warning 3: File\n\'{0:s}\'\nAt line {1:s}\n\nModuleId \'{2:s}\'\n\nDoesn\'t match filename\n\n\'{3:s}\'\n'.format(str(InFile), str(Elem.sourceline), str(ModuleId), str(File)))
            
        # End of if File != ModuleId:
    
        if 'moduleId' in FzpDict:
        
            Errors.append('Error 25: File\n\'{0:s}\'\nAt line {1:s}\n\nMultiple ModuleIds found in fzp file\n'.format(str(InFile), str(Elem.sourceline)))

            FzpDict['moduleId'].append(ModuleId)

        else:

            # Otherwise create a new key with the value as a single element
            # list (so we can append if we find another.)

            FzpDict['moduleId'] = [ModuleId]

            logger.debug('FzpmoduleId\n    Added ModuleId\n     \'%s\'\n    to FzpDict\n', ModuleId)

        # End of if 'ModuleId' in FzpDict:

    # End of if ModuleId == None:

    # Now look for a reference file.

    RefFile =  Elem.get('referenceFile')

    logger.debug('FzpmoduleId\n    RefFile\n     \'%s\'\n    File\n     \'%s\'\n', RefFile, File)
    
    if RefFile == None:

        Warnings.append('Warning 4: File\n\'{0:s}\'\nAt line {1:s}\n\nNo referenceFile found in fzp file\n'.format(str(InFile), str(Elem.sourceline)))

    else:

        if 'referenceFile' in FzpDict:

            Warnings.append('Warning 5: File\n\'{0:s}\'\nAt line {1:s}\n\nMultiple referenceFile found in fzp file\n'.format(str(InFile), str(Elem.sourceline)))

            FzpDict['referenceFile'].append(RefFile)

        else:

            # Otherwise create a new key with the value as a single element
            # list (so we can append if we find another.)

            FzpDict['referenceFile'] = [RefFile]

        # End of if 'referenceFile' in FzpDict:

        if RefFile != File + '.fzp':

            # The reference file doesn't match the input file name which it 
            # should.

            Warnings.append('Warning 6: File\n\'{0:s}\'\nAt line {1:s}\n\nReferenceFile name \n\n\'{2:s}\'\n\nDoesn\'t match fzp filename\n\n\'{3:s}\'\n'.format(str(InFile), str(Elem.sourceline), str(RefFile), str(File + '.fzp')))

        # End of if RefFile != File + '.fzp':

    # End of if RefFile == None:

    # Then check for a Fritzing version

    Version =  Elem.get('fritzingVersion')

    if Version == None:

            Warnings.append('Warning 7: File\n\'{0:s}\'\nAt line {1:s}\n\nNo Fritzing version in fzp file\n'.format(str(InFile), str(Elem.sourceline)))

    else:

        # There is a Fritzing version so record it.
            
        if 'fritzingVersion' in FzpDict:
        
            Warnings.append('Warning 8: File\n\'{0:s}\'\nAt line {1:s}\n\nMultiple fritzingVersion found in fzp file\n'.format(str(InFile), str(Elem.sourceline)))

            FzpDict['fritzingVersion'].append(Version)

        else:

            # Otherwise create a new key with the value as a single element
            # list (so we can append if we find another.)

            FzpDict['fritzingVersion'] = [Version]

        # End of if 'fritzingVersion' in FzpDict:

    # End of if Version == None:

    logger.info ('Exiting FzpmoduleId XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def FzpmoduleId(FzpType, InFile, Elem, Errors, Warnings, Info, FzpDict, State, Level):

def FzpProcessViewsTs3(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    # We are in the views grouping so find and record our groupnames, layerIds
    # and filenames in the input stream. 

    logger.info ('Entering FzpProcessViewsTs3 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    StackTag, StackLevel = TagStack[len(TagStack) - 1]

    logger.debug ('FzpProcessViewsTs3\n    StackTag \'%s\'\n    State\n %s\n    TagStack\n     %s\n    attributes %s\n', StackTag, State, TagStack, Elem.attrib)

    # TagStack length of 3 ('empty', 'module', 'views') is what tripped the 
    # call to this routine so we start processing at TagStack length 4 in 
    # this large case statement which trips when it finds the correct state 
    # (or complains if it finds an incorrect state due to errrorS.)

    if len(TagStack) == 4:

        # TagStack should be 'module', 'views', view name so check and process
        # the view name. Check that State['nexttag'] is 'viewname' or 'layer'
        # (the end of a previous entry) to indicate that is what we are 
        # expecting at this time. 

        if State['nexttag'] != 'viewname' and State['nexttag'] != 'layer':

            Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, expected tag {2:s} not a view name\n'.format(str(InFile), str(Elem.sourceline), str(State['nexttag'])))
            
        # End of if State['nexttag'] != 'viewname' and State['nexttag'] != 'layer':

        # Get the latest tag value from StackTag in to View

        View = StackTag

        if View == 'layers':

            # If it is 'layers' (indicating we don't have a valid view),  
            # set View to none so it has a value (even though its wrong) and 
            # the state is unrecoverable. So as we have noted the error just 
            # proceed although it will likely cause an error cascade. 

            View = 'none'

            logger.debug ('FzpProcessViewsTs3\n    missing view, View set to none\n')

            Errors.append('Error 27: File\n\'{0:s}\'\nAt line {1:s}\n\nView name missing\n'.format(str(InFile), str(Elem.sourceline)))

        # End of if View == 'layers':
            
        if View in ['iconView', 'breadboardView', 'schematicView', 'pcbView']:

            # View value is legal so process it. 

            if not 'views' in FzpDict:

                # views doesn't exist yet so create it and add this view.

                FzpDict['views'] = [View]

                logger.debug ('FzpProcessViewsTs3\n    Created dict entry \'views\' and added\n      \'%s\'\n', View)

            else:

                if View in FzpDict['views']:

                    # Error, already seen.

                    Errors.append('Error 28: File\n\'{0:s}\'\nAt line {1:s}\n\nMultiple view tags {2:s} present, ignored\n'.format(str(InFile), str(Elem.sourceline), str(View)))

                    logger.debug ('FzpProcessViewsTs3\n    error, view \'%s\' already present\n', View)

                else: 

                    # Add this view to the list. 
                    
                    FzpDict['views'].append(View)

                    logger.debug ('FzpProcessViewsTs3\n    appended View \'%s\' to dict entry views\n', View)

                # End of if View in FzpDict['views']:

            # End of if not 'views' in FzpDict:

        else:

            Errors.append('Error 29: File\n\'{0:s}\'\nAt line {1:s}\n\nView tag {2:s} not recognized (typo?)\n'.format(str(InFile), str(Elem.sourceline), str(View)))

            logger.debug ('FzpProcessViewsTs3\n    error View \'%s\' not recognized\n', View)

        # End of if View in ['iconView', 'breadboardView', 'schematicView', 'pcbView']:

        # Now set State['lastvalue'] to View to keep state for the next entry 

        State['lastvalue'] = View

        # Set State['nexttag'] to the next tag we expect to see for the next entry

        State['nexttag'] = 'layers'

        logger.debug ('FzpProcessViewsTs3\n    Set State[\'views\'] to \'%s\'\n   and State[\'tag\'] to \'%s\'\n', State['lastvalue'], State['nexttag'])

    elif len(TagStack) == 5 and StackTag == 'layers':

        if State['nexttag'] != 'layers':

            # note an internal state error.

            Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nNState error, nexttag {2:s} not \'layers\'\n'.format(str(InFile), str(Elem.sourceline), str(State['nexttag'])))
           
        # End of if State['nexttag'] != 'layers': 
        
        # Get the current tag value from the state variable set on a previous 
        # call to this routine. 

        View = State['lastvalue'] 

        # We should have an image file here so try and get it. 
        
        Image = Elem.get('image')

        if Image == None:

            # We didn't find an image, so set it to 'none' so it has a value
            # even if it is bogus. 

            Image = 'none'

            Errors.append('Error 30: File\n\'{0:s}\'\nAt line {1:s}\n\nNo image name present\n'.format(str(InFile), str(Elem.sourceline)))

        # End of if Image == None:
        
        # We have found an image attribute so put it in the dictonary 
        # indexed by viewname aquired above.

        if (View + '.image') in FzpDict:

            # too many input files!

            Errors.append('Error 31: File\n\'{0:s}\'\nAt line {1:s}\n\nMultiple {2:s} image files present\n'.format(str(InFile), str(Elem.sourceline), str(View)))

            FzpDict[View + '.image'].append(Image)
    
            logger.debug ('FzpProcessViewsTs3\n    error, multiple image files added \'%s\'\n', Image)

        else:

            # Put it in a list in case we find another (which is an error!)

            FzpDict[View + '.image'] = [Image]

            logger.debug ('FzpProcessViewsTs3\n    added image file\n     \'%s\'\n', Image)

        # End if (View + 'image') in FzpDict:

        # Then set State['lastvalue'] to the image to capture the layerids that 
        # should follow this image file.

        State['image'] = Image

        # then set the next expected tag to be 'layer' for the layerId.

        State['nexttag'] = 'layer'

    elif len(TagStack) == 6 and StackTag == 'layer':

        if State['nexttag'] != 'layer':

            # note an internal state error.

            Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, nexttag {2:s} not \'layer\'\n'.format(str(InFile), str(Elem.sourceline), str(State['nexttag'])))
           
        # End of if State['nexttag'] != 'layers': 
        
        # set the current view from State['lastvalue'] and the current image 
        # path/filename value from State['image'] for dict keys. The values 
        # are those saved the last time we were in this routine). 

        View = State['lastvalue']

        Image = State['image']

        # Now do the same for a layerId if it is here (there may be multiple
        # layerIds for a single view so use a list).

        LayerId = Elem.get('layerId')

        if LayerId == None:

            # There isn't a layer id so set it to none so it has a value even
            # if it is bogus. 

            LayerId = 'none'

            Errors.append('Error 32: File\n\'{0:s}\'\nAt line {1:s}\n\nNo layerId value present\n'.format(str(InFile), str(Elem.sourceline)))

        # End of if LayerId == None:

        # Set the index value to View.LayerId

        Index = View + '.' + 'LayerId'

        # For all except pcb view there should only be one LayerId

        if View != 'pcbView':

            if Index in FzpDict:

                Errors.append('Error 33: File\n\'{0:s}\'\nAt line {1:s}\n\nView {2:s} already has layerId {3:s}, {4:s} ignored\n'.format(str(InFile), str(Elem.sourceline),str(View), str(FzpDict[Index]), str(LayerId)))

            else:

                FzpDict[Index] = LayerId

            # End of if Index in FzpDict:

        else:

            # This is pcb view so there may be multiple layerIds but they must
            # be unique.

            if not Index in FzpDict:

                # this is the first and possibly only layerId so create it. 

                FzpDict[Index] = [LayerId]

                logger.debug ('FzpProcessViewsTs3\n    created LayerId \'%s\'\n', LayerId)

            elif LayerId in FzpDict[Index]:

                # must be unique and isn't.

                Errors.append('Error 33: File\n{0:s}\nAt line {1:s}\n\nView {2:s} already has layerId {3:s}, ignored\n'.format(str(InFile), str(Elem.sourceline),str(View), str(FzpDict[Index]), str(LayerId)))

            else:

                # if this is a second or later layerId append it

                FzpDict[Index].append(LayerId)

                logger.debug ('FzpProcessViewsTs3\n    appended LayerId \'%s\'\n', LayerId)

            # End of if not Index in FzpDict:

        # End of if View != 'pcbView':

        # if the view is pcbview and the layer is copper0 or copper1 note 
        # the layers presense to decide if this is a through hole or smd part
        # later (if there is only copper1 layer it is smd if both are present
        # it is through hole only copper0 is an error.

        logger.debug ('FzpProcessViewsTs3\n    View \'%s\'\n    LayerId \'%s\'\n', View, LayerId)

        if View == 'pcbView' and LayerId in ['copper0', 'copper1']:

            # mark this layer id as present

            FzpDict[LayerId + '.layerid'] = 'y'

            # and save its source line number for error messages later.

            FzpDict[LayerId + '.lineno'] = Elem.sourceline

        # End of if View == 'pcbview' and LayerId in ['copper0', 'copper1']:

        # State is fine as is, no need for updates here. 

    else:

        # Input state incorrect so set an error.

        Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, expected tag {2:s} got tag {3:s}\n'.format(str(InFile), str(Elem.sourceline), str(State['nexttag']), str(StackTag)))
            
        # then set the next expected tag to be 'layer' for the layerId.

        State['nexttag'] = 'layer'

        logger.debug ('FzpProcessViewsTs3\n    unknown state combination.\n    Expected \'%s\'\n    got \'%s\'\n', State['nexttag'], StackTag)

    # End of if len(TagStack) == 4:

    logger.debug ('FzpProcessViewsTs3\n    FzpDict\n     %s\n', FzpDict)

    logger.info ('Exiting FzpProcessViewsTs3 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def FzpProcessViewsTs3(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def FzpCheckViews(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    logger.info ('Entering FzpCheckViews XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug ('FzpCheckViews\n    State\n     %s\n', State)

    # note no valid views seen yet

    ViewsSeen = 0

    if not 'views' in FzpDict:

        Errors.append('Error 34: File\n\'{0:s}\'\n\nNo views found.\n'.format(str(InFile)))
       
    else:

        # Check for unexpected View names

    
        for View in FzpDict['views']:

            if View not in ['iconView', 'breadboardView', 'schematicView', 'pcbView']:

                Errors.append('Error 35: File\n\'{0:s}\'\n\nUnknown view {1:s} found. (Typo?)\n'.format(str(InFile), str(View)))

            else:

                # Note we have seen a valid view.

                ViewsSeen += 1

            # End of if View not in ['iconView', 'breadboardView', 'schematicView', 'pcbView']

        # End of for View in FzpDict['views']:

    # End of if not 'views' in FzpDict:

    # Now make sure we have at least one view and warn if we don't have all 4.

    if ViewsSeen == 0:

            Errors.append('Error 36: File\n\'{0:s}\'\n\nNo valid views found.\n'.format(str(InFile)))

    elif ViewsSeen < 4:

            Warnings.append('Warning 9: File\n\'{0:s}\'\n\nOne or more expected views missing (may be intended)\n'.format(str(InFile)))
         
    # End of if ViewsSeen == 0:

    # Now check for copper0 and copper1 layers. Only copper1 indicates 
    # an smd part, both copper0 and copper1 indicates a through hole part
    # and only copper0 is an error. No copper or State['hybridsetforpcbView'] 
    # indicates no pcb view.

    if 'hybridsetforpcbView' in State:

        # There is no pcb view.

        Info.append('File\n\'{0:s}\'\n\nThere is no PCB view for this part.\n')

    elif 'copper0.layerid' in FzpDict and 'copper1.layerid' in FzpDict:

        Info.append('File\n\'{0:s}\'\n\nThis is a through hole part as both copper0 and copper1 views are present.\nIf you wanted a smd part remove the copper0 definition from line {1:s}\n'.format(str(InFile), str(FzpDict['copper0.lineno'])))

    elif not 'copper0.layerid' in FzpDict and 'copper1.layerid' in FzpDict:

        Info.append('File\n\'{0:s}\'\n\nThis is a smd part as only the copper1 view is present.\nIf you wanted a through hole part add the copper0 definition before line {1:s}\n'.format(str(InFile), str(FzpDict['copper1.lineno'])))

    elif 'copper0.layerid' in FzpDict and not 'copper1.layerid' in FzpDict:

        Errors.append('Error 37: File\n\'{0:s}\'\n\nThis is a smd part as only the copper0 view is present but it is on the bottom layer, not the top.\nIf you wanted a smd part change copper0 to copper 1 at line  {1:s}\nIf you wanted a through hole part add the copper1 definition after line {1:s}\n'.format(str(InFile), str(FzpDict['copper0.lineno'])))

    # End of if 'hybridsetforpcbView' in State:

    logger.info ('Exiting FzpCheckViews XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of FzpCheckViews(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def FzpProcessConnectorsTs3(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    # We are in the connectors grouping so find and record connectors and their
    # attributes in the input stream. 

    logger.info ('Entering FzpProcessConnectorsTs3 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug ('FzpProcessConnectorsTs3\n    Entry TagStack\n     %s\n    State\n     %s\n    Errors\n     %s\n', TagStack, State, Errors)

    # TagStack length of 3 ('empty', 'module', 'connectors') is what tripped 
    # the call to this routine so we start processing at TagStack length 4 in 
    # this large case statement which trips when it finds the correct state 
    # (or complains if it finds an incorrect state due to errrorS.)

    if len(TagStack) == 4:

        # Go and process the TagStack level 4 stuff (connector name type id)

        FzpProcessConnectorsTs4(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)

    elif len(TagStack) == 5:

        # Go and process the TagStack level 5 stuff (description or views)

        FzpProcessConnectorsTs5(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)


    elif len(TagStack) == 6:

        # Go and process the TagStack level 6 stuff (viewname)

        FzpProcessConnectorsTs6(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)

    elif len(TagStack) == 7:

        # Go and process the TagStack level 7 stuff (p svgId layer terminalId
        # legId copper0 copper1 etc.)

        FzpProcessConnectorsTs7(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)

    else:

        # Too many levels down in the tag stack. There is an error somewhere. 

        Errors.append('Error 38: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, tag stack is at level {2:s} and should only go to level 7\n'.format(str(InFile), str(Elem.sourceline), str(len(TagStack))))

    # End of if len(TagStack) == 4:

    logger.info ('Exiting FzpProcessConnectorsTs3 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def FzpProcessConnectorsTs3(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def FzpProcessConnectorsTs4(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    logger.info ('Entering FzpProcessConnectorsTs4 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug ('FzpProcessConnectorsTs4\n    Entry TagStack\n     %s\n    State\n     %s\n', TagStack, State)

    LeadingConnectorRegex = re.compile(r'connector',  re.IGNORECASE)

    # Check for a comment to ignore it.

    CommentRegex = re.compile(r'cyfunction Comment at',  re.IGNORECASE)

    # TagStack should be 'module', 'connectors', 'connector' with attributes
    # name, type and id so check and process them. Check that 
    # State['nexttag'] is 'connector' or 'p' (from the end of a previous 
    # connector) to indicate that is what we are expecting at this time. 
    
    # Because we may also have spice data here (that we want to ignore) that 
    # isn't on the tag stack, check if the current tag may be spice (or at 
    # typo, we can't tell the difference) by checking the current tag value. 

    # Set the value of Tag from Elem (because spice tags won't be on the stack)

    Tag = Elem.tag

    logger.debug ('ProcessConnectorsTs4\n    initial Tag \'%s\'\n', Tag)

    # Since we can have spice data inserted here, check the tag to see if it
    # is one we are willing to deal with. If not read on discarding and warning
    # as we go until we come to something we recognize.

    if Tag == None or not Tag in ['connector', 'description', 'views', 'breadboardView', 'p', 'schematicView', 'pcbView']:

        # Assume this is spice data, but warn about it in case it is a typo
        # Ignore those tags which we know are spice related.

        if not Tag in ['erc', 'voltage', 'current']:

            logger.debug ('FzpProcessConnectorsTs4\n    assuming Tag\n     \'%s\'\n    is spice data\n', Tag)

            # Check for a comment and ignore it if present.

            if CommentRegex.search(str(Tag)) == None:

                # Otherwise issue a spice warning.

                Warnings.append('Warning 10: File\n\'{0:s}\'\nAt line {1:s}\n\nTag {2:s}\nis not recognized and assumed to be spice data which is ignored\n(but it might be a typo, thus this warning)\n'.format(str(InFile), str(Elem.sourceline), str(Tag)))

            # End of if CommentRegex.search(str(Tag)) == None:

        # End of if not Tag in ['erc', 'voltage', 'current']:
         
        # leave the state variables as is until we find something we recognize.

    else:
    
        StackTag, StackLevel = TagStack[len(TagStack) - 1]

        Tag = StackTag
    
        if State['nexttag'] != 'connector' and State['nexttag'] != 'p':
    
            logger.debug ('FzpProcessConnectorsTs4\n    tag error, State[\'nexttag\'] \'%s\' should be p or connector\n', State['nexttag'])
    
            Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, expected tag \'connector\' or \'p\' not {2:s}\n'.format(str(InFile), str(Elem.sourceline), str(State['nexttag'])))
            
        # End of if State['nexttag'] != 'connector' and State['nexttag'] != 'p':
    
        # Make sure the tag we saw is connector (independent of what we
        # expected to see above)
    
        if Tag != 'connector':
    
            logger.debug ('FzpProcessConnectorsTs4\n    error, Tag \'%s\' should be \'connector\'\n', Tag)
    
            Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nSate error, expected tag \'connector\' not {2:s}\n'.format(str(InFile), str(Elem.sourceline), str(Tag)))
    
        # End of if Tag != 'connector':
    
        # Set the current tag to 'connector'
    
        State['lasttag'] = 'connector'
    
        # and that we expect a description to be next.
    
        State['nexttag'] = 'description'
    
        # Get the attribute values we should have
    
        Id = Elem.get('id')
    
        Type = Elem.get('type')
    
        Name = Elem.get('name')
    
        if Id == None:
    
            Errors.append('Error 39: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector has no id\n'.format(str(InFile), str(Elem.sourceline)))
    
            # give it a bogus value so it has one.
    
            Id = 'none'
        
        elif Id in FzpDict:
    
            # If it is a dup, error!
    
            DupNameError(InFile, Id, Elem, Errors)
    
        else:
    
            # else mark it as seen
    
            FzpDict[Id] = Id

            # and note that we have seen this pin number. To get the number
            # remove the prepended 'connector'.

            PinNo = LeadingConnectorRegex.sub('', Id)

            if 'pinnos' in FzpDict:

                # The entry already exists so append this pin number to the 
                # list. 

                FzpDict['pinnos'].append(PinNo)

            else:

                # create the entry and add the pin number.

                FzpDict['pinnos'] = [PinNo]

            # End of if 'pinnos' in FzpDict:
    
        # End of if Id == None:
    
        # Create an entry with unique prefix 'connectorx.id.bus so bus 
        # checking won't match svg terminal or leg ids, only id entries. 
        # Set it to itself so we know this isn't yet part of any bus during 
        # bus processing later. 
    
        FzpDict[Id + '.id.bus'] = Id + '.id.bus'

        # Do the same for subparts so we are ready if buses and subparts can
        # ever coexist (they can't right now ...)

        FzpDict[Id + '.id.subpart'] = Id + '.id.subpart'
    
        # Set the id value in to State for later processing. 
    
        State['lastvalue'] = Id
    
        if Name == None:
    
            Errors.append('Error 40: File\'n{0:s}\'\nAt line {1:s}\n\nConnector has no name\n'.format(str(InFile), str(elem.sourceline)))
    
            # give it a bogus value so it has one.
    
            Name = 'none'
    
        elif Name in FzpDict:

            # If it is a dup, warning if such warnings are enabled!
    
            logger.debug ('FzpProcessConnectorsTs4\n   XML source line %s\n    dup Name \'%s\'\n    IssueNameDupWarning \'%s\'\n', Elem.sourceline, Name, IssueNameDupWarning)

            if IssueNameDupWarning == 'y': 

                DupNameWarning(InFile, Name, Elem, Warnings)

            # End of if IssueNameDupWarning == 'y': 
    
        else:
    
            # else mark it as seen
    
            FzpDict[Name] = Name
    
        # End of if Name == None:
    
        # record the name in the dictionary
    
        FzpDict[Id + '.name'] = Name
    
        logger.debug ('FzpProcessConnectorsTs4\n    not male warning\n    XML source line %s\n    Tag \'%s\'\n    Id \'%s\'\n     Type \'%s\'\n    Name \'%s\'\n', Elem.sourceline, Tag, Id, Type, Name)
    
        if Type != 'male' and not 'notmalewarning' in State and not'breadboardfzp' in State:

            # If this isn't a breadboard file (which has hundreds of female 
            # connectors) give a warning. 
    
            Warnings.append('Warning 11: File\n\'{0:s}\'\nAt line {1:s}\n\nType {2:s} is not male (it usually should be)\n'.format(str(InFile), str(Elem.sourceline), str(Type)))

            # Note we have output this warning so we don't repeat it.

            State['notmalewarning'] = 'y'
    
        # End of if Type != 'male' and not 'notmalewarning' in State and not'breadboardfzp' in State:
            
        if Type == None:
    
            # If not flag an error as it must have one.
    
            Errors.append('Error 41: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector {2:s} has no type\n'.format(str(InFile), str(Elem.sourceline), str(Id)))
    
            # then assign it a bogus value so it has one. 
    
            Type = 'none'
    
        # End of if Type == None:
    
        # Record the connector type indexed by connector name
    
        FzpDict[Id + '.type'] = Type
    
    # end of if Tag == None or not Tag in ['connector', 'description', 'views', 'breadboardView', 'p', 'schematicView', 'pcbView']:
    
    logger.info ('Exiting FzpProcessConnectorsTs4 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of FzpProcessConnectorsTs4(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def FzpProcessConnectorsTs5(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    logger.info ('Entering FzpProcessConnectorsTs5 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug ('FzpProcessConnectorsTs5\n    entry, TagStack\n     %s\n    State\n     %s\n', TagStack, State)

    # Check for a comment to ignore it.

    CommentRegex = re.compile(r'cyfunction Comment at',  re.IGNORECASE)

    # Set the value of Tag from Elem (because spice tags won't be on the stack)

    Tag = Elem.tag

    logger.debug ('FzpProcessConnectorsTs5\n    initial Tag \'%s\'\n', Tag)

    # Since we can have spice data inserted here, check the tag to see if it
    # is one we are willing to deal with. If not read on discarding and warning
    # as we go until we come to something we recognize.

    if Tag == None or not Tag in ['connector', 'description', 'views', 'breadboardView', 'p', 'schematicView', 'pcbView']:

        # Check for a comment and ignore it if present.

        if CommentRegex.search(str(Tag)) == None:

            # Assume this is spice data, but warn about it in case it is a typo

            logger.debug ('FzpProcessConnectorsTs5\n    assuming Tag\n     \'%s\'\n    is spice data\n', Tag)

            Warnings.append('Warning: File\n\'{0:s}\'\nAt line {1:s}\n\nTag {2:s}\nis not recognized and assumed to be spice data which is ignored\n(but it might also be a typo, thus this warning)\n'.format(str(InFile), str(Elem.sourceline), str(Tag)))

        # End of if CommentRegex.search(str(Tag)) == None:
     
        # leave the state variables as is until we find something we recognize.

    else:
    
        # Set Id from State['lastvalue']
    
        Id = State['lastvalue']
    
        # We should now have either description or views so check what we 
        # expect and then what we actually have. 
    
        if State['nexttag'] != 'description' and State['nexttag'] != 'views':
    
            Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, expected tag \'description\' or \'views\' not {2:s}\n'.format(str(InFile), str(Elem.sourceline), str(State['nexttag'])))
    
        # End of if State['nexttag'] != 'description' and State['nexttag'] != 'views':
        if  Tag == 'description':
    
            # All we need to do is set up the last and next tags. 
    
            State['lasttag'] = 'description'
    
            State['nexttag'] = 'views'
    
        elif Tag == 'views':
    
            # All we need to do is check the last tag was 'description' then
            # set up the last and next tags.
    
            if State['lasttag'] != 'description':
                
                Errors.append('Error 42: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector {2:s} has no description\n'.format(str(InFile), str(Elem.sourceline), str(Id)))
    
            # End of if State['lasttag'] != 'description':
    
            State['lastag'] = 'views'
    
            State['nexttag'] = 'viewname'
    
        else:
    
            Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, connector {2:s}, expected tag \'description\' or \'views\' got {3:s}\n'.format(str(InFile), str(Elem.sourceline), str(Id), str(Tag)))
    
        # End of if Tag == 'description':
    
    # End of if not Tag in ['connector', 'description', 'views', 'breadboardView', 'p', 'schematicView', 'pcbView']:

    logger.info ('Exiting FzpProcessConnectorsTs5 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

#End of FzpProcessConnectorsTs5(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def FzpProcessConnectorsTs6(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    logger.info ('Entering FzpProcessConnectorsTs6 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug ('FzpProcessConnectorsTs6\n    entry TagStack\n     %s\n    State\n     %s\n', TagStack, State)

    # Set the value of Tag from the TagStack

    StackTag, StackLevel = TagStack[len(TagStack) - 1]

    Tag = StackTag

    # Set Id from State['lastvalue']

    Id = State['lastvalue']

    if Tag == 'p':

        Errors.append('Error 43: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector {2:s} missing viewname\n'.format(str(InFile), str(Elem.sourceline), str(Id)))
   
        State['lasttag'] = 'viewname'

        State['nexttag'] = 'p' 

    elif State['nexttag'] != 'p' and State['nexttag'] != 'viewname':

        Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, connector {2:s}, expected \'p\' or \'viewname\' got {3:s}\n'.format(str(InFile), str(Elem.sourceline), str(Id), str(State['nexttag'])))

        # It is unclear what State should be so leave it as is which will
        # likely cause an error cascade, but we have flagged the first one.

    else:

        # We look to have a view name so process it. 

        if Tag not in ['breadboardView', 'schematicView', 'pcbView']:

            logger.debug ('ProcessConnectorsTs6\n    invalid view name \'%s\'\n    XML source line %s\n    Tag \'%s\'\n    TagStack\n     %s\n    State\n     %s\n', Elem.sourceline, Tag, TagStack, State)

            Errors.append('Error 44: File\n\'{0:s}\'\nAt line {1:s}\n\nViewname {2:s} invalid (typo?)\n'.format(str(InFile), str(Elem.sourceline), str(Tag)))

        else:

            # Note that we have seen this view in State.

            State[Tag] = 'y'

        # End of if Tag not in ['breadboardView', 'schematicView', 'pcbView']:

        State['lasttag'] = Tag

        State['nexttag'] = 'p'

    # End of if Tag == 'p':

    logger.debug ('FzpProcessConnectorsTs6\n    at exit\n    TagStack\n     %s\n    State\n     %s\n', TagStack, State)

    logger.info ('Exiting FzpProcessConnectorsTs6 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def FzpProcessConnectorsTs6(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):


def FzpProcessConnectorsTs7(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    logger.info ('Entering FzpProcessConnectorsTs7 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug ('FzpProcessConnectorsTs7\n   on entry\n    TagStack\n     %s\n    State\n     %s\n', TagStack, State)

    # Set the value of Tag from the TagStack

    StackTag, StackLevel = TagStack[len(TagStack) - 1]

    Tag = StackTag

    # Set Id from State['lastvalue']

    Id = State['lastvalue']

    if not State['nexttag'] == 'p':

        # expected state doesn't match. 

        logger.debug ('FzpProcessConnectorsTs7\n    state error\n    XML source line %s\n    State[\'nexttag\'] \'%s\' isn\'t \'p\'\n', Elem.sourceline, State['nexttag'])

        Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, expected tag \'p\' got {2:s}\n'.format(str(InFile), str(Elem.sourceline), str(State['nexttag'])))

        # unclear what State should be so leave as is which may cause an
        # error cascade. 

    else:

        if Tag == 'p':

            # We have found a 'p' line which means we have the associated 
            # view id on the tag stack and need to add the connector names 
            # to the dictionary for use checking the pins in the svgs 
            # later.  

            # Get the viewname from the TagStack.

            StackTag, StackLevel = TagStack[len(TagStack) - 2]

            View = StackTag

            logger.debug ('FzpProcessConnectorsTs7\n    View set to \'%s\'\n', View)

            # We need a layer value (even if it is None) for the index.

            Layer = Elem.get('layer')

            if Layer == None:

                Layer = 'none'

                logger.debug ('FzpProcessConnectorsTs7\n    missing layer\n   XML source line %s\n', Elem.sourceline)

                Errors.append('Error 45: File\n\'{0:s}\'\nAt line {1:s}\n\nLayer missing\n'.format(str(InFile), str(Elem.sourceline)))

            # End of if Layer == None:

            # Verify the layerId is correct. 

            if not View  + '.' + 'LayerId' in FzpDict:

                # Don't have a layerId for this view!

                Errors.append('Error 46: File\n\'{0:s}\'\nAt line {1:s}\n\nNo layerId for View {2:s}\n'.format(str(InFile), str(Elem.sourceline), str(View)))

            elif View != 'pcbView' and Layer != FzpDict[View  + '.' + 'LayerId']:

                # For all except pcbView, the layerIds don't match.

                Errors.append('Error 47: File\n\'{0:s}\'\nAt line {1:s}\n\nLayerId {2:s} doesn\'t match View {3:s} layerId {4:s}\n'.format(str(InFile), str(Elem.sourceline), str(Layer), str(View), str(FzpDict[View  + '.' + 'LayerId'])))

            elif View == 'pcbView':

                if  not Layer in FzpDict[View  + '.' + 'LayerId']:

                    # Layer isn't a valid layer for pcbView.

                    Errors.append('Error 47: File\n\'{0:s}\'\nAt line {1:s}\n\nLayerId {2:s} doesn\'t match any in View {3:s} layerIds {4:s}\n'.format(str(InFile), str(Elem.sourceline), str(Layer), str(View), str(FzpDict[View  + '.' + 'LayerId'])))

                elif Layer == 'copper0':

                    # While multiple layers are allowed, only copper0 and 
                    # copper1 (if they exist) are allowed in connectors and
                    # they must be unique. 

                    if Id + '.' + Layer in FzpDict:

                        # Not unique so error. 

                        Errors.append('Error 48: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector {2:s} layer {3:s} already defined, must be unique\n'.format(str(InFile), str(Elem.sourceline), str(Id), str(Layer)))

                    else:
    
                        # It is unique so note that we have seen it now. 

                        FzpDict[Id + '.' + Layer] = 'y'

                    # End of if Id + '.' + Layer in FzpDict:

                elif Layer == 'copper1':

                    # While multiple layers are allowed, only copper0 and 
                    # copper1 (if they exist) are allowed in connectors and
                    # they must be unique. 

                    if Id + '.' + Layer in FzpDict:

                        # Not unique so error. 

                        Errors.append('Error 48: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector {2:s} layer {3:s} already defined, must be unique\n'.format(str(InFile), str(Elem.sourceline), str(Id), str(Layer)))

                    else:
    
                        # It is unique so note that we have seen it now. 

                        FzpDict[Id + '.' + Layer] = 'y'

                    # End of if Id + '.' + Layer in FzpDict:

                # End of if  not Layer in FzpDict[View  + '.' + 'LayerId']:

            # End of if not View  + '.' + 'LayerId' in FzpDict:

            # Get the hybrid attribute if present (as it affects checking 
            # below)

            Hybrid = Elem.get('hybrid')

            if Hybrid != None:

                # If Hybrid isn't present just drop through as that is fine.
                # If Hybrid is present, anything but 'yes' is an error ...

                if Hybrid != 'yes':

                    Errors.append('Error 49: File\n\'{0:s}\'\nAt line {1:s}\n\nhybrid is present but isn\'t \'yes\' but {2:s} (typo?)\n'.format(str(InFile), str(Elem.sourceline),str(Hybrid)))

                else:

                    # hybrid is set so if this is pcbview note that in State

                    if View == 'pcbView':

                        State['hybridsetforpcbView'] = 'y'

                    # End of if View == 'pcbView':

                # End of if Hybrid != 'yes':

            # End of if Hybrid != None:

            logger.debug ('FzpProcessConnectorsTs7\n    Layer set to \'%s\'\n', Layer)

            # then get all the attributes and check their values as 
            # appropriate. Mark we haven't yet seen a svgid, terminalId or
            # legId. A svgId is required and will cause an error, terminalId 
            # will be warned about (becuase it is usually an error) in 
            # schematicview and both a TerminalId and a LegId is an error, it 
            # must be one or the other not both. 

            SvgIdSeen = 'n'

            TerminalIdSeen = 'n'

            LegIdSeen = 'n'

            for Key in Elem.keys():

                logger.debug ('FzpProcessConnectorsTs7\n   check Key \'%s\'\n    XML source line %s\n   Tag \'%s\'\n    Id \'%s\'\n', Key, Elem.sourceline, Tag, Id)

                if Key not in ['terminalId', 'svgId', 'layer', 'legId', 'hybrid']:

                    # Warn about a non standard key ...

                    logger.debug ('FzpProcessConnectorsTs7\n    unknown key \'%s\'\n', Key)

                    Warnings.append('Warning 12: File\n\'{0:s}\'\nAt line {1:s}\n\nKey {2:s} is not recognized\n'.format(str(InFile), str(Elem.sourceline), str(Key)))

                # End of if Key not in ['terminalId', 'svgId', 'layer', 'legId']:
                # Now get the value of the key.

                Value = Elem.get(Key)

                if Key == None:

                    Errors.append('Error 50: File\n\'{0:s}\'\nAt line {1:s}\n\nTag {2:s} is present but has no value\n'.format(str(InFile), str(Elem.sourceline),str(Key)))

                # End of if Key == None"

                # then make checks depending on the value of the key.

                if Key == 'svgId':

                    # Note that we have seen an svgId tag (if the value is 
                    # None, the error will have been noted above.) 

                    SvgIdSeen = 'y'

                # End of if Key == 'svgId':

                if Key == 'terminalId':

                    # Note that we have seen an terminalId tag (if the value 
                    # is None, the error will have been noted above.) 

                    TerminalIdSeen = 'y'
            
                # End of if Key == 'terminalId':

                if Key == 'legId':

                    # Note that we have seen an legId tag (if the value is 
                    # None, the error will have been noted above.) 

                    LegIdSeen = 'y'

                # End of if Key == 'legId':
            

                if Key == 'layer':

                    # If the key is 'layer' then this layer id needs to exist
                    # in the associated svg, so add this to the list of layers
                    # to look for in the svg. The layer needs to be the same
                    # for all

                    if View + '.layer' in FzpDict:

                        # Already exists so append this one if it isn't 
                        # already present.

                        if not Layer in FzpDict[View + '.layer']:

                            logger.debug ('FzpProcessConnectorsTs7\n   add Layer \'%s\' to existing layer\n    XML source line %s\n    View \'%s\'\n', Layer, Elem.sourceline, View)

                            FzpDict[View + '.layer'].append(Layer)

                        # End of if not Layer in FzpDict[View + '.layer']:

                    else:

                        # Doesn't exist yet, so create it and add the layer.

                        logger.debug ('FzpProcessConnectorsTs7\n   add new layer \'%s\'\n    XML source line %s\    View \'%s\'\n', Layer, Elem.sourceline, View)
                        FzpDict[View + '.layer'] = [Layer]

                    # End of if View + '.layer' in FzpDict:

                else:

                    # Key isn't layer so if it is a connector and Hybrid isn't
                    # set to 'yes' (in which case the connector will be ignored
                    # as this view is unused)
                
                    if Key in ['terminalId', 'svgId', 'legId'] and Hybrid != 'yes':

                        # Check if it matches with the connector defined
                
                        if not re.match(Id, Value):

                            # No, flag it as a warning, as it is unusual (but
                            # not illegal) and thus possibly an error.
 
                            logger.debug ('FzpProcessConnectorsTs7\n    warning Id \'%s\' doesn\'t match Value \'%s\'\n',Id, Value)

                            Warnings.append('Warning 13: File\n\'{0:s}\'\nAt line {1:s}\n\nValue {2:s} doesn\'t match Id {3:s}. (Typo?)\n'.format(str(InFile), str(Elem.sourceline), str(Value), str(Id)))


                        # End of if not re.match(Id, Value):

                        # Now make sure this connector is unique in this view
                        # and if it is add it to the list of connectors to 
                        # verify is in the associated svg.

                        if not View + '.' + Value + '.' + Layer in FzpDict:

                            # This is one of the pin names and we haven't seen
                            # it before, so add it to the connectors list for 
                            # matching in the svg. Indicate we have seen this
                            # connector (in case we see another)

                            FzpDict[View + '.' + Value + '.' + Layer] = 'y'

                            # If the entry for this view doesn't exist yet, 
                            # create it and add this connector to the list
                            # otherwise append the connector to the existing
                            # list (weeding out duplicates.)

                            if not 'connectors.fzp.' + View in FzpDict:
    
                                logger.debug ('FzpProcessConnectorsTs7\n    create entry \'%s\', add \'%s\' to it\n','connectors.fzp.' + View, Value)

                                # First connector so create the list.

                                FzpDict['connectors.fzp.' + View] = [Value]

                            else:

                                logger.debug ('FzpProcessConnectorsTs7\n    pre dup check\n    View \'%s\'\n    connectors\n     %s\n', 'connectors.fzp.' + View, FzpDict['connectors.fzp.' + View])

                                if not Value in FzpDict['connectors.fzp.' + View]:

                                    # For pcb view pins will appear twice, once
                                    # for copper0 and once for copper1, we only
                                    # need one value so if it is already here 
                                    # don't add a new one.

                                    logger.debug ('FzpProcessConnectorsTs7\n    add \'%s\' to \'%s\'\n', Value, 'connectors.fzp.' + View)

                                    FzpDict['connectors.fzp.' + View].append(Value)

                                else:

                                    logger.debug ('FzpProcessConnectorsTs7\n    \'%s\' already in \'%s\'\n', Value, 'connectors.fzp.' + View)

                                # End of if not Value in FzpDict['connectors.fzp.' + View]:

                            # End of if not 'connectors.fzp.' + View in FzpDict:

                        # End of if not View + '.' + Value + '.' + Layer in FzpDict:

                        if View == 'schematicView':

                            # This is schematic view, so in case this is a 
                            # subpart, associate the pins with the connectorId

                            if not 'schematic.' + Id in FzpDict:

                                # Doesn't exist yet so create it.

                                FzpDict['schematic.' + Id] = []

                            # End of if not 'schematic.' + Id in FzpDict:

                            FzpDict['schematic.' + Id].append(Value)

                        # End of if View == 'schematicView':

                    # End of if Key in ['terminalId', 'svgId', 'legId'] and Hybrid != 'yes':

                # End of if Key == 'layer':

            # End of for Key in Elem.keys():

            # Now we have all the attributes, see whats missing. We already
            # complained about a missing layer above so only do svgId and if
            # view is schematicview, terminalId as a warning, here.TerminalId
            # and legId are optional although no terminalId is usually an error
            # in schematic, only svgId is required, but if hybrid is 'yes' 
            # even that is optional. However both a terminalId and a legID are
            # an error so note that. 

            if TerminalIdSeen == 'y' and LegIdSeen == 'y':

                Errors.append('Error 80: File\n\'{0:s}\'\nAt line {1:s}\n\nBoth terminalId and legId present, only one or the other is allowed.\n'.format(str(InFile), str(Elem.sourceline)))

            # End of if TerminalIdSeen == 'y' and LegIdSeen == 'y':

            if SvgIdSeen != 'y' and Hybrid != 'yes':

                Errors.append('Error 51: File\n\'{0:s}\'\nAt line {1:s}\n\nsvgId missing\n'.format(str(InFile), str(Elem.sourceline)))
         
            # End of if SvgIdSeen != 'y' and Hybrid != 'yes':

            if TerminalIdSeen != 'y' and View == 'schematicView' and Hybrid != 'yes':
                Warnings.append('Warning 14: File\n\'{0:s}\'\nAt line {1:s}\n\nterminalId missing in schematicView (likely an error)\n'.format(str(InFile), str(Elem.sourceline)))

            # End of if TerminalIdSeen != 'y' and View == 'schematicview' and Hybrid != 'yes':

        # End of if Tag == 'p':

    # End of if not State['nexttag'] == 'p':

    logger.debug ('FzpProcessConnectorsTs7\n    returns\n    TagStack\n     %s\n    State\n     %s\n', TagStack, State)

    logger.info ('Exiting FzpProcessConnectorsTs7 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of FzpProcessConnectorsTs7(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def FzpProcessBusTs3(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    logger.info ('Entering FzpProcessBusTs3 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    # TagStack length of 3 ('empty', 'module', 'buses') is what tripped the 
    # call to this routine so we start processing at TagStack length 3 in this 
    # case statement which trips when it finds the correct state (or complains
    # if it finds an incorrect state due to errors.)

    if len(TagStack) == 4:

        # Go and process the TagStack level 4 stuff (bus for the bus id)

        FzpProcessBusTs4(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)

    elif len(TagStack) == 5:

        # Go and process the TagStack level 5 stuff (nodeMembers)

        FzpProcessBusTs5(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)

    elif len(TagStack) > 5:

        # There shouldn't be anything past 5th level so something is wrong. 

        Errors.append('Error 38: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, tag stack is at level {2:s} and should only go to level 5\n\n'.format(str(InFile), str(Elem.sourceline), str(len(TagStack))))

    # End of if len(TagStack) == 4:
    
    logger.info ('Exiting FzpProcessBusTs3 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def FzpProcessBusTs3(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def FzpProcessBusTs4(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    logger.info ('Entering FzpProcessBusTs4 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug ('FzpProcessBusTs4\n    entry\n    TagStack\n     %s\n    State\n      %s\n', TagStack, State)

    if not State['lasttag'] in ['buses', 'bus', 'nodeMember']:

        logger.debug ('FzpProcessBusTs4\n    Unexpected state \'%s\', expected buses or nodeMember\n',State['lasttag'])

        # Not the expected state possibly a missing line. 

        Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, expected lasttag \'buses\' or \'nodeMember\' not {2:s}\n(Missing line?)\n'.format(str(InFile), str(Elem.sourceline), str(State['lasttag'])))
        
    # End of if not State['lasttag'] in ['buses', 'nodeMember']:

    StackTag, StackLevel = TagStack[len(TagStack) - 1]

    Tag = StackTag

    if Tag != 'bus':

        logger.debug ('FzpProcessBusTs4\n    Unexpected Tag \'%s\', expected bus\n', Tag)

        Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, expected tag \'bus\' not {2:s}. (Missing line?)\n'.format(str(InFile), str(Elem.sourceline), str(Tag)))
        
        # it is unclear what state should be so leave it as is which may cause
        # an error cascade ...

    else:

        # We look to have a bus line so get the bus id. 

        Id = Elem.get('id')

        if Id == None:

            # Note that we have seen an empty bus definition (some parts have
            # one) and give the Id a text value

            Id = ''

            FzpDict['empty_bus_defined'] = 'y'

            Warnings.append('Warning 15: File:\n\'{0:s}\'\nAt line {1:s}\n\nEmpty bus definition, no id (remove?)\n'.format(str(InFile), str(Elem.sourceline)))

        else:            

            # and note we have seen a bus (not just the buses tag) for subparts 
            # but we haven't put out an error message for it yet, if there  
            # is a sub parts definition later, we will. 

            FzpDict['bus_defined'] = 'n'

            logger.debug ('FzpProcessBusTs4\n    set bus id \'%s\'\n   XML source line %s\n   Tag \'%s\'\n    State\n    %s\n', Id, Elem.sourceline, Tag, State)

            if Id + '.bus_seen' in FzpDict:
    
                # Not unique error
    
                DupNameError(InFile, Id, Elem, Errors)
    
            else:
    
                logger.debug ('FzpProcessBusTs4\n    Mark bus Id \'%s\' as seen\n', Id)
    
                # else mark it as seen 
    
                FzpDict[Id + '.bus_seen'] = Id
    
            # End of if Id + '.bus_seen' in FzpDict:
    
        # End of Id == None:

        # Set the bus id even if it is None, so we don't impact the last bus
        # with the current information. 

        State['lastvalue'] = Id

        if (Id + '.bus') in FzpDict:

            logger.debug ('FzpProcessBusTs4\n    Id \'%s\' already exists\n', Id)

            # If we already have this bus id flag an error.

            Errors.append('Error 52: File\n\'{0:s}\'\nAt line {1:s}\n\nBus {2:s} already defined\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

        else:

            logger.debug ('FzpProcessBusTs4\n    created bus node counter for Id \'%s\'\n', Id)

            # mark this as a bus currently with no nodes.

            FzpDict[Id + '.bus'] = 0

        # End of if (Id + '.bus') in FzpDict:

        # Set the current and expected State

        State['lasttag'] = 'bus'

        State['nexttag'] = 'nodeMember'

        logger.debug ('FzpProcessBusTs4\n    end of bus tag \'%s\'\n    XML source line %s\n    State\n      %s\n', Id, Elem.sourceline, State)

    # End of if Tag != 'bus':

    logger.info ('Exiting FzpProcessBusTs4 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def FzpProcessBusTs4(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def FzpProcessBusTs5(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    logger.info ('Entering FzpProcessBusTs5 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug ('FzpProcessBusTs5\    entry\n    TagStack\n     %s\n    State\n     %s\n', TagStack, State)

    # At this point we set the last Id we saw from State and Tag from the 
    # TagStack. 

    Id = State['lastvalue']

    StackTag, StackLevel = TagStack[len(TagStack) - 1]

    Tag = StackTag

    if not State['nexttag'] in ['bus', 'nodeMember']:

        logger.debug ('FzpProcessBusTs5\n    Unexpected state \'%s\' expected bus or nodeMember\n',State['nexttag'])

        # State isn't what we expected, error

        Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, expected lasttag \'bus\' or \'nodeMember\' not {2:s}\n(Missing line?)\n'.format(str(InFile), str(Elem.sourceline), str(State['lasttag'])))

    else:    
    
        if Tag == 'nodeMember':
    
            # Since Connector shouldn't be unique we don't need to check if 
            # it is.
    
            Connector = Elem.get('connectorId')
    
            if Connector != None:
    
                # Check if the connector exists
    
                if not Connector + '.id.bus' in FzpDict:

                    logger.debug ('FzpProcessBusTs5\n    bus Connector \'%s\' doesn\'t exist\n',Connector)
    
                    # No, flag an error.
    
                    Errors.append('Error 53: File\n\'{0:s}\'\nAt line {1:s}\n\nBus nodeMember {2:s} does\'t exist\n'.format(str(InFile), str(Elem.sourceline), str(Connector)))
    
                else:
    
                    # Since we set the value as the key as a place holder 
                    # intially, check if that is still true (i.e. this isn't 
                    # part of another bus already). 

                    logger.debug ('FzpProcessBusTs5\n    Before test\n    Connector \'%s\'\n    FzpDict \'%s\'\n ',Connector, str(FzpDict[Connector + '.id.bus']))
    
                    if FzpDict[Connector + '.id.bus'] == Connector + '.id.bus':

                        logger.debug ('FzpProcessBusTs5\n    Connector \'%s\' added to bus \'%s\'\n',Connector, Id)
    
                        # connector not part of another bus so mark it as ours. 
                        # by writing our bus Id in to it.
    
                        FzpDict[Connector + '.id.bus'] = Id
    
                    else:
    
                        # connector is already part of another bus, flag an error.

                        logger.debug ('FzpProcessBusTs5\n    connector \'%s\' already in another bus\n', Connector)
    
                        Errors.append('Error 54: File\n\'{0:s}\'\nAt line {1:s}\n\nBus nodeMember {2:s} already in bus {3:s}\n'.format(str(InFile), str(Elem.sourceline), str(Connector), str(FzpDict[Connector + '.id.bus'])))
    
                    # End of if FzpDict[connector + '.id.bus'] == FzpDict[connector + '.id.bus']:
    
                # End of if not Connector + '.id.bus' in FzpDict:
    
                # Now increase the count of nodes in the bus by 1.
    
                FzpDict[Id + '.bus'] += 1
    
            # End of if Connector != None:
    
        # End of if Tag == 'nodeMember':
    
    # End of if not State['nexttag'] in ['bus', 'nodeMember']:

    logger.info ('Exiting FzpProcessBusTs5 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def FzpProcessBusTs5(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def FzpProcessSchematicPartsTs3(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    logger.info ('Entering FzpProcessSchematicPartsTs3 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    StackTag, StackLevel = TagStack[len(TagStack) - 1]

    Tag = StackTag

    # Check for a duplicate schematic-subparts

    if Tag == 'schematic-subparts':

        # Unexpected state error

        Errors.append('Error: File\n\'{0:s}\'\nAt line {1:s}\n\nDuplicate tag in schematic-subparts\n'.format(str(InFile), str(Elem.sourceline)))

    # End of if Tag == 'schematic-subparts':

    logger.debug ('FzpProcessSchematicPartsTs3\n    TagStack len \'%s\' Tag \'%s\'\n', len(TagStack), Tag)

    # Process the data according to tag stack level.

    if len(TagStack) == 4:

        # Go and process the TagStack level 4 stuff (subpart id and label)

        FzpProcessSchematicPartsTs4(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)

    elif len(TagStack) == 5:

        # Go and process the TagStack level 4 stuff (connectors)

        FzpProcessSchematicPartsTs5(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)

    elif len(TagStack) == 6:

        # Go and process the TagStack level 5 stuff (connector)

        FzpProcessSchematicPartsTs6(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)


    elif len(TagStack) > 6:

        # There shouldn't be anything past 5th level so something is wrong. 

        Errors.append('Error 38: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, tag stack is at level {2:s} and should only go to level 6\n\nTag {3:s} will be ignored\n'.format(str(InFile), str(Elem.sourceline), str(len(TagStack)), str(Tag)))

    # End of if len(TagStack) == 3:

    logger.info ('Exiting FzpProcessSchematicPartsTs3 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def FzpProcessSchematicPartsTs3(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def FzpProcessSchematicPartsTs4(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    logger.info ('Entering FzpProcessSchematicPartsTs4 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    StackTag, StackLevel = TagStack[len(TagStack) - 1]

    Tag = StackTag

    if Tag != 'subpart':

        logger.debug ('FzpProcessSchematicPartsTs4\n    Unexpected Tag \'%s\', expected subpart\n', Tag)

        # State isn't what we expected, error

        Errors.append('Error 26: File\n\n{0:s}\'\nAt line {1:s}\n\nState error, expected tag \'subpart\' not {2:s}. (Missing line?)\n'.format(str(InFile), str(Elem.sourceline), str(Tag)))

    else:

        if State['lasttag'] == 'schematic-subparts' or State['lasttag'] == 'connector':
    
            Id = Elem.get('id')
    
            if Id == None:
    
                logger.debug ('FzpProcessSchematicPartsTs4\n    Id none error\n')

                Errors.append('Error 55: File\n\'{0:s}\'\nAt line {1:s}\n\nSubpart has no id\n'.format(str(InFile), str(Elem.sourceline)))
    
            elif Id in FzpDict:
    
                logger.debug ('FzpProcessSchematicPartsTs4\n    subpart Id not unique error\n')

                # error, connector must be unique
    
                Errors.append('Error 56: File\n\'{0:s}\'\nAt line {1:s}\n\nSubpart id {2:s} already exists (must be unique)\n'.format(str(InFile), str(Elem.sourceline), str(Id)))
    
            # End of if Id == None:
    
            Label = Elem.get('label')
    
            if Label == None:
    
                logger.debug ('FzpProcessSchematicPartsTs4\n    Label None error\n')
    
                Errors.append('Error 57: File\n\'{0:s}\'\nAt line {1:s}\n\nSubpart has no label\n'.format(str(InFile), str(Elem.sourceline)))
    
            elif Label in FzpDict:
    
                # not unique error
    
                logger.debug ('FzpProcessSchematicPartsTs4\n    Label Not unique error\n')
    
                DupNameError(InFile, Label, Elem, Errors)
    
            else:
    
                # mark it as seen
    
                logger.debug ('FzpProcessSchematicPartsTs4\n    Mark Label \'%s\' seen\n',Label)
    
                FzpDict[Label] = Label 
    
            # End of if Label in FzpDict:
    
            # Set the subpart id even if it is None so we don't impact the last
            # subpart.
    
            State['lastvalue'] = Id
    
            if (Id + '.subpart') in FzpDict:
    
                # If we already have this subpart id flag an error (note in the
                # case of None, it may be due to other errors.)
    
                logger.debug ('FzpProcessSchematicPartsTs4\n    Id \'%s\' seen already\n',Id)
    
                Errors.append('Error 58: File\n\'{0:s}\'\nAt line {1:s}\n\nSubpart {2:s} already defined (duplicate?)\n'.format(str(InFile), str(Elem.sourceline), str(Id)))
    
            else:
    
                # mark this as a subpart currently with no connections.
    
                logger.debug ('FzpProcessSchematicPartsTs4\n    Id \'%s\' set empty\n',Id)
    
                FzpDict[Id + '.subpart'] = 0

                if not 'subparts' in FzpDict:

                    # Note that we have subparts in the dictionary for svg 
                    # processing. 

                    FzpDict['subparts'] = []

                # End of if not Subparts in FzpDict:

                # Then add this subpart to the list of subpart ids and indicate
                # we haven't yet seen it in the svg. 

                FzpDict['subparts'].append(Id) 
    
            # End of if (Id + '.subpart') in FzpDict:
    
        else:

            # State isn't what we expected, error
    
            logger.debug ('FzpProcessSchematicPartsTs4\n    State error, expected \'schematic-subparts\' or \'connector\' not \'%s\'\n',State['lasttag'])

            Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, expected tag \'schematic-subparts\' or \'connector\' not {2:s}.\n'.format(str(InFile), str(Elem.sourceline), str(State['lasttag'])))

        # End of if State['lasttag'] == 'schematic-subparts' or State['lasttag'] == 'connector':

        State['lasttag'] = Tag

        State['nexttag'] = 'connectors'

    # End of if Tag != 'subpart':

    logger.info ('Exiting FzpProcessSchematicPartsTs4 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def FzpProcessSchematicPartsTs4(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def FzpProcessSchematicPartsTs5(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    logger.info ('Entering FzpProcessSchematicPartsTs5 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    StackTag, StackLevel = TagStack[len(TagStack) - 1]

    Tag = StackTag

    if Tag != 'connectors':

        logger.debug ('FzpProcessSchematicPartsTs5\n    Unexpected Tag \'%s\', expected \'connectors\'\n', Tag)

        # State isn't what we expected, error

        Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nState error expected tag \'connectors\' not {2:s}. Missing line?\n'.format(str(InFile), str(Elem.sourceline), str(Tag)))

    # End of if Tag != 'connectors':

    if State['lasttag'] == 'subpart':

        logger.debug ('FzpProcessSchematicPartsTs5\n    set State[\'nexttag\'] to \'connector\'\n')

        State['lasttag'] = Tag

        State['nexttag'] = 'connector'

    else:

        # State isn't what we expected, error

        logger.debug ('FzpProcessSchematicPartsTs5\n    unexpected state \'%s\' expected \'connector\'\n', Tag)

        Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, expected last tag \'subpart\' not {2:s}.  (Missing line?)\n'.format(str(InFile), str(Elem.sourceline), str(State['lasttag'])))

    # End of if State['lasttag'] == 'subpart':

    logger.info ('Exiting FzpProcessSchematicPartsTs5 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def FzpProcessSchematicPartsTs5(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def FzpProcessSchematicPartsTs6(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    logger.info ('Entering FzpProcessSchematicPartsTs6 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    StackTag, StackLevel = TagStack[len(TagStack) - 1]

    Tag = StackTag

    if Tag != 'connector':

        logger.debug ('FzpProcessSchematicPartsTs6\n    Unexpected Tag \'%s\', expected \'connector\'\n', Tag)

        # State isn't what we expected, error

        Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, expected tag \'connector\' not {2:s}. (Missing line?)\n'.format(str(InFile), str(Elem.sourceline), str(Tag)))

    # End of if Tag != 'connector':

    # Set the Id from the previous value we have seen.

    Id = State['lastvalue']

    if State['lasttag'] == 'connectors' or State['lasttag'] == 'connector':

        # Get the ConnectorId
        
        ConnectorId = Elem.get('id')

        if ConnectorId == None:

            Errors.append('Error 59: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector id missing, ignored\n'.format(str(InFile), str(Elem.sourceline)))

        elif not ConnectorId in FzpDict:

            Errors.append('Error 60: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector {2:s} doesn\'t exist (and it must)\n'.format(str(InFile), str(Elem.sourceline), str(ConnectorId)))

        else:
    
            # Since we set the value as the key as a place holder 
            # intially, check if that is still true (i.e. this isn't 
            # part of another subpart already). 
    
            if FzpDict[ConnectorId + '.id.subpart'] == FzpDict[ConnectorId + '.id.subpart']:

                logger.debug ('FzpProcessSchematicPartsTs6\n    Connector \'%s\' added to bus \'%s\'\n',ConnectorId, Id)
    
                # connector not part of another subpart so mark it as ours. 
                # by writing our subpart Id in to it.
    
                FzpDict[ConnectorId + '.id.subpart'] = Id

                # success, so increase the connector count for this subpart
                # by 1. 

                FzpDict[Id + '.subpart'] += 1

                if not Id + '.subpart.cons' in FzpDict:

                    # Entry doesn't exist so create it.

                    FzpDict[Id + '.subpart.cons'] = []

                # End of if not Id + '.subpart.cons' in FzpDict:

                # Then add this connector to it. 

                if not 'schematic.' + ConnectorId in FzpDict:
    
                    Errors.append('Error 81: File\n\'{0:s}\'\nAt line {1:s}\n\nSubpart connector {2:s} has no pins defined\n'.format(str(InFile), str(Elem.sourceline), str(ConnectorId), str(FzpDict[ConnectorId + '.id.subpart'])))

                else:

                    for Con in FzpDict['schematic.' + ConnectorId]: 

                        # Append the pins associated with this connector to 
                        # the subpart ID list to check when the schematic 
                        # svg is processed later. 

                        FzpDict[Id + '.subpart.cons'].append(Con)

                    # End of for Con in FzpDict['schematic.' + ConnectorId]: 

                # End of if not 'schematic.' + ConnectorId in FzpDict:
    
            else:
    
                # connector is already part of another subpart, flag an error.

                logger.debug ('FzpProcessSchematicPartsTs6\n    connector \'%s\' already in another subpart\n',ConnectorId)
    
                Errors.append('Error 61: File\n\'{0:s}\'\nAt line {1:s}\n\nSubpart connector {2:s} already in subpart {3:s}\n'.format(str(InFile), str(Elem.sourceline), str(ConnectorId), str(FzpDict[ConnectorId + '.id.subpart'])))
    
            # End of if FzpDict[connectorId + '.id.subpart'] == FzpDict[connectorId + '.id.subpart']:

        # End of if ConnectorId == None:

    else:

        # State isn't what we expected, error

        Errors.append('Error 26: File\n\'{0:s}\'\nAt line {1:s}\n\nState error, expected last tag \'connectors\' or \'connector\' not {2:s}.\n'.format(str(InFile), str(Elem.sourceline), str(State['lasttag'])))

    # end of if State['lasttag'] == 'connectors' or State['lasttag'] == 'connector':

    State['lasttag'] = Tag

    State['nexttag'] = 'connector'

    logger.info ('Exiting FzpProcessSchematicPartsTs6 XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def FzpProcessSchematicPartsTs6(InFile, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def FzpCheckConnectors(InFile, Elem, FzpDict, Errors, Warnings, Info, State):

    logger.info ('Entering FzpCheckConnectors\n')

    if not 'pinnos' in FzpDict or len(FzpDict['pinnos']) == 0:

        # no connectors found!

        logger.debug ('FzpCheckConnectors\n    no pinnos found\n')

        Errors.append('Error 62: File\n\'{0:s}\'\n\nNo connectors found to check\n'.format(str(InFile)))

    else:

        # Check that pin numbers start at 0 and are contiguous. 

        if not '0' in FzpDict['pinnos']:

            Warnings.append('Warning 36: File\n\'{0:s}\'\n\nConnector0 doesn\'t exist. Connectors should start at 0\n'.format(str(InFile)))

        # End of if not '0' in FzpDict['pinnos']:

        logger.debug ('FzpCheckConnectors\n    pinnos\n    %s\n',FzpDict['pinnos'])

        for Pin in range(len(FzpDict['pinnos'])):
    
            # Mark an error if any number in sequence doesn't exist as the 
            # connector numbers must be contiguous. 

            logger.debug ('FzpCheckConnectors\n    checking Pin \'%s\'\n', Pin)

            if not 'pinnosmsg' in State:

                # Only output a pin number message once per file.

                if not str(Pin) in FzpDict['pinnos']:

                    logger.debug ('FzpCheckConnectors\n    error, pin \'%s\' not in pinnos\n     %s\n',Pin, FzpDict['pinnos'])

                    Warnings.append('Warning 35: File\n\'{0:s}\'\n\nConnector{1:s} doesn\'t exist when it must to stay in sequence\n'.format(str(InFile), str(Pin)))

                    State['pinnosmsg'] = 'y'

                # End of if not Pin in FzpDict['pinnos']:

            # End of if not 'pinnosmsg' in State:
        
        # End of for pin in range(len(FzpDict['pinnos'])):

    # End of if not pinnos in FzpDict or len(FzpDict['pinnos']) == 0:

    logger.info ('Exiting FzpCheckConnectors\n')

# End of def FzpCheckConnectors(InFile, Elem, FzpDict, Errors, Warnings, Info, State):

def ProcessSvg(FzpType, FileType, InFile, OutFile, CurView, PrefixDir, Errors, Warnings, Info, FzpDict, FilesProcessed, TagStack, State, Debug):

    logger.info ('Entering ProcessSvg\n')

    logger.debug ('ProcessSvg\n    FileType \'%s\'\n    InFile\n     \'%s\'\n    OutFile\n     \'%s\'\n    CurView\n     \'%s\'\n', FileType, InFile, OutFile, CurView)

    # Output a splash screen to differentiate the start of this file
    # being processed. If debug is > 1 it will be larger to be more
    # visable.

    OutputSplashScreen(InFile, Debug)

    # Parse the input document.

    Doc, Root = PP.ParseFile (InFile, Errors)

    logger.debug ('ProcessSvg\n    return from parse\n    Doc\n     \'%s\'\n', Doc)

    if Doc != None:

        logger.debug ('ProcessSvg\n    calling ProcessTree\n    Doc\n     \'%s\'\n', Doc)

        # We have successfully parsed the input document so process it. If
        # this is only an svg file without an associated fzp, the FzpDict 
        # will be empty as there is no fzp data to check the svg against. 

        ProcessTree(FzpType, FileType, InFile, OutFile, CurView, PrefixDir, Root, Errors, Warnings, Info, FzpDict, TagStack, State, Debug)

        if not 'fzp' in FzpDict and 'pcbsvg' in State:
    
            # We don't have a fzp file so check the pcb layers which it would
            # normally do if this is a pcb svg. 

            SvgCheckPcbLayers(InFile, Errors, Warnings, Info, FzpDict, TagStack, State)

        # End of if not 'fzp' in FzpDict:

        PP.OutputTree(Doc, Root, FileType, InFile, OutFile, Errors, Warnings, Info, Debug)

    # End of if Doc != None:

    logger.info ('Exiting ProcessSvg\n')

# End of def ProcessSvg(FzpType, FileType, InFile, OutFile, CurView, PrefixDir, Errors, Warnings, Info, FzpDict, FilesProcessed, TagStack, State, Debug):

def RemovePx(InFile, Elem, Info, Level):

    # Remove the trailing px from a font-size command if present.

    logger.info ('Entering RemovePx XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    pxRegex = re.compile(r'px', re.IGNORECASE)

    FontSize = Elem.get('font-size')

    if not FontSize == None:

        if pxRegex.search(FontSize) != None:

            logger.debug ('RemovePx\n    Removed a px from font-size\n')

            # we have a font size, so see if it has a px and remove it if so.

            FontSize = pxRegex.sub('', FontSize)

            Elem.set('font-size', FontSize)

            Info.append('Modified 1: File\n\'{0:s}\'\nAt line {1:s}\n\nRemoved px from font-size leaving {2:s}\n'.format(str(InFile), str(Elem.sourceline), str(FontSize)))

        # End of if pxRegex.search(FontSize) != None:

    # End of if not FontSize == None:

    logger.info ('Exiting RemovePx XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def RemovePx(InFile, Elem, Info):

def ProcessTspan(InFile, TspanAttributes, TspanText, SeenTspan, Elem, Errors, Warnings, Info, State, Level):

    # Recurse down the tree until we run out of tspan elements (for some
    # reason they can be nested!). Once we hit bottom, we will begin 
    # aquiring attributes and Text to pass back to the next level and then
    # delete the node(s) as we return to eliminate all the tspans.

    logger.info ('Entering ProcessTspan XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug ('ProcessTspan\n    Elem len \'%s\'\n    Tag \'%s\'\n    attributes\n     %s\n    text\n     \'%s\'\n    Elem     %s\n', len(Elem), Elem.tag, Elem.attrib, Elem.text, Elem)

    NameSpaceRegex = re.compile(r'{.+}')

    if len(Elem) > 0:

        # There are more children so recurse to process them.

        for ChildElem in Elem:

            logger.debug ('ProcessTspan\n    Child Elem %s\n', ChildElem)

            Tag = ChildElem.tag

            Tag = NameSpaceRegex.sub('', str(Tag))

            logger.debug ('ProcessTspan\n    removed namespace from Tag \'%s\'\n', Tag)

            if Tag != 'tspan':

                if not SeenTspan == 'n':

                    # We have seen a tspan so issue a warning, as
                    # this is unusual and perhaps wrong.

                    Warnings.append('Warning 26: File\n\'{0:s}\'\nAt line {1:s}\n\nFound Tag {2:s} while removing tspans, likely an error.\n'.format(str(InFile), str(Elem.sourceline), Tag))

                # End of if not SeenTspan == 'n':

                logger.info ('Exiting ProcessTspan XML source line %s Tree Level %s\n', Elem.sourceline, Level)
                    
                return (TspanAttributes, TspanText, SeenTspan)

            # End of if Tag != 'tspan':

            # Found a tspan tag so mark it as seen then recurse to process it. 

            SeenTspan = 'y'

            (TspanAttributes, TspanText, SeenTspan) = ProcessTspan(InFile, TspanAttributes, TspanText, SeenTspan, ChildElem, Errors, Warnings, Info, State, Level + 1)

        # End of for ChildElem in Elem:

    # End of if len(Elem) > 0:

    logger.debug ('ProcessTspan\n    Elem.text\n     \'%s\'\n    Elem %s \n', Elem.text, Elem)

    if Elem.text:

        logger.debug ('ProcessTspan\n    Elem.text\n     \'%s\'\n    Elem %s \n', Elem.text, Elem)

        if TspanText == '':

            TspanText = Elem.text

        else:

            # I don't know if this is possible, but if it is there
            # will be a problem so log an error.

            logger.debug ('ProcessTspan\n    Already text\n     \'%s\'\n    when trying to add text\n     \'%s\'\n', TspanText, Elem.text)

            Errors.append('Error 91: File\n\'{0:s}\'\nAt line {1:s}\n\nTspan removal error, TspanText already has text\n\n\'{2:s}\'\n\nin it.\n'.format(str(InFile), str(Elem.sourceline), TspanText))

        # End of if TspanText == '':

    # End of if not Elem.text == '':

    Attributes = Elem.attrib

    # There are already attribute present so we need to compare and
    # only append new ones. 

    for Attribute in Attributes:

        if  not Attribute in TspanAttributes:

            # attribute not present so add it. 

            TspanAttributes[Attribute] = Elem.get(Attribute)

            logger.debug ('ProcessTspan\n    exit\n     TspanAttributes\n      %s\n     Attribute\n      \'%s\'\n', str(TspanAttributes), Attribute)

        # End of if not Attribute in TspanAttributes:

    # End of for Attribute in Attributes:

    # Now we have the text and attributes, delete this node.

    logger.debug ('ProcessTspan\n    Delete this node.\n     Parent %s\n     This node %s\n', Elem.getparent, Elem)

    Elem.getparent().remove(Elem)

    logger.debug ('ProcessTspan\n    exit\n     TspanAttributes\n      %s\n     TspanText\n      \'%s\'\n', str(TspanAttributes), TspanText)

    logger.info ('Exiting ProcessTspan XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    return (TspanAttributes, TspanText, SeenTspan)

# End of def ProcessTspan(InFile, TspanAttributes, TspanText, SeenTspan, Elem, Errors, Warnings, Info, State, Level):

def RemoveTspanFromText(InFile, TspanAttributes, TspanText, Elem, Errors, Warnings, Info, State, Level):

    logger.info ('Entering RemoveTspanFromText XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug ('RemoveTspanFromText\n    entry\n    Elem %s\n    TspanAttributes\n     %s\n    TspanText\n     \'%s\'\n', Elem, TspanAttributes, TspanText)

    NameSpaceRegex = re.compile(r'{.+}')

    # Remove tspan elements from text if they are present. 

    if len(Elem) == 0:

        # If this node doesn't have children there aren't any tspans so 
        # return as nothing needs to be done.

        logger.debug ('RemoveTspanFromText\n    No children so no tspan. Returning\n')

        logger.info ('Exiting RemoveTspanFromText XML source line %s Tree Level %s\n', Elem.sourceline, Level)

        return  (TspanAttributes, TspanText)

    # End of if len(Elem) == 0:

    # There are children, so see if they are tspans and process them if so. 
    # Mark that we so far haven't seen a tspan.

    SeenTspan = 'n'

    # Check for a xml:space="preserve" attribute and if it is present toss
    # an error because we can't deal with it. 

    if  Elem.get('{http://www.w3.org/XML/1998/namespace}space') == 'preserve':

        Errors.append('Error 92: File\n\'{0:s}\'\nAt line {1:s}\n\nTspan removal error: xml:space=\"preserve\" found.\n'.format(str(InFile), str(Elem.sourceline)))

        return  (TspanAttributes, TspanText)

    # End of if  Elem.get('xml:space') == 'preserve':

    for Elem in Elem:

        Tag = Elem.tag

        Tag = NameSpaceRegex.sub('', str(Tag))

        if Tag == 'tspan':

            (TspanAttributes, TspanText, SeenTspan) = ProcessTspan(InFile, TspanAttributes, TspanText, SeenTspan, Elem, Errors, Warnings, Info, State, Level + 1)

        # End of if Tag == 'tspan':

    # End of for Elem in Elem:

    return (TspanAttributes, TspanText)

    logger.info ('Exiting RemoveTspanFromText XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def RemoveTspanFromText(InFile, TspanAttributes, TspanText, Elem, Errors, Warnings, Info, State, Level):

def ProcessSvgLeafNode(FzpType, FileType, InFile, CurView, PrefixDir, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    logger.info ('Entering ProcessSvgLeafNode XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug ('ProcessSvgLeafNode\n    entry\n    File\n     \'%s\'\n    FileType \'%s\'\n    CurView \'%s\'\n    State\n     %s\n',InFile, FileType, CurView, State)

    logger.debug ('ProcessSvgLeafNode\n    entry\n    Elem\n      \'%s\'\n    Attributes\n      \'%s\'\n    Text\n     \'%s\'\n', Elem, Elem.attrib, Elem.text)

    NameSpaceRegex = re.compile(r'{.+}')

    ConnectorRegex = re.compile(r'connector', re.IGNORECASE)

    ConnectorTermRegex = re.compile(r'connector.+terminal', re.IGNORECASE)

    # Get the id and tag values and remove the namespace if present. 

    Id = Elem.get('id')

    logger.debug ('ProcessSvgLeafNode\n    Id \'%s\'\n', Id)

    # If there is a tag for this node, remove the name space element 
    # from the tag to make later processing easier. 

    Tag = Elem.tag

    Tag = NameSpaceRegex.sub('', str(Tag))

    logger.debug ('ProcessSvgLeafNode\n    removed namespace from Tag \'%s\'\n', Tag)

    CheckGroupConnector(InFile, Elem, Tag, Id, State, Errors)

    if ('ChangeGroupId' in State and State['ChangeGroupId'] != "" and 
         Tag in ['circle', 'ellipse']): 

        Elem.set ('id', State['ChangeGroupId'])

        logger.debug ('ProcessSvgLeafNode\n    changed id to \'%s\'\n', State['ChangeGroupId'])

        State['ChangeGroupId'] = ""

    #End of if ('ChangeGroupId' in State and State['ChangeGroupId'] != "" and 

    if not 'SvgStart' in State:

        # Haven't yet seen the svg start line so check this one. 

        SvgStartElem(InFile, Elem, Errors, Warnings, Info, State, Level)

    # End of if not SvgStart in State:

    # Check if this is the refenence file attribute and if so if it is correct.

    SvgRefFile(FzpType, InFile, Elem, Errors, Warnings, Info, State, Level)

    # First find and set any of Fritzing's layer ids in this element. 

    SvgGroup(InFile, CurView, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)

    # Check we have a layerId before any drawing element.

    SvgCheckForLayerId(Tag, InFile, CurView, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)

    # Then convert any style commands to inline xml (as Fritzing sometimes 
    # doesn't process style commands and the 2 forms are identical). 

    SvgInlineStyle(InFile, Elem, Warnings, State, Level)

    if Tag == 'text':

        logger.debug ('ProcessSvgLeafNode\n    found tag text\n     len(Elem) %d\n', len(Elem))

        if not RemoveTspans == 'n':

            if len(Elem) > 0:

                # This node has children (which may be tspans) so check
                # for and remove tspan elements because Fritzing doesn't 
                # correctly support them.

                # Establish initial value for TspanText
                # as RemoveTspanFromText is recursive and uses them.

                TspanText = ''

                # Establish TspanAttributes as a dict so that new values
                # can be added without overwritting values already there. 

                TspanAttributes = {};

                (TspanAttributes, TspanText) = RemoveTspanFromText(InFile, TspanAttributes, TspanText, Elem, Errors, Warnings, Info, State, Level)

                # At this point all the tspans have been processed 
                # in to TspanAttributes and TspanText so merge them in 
                # to the text node (which is the current Elem). 

                Elem.text = TspanText

                for Attribute in TspanAttributes:

                    # Cycle through the attributes collected from the 
                    # tspan nodes and add them to the attributes of 
                    # this node (ignoring the id attribute). Later 
                    # some may be discarded as unneeded.

                    if not Attribute == 'id':

                        # Overwrite (or add if it is not present) the 
                        # value with the one from the tspan.

                        Elem.set(Attribute, TspanAttributes[Attribute])

                    # End of if not Attribute == 'id':

                # End of for Attribute in TspanAttributes:

                if TspanAttributes or TspanText:

                    # We have modified a tspan element so toss an error so 
                    # the user knows to check the output svg is correct.

                    Info.append('Modified 7: File\n\'{0:s}\'\nAt line {1:d}\n\nA Tspan was removed.\nCheck the output svg is correctly formatted after the change.\n'.format(InFile, Elem.sourceline))

                    if not 'modified' in State:

                        # If we haven't output a modified error yet, do so 
                        # now to tell the user to check the modified svg.

                        Errors.append('Error 94: File\n\'{0:s}\'\n\nThe svg has been modified (details in the Modified section).\nExamine the svg with a svg editor to make sure it is correctly formatted.\n'.format(InFile))

                        # Then note that we have issued this error in state
                        # so it only occurs once per file. 

                        State['modified'] = 'y'

                    # End of if not 'modified' in State:

                # End of if TspanAttributes or TspanText:

            # End of if RemoveTspan == 'y':

        # End of if len(Elem) > 0:

        logger.debug ('ProcessSvgLeafNode\n    end of tspan remove\n    Elem\n      \'%s\'\n    Attributes\n      \'%s\'\n    Text\n     \'%s\'\n',Elem, Elem.attrib, Elem.text)

    # End of if Tag == 'Text':

    # Remove any inheritable attributes (external scripts for pcb generation
    # can't inherit parameters so make them local). 

    SvgRemoveInheritableAttribs(InFile, Elem, Errors, Warnings, Info, State, Level)

    # Remove any px from the font-size commands. 

    RemovePx(InFile, Elem, Info, Level)

    # Check for non supported font-family

    FontFamily = Elem.get('font-family')

    if not FontFamily == None and not FontFamily in ['DroidSans', "'DroidSans'", 'Droid Sans', "'Droid Sans'", 'OCRA', "'OCRA'"]:

        if not 'font.warning' in FzpDict:

            # Issue the warning then mark it as done so it only happens once
            # per file. 

            Warnings.append('Warning 24: File\n\'{0:s}\'\nAt line {1:s}\n\nFont family {2:s} is not Droid Sans or OCRA\nThis won\'t render in Fritzing\n'.format(str(InFile), str(Elem.sourceline), str(FontFamily)))

            FzpDict['font.warning'] = 'y'

        # End of if not 'font.warning' in FzpDict:

    # End of if not FontFamily == None and not FontFamily in ['DroidSans', "'Droid Sans'", "'OCRA'", 'OCRA']:

    # Check if this is a connector terminal definition
    # The str below takes care of comments which aren't a byte string and 
    # thus cause an exception. 

    Term = ConnectorTermRegex.search(str(Id))

    logger.debug ('ProcessSvgLeafNode\n    Term \'%s\'\n    Tag \'%s\'\n', Term, Tag)
    
    if Term != None:

        # This looks to be a terminal definition so check it is a valid type.

        if Tag in ['path' , 'g']: 

            # Note one of the illegal terminalId types is present.

            Errors.append('Error 77: File\n\'{0:s}\'\nAt line {1:s}\n\nterminalId {2:s} can\'t be a {3:s} as it won\'t work.\n'.format(str(InFile), str(Elem.sourceline), str(Id), str(Tag)))

        # End of if Tag in ['path']: 

        # Since this is a terminal, check for height or width of 0 and complain
        # if so. 
            
        Height = Elem.get('height')
            
        Width = Elem.get('width')

        logger.debug ('ProcessSvgLeafNode\n    terminal \'%s\' height / width check\n     height \'%s\'\n    width \'%s\'\n', Id, Height, Width)

        if Height == '0':

            if ModifyTerminal == 'y':

                # Set the element to 10

                Elem.set('height', '10')

                # and log an error to warn the user we made a change that will 
                # affect the svg terminal position so they check it. 

                Info.append('Modified 2: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector {2:s} had a zero height, set to 10\nCheck the alignment of this pin in the svg!\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

                if not 'modified' in State:

                    # If we haven't output a modified error yet, do so 
                    # now to tell the user to check the modified svg.

                    Errors.append('Error 64: File\n\'{0:s}\'\n\nThe svg has been modified (details in the Modified section).\nExamine the svg with a svg editor to make sure it is correctly formatted.\n'.format(InFile))

                    # Then note that we have issued this error in state
                    # so it only occurs once per file. 

                    State['modified'] = 'y'

                # End of if not 'modified' in State:

            else :

                Warnings.append('Warning 16: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector {2:s} has a zero height\nand thus is not selectable in Inkscape\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

            # End of if ModifyTerminal == 'y':

            logger.debug ('ProcessSvgLeafNode\n    terminal \'%s\' 0 height warned or changed\n', Id)

        # End of if Height == '0':

        if Width == '0':

            if ModifyTerminal == 'y':

                # Set the element to 10 and issue an error so the user knows
                # to check the alignment of the terminal (which will have 
                # changed). 

                Elem.set('width', '10')

                Errors.append('Modified 2: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector {2:s} had a zero width, set to 10\nCheck the alignment of this pin in the svg!\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

            else:

                Warnings.append('Warning 16: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector {2:s} has a zero width\nand thus is not selectable in Inkscape\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

            # End of if ModifyTerminal == 'y':

            logger.debug ('ProcessSvgLeafNode\n    terminal \'%s\' 0 width warned or changed\n', Id)

        # End of if Width == '0':
    
    # End of if Term != None:

    # End of if not 'connectors.svg.' + CurView in FzpDict:

    if Id != None and 'fzp' in FzpDict:

        # We are processing an svg from a fzp file so we can do more tests as 
        # we have connector and subpart data in the dict.

        # iconView doesn't have connectors so ignore it. 

        if CurView != None and CurView != 'iconView' and Id in FzpDict['connectors.fzp.' + CurView]:

            if not 'connectors.svg.' + CurView in FzpDict:
        
                # Doesn't exist yet so create it and add this connector.
        
                FzpDict['connectors.svg.' + CurView] = [Id]
        
                logger.debug ('ProcessSvgLeafNode\n    Created \'connectors.svg.%s\' and\n    added \'%s\' to get \'%s\'\n', CurView, Id, FzpDict['connectors.svg.' + CurView])
        
            else:
        
                # Check for a dup connector. While Inkscape won't let you 
                # create one, a text editor or script generated part would ...
        
                if Id in FzpDict['connectors.svg.' + CurView]:
        
                    Errors.append('Error 66: File\n{0:s}\nAt line {1:s}\n\nConnector {2:s} is a duplicate (and should be unique)\n'.format(str(InFile), str(Elem.sourceline), str(Id)))
        
                else:
        
                    # not a dup, so append it to the list. 
        
                    FzpDict['connectors.svg.' + CurView].append(Id)
        
                    logger.debug ('ProcessSvgLeafNode\n    appended \'%s\' to \'connectors.svg.%s\'\n    to get\n     %s\n', Id, CurView, FzpDict['connectors.svg.' + CurView])
        
                # End of if Id in FzpDict['connectors.svg.' + CurView]:

            # End of if not 'connectors.svg.' + CurView in FzpDict:

            if CurView == 'schematicView' and 'subparts' in FzpDict:

                # Get what should be the subpart tag from the tag stack

                if len(TagStack) > 2:
        
                    SubPartTag, StackLevel = TagStack[2]

                else:

                    SubPartTag = 'none'

                # End of if len(TagStack) > 2:

                logger.debug ('ProcessSvgLeafNode\n    SubPartTag \'%s\'\n', SubPartTag)

                if not 'subpartid' in State:

                    # no subpartID present at this time error.

                    Errors.append('Error 82: File\n\'{0:s}\'\nAt line {1:s}\n\nconnector {2:s} isn\'t in a subpart\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

                    logger.debug ('ProcessSvgLeafNode\n    subparts connector \'%s\' not in subpart\n', Id)

                else:

                    logger.debug ('ProcessSvgLeafNode\n    State[\'subpartid\'] \'%s\'\n    SubPartTag \'%s\'\n', State['subpartid'], SubPartTag)
    
                    if not State['subpartid'] == SubPartTag:

                        if SubPartTag == 'none':

                            Errors.append('Error 82: File\n\'{0:s}\'\nAt line {1:s}\n\nconnector {2:s} isn\'t in a subpart\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

                            logger.debug ('ProcessSvgLeafNode\n    subparts connector \'%s\' not in subpart\n', Id)

                        else:

                            Errors.append('Error 83: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector {2:s} shouldn\'t be in subpart {3:s} as it is\n'.format(str(InFile), str(Elem.sourceline), str(Id), str(SubPartTag)))

                            logger.debug ('ProcessSvgLeafNode\n    subparts connector \'%s\' not in correct subpart\n', Id)

                        # End of if SubPartTag == 'none':

                    elif Id in FzpDict[SubPartTag + '.subpart.cons']:

                        # Correct subpart so mark this connector as seen

                        FzpDict[SubPartTag + '.svg.subparts'].append(Id)

                        logger.debug ('ProcessSvgLeafNode\n    connector \'%s\' added to \'FzpDict[%s]\'\n', Id, SubPartTag + '.svg.subparts')

                    else:

                        Errors.append('Error 84: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector {2:s} in incorrect subpart {3:s}\n'.format(str(InFile), str(Elem.sourceline), str(Id), str(SubPartTag)))

                        logger.debug ('ProcessSvgLeafNode\n    subparts connector \'%s\' in wrong subpart \'%s\'\n', Id, SubPartTag)

                    # End of if Id in FzpDict[SubPartTag + ',subpart.cons']:

                # End of if not 'subpartid' in State and not State['subpartid'] == SubPartTag:

            # End of if CurView == 'schematicView' and 'subparts' in FzpDict:

            if CurView == 'pcbView':

                # This is pcbView so check for connectors with ellipses instead
                # of circles

                # As this is only true for through hole parts and we don't yet
                # know if this part is through hole, put this in State for now
                # to be added to Errors only if this turns out to be a through
                # hole part later. 

                RadiusX = Elem.get('rx')

                if RadiusX != None:

                    if not 'hybridsetforpcbView' in State and 'copper0.layerid' in FzpDict and 'copper1.layerid' in FzpDict:

                        # pcb exists and has copper0 and copper1

                        Errors.append('Error 65: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector {2:s} is an ellipse not a circle, (gerber generation will break.)\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

                    else:

                        State['noradius'].append('Error 65: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector {2:s} is an ellipse not a circle, (gerber generation will break.)\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

                    # End of if not 'hybridsetforpcbView' in State and copper0.layerid' in FzpDict and 'copper1.layerid' in FzpDict:

                # End of if RadiusX != None:

                Radius = Elem.get('r')

                # As this is only true for through hole parts and we don't yet
                # know if this part is through hole, put this in State for now
                # to be added to Errors only if this turns out to be a through
                # hole part later. 

                if Radius == None:

                    if not 'hybridsetforpcbView' in State and 'copper0.layerid' in FzpDict and 'copper1.layerid' in FzpDict:

                        # pcb exists and has copper0 and copper1

                        Errors.append('Error 74: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector {2:s} has no radius no hole will be generated\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

                    else:
        
                        # this is only an svg so we don't yet know if this is
                        # a through hole part yet so save the error message
                        # in State until we do.
            
                        State['noradius'].append('Error 74: File\n\'{0:s}\'\nAt line {1:s}\n\nConnector {2:s} has no radius no hole will be generated\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

                    # End of if not 'hybridsetforpcbView' in State and copper0.layerid' in FzpDict and 'copper1.layerid' in FzpDict:

                # End of if Radius != None:

            # End of if CurView == 'pcbView':

        # End of if Id in FzpDict['connectors.fzp' + CurView]:

        if CurView == 'schematicView' and 'subparts' in FzpDict:

            # We are in schematic and it has subparts so check they are 
            # correct.

            if Id in FzpDict['subparts']:

                logger.debug ('ProcessSvgLeafNode\n    start of  subpart Id \'%s\'\n', Id)

                # Mark that we have seen a subpart label with (so far) no 
                # connectors

                if Id + '.svg.subparts' in FzpDict:

                    # Complain about a dup (although this shouldn't be able 
                    # to occur except via manual editing). 

                    logger.debug ('ProcessSvgLeafNode\n    subparts Id \'%s\' duplicate\n', Id)

                    Errors.append('Error 85: File\n\'{0:s}\'\nAt line {1:s}\n\nsubpart label {2:s} is already defined\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

                else:

                    # Create an empty list to contain the connectorids 
                    # for this label for later checking (to make sure they are
                    # all present). 

                    FzpDict[Id + '.svg.subparts'] = []

                    # Then record this subpartid in State for later connector
                    # ids. 

                    State['subpartid'] = Id

                    logger.debug ('ProcessSvgLeafNode\n    Create \'FzpDict[%s]\' and\n   set \'state[\'subpartid\']\' to \'%s\'\n', Id + '.svg.subparts', Id)

                # End of if Id + '.subparts' in FzpDict:

            # End of if Id in FzpDict['subparts']:

        # End of if CurView == 'schematicView' and 'subparts' in FzpDict:

    # End of if Id != None and 'fzp' in FzpDict:

    # Check for inherited attributes and apply them if necessary. 

    SvgSetInheritedAttributes(InFile, Elem, Info, Tag, State, Level)

    # Finally after all the attributes are set, search for font-size commands
    # and remove the trailing px (which Fritzing doesn't like) if it is present.

    RemovePx(InFile, Elem, Info, Level)

    # Then if this is group silkscreen, convert old style white silkscreen
    # (in all its forms) to new style black silkscreen. Warn about and 
    # modify items that are neither black nor white.

    if State['lastvalue'] == 'silkscreen':

        # Create the two color dictionaries

        ColorIsWhite = { 'white': 'y', 'WHITE': 'y', '#ffffff': 'y', '#FFFFFF': 'y', 'rgb(255, 255, 255)': 'y'}

        ColorIsBlack = { 'black': 'y', 'BLACK': 'y', '#000000': 'y', 'rgb(0, 0, 0)': 'y'}

        Stroke = Elem.get('stroke')

        if Stroke in ColorIsWhite:

            Elem.set('stroke', '#000000')

            # Change any non black color to black. 

            Info.append('Modified 3: File\n\'{0:s}\'\nAt line {1:s}\n\nSilkscreen, converted stoke from white to black\n'.format(str(InFile), str(Elem.sourceline)))

        elif not (Stroke == None or Stroke == 'none' or Stroke in ColorIsBlack):

            Info.append('Modified 3: File\n\'{0:s}\'\nAt line {1:s}\n\nSilkscreen stroke color {2:s} isn\'t white or black. Set to black.\n'.format(str(InFile), str(Elem.sourceline), str(Stroke)))

            Elem.set('stroke', '#000000')

        # End of if Stroke in ColorIsWhite:

        Fill = Elem.get('fill')

        if Fill in ColorIsWhite:

            # If the color is currently white or not black set it to black.

            Info.append('Modified 3: File\n\'{0:s}\'\nAt line {1:s}\n\nSilkscreen, converted fill from white to black\n'.format(str(InFile), str(Elem.sourceline)))

            Elem.set('fill', '#000000')

        elif not (Fill == None or Fill == 'none' or Fill in ColorIsBlack):

            # If the current color is neither white nor black (but not none),
            # tell the user so but otherwise ignore it.

            Info.append('Modified 3: File\n\'{0:s}\'\nAt line {1:s}\n\nSilkscreen fill color {2:s} isn\'t white or black. Set to black.\n'.format(str(InFile), str(Elem.sourceline), str(Fill)))

            Elem.set('fill', '#000000')

        # end of if Fill in ColorIsWhite:

    # End of if State['lastvalue'] == 'silkscreen':

    logger.debug ('ProcessSvgLeafNode\n    exit\n    Elem\n      \'%s\'\n    Attributes\n      \'%s\'\n    Text\n     \'%s\'\n',Elem, Elem.attrib, Elem.text)

    logger.debug ('ProcessSvgLeafNode\n    exiting, State\n     %s\n', State)

    logger.info ('Exiting ProcessSvgLeafNode XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def ProcessSvgLeafNode(FzpType, FileType, InFile, CurView, PrefixDir, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def SvgStartElem(InFile, Elem, Errors, Warnings, Info, State, Level):

    logger.info ('Entering SvgStartElem XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    NumPxRegex = re.compile(r'\d$|px$', re.IGNORECASE)

    # Only digits, spaces and zero or one . at a time allowed in a
    # ViewBox value, and it must have 4 values.

    NumDecimalOnlyRegex = re.compile(r'^(\s*\d*\.?\d+\s+)(\d*\.?\d+\s+)(\d*\.?\d+\s+)(\d*\.?\d+\s*)$')

    Tag = Elem.tag

    if Tag == '{http://www.w3.org/2000/svg}svg' or Tag == 'svg':
    
        if 'SvgStart' in State:

            Warnings.append('Warning 17: File\n\'{0:s}\'\nAt line {1:s}\n\nMore than one svg tag found\n'.format(str(InFile), str(Elem.sourceline)))
    
        # End of if 'SvgStart' in State:

        # Mark that we have seen the start tag for later. 

        State['SvgStart'] = 'y'

        Height = Elem.get('height')

        Width = Elem.get('width')

        ViewBox =  Elem.get('viewBox')

        # Check for either a bare number or numberpx as the height or width.

        logger.debug ('SvgStartElem\n    Height \'%s\'\n    Width \'%s\'\n',Height, Width)

        if Height == None:

            # Change to an error as it breaks Fritzing!

            Warnings.append('Warning 18: File\n\'{0:s}\'\nAt line {1:s}\n\nHeight attribute missing\n'.format(str(InFile), str(Elem.sourceline)))

            # Make sure HeightUnits has a value!

            HeightUnits = None

        else:

            HeightUnits = NumPxRegex.search(str(Height))

            logger.debug ('SvgStartElem\n    Height units \'%s\'\n', HeightUnits)

            if HeightUnits != None:

                Warnings.append('Warning 19: File\n\'{0:s}\'\nAt line {1:s}\n\nHeight {2:s} is defined in px\nin or mm is a better option (px can cause scaling problems!)\n'.format(str(InFile), str(Elem.sourceline), str(Height)))

                # Then set the Height to None to skip the scale checks.

                Height = None

            else:

                # Since height isn't px convert it to inches (if it isn't 
                # already.) First grab the HeightUnits value if there is one.

                M = re.search(('\D+$'),Height)

                logger.debug ('SvgStartElem\n    Height \'%s\'\n    M \'%s\'\n', Height, str(M))

                if M:

                    HeightUnits = M.group()

                else:

                    HeightUnits = None

                # End of if M:

                # Then remove it from height to leave only the digits.

                Height = str(re.sub('\D+$','',Height)) 

                logger.debug ('SvgStartElem\n    HeightUnits\'%s\'\n    Height \'%s\'\n', HeightUnits, Height)

                if not HeightUnits == None:

                    if HeightUnits.lower() == 'mm':

                        # Covert to inches after removing the mm from Height

                        Height = re.sub( r'mm','', Height, re.IGNORECASE )

                        # Then convert to inches

                        Height = float(Height) / 25.4
                    
                    elif HeightUnits.lower() == 'cm':

                        Height = re.sub( r'cm','', Height, re.IGNORECASE )

                        Height = float(Height) / 2.54
                    
                    elif HeightUnits.lower() == 'in':

                        Height = re.sub( r'in','', Height, re.IGNORECASE )

                    else:

                        # Flag unknown unit and skip scale check!

                        Warnings.append('Warning 30: File\n\'{0:s}\'\nAt line {1:s}\n\nheight {2:s} is defined in unknown units {3:s}, scale check skipped\n'.format(str(InFile), str(Elem.sourceline), Height, HeightUnits))

                        # Set Height to None to skip check (we are only usingi
                        # it for the check at this point!)

                        Height = None

                    # End of if HeightUnits.lower() == 'mm':

                # End of if not HeightUnits == None:

            # End of if Height != None:

        # End of if Height = None:

        if Width == None:

            # Change to an error as it breaks Fritzing!

            Warnings.append('Warning 18: File\n\'{0:s}\'\nAt line {1:s}\n\nWidth attribute missing\n'.format(str(InFile), str(Elem.sourceline)))

            # Make sure WidthUnits has a value!

            WidthUnits = None

        else:

            WidthUnits = NumPxRegex.search(str(Width))

            logger.debug ('SvgStartElem\n    Width units \'%s\'\n', WidthUnits)

            if WidthUnits != None:

                Warnings.append('Warning 19: File\n\'{0:s}\'\nAt line {1:s}\n\nWidth {2:s} is defined in px\nin or mm is a better option (px can cause scaling problems!)\n'.format(str(InFile), str(Elem.sourceline), str(Width)))

                # Then set the Width to none to skip the scale checks.

                Width = None

            else:

                # Since Width isn't px convert it to inches (if it isn't 
                # already.) First grab the WidthUnits value if there is one.

                M = re.search(('\D+$'),Width)

                logger.debug ('SvgStartElem\n    Width \'%s\'\n    M \'%s\'\n', Width, str(M))


                if M:

                    WidthUnits = M.group()

                else:

                    WidthUnits = None

                # End of if M:

                # Then remove it from Width to leave only the digits.

                Width = str(re.sub('\D+$','',Width)) 

                logger.debug ('SvgStartElem\n    WidthUnits \'%s\'\n    Width \'%s\'\n', WidthUnits, Width)

                if not WidthUnits == None:

                    if WidthUnits.lower() == 'mm':

                        # Covert to inches after removing the mm from Width

                        Width = re.sub( r'mm','', Width, re.IGNORECASE )

                        # Then convert to inches

                        Width = float(Width) / 25.4

                        logger.debug ('SvgStartElem\n    WidthUnits \'%s\'\n    converted Width \'%s\'\n', WidthUnits, Width)
                    
                    elif WidthUnits.lower() == 'cm':

                        Width = re.sub( r'cm','', Width, re.IGNORECASE )

                        Width = float(Width) / 2.54

                        logger.debug ('SvgStartElem\n    WidthUnits \'%s\'\n    converted Width \'%s\'\n', WidthUnits, Width)
                    
                    elif WidthUnits.lower() == 'in':

                        Width = re.sub( r'in','', Width, re.IGNORECASE )

                        logger.debug ('SvgStartElem\n    WidthUnits \'%s\'\n    converted Width \'%s\'\n', WidthUnits, Width)

                    else:

                        # Flag unknown unit and skip scale check!

                        Warnings.append('Warning 31: File\n\'{0:s}\'\nAt line {1:s}\n\nwidth {2:s} is defined in unknown units {3:s}, scale check skipped\n'.format(str(InFile), str(Elem.sourceline), Width, WidthUnits))

                        logger.debug ('SvgStartElem\n    WidthUnits \'%s\' unknown!\n    Width \'%s\'\n', WidthUnits, Width)

                        # Set Width to None to skip check (we are only using
                        # it for the check at this point!)

                        Width = None

                        logger.debug ('SvgStartElem\n    WidthUnits \'%s\' unknown!\n    Width \'%s\'\n', WidthUnits, Width)

                    # End of if WidthUnits.lower() == 'mm':

                # End of if not WidthUnits == None:
                    
            # End of if WidthUnits != None:

        # End of if Width = None:

        if ViewBox == None:

            Errors.append('Error 88: File\n\'{0:s}\'\nAt line {1:s}\n\nviewBox attribute missing\n\n'.format(str(InFile), str(Elem.sourceline)))

        else:

            # We have a viewBox so check it is dimensionless

            if not NumDecimalOnlyRegex.match(ViewBox):

                Errors.append('Error 89: File\n\'{0:s}\'\nAt line {1:s}\n\nViewBox \'{2:s}\'\n\nhas characters other than 0-9, whitespace or \'.\' or not four values.\nIt must be dimensionless and have 4 numeric values\n\n'.format(str(InFile), str(Elem.sourceline), ViewBox))

            else:

                logger.debug ('SvgStartElem\n    Check ViewBox\n    WidthUnits \'%s\'\n   HeightUnits \'%s\'\n', WidthUnits, HeightUnits)

                if not Width == None and not Height == None:

                    # Both Height and Width are in inches so compare them 
                    # to the viewBox values to check the scale is the 
                    # desired 1px is 1 thousandth of an inch. First split
                    # out the 4 view box values.

                    (WidthOrigin, HeightOrigin, WidthLimit, HeightLimit) = ViewBox.split( )    

                    logger.debug ('SvgStartElem\n    split ViewBox \'%s\'\n     WidthOrigin \'%s\'\n    HeightOrigin \'%s\'\n    WidthLimit \'%s\'\n    HeightLimit \'%s\'\n', ViewBox, WidthOrigin, HeightOrigin, WidthLimit, HeightLimit)
        
                    if WidthOrigin != '0' or HeightOrigin != '0':

                        Errors.append('Error 90: File\n\'{0:s}\'\nAt line {1:s}\n\nviewBox origin isn\'t 0 0 but {2:s} {3:s}\n\n'.format(str(InFile), str(Elem.sourceline), WidthOrigin, HeightOrigin))

                    else:

                        # Origin is OK, so check the scale. 

                        Width  = float(Width)

                        Height = float(Height)

                        # Use the math.isclose function to check the scale 
                        # is somewhere close to 1/100 as Inkscape likes to 
                        # play around with the actual sizes a bit. The rel_tol
                        # field allows you to adjust how close close is. 

                        logger.debug ('SvgStartElem\n    Check scale\n    Height \'%s\'\n    Width \'%s\'\n    HeightLimit \'%s\'\n    WidthLimit \'%s\'\n', str(Height * 1000), str(Width * 1000), HeightLimit, WidthLimit)

                        if not math.isclose((Width * 1000),float(WidthLimit),rel_tol=.00001) or  not math.isclose((Height * 1000),float(HeightLimit),rel_tol=.00001):

                            Warnings.append('Warning 32: File\n\'{0:s}\'\nAt line {1:s}\n\nScale is not the desirable 1/1000 ratio from width/height to\nviewBox width/height.\n'.format(str(InFile), str(Elem.sourceline)))

                        # End of if not math.isclose((Width * 100),float(WidthLimit),rel_tol=1) or  not math.isclose((Height * 100),float(HeightLimit),rel_tol=1):
                    
                # End of if not Width == None and not Height == None:

            # End of if not NumDecimalOnlyRegex(viewBox):

        # End of if ViewBox == None:

    else:
    
        if not 'SvgStart' in State:

            Errors.append('Error 67: File\n\'{0:s}\'\nAt line {1:s}\n\nFirst Tag {2:s} isn\'t an svg definition\n\n'.format(str(InFile), str(Elem.sourceline), str(Tag)))

            # then set 'SvgStart' so we don't repeat this warning.

            State['SvgStart'] = 'y'
    
        # End of if not 'SvgStart' in State:

    # End of if Tag == '{http://www.w3.org/2000/svg}svg':

    logger.info ('Exiting SvgStartElem XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def SvgStartElem(InFile, Elem, Errors, Warnings, Info, State, Level):

def SvgRefFile(FzpType, InFile, Elem, Errors, Warnings, Info, State, Level):

    logger.info ('Entering SvgRefFile XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug ('SvgRefFile\n    FzpType \'%s\'\n    InFile\n     \'%s\'\n', FzpType, InFile)
   
    SvgRegex = re.compile(r'^svg\.\w+\.', re.IGNORECASE)
    
    # Check if this is a referenceFile definition.

    Tag = Elem.tag

    logger.debug ('SvgRefFile\n    Tag \'%s\'\n',Tag)

    if Tag != '{http://www.w3.org/2000/svg}referenceFile':

        # No, so return.

        logger.debug ('SvgRefFile\n    not reference file, returning\n')

        return

    # End of if ReferenceFile == None:

    # This is the reference file so get the input file name (minus the path)

    File = os.path.basename(InFile)

    # Remove the trailing .bak if it is present.

    File = re.sub(r'\.bak$','', File)

    logger.debug ('SvgRefFile\n    File\n     \'%s\'\n', File)

    if FzpType == 'FZPPART':

        # This is a part. type file so remove the "svg." from the
        # file name before the compare.

        File = SvgRegex.sub('', File)

        logger.debug ('SvgRefFile\n    Corrected file\n     \'%s\'\n', File)

    # End of if FzpType == 'FZPPART':

    if Elem.text != File:

        # They don't match, so correct it (and log it).

        Info.append('Modified 4: File\n\'{0:s}\'\nAt line {1:s}\n\nReferenceFile\n\n\'{2:s}\'\n\ndoesn\'t match input file\n\n\'{3:s}\'\n\nCorrected\n'.format(str(InFile), str(Elem.sourceline), str(Elem.text), str(File)))

        Elem.text = File

        logger.debug ('SvgRefFile\n    set reference file to\n     \'%s\'\n',Elem.text)

    # End of if ReferenceFile != File:

    logger.info ('Exiting SvgRefFile XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def SvgRefFile(FzpType, InFile, Elem, Errors, Warnings, Info, State, Level):

def SvgCheckForLayerId(Tag, InFile, CurView, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    logger.info ('Entering SvgCheckForLayerId XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug('SvgCheckForLayerId\n    On entry\n    Tag \'%s\'\n    TagStack\n     %s\n    State\n     %s\n', Tag, TagStack, State)

    # Check we have seen a svg definition and a layerId before the first 
    # drawing element. Ignore iconview because it doesn't matter as it isn't
    # processed by Fritzing. 

    if CurView != 'iconView' and not 'SvgFirstGroup' in State and Tag in ['rect', 'line', 'text', 'polyline', 'polygon', 'path', 'circle', 'ellipse',]:

        if not 'SvgStart' in State:

            # If we haven't seen the svg definition flag an error.

            Errors.append('Error 68: File\n\'{0:s}\'\nAt line {1:s}\n\nFound first group but without a svg definition\n'.format(str(InFile), str(Elem.sourceline)))

        # End of if not 'SvgStart' in State:

        # Check if 'defs' exists in TagStack.

        if not any ('defs' in sublist for sublist in TagStack):

            # Mark that we have seen a drawing element

            State['SvgFirstGroup'] = 'y'

            logger.debug('SvgCheckForLayerId\n    XML source line %s\n    Tag \'%s\'\n    found starting tag\n', Elem.sourceline, Tag)

        # End of if not any ('defs' in sublist for sublist in TagStack):
        
        if CurView != 'iconView' and 'SvgFirstGroup' in State and not 'LayerId' in State and not  any ('defs' in sublist for sublist in TagStack):

            logger.debug('SvgCheckForLayerId\n    drawing element before layerid\n    State\n     %s\n', State)

            # Complain about a drawing element before a layerId

            Errors.append('Error 69: File\n\'{0:s}\'\nAt line {1:s}\n\nFound a drawing element before a layerId (or no layerId)\n'.format(str(InFile), str(Elem.sourceline)))

        # End of if CurView != 'iconView' and 'SvgFirstGroup' in State and not 'LayerId' in State and not any ('defs' in sublist for sublist in TagStack): 
                
    # End of if not 'SvgFirstGroup' in State and Tag in ['rect', 'line', 'text', 'polyline', 'polygon', 'path', 'circle', 'ellipse']:

    logger.info ('Exiting SvgCheckForLayerId XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def SvgCheckForLayerId(Tag, InFile, CurView, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def SvgCheckCopperTransform(Id, Transform, State, Level):

    logger.info ('Entering SvgCheckCopperTransform Level %s\n', Level)

    if Transform != None:

        State[Id + '_trans'] = Transform

    else:

        State[Id + '_trans'] = ''

    # End of if Transform != None:

    logger.debug('SvgCheckCopperTransform\n    returned \'%s\' \'%s\'\n', Id + '_trans', State[Id + '_trans'])

    logger.info ('Exiting SvgCheckCopperTransform Level %s\n', Level)

# End of def SvgCheckCopperTransform(Id, Transform, State, Level):

def SvgPcbLayers(Id, InFile, CurView, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    logger.info ('Entering SvgPcbLayers XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug ('SvgPcbLayers\n    State\n     %s\n', State)

    StackTag, StackLevel = TagStack[len(TagStack) - 1]

    # get the first Fritzing tag to BaseTag

    if len(TagStack) > 1:

        BaseTag, StackLevel = TagStack[1]

    else:

        BaseTag = ''

    # End of if len(TagStack) > 1:

    if Id == 'silkscreen':

        if 'seensilkscreen' in State:

            # Already seen is an error. 

            Errors.append('Error 70: File\n\'{0:s}\'\nAt line {1:s}\n\nMore than one silkscreen layer\n'.format(str(InFile), str(Elem.sourceline)))

            logger.debug ('SvgPcbLayers\n    Already seen silkscreen\n    State\n     %s\n', State)

        else:

            # mark it as seen for the future.

            State['seensilkscreen'] = 'y'

            logger.debug ('SvgPcbLayers\n    Mark seen silkscreen\n    State\n      %s\n', State)

            # If we have already seen a copper layer issue a warning as that 
            # makes selection in pcb more difficult. 

            if 'seencopper0' in State or 'seencopper1' in State:

                Warnings.append('Warning 25: File\n\'{0:s}\'\nAt line {1:s}\n\nSilkscreen layer should be above the copper layers for easier selection\nin pcb view\n'.format(str(InFile), str(Elem.sourceline)))

            # End of if 'seencopper0' in State or 'seencopper1' in State:

        # End of if 'seensilkscreen' in State:
            
        if len(TagStack) != 2:

            # Not at the top layer is an error. 

            Errors.append('Error 71: File\n\'{0:s}\'\nAt line {1:s}\n\nSilkscreen layer should be at the top, not under group {2:s}\n'.format(str(InFile), str(Elem.sourceline), str(BaseTag)))
            
        # End of if len(TagStack) != 2:

    # End of if Id == 'silkscreen':

    if Id == 'copper1':

        if 'seencopper1' in State:

            Errors.append('Error 70: File\n\'{0:s}\'\nAt line {1:s}\n\nMore than one copper1 layer\n'.format(str(InFile), str(Elem.sourceline)))

            logger.debug ('SvgPcbLayers\n    Already seen copper1\n    State\n     %s\n', State)

        else:

            # mark it as seen for the future.

            State['seencopper1'] = 'y'

            logger.debug ('SvgPcbLayers\n    Mark seen copper1\n    State\n     %s\n', State)

        # End of if 'seencopper1' in State:

        if len(TagStack) != 2:

            # Not at the top layer is an error but not fatal. 

            Warnings.append('Warning 20: File\n\'{0:s}\'\nAt line {1:s}\n\ncopper1 layer should be at the top, not under group {2:s}\n'.format(str(InFile), str(Elem.sourceline), str(BaseTag)))

        # End of if len(TagStack) != 2:

    # End of if Id == 'copper1':

    if Id == 'copper0':

        if 'seencopper0' in State:

            Errors.append('Error 70: File\n\'{0:s}\'\nAt line {1:s}\n\nMore than one copper0 layer\n'.format(str(InFile), str(Elem.sourceline)))

            logger.debug ('SvgPcbLayers\n    Already seen copper0\n    State\n     %s\n', State)

        else:

            # mark it as seen for the future.

            State['seencopper0'] = 'y'

            logger.debug ('SvgPcbLayers\n    Mark seen copper0\n    State\n     %s\n', State)

        # End of if 'seencopper0' in State:

        if len(TagStack) == 2 and 'seencopper1' in State:

            # Not under copper1 is an error (this is the same level as copper1) 

            Errors.append('Error 72: File\n\'{0:s}\'\nAt line {1:s}\n\ncopper0 should be under copper1 not the same level\n'.format(str(InFile), str(Elem.sourceline)))

        elif len(TagStack) > 3:

            # too many layers is an error.

            Errors.append('Error 73: File\n\'{0:s}\'\nAt line {1:s}\n\nToo many layers, there should only be copper1 then copper0\n'.format(str(InFile), str(Elem.sourceline)))

        # End of if len(TagStack) == 3 and 'seencopper1' in State:

    # End of if Id == 'copper0':

    logger.info ('Exiting SvgPcbLayers XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def SvgPcbLayers(Id, InFile, CurView, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def SvgCheckPcbLayers(InFile, Errors, Warnings, Info, FzpDict, TagStack, State):

    logger.info ('Entering SvgCheckPcbLayers\n')

    # This is only an svg file (we haven't seen the associated fzp)
    # so determine if this is likely SMD and if not output the no
    # hole messages in State and set SMD or Through hole in Info.

    logger.debug ('SvgCheckPcbLayers\n    No fzp file\n    State\n     %s\n', State)

    if 'seencopper0' in State and 'seencopper1' in State:

        # This is a through hole part so note that in Info and 
        # copy any no radius error messages to Errors. 

        Info.append('File\n\'{0:s}\'\n\nThis is a through hole part as both copper0 and copper1 views are present.\n'.format(str(InFile)))


        if State['noradius'] != '':

            # We have seen holes without a radius (which is normal for 
            # smd parts but an error in through hole) so report them 
            # by moving them from State in to Errors.

            for Message in State['noradius']:

                Errors.append(Message)

            # End of for Message in State['noradius']:

        # End of if State['noradius'] != '':

    elif 'seencopper1' in State:

        # This appears to be a normal SMD part so note that in Info.

        Info.append('File\n\'{0:s}\'\n\nThis is a smd part as only the copper1 view is present.\n'.format(str(InFile)))

    elif 'seencopper0' in State:

        # This appears to be a SMD part but on the bottom of the board
        # so note that in Errors.

        Errors.append('Error 75: File\n\'{0:s}\'\n\nThis is a smd part as only the copper0 view is present\nbut it is on the bottom layer, not the top.\n\n'.format(str(InFile)))

    elif 'seensilkscreen' in State:

        # This appears to be only a silkscreen so note that in Info.

        Info.append('File\n\'{0:s}\'\n\nThis is an only silkscreen part as has no copper layers present.\n'.format(str(InFile)))

    else:

        Warnings.append('Warning 21: File\n\'{0:s}\'\n\nThis appears to be a pcb svg but has no copper or silkscreen layers!\n'.format(str(InFile)))

    # End of if 'seencopper0' in State and 'seencopper1' in State:

    logger.info ('Exiting SvgCheckPcbLayers\n')

# End of def SvgCheckPcbLayers(InFile, Errors, Warnings, Info, FzpDict, TagStack, State):

def SvgGroup(InFile, CurView, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

    logger.info ('Entering SvgGroup XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    logger.debug('SvgGroup\n    On entry\n    Errors\n     %s\n    CurView \'%s\'\n    TagStack\n     %s\n    State\n     %s\n', Errors, CurView, TagStack, State)

    NameSpaceRegex = re.compile(r'{.+}')

    # First get the tag to see if we are past the boiler plate and have seen
    # the initial group that starts the actual svg (so we can search for the
    # layerid before any constructs). 

    Tag = Elem.tag

    # Remove the namespace attribute from the tag

    Tag = NameSpaceRegex.sub('', str(Tag))

    Id =  Elem.get('id')
    
    logger.debug('SvgGroup\n    Entry\n    Id \'%s\'\n    TagStack\n     %s\n', Id, TagStack )

    # Pop the tag stack if needed.

    PopTag(Elem, TagStack, Level)

    if RemoveTspans == 'n' and Tag == 'tspan':

        # If tspans aren't set to be removed toss an error if a tspan.

        # but only do it once per file. 

        if not 'SeenTspan' in State:

            Errors.append('Error 63: File\n\'{0:s}\'\nAt line {1:s}\n\ntspan found.\nFritzing doesn\'t support tspans and this will cause Fritzing to hang.\n'.format(str(InFile), str(Elem.sourceline)))

            State['SeenTspan'] = True

         # End of if not SeenTspan in State:

    # End of if RemoveTspans == 'n' and Tag == 'tspan':

    # Check for a Fritzing layerid and record we have seen it.

    if CurView == None:

        # This isn't from an fzp file so we don't have a layerid list to 
        # compare against. So see if this is likely a layerId (this will 
        # sometimes false error when a layerId is nonstandard).

        if Tag == 'defs':

            # Mark we are in defs by pushing it on to the tag stack. 

            TagStack.append([Tag, Level])
    
            logger.debug('SvgGroup\n    pushed \'%s\' on to tag stack\n', Tag)

        # End of if Tag == 'defs':

        if Id in ['breadboard', 'icon', 'schematic', 'silkscreen', 'copper0', 'copper1']:
    
            # Push the Id and Level on to the tag stack.

            TagStack.append([Id, Level])

            # Check it the tag is a group or svg and issue a warning if it 
            # is not. 

            if not Tag == 'g' and not Tag == 'svg':

                Warnings.append('Warning 27: File\n\'{0:s}\'\nAt line {1:s}\n\nFritzing layerId {2:s} isn\'t a group which it usually should be\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

            # End of if not Tag == 'g' and not Tag == 'svg':

            # Set the current layer in to State['lastvalue']
        
            State['lastvalue'] = Id
    
            if Id in ['silkscreen', 'copper0', 'copper1']:

                # Mark that this appears to be a pcb svg in State.

                State['pcbsvg'] = 'y'

                # Then check that the layers are in the correct order.

                SvgPcbLayers(Id, InFile, CurView, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)

            else:

                if 'LayerId' in State:

                    # Single layerId case, but more than one layerId. 

                    Warnings.append('Warning 22: File\n\'{0:s}\'\nAt line {1:s}\n\nAlready have a layerId\n'.format(str(InFile), str(Elem.sourceline)))
    
                    logger.debug('SvgGroup\n    dup layer warning issued\n')

                # End of if 'LayerId' in State:

            # End of if Id in ['silkscreen', 'copper0', 'copper1']:
    
            # and note we have seen a LayerId in State for later.
   
            State['LayerId'] = 'y'

        # End of if Id in ['breadboard', 'icon', 'schematic', 'silkscreen', 'copper0', copper1']:

    else:

        # We are processing svgs from an fzp and have a FzpDict with a list
        # of expected layers.

        if CurView != 'pcbView':

            if CurView == 'schematicView' and 'subparts' in FzpDict:

                # We are in a schematic svg that has subparts so check if this
                # is a subpart id and add it to the tag stack if so. 

                logger.debug('SvgGroup\n    CurView \'%s\'\n    subparts\n     %s\n', CurView, FzpDict['subparts'])

                if Id in FzpDict['subparts']:

                    # Check that schematic is the only thing above this on 
                    # the tag stack and issue a warning if that isn't true.

                    if len(TagStack) != 2:

                        logger.debug('SvgGroup\n    TagStack len \'%s\', not top level warning issued\n', len(TagStack))

                        Errors.append('Error 86: File\n\'{0:s}\'\nAt line {1:s}\n\nSubpart {2:s} isn\'t at the top level when it must be\nFollowing subpart errors may be invalid until this is fixed\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

                    # End of if len(TagStack) != 2:

                    logger.debug('SvgGroup\n    subpart \'%s\' found and added\n', Id)
    
                    # Push the Id and Level on to the tag stack.

                    TagStack.append([Id, Level])
    
                    # Set the current layer in to State['lastvalue']
        
                    State['lastvalue'] = Id

                # End of if Id in FzpDict['subparts']:

            # End of if CurView == 'schematicView' and 'subparts' in FzpDict:

            # Only one layerid so check for it.

            logger.debug('SvgGroup\n    CurView \'%s\'\n    LayerId \'%s\'\n', CurView, FzpDict[CurView + '.LayerId'])

            if Tag == 'defs':

                # Mark we are in defs by pushing it on to the tag stack. 

                TagStack.append([Tag, Level])
    
                logger.debug('SvgGroup\n    pushed \'%s\' on to tag stack\n', Tag)

            # End of if Tag == 'defs':

            if Id == FzpDict[CurView + '.LayerId']:

                # Push the Id and Level on to the tag stack.

                TagStack.append([Id, Level])

                if 'LayerId' in State:

                    # More than one layerid warning. 

                    Warnings.append('Warning 25: File\n\'{0:s}\'\nAt line {1:s}\n\nAlready have a layerId\n'.format(str(InFile), str(Elem.sourceline)))

                else:

                    # and note we have seen a LayerId in State for later.
       
                    State['LayerId'] = 'y'

                    # Set the current layer in to State['lastvalue']
        
                    State['lastvalue'] = Id
        
                    logger.debug('SvgGroup\n    set State[\'lastvalue\'] to \'%s\'\n', Id)

                # End of if 'LayerId' in State:

                # Issue a warning if the layerId isn't a group or svg. 

                if not Tag == 'g'and not Tag == 'svg' :

                    Warnings.append('Warning 27: File\n\'{0:s}\'\nAt line {1:s}\n\nFritzing layerId {2:s} isn\'t a group which it usually should be\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

                # End of if not Tag == 'g'and not Tag == 'svg' :

            # End of if Id == FzpDict[CurView + '.LayerId']:

        else:

            # This is pcbView so the LayerIds are a list, and life is more 
            # complex. For layerids other than copper0 and copper1, they must
            # be at the top of the tagstack (not under another layerid). If 
            # both copper0 and copper1 are present the order should be copper1 
            # copper0 so smd parts are by default on the top layer. So warn
            # about copper1 under copper0 and error for copper0 and copper1 on
            # the same level. 

            logger.debug('SvgGroup\n    ID \'%s\'\n    Curview \'%s\'\n    LayerIds\n     %s\n', Id, CurView, FzpDict[CurView + '.LayerId'])

            if Tag == 'defs':

                # Mark we are in defs by pushing it on to the tag stack. 

                TagStack.append([Tag, Level])
    
                logger.debug('SvgGroup\n    pushed \'%s\' on to tag stack\n', Tag)

            # End of if Tag == 'defs':
    
            if Id in FzpDict[CurView + '.LayerId']:
    
                # Push the Id and Level on to the tag stack.

                TagStack.append([Id, Level])
    
                logger.debug('SvgGroup\n    pushed \'%s\' on to tag stack\n', Id)
    
                # and note we have seen the LayerId in State for later.

                State['LayerId'] = 'y'
    
                State[CurView + 'LayerId'] = 'y'
    
                # Set the current layer in to State['lastvalue']
    
                State['lastvalue'] = Id

                SvgPcbLayers(Id, InFile, CurView, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level)
    
                logger.debug('SvgGroup\n    set State[\'view\'] to \'%s\'\n', Id)

                # Issue a warning if the layerId isn't a group. 

                if not Tag == 'g':

                    Warnings.append('Warning 27: File\n\'{0:s}\'\nAt line {1:s}\n\nFritzing layerId {2:s} isn\'t a group which it usually should be\n'.format(str(InFile), str(Elem.sourceline), str(Id)))

                # End of if not Tag == 'g':
    
            # End of if Id in FzpDict[CurView + '.LayerId']:

        # End of if CurView == None:

        if Id in ['copper0', 'copper1']:

            # If this is copper0 or copper1, check for a transform as a 
            # transform in one but not the other is an error.

            Transform = Elem.get('transform')

            SvgCheckCopperTransform(Id, Transform, State, Level)

        # End of if Id in ['copper0', 'copper1']:

        if 'copper0' in TagStack and 'copper1' in TagStack and State['copper0_trans'] != State['copper1_trans']:

            # We have seen both coppers and they doesn't have  
            # identical transforms so set an error. 

            Errors.append('Error 76: File\n\'{0:s}\'\nAt line {1:s}\n\nCopper0 and copper1 have non identical transforms (no transforms is best)\n'.format(str(InFile), str(Elem.sourceline)))

            logger.debug('SvgGroup\n    set copper transform error\n')

       # End of if 'copper0' in TagStack and 'copper1' in TagStack and State['copper0_trans'] != State['copper1_trans']:

    # End of if CurView == None:

    logger.debug('SvgGroup\n    at exit\n    Errors\n     %s\n    CurView \'%s\'\n    TagStack len \'%s\'\n    TagStack\n     %s\n    State\n     %s\n', Errors, CurView, len(TagStack), TagStack, State)

    logger.info ('Exiting SvgGroup XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def SvgGroup(InFile, CurView, Elem, Errors, Warnings, Info, FzpDict, TagStack, State, Level):

def SvgInlineStyle(InFile, Elem, Warnings, State, Level):

    # If there is a style command in the attributes, convert it to inline
    # xml (overwriting current values if present). 
    
    logger.info ('Entering SvgInlineStyle XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    # Get the current style values if any

    ElemAttributes = Elem.get('style')

    if not ElemAttributes == None: 

        # Delete the current style attribute

        logger.debug ('SvgInlineStyle\n    delete style\n     \'%s\'\n', ElemAttributes)

        Elem.attrib.pop("style", None)

        # Then add the elements back in inline (replacing current values if 
        # present, as style should overide inline values usually). 

        Attributes = ElemAttributes.split(';')

        logger.debug ('SvgInlineStyle\n   XML source line %s\n    attributes\n    %s\n', Elem.sourceline, Attributes)

        for Attribute in Attributes:

            KeyValue = Attribute.split (':')

            logger.debug ('SvgInlineStyle\n    Attribute\n     %s\n    KeyValue \'%s\'\n', Attribute, KeyValue)

            # Then set the pair as attribute=value

            logger.debug ('SvgInlineStyle\n    Attribute\n     %s\n    key len \'%s\'\n    key[0] \'%s\'\n', Attribute, str(len(KeyValue)), KeyValue[0])

            if len(KeyValue) == 2:

                # The attribute has a value so set it. At least one file has
                # a trailing ';' without a tag / value pair which breaks here
                # if this test isn't made. Probably invalid xml but harmless.
                # Whitespace (I think only leading whitespace) in the i
                # attributes also causes this exception so remove any leading
                # white space (because there is at least one file that not 
                # doing so breaks!).

                logger.debug ('SvgInlineStyle\n    before regex\n    KeyValue[0] \'%s\'\n    KeyValue[1] \'%s\'\n', KeyValue[0], KeyValue[1])

                KeyValue[0] = re.sub(r'^\s+','', KeyValue[0])

                KeyValue[1] = re.sub(r'^\s+','', KeyValue[1])

                logger.debug ('SvgInlineStyle\n    after regex\n    KeyValue[0] \'%s\'\n    KeyValue[1] \'%s\'\n', KeyValue[0], KeyValue[1])

                try:
                
                    Elem.set(KeyValue[0], KeyValue[1])

                except ValueError:

                    # This is typically an atribute like
                    # -inkscape-font-specification 'Droid Sans, Normal'
                    # or the previously mentioned trailing ";" and won't be
                    # missed (it is logged here in case there is something
                    # important being deleted at some time!)

                    if not KeyValue[0] in State['KeyErrors']:

                        logger.debug ('SvgInlineStyle\n    KeyValue[0] \'%s\'\n    State\n     %s\n', KeyValue[0], State)

                        # Haven't seen this one yet so log it.

                        Warnings.append('Warning 23: File\n\'{0:s}\'\nAt line {1:s}\n\nKey {2:s}\nvalue {3:s} is invalid and has been deleted\n'.format(str(InFile), str(Elem.sourceline), str(KeyValue[0]),  str(KeyValue[1])))

                        # Then add it to State to ignore more of them

                        State['KeyErrors'].append(KeyValue[0])

                        logger.debug ('SvgInlineStyle\n    attribute \'%s\' value \'%s\' is invalid, deleted\n', KeyValue[0], KeyValue[1])

                    # End of if not KeyValue[0] in State['KeyErrors']:

                # End of try

            # End of if len(KeyValue) == 2:

        # End of for Attribute in Attributes:

    # end of if not ElemAttributes == None: 

    logger.info ('Exiting SvgInlineStyle` XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def SvgInlineStyle(InFile, Elem, Warnings, State):

def SvgRemoveInheritableAttribs(InFile, Elem, Errors, Warnings, Info, State, Level):

    # Some part of Fritzing (probably the script to produce the gerber output)
    # does't deal with inheritance. The case that drove this change (and the
    # only translation currently being done) is to save the svg in Inkscape
    # as optimized svg (rather than plain) at which point the stroke-width
    # attribute is optimized in to copper0 or copper1 top Level and inherited.
    # The output geber missing the stroke-width parameter outputs an oversize
    # nonplated through hole. To fix that we copy the stroke length in to
    # the leaf nodes of all elements of copper0 or copper1 which should fix
    # the problem and allow us to use optimised svg in Inkscape.

    logger.info ('Entering SvgRemoveInheritableAttribs XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    if not (State['lastvalue'] == 'copper0' or State['lastvalue'] == 'copper1'):

        # Not in a pcb copper layer so don't do anything. 

        logger.debug('SvgRemoveInheritableAttribs\n    exiting  unchanged, not pcb group\n')

        return

    # End of if not (State['lastvalue'] == 'copper0' or State['lastvalue'] == 'copper1'):

    # First Convert any style command to inline xml

    SvgInlineStyle(InFile, Elem, Warnings, State, Level)

    # Then see if we have a stroke-width

    StrokeWidth = Elem.get('stroke-width')

    if not StrokeWidth == None:

        # Overwrite any previous value with the current value. 

        State['InheritedAttributes'] = 'stroke-width:' + StrokeWidth

    # End of if StrokeWidth != None:

    logger.debug('SvgRemoveInheritableAttribs\n    set State[\'InheritedAttributes\'] to \'stroke-width:%s\'\n', StrokeWidth)

    logger.info ('Exiting SvgRemoveInheritableAttribs XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def SvgRemoveInheritableAttribs(InFile, Elem, Errors, Warnings, Info, State, Level):

def SvgSetInheritedAttributes(InFile, Elem, Info, Tag, State, Level):

    # Some part of Fritzing (probably the script to produce the gerber output)
    # can't deal with inheritance. The case that drove this change (and the
    # only translation currently being done) is to save the svg in Inkscape
    # as optimized svg (rather than plain) at which point the stroke-width 
    # attribute is optimized in to copper0 or copper1 top level and inherited.
    # The output geber missing the stroke-width parameter outputs an oversize
    # nonplated through hole. To fix that we copy the stroke length in to 
    # the leaf nodes of all elements of copper0 or copper1 which should fix
    # the problem and allow us to use optimised svg in Inkscape.

    logger.info ('Entering SvgSvgSetInheritedAttributes XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    if not (State['lastvalue'] == 'copper0' or State['lastvalue'] == 'copper1'):

        # Not in a pcb copper layer so don't do anything. 

        logger.debug('SvgRemoveInheritableAttribs\n    exiting  unchanged, not pcb group\n')

        return

    # End of if not (State['lastvalue'] == 'copper0' or State['lastvalue'] == 'copper1'):

    logger.debug('SvgRemoveInheritableAttribs\n    State[\'InheritedAttributes\'] %s\n', State['InheritedAttributes'])

    if State['InheritedAttributes'] == None:

        # Nothing to process so just return

        logger.debug('SvgRemoveInheritableAttribs\n    exiting  unchanged, no inherited attributes\n    State[\'InheritedAttributes\']\n     \'%s\'\n', State['InheritedAttributes'])

        return

    # End of if not State['InheritedAttributes'] == None:

    logger.debug ('SvgSetInheritedAttributes\n    on entry\n    attributes\n     %s\n    Tag \'%s\'\n    State[\'InheritedAttributes\'] \'%s\'\n', Elem.attrib, Tag, State['InheritedAttributes'])

    if Tag == 'circle' or Tag == 'path':

        # For now we are only adding the stroke-width to circles or paths
        # in the copper groups as they should be the only two generating 
        # holes.

        # Copy the attribute list in to a string to be split.

        Attributes = State['InheritedAttributes']

        for attribute in Attributes.split(';'):

            KeyValue = attribute.split(':')

            if not Elem.get(KeyValue[0]):

                # if the key doesn't currently exist then add it and its 
                # associated value. 

                logger.debug ('SvgSetInheritedAttributes\n    Set new element key \'%s\'\n    to inherited attribute value \'%s\'\n', KeyValue[0], KeyValue[1])

                Elem.set(KeyValue[0], KeyValue[1])

                # Notify the user that we made a modification to the svg.

                Info.append('Modified 6: File\n\'{0:s}\'\nAt line {1:s}\n\nAdded inherited stroke-width value\n'.format(str(InFile), str(Elem.sourceline)))

            # End of if not Elem.get(KeyValue[0]):

        # End of for attribute in attributes:

    # End of if Tag == 'circle':

    logger.debug ('SvgSetInheritedAttributes\n    exiting\n    Elem attributes\n     %s\n', Elem.attrib)

    logger.info ('Exiting SvgSvgSetInheritedAttributes XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def SvgSetInheritedAttributes(InFile, Elem, Info, Tag, State, Level):
