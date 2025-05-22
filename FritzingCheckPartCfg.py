#!/usr/bin/env python3

# Global storage for the argv command line flags and other status information
# or the FritzingCheckPart.py script. Imported as Cfg.

# variables and their default value.

Repo                = ""            # Default parts repo. Replace this with the
                                    # path to the Fritzing-parts repo. 
                                    # -a override the default repo with the 
                                    # supplied path. 

CheckOnly           = ""            # -c override script name to Check files 
                                    #    only, no modify no backup files.

CopyOnly            = False         # -C Don't process the files, only copy
                                    # input to output (process fzp only to get
                                    # the associated svgs)

OutputCore          = False         # -D force output in core directory format

OutputFzpz          = False         # -F force output in fzpz mode

                                    # -h help (no entry here)

SrcDir              = ""            # -i Input directory

SeparateIcon        = False         # -I enable separate icon file

ModifyTerminal      = True          # -m Disable change terminal size

IssueNameDupWarning = False         # -n Enable dup name warnings

DstDir              = ""            # -o Output directory

OverWrite           = False         # -O Overwrite files

Rename              = False         # -r rename files to base file name. 

                                    # -v fullhelp (no entry here)

DetailPP            = True          # -x Disable detail prettyprinting

# State not set by input flags directly.

FzpType             = None

RenameInFile        = True

FzpType             = None

DirProcessing       = False

BoardType           = ''            # text fo board type for output
                                    # (throughhole, smd, silkscreen, none)

PrefixDir           = ""            # current PrefixDir being processed. 

DirsCreated         = False         # dst directories created
