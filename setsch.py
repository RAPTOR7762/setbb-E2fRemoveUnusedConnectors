import FritzingCheckPartCfg as cfg

cfg.Debug = 0

Version = '0.0.2b'  # Version number of this file.

# Import os and sys to get file rename and the argv stuff, re for regex and 
# logging to get logging support. 

import os, sys, re, logging, getopt

# This library lets me write the lxml output to a string (which apparantly 
# can't be done from lxml) to pretty print it further than lxml does.

from io import BytesIO

# and the lxml library for the xml

from lxml import etree


# Configure the root logger instance, even though we won't be using it
# (we will create loggers for each module) as this is said to be best
# practice.

logging.basicConfig(stream=sys.stderr, format='  %(levelname)s: %(filename)s line %(lineno)d \n   %(message)s', level=logging.DEBUG)

# Import various svg routines and pretty printing routines from the
# support library modules. We need them imported to configure their
# logger routines.

import FritzingToolsw as Fritzing, PPToolsw as PP

# Create a child logger for this routine.

logger = logging.getLogger(__name__)

if cfg.Debug > 2:

    logger.setLevel(logging.DEBUG)
    Fritzing.logger.setLevel(logging.DEBUG)

    # Set the level to DEBUG to debug the pretty printing routines.
    # Supress them as uninteresting at Debug level 3, print them at 4 or
    # higher.

    if cfg.Debug > 3:

        PP.logger.setLevel(logging.DEBUG)

    else:

        PP.logger.setLevel(logging.WARNING)

    # End of if cfg.Debug > 3:

elif cfg.Debug == 2:

    logger.setLevel(logging.INFO)
    Fritzing.logger.setLevel(logging.INFO)

    # Once they are working set them to WARNING to supress clutter.

    PP.logger.setLevel(logging.WARNING)

else:

    # cfg.Debug set to 0 or 1.
    #
    # cfg.Debug = 1 causes the output to be printed to the console rather
    # than to a file with no debug messages for debugging.
    #
    # cfg.Debug = 0 is for normal operation where the output will be written
    # to a file.

    logger.setLevel(logging.WARNING)
    PP.logger.setLevel(logging.WARNING)
    Fritzing.logger.setLevel(logging.WARNING)

# End of if cfg.Debug > 2:

# subroutines.

def DumpTree(Elem, State, level=0):
    
    logger.info (' Entering DumpTree level %s Elem len %s\n', level, len(Elem))

    IdRegex = re.compile(r'connector', re.IGNORECASE)

#    print ('line {0:s} Attrib = {1:s}\n'.format(str(Elem.sourceline), str(Elem.attrib)))

    Id = Elem.get('id')

    if Id != None and IdRegex.search(Id) != None: 

        # Found 'connector'

        State['ConSeen'] = True
    
        logger.debug ('DumpTree\n    Found connector. Line %s\n', Elem.sourceline)

    # End of if Id != None and IdRegex.search(Id) != None: 

    if State['ConSeen']:

        Tag = Elem.tag
    
        logger.debug ('DumpTree\n    Process Id %s Tag %s\n', Id, Tag)

        if Tag == '{http://www.w3.org/2000/svg}line':

            if State['Expect'] != 'line':

                print ('Error: Line: {0:s} Expected line!\n'.format(str(Elem.sourceline)))

            else:

                # process line.

                Id = 'connector' + str(State['ConNo']) + 'pin' 

                Elem.set('id', Id)

                State['Expect'] = 'rect'

            # End of if State['Expect'] != 'line':

        elif Tag == '{http://www.w3.org/2000/svg}rect':

            if State['Expect'] != 'rect':

                print ('Error: Line: {0:s} Expected rect!\n'.format(str(Elem.sourceline)))

            else:

                 # process line.

                Id = 'connector' + str(State['ConNo']) + 'terminal' 

                Elem.set('id', Id)

                # Then set what we expect next. 

                State['Expect'] = 'line'

                # increase the connector number by 1. 

                State['ConNo'] = State['ConNo'] + 1
                     

            # End of if State['Expect'] != 'rect':

        else:

            print ('Error: Line {0:s} neither line nor rect!\n'.format(str(Elem.sourceline)))

        # End of if Tag == '{http://www.w3.org/2000/svg}line':

    # End of if State['ConSeen']:

                



#    for Entry in Elem.attrib:

#        Attrib = Elem.get(Entry)

#        print ('Entry = {0:s} Attrib = {1:s}\n'.format(str(Entry), str(Attrib)))

#        if Attrib != None:

#                print ('Convert = {0:s} \n'.format(str(Attrib)))

            # End of if IdRegex.search(Id) != None:

        # End of if Id != None:

    # End of for Entry in Elem.attrib:

#    if Id != None:

#        if IdRegex.search(Id) != None: 

#            Con = int(''.join(filter(str.isdigit, Id)))

#            if Con < 0:

#                Id = Id.replace(str(Con), str(Con - 16)) 

#                Elem.set('id', Id)

#            print ('Id = {0:s} Con = {1:s}\n'.format(str(Id), str(Con)))


    i = "\n" + level*"  "
    if len(Elem):
        if not Elem.text or not Elem.text.strip():
            Elem.text = i + "  "
        if not Elem.tail or not Elem.tail.strip():
            Elem.tail = i
        for Elem in Elem:
            DumpTree(Elem, State, level+1)
        if not Elem.tail or not Elem.tail.strip():
            Elem.tail = i
    else:
        if level and (not Elem.tail or not Elem.tail.strip()):
            Elem.tail = i

    logger.info (' Exiting DumpTree level %s\n', level)

# end of def DumpTree

# Start of main script:

# Try and parse the input file with lxml and print the contents of the 
# lxml tree generated for debugging purposes. 

# First create the empty Errors array for error messages.

Errors = []

Warnings = []

Info = []

State={'Debug': 0, 'ConSeen': False, 'Expect': 'line', 'ConNo': 0, 'DetailPP': True}

# Get a list of input files from argv (the list will be empty if there 
# aren't any input files) then process them one at a time. 

Files = PP.ProcessArgs (sys.argv, Errors)

if len(Files) > 0:

    for InFile in Files:

        FQOutFile = None

        print ('\n\n***    Process {0:s}    ***\n\n'.format(str(InFile)))

        if cfg.Debug == 0:
    
            InFile, FQOutFile = Fritzing.BackupFilename(InFile, Errors)
    
            logger.debug ('ProcessFzp\n    after BackupFilename\n    InFile\n      \'%s\'\n    FQOutFile\n      \'%s\'\n', InFile, FQOutFile)
    
            if FQOutFile != None:
        
                # Then parse the xml document returning the etree root, or 
                # if errors occur with Doc set to None and the error(s) in 
                # array Errors to be reported.
        
                Doc, Root = PP.ParseFile (InFile, Errors)
        
                if Root != None:
        
                    # If we parsed the file, then dump the tree. 
        
                    DumpTree(Root, State)

                    PP.OutputTree(Doc, Root, "PARTFZP", InFile, FQOutFile, Errors, Warnings, Info, cfg.Debug)
        
                # End of Root != None:
        
            # End of if FQOutFile != None:

        else:
    
            # Then parse the xml document returning the etree root, or 
            # if errors occur with Doc set to None and the error(s) in 
            # array Errors to be reported.
    
            Doc, Root = PP.ParseFile (InFile, Errors)
    
            if Root != None:
    
                # If we parsed the file, then dump the tree. 
    
                DumpTree(Root, State)

                PP.OutputTree(Doc, Root, "SVG", InFile, FQOutFile, Errors, Warnings, Info, cfg.Debug)
    
            # End of Root != None:

        # End of if cfg.Debug == 0:

        # Print the error message to the console.

        PP.PrintErrors(Errors)

        # Then clear Errors for the next file 

        Errors = []

    # End of for File in InFile:

    sys.exit(0)

else:

    # Print the error message to the console.

    PP.PrintErrors(Errors)

# End of if len(InFile) > 0:
    
