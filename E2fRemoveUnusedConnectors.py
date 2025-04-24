#!/usr/bin/env python3

# Copyright (c) 2020 Peter Van Epp

# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# Make changes to an svg file (usually renumber the connectors)

# Set cfg.Debug to 0 for normal operation (rename the input file and write the
# pretty printed output to the input file name.
#
# Set cfg.Debug to 1 to not rename the input file and write the output to stdout
# rather than the file for debugging but with no debug messages.
#
# Set cfg.Debug to 2 to not rename the input file and write the output to stdout

# rather than the file for debugging with debug messages for entry and exit
# from routines.
#
# Set cfg.Debug to 3 to not rename the input file and write the output to stdout
# rather than the file for debugging with verbous debug messages for detail
# debugging. This supresses messages from already debugged code to suppress
# clutter in the debug output.
#
# Set cfg.Debug to 4 to output all the debug messages even those suppressed 
# at 3.

# Set the initial cfg.Debug value before getopt runs (which will override this
# value). Used to debug the getopt routines before a cfg.Debug value is set. For
# normal operation, set it to 0 to supress debugging until a debug value is
# set by getopt. To enable debugging getopt, set a value in cfg.Debug.

import FritzingCheckPartCfg as cfg

cfg.Debug = 0

Version = '0.0.1'  # Version number of this file.

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

    con0regex = re.compile(r'connector0pin\+', re.IGNORECASE)

    NameSpaceRegex = re.compile(r'{.+}')

#    print ('line {0:s} Attrib = {1:s}\n'.format(str(Elem.sourceline), str(Elem.attrib)))

    Id = Elem.get('id')

    Tag = Elem.tag

    # remove the namespace from Id and Tag.

    Id = NameSpaceRegex.sub('', str(Id))

    Tag = NameSpaceRegex.sub('', str(Tag))

    if Id != None and IdRegex.search(Id) != None: 

        # Found 'connector'
    
        logger.debug ('DumpTree\n   found connector %s at Line %s\n', Id, Elem.sourceline)

        if Id != None and con0regex.search(Id) != None:

            # This is connector0pin so start numbering.

            State['con_zero_seen'] = True
    
            logger.debug ('DumpTree\n    Found connector0pin. Line %s\n', Elem.sourceline)

        # End of if Id != None and con0regex.search(Id) != None:

        if not State['con_zero_seen']:

            print ('line {0:s} connector \'{1:s}\' deleted as unused.\n'.format(str(Elem.sourceline), str(Id))) 

            # Haven't seen connector0 yet so rename this pin
    
            logger.debug ('DumpTree\n   Renamed connector %s at Line %s\n', Id, Elem.sourceline)

            # first delete the pin from Id

            Id = re.sub(r'pin', '', Id, re.IGNORECASE)

            # Then replace connector with Tag. 

            Id = re.sub(r'connector', Tag, Id, re.IGNORECASE) 
    
            logger.debug ('DumpTree\n   Renamed connector to %s at Line %s\n', Id, Elem.sourceline)

            Elem.set('id', Id)

        # End of if not State['con_zero_seen'] == True:
    
    # End of if Id != None and IdRegex.search(Id) != None: 

    if State['con_zero_seen']:

        # We have seen connector0 so renumber the pins.

        logger.debug ('DumpTree\n    Process Id %s Tag %s\n', Id, Tag)

        # process line.

        Old_Id = Id

        Id = 'connector' + str(State['ConNo']) + 'pin' 

        print ('line {0:s} connector \'{1:s}\' changed to \'{2:s}\'.\n'.format(str(Elem.sourceline), str(Old_Id), str(Id))) 

        Elem.set('id', Id)

        # increase the connector number by 1. 

        State['ConNo'] = State['ConNo'] + 1

        logger.debug ('DumpTree\n    Process to Id %s Tag %s\n', Id, Tag)

    # End of if State['ConSeen']:
    
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

State={'Debug': 0, 'con_zero_seen':False, 'ConSeen': False, 'Expect': 'line', 'ConNo': 0, 'DetailPP': True}

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
    
