#!/usr/bin/env python3

# The support routines for pretty printing Fritzing svg files (and possibly
# other xml as well.)

# Enable detail pretty printing of svg files. If you suspect the detail pretty
# printing is causeing problems, set this to 'n' to disable detail pretty 
# printing (and if that fixes it, please report the bug).

DetailPP = 'Y'

Version = '0.0.2'  # Version number of this file.

# Import os and sys to get file rename and the argv stuff, re for regex and 
# logging to get logging support. 

import os, sys, re, logging 

# This library lets me write the lxml output to a string (which apparantly
# can't be done from lxml) to pretty print it further than lxml does.

from io import BytesIO

# and the lxml library for the xml parsing.

from lxml import etree

# Establish a local logger instance for this module.

logger = logging.getLogger(__name__)

# Define a XML pretty printer function because the system supplied one doesn't
# pretty print the svg stuff correctly and this does (at least so far).
# Obtained from:

# http://effbot.org/zone/element-lib.htm#prettyprint

def Indent(Elem, Debug, Level=0):

    logger.info ('Entering Indent XML source line %s Tree Level %s\n', Elem.sourceline, Level)

    I = "\n" + Level*"  "
    if len(Elem):
        if not Elem.text or not Elem.text.strip():
            Elem.text = I + "  "
        if not Elem.tail or not Elem.tail.strip():
            Elem.tail = I
        for Elem in Elem:
            Indent(Elem, Debug, Level+1)
        if not Elem.tail or not Elem.tail.strip():
            Elem.tail = I
    else:
        if Level and (not Elem.tail or not Elem.tail.strip()):
            Elem.tail = I

    logger.info ('Exiting Indent XML source line %s Tree Level %s\n', Elem.sourceline, Level)

# End of def Indent(Elem, Debug, Level=0):

# A splitting subroutine that will split only on blanks not in a quoted 
# string (the only one in the thread that will do so without either eating
# the quotes or putting them in a separate item neither of which will do here)
# from:
#
# http://stackoverflow.com/questions/79968/split-a-string-by-spaces-preserving-quoted-substrings-in-python
#
# modified to also ignore spaces in text by matching '>.+?</text' as well as 
# '".+?"' so it doesn't break text strings with blanks in them. As well it 
# substitues a blank in front of the '>.+?</text' so that it will be split
# on to a new line by splitter, making it more readable. This works by
# first substituting '\x00' for the blanks we want to ignore (i.e. those in
# quoted strings and text), splitting on blanks, then substituting the '\x00'
# for a blank again after the split. Very clever!   

def Splitter(S, Debug):
 
    logger.info ('Entering Splitter\n')

    # Replace ' ' with \x00 in places we don't want to split on the blank
    # (inside quoted strings and in text elements)

    def Replacer(M):
        return M.group(0).replace(" ", "\x00")

    # Replace the text string '>.+?<\/text>' by ' >.+?<\/text>' so the the 
    # text will be split on to a new line (even if there wasn't a space 
    # there before, which in ours is usually the case, it is on a line with 
    # a grom. 

    T = re.sub(r'(>.+?<\/text>)', ' \g<1>', S)

    # Do the same for tspan

    T = re.sub(r'(>.+?<\/tspan>)', ' \g<1>', S)


    # Do this with a trailing blank for comments to so the following element
    # is correctly indented on a new line.

    T = re.sub(r'(<!--.+?-->)', '\g<1> ', S)

    # Now replace the blanks in quoted strings, text, comments and 
    # referenceFile (all of which contain blanks we need to keep) with \x00 
    # then split the string on blanks. 

    Parts = re.sub(r'".+?"|>.+?<\/text>|>.+?<\/tspan>|<!--.+?-->|referenceFile\s*>.+?</\s*referenceFile', Replacer, T).split()

    # Then substitute the \x00 for blanks again in all the resulting strings. 

    Parts = [P.replace("\x00", " ") for P in Parts]

    logger.info ('Exiting Splitter\n')

    return Parts

# End of def Splitter(S, Debug):

def PrettyPrintElements(XmlIn, Errors, Warnings, Debug):

    # Given the pretty printed (to the element level) xml from lxml, split the
    # elements within an element in to one per line with the correct indenting.
    # Then return the adjusted string to be written to the output file. 

    logger.info ('Entering PrettyPrintElements\n')

    # Since we are processing in a loop, compile our regexes for efficiency. 

    # A regext to match the initial xml def if present

    XmlRegex = re.compile(r'^<\?xml')

    # A regex to match and save the leading whitespace

    LeadingWhiteSpaceRegex = re.compile(r'^(\s*)')

    # A regex to match the most common end tag.

    EndTagRegex = re.compile(r'\/>$')

    if Debug > 3:

        # Really high debug level, so print the input xml.

        logger.debug ('PrettyPrintElements\n     XmlIn\n\n%s\n\n', XmlIn)

    # End of if Debug > 3:

    # Set up the output string initially empty

    XmlPP = ''

    # Set that we haven't seen an EndTag in case there isn't one (or more 
    # correctly we can't deal with the end tag present). 

    EndTag = None

    # The output library emits a blank line at the end of the xml. There 
    # shouldn't be any blank lines in the xml, so keep a counter of blank
    # lines. If it is non zero when we still have another line throw an 
    # error.

    BlankLines = 0

    for Line in XmlIn.split('\n'):

        # if this is the xml definintions line (the first line), pass it 
        # through to the output string unchanged.  

        if (XmlRegex.search(Line)):

            logger.debug ('PrettyPrintElements\n     Pass xml def through\n')

            XmlPP = XmlPP + Line + '\n'

        else :

            # First get the leading whitespace (if any) and save it 
            # for later use

            WhiteSpace = LeadingWhiteSpaceRegex.search(Line)            

            LeadingWhiteSpace = WhiteSpace.group(1)

            # Then remove the initial white space from the line to leave
            # only the elements. 

            Line = LeadingWhiteSpaceRegex.sub('', Line)

            if Line == '':
                
                BlankLines += 1

            elif BlankLines == 1:

                # Only warn about a blank line in the XML once per file. I
                # have a svg from Illustrator that has many of these and 
                # the large number of warnings are an annoyance. 

                Warnings.append('Error 33: Blank line in the output XML before line\n\'{0:s}\'\n'.format(Line))

            # End of if Line == '':

            logger.debug ('PrettyPrintElements\n    Input line\n     \'%s\'\n', Line)

            # Use splitter (again from stackoverflow) to split only 
            # on blanks not inside a quoted string.

            Items = Splitter(Line, Debug)

            logger.debug ('PrettyPrintElements\n    Split line\n     \'%s\'\n', Items)

            # The first element of the list is the tag name for this 
            # element so (if the list exists) pop the first element of 
            # the list in to variable Tag to keep to match the end tag 
            # if we need to and write the tag value to XmlPP with only 
            # the leading whitespace and no indentation. 

            if len(Items) == 0:

                # Null element, shouldn't occur but it will be warned about
                # earlier so do nothing here (except if debug is enabled)
                # which also keeps python happy about the indentation. 

                logger.debug ('PrettyPrintElements\n    Error, blank field in line\n')

            elif len(Items) == 1:

                # There is only one element so just copy it to the output 
                # with out any additional indentation. 

                XmlPP = XmlPP + LeadingWhiteSpace + Items[0] + '\n'

            else:

                # This is the first element of a multi element list and
                # thus is the opening tag, so copy it to the output 
                # without further indentation. 

                XmlPP = XmlPP + LeadingWhiteSpace + Items[0] + '\n'

                # Then remove it from the input. 

                Items.pop(0)

                # Now move to the end of the list to remove the closing
                # tag if present. Note this ignores end tags of the form 
                # </text> and the like, both because I was unsuccessful
                # matching them and because removing </text> breaks the
                # text formating. They seem to be rare enough to ignore 
                # for now.

                RegexMatch = EndTagRegex.search(Items[len(Items) - 1])

                if RegexMatch != None:

                    EndTag = RegexMatch.group(0)

                    logger.debug ('PrettyPrintElements\n    Last element Endtag \'%s\'\n', EndTag)

                    # Then remove the end tag from the list element. 

                    Items[len(Items) - 1] = EndTagRegex.sub('', Items[len(Items) - 1])

                else:

                    logger.debug ('PrettyPrintElements\n     regex no match\n      \'%s\'\n', Items[len(Items) - 1])

                # End of RegexMatch != None:

                logger.debug ('PrettyPrintElements\n    Modified last element \'%s\'\n', Items[len(Items) - 1])

                for Item in Items:

                    # Then print the elements (with a 2 space indent),
                    # one to a line. 

                    XmlPP = XmlPP + LeadingWhiteSpace + '  ' + Item + '\n'

                # End of for Item in Items:

                # Then, assuming we have an end tag (which we usually
                #  should) print it without the 2 space indent.

                if EndTag != None:

                    XmlPP = XmlPP + LeadingWhiteSpace + EndTag + '\n'

                    # Then clear the EndTag to indicate we have finished
                    # with it,

                    EndTag = None

                # End of if EndTag != None:

            # End of if len(Items) == 0:

        # end of if (XmlRegex.search(Line)):

    # End of for Line in XmlIn.split('\n'):

    logger.info ('Exiting PrettyPrintElements\n')

    return (XmlPP)

# End of def PrettyPrintElements(XmlIn, Errors, Warnings, Debug):

def OutputTree(Doc, Root, FileType, InFile, OutFile, Errors, Warnings, Info, Debug):

    # Prettyprint the xml and write it to a file or the console (depending on
    # the debug setting). If OutFile is None rename the InFile to InFile.bak
    # and write the new data to InFile.  

    logger.info ('Entering OutputTree\n')

    # Do a rough (to the element level) pretty print of the document.
    # (this is all we will do for an fpz file). 

    Root = Indent(Root, Debug)
 
    # now use an answer from stackoverflow to get the properly formatted 
    # xml definition xml to a string using BytesIO (as lxml doesn't seem 
    # to be able to write this to a string directly)
	
    Xml = BytesIO()
	
    Doc.write(Xml, xml_declaration=True, encoding=Doc.docinfo.encoding, standalone=Doc.docinfo.standalone)
	
    # again use a couple of stackoverflow answers to get that to a splitable 
    # string
	
    ByteStr  = Xml.getvalue()
	
    # Then convert the bytes stream to a string for processing.
	
    XmlIn = ByteStr.decode(Doc.docinfo.encoding)
	
    if FileType == 'SVG' and DetailPP == 'Y':

        # If this is an svg file (as opposed to an fpz file) then do a 
        # a finer grained pretty print inside the elements as well.

        logger.debug('OutputTree\n     doing element level pretty print\n')

        XmlPP = PrettyPrintElements(XmlIn, Errors, Warnings, Debug)        

    else:

        # We aren't detail pretty printing so just copy input to output.

        XmlPP = XmlIn

    # End of if FileType == 'SVG':


    logger.debug('OutputTree\n    Start OutFile\n     \'%s\'\n    Debug %s\n', OutFile, Debug)

    if Debug != 0:

        # We are debugging so print the output to sysout rather than a file
        # and do not rename (or change) the input file but do print the 
        # filename we would have used if sending it to a file. 

        if OutFile == None:

            # OutFile None will go to the input filename

            print ('Output would go to file:\n\n{0:s}\n\n'.format(InFile))

        else:
    
            # otherwise it will go to the OutFile as expected.

            print ('Output would go to file:\n\n{0:s}\n\n'.format(OutFile))

        # End of if OutFile == None:

        print (XmlPP)

    else:

        # Normal operation, if OutFile is None rename the input file to 
        # filename.bak and write the xml to a new file with the original 
        # filename. 

        logger.debug('OutputTree\n     Normal operation\n      OutFile\n       \'%s\'\n      Debug %s\n', OutFile, Debug)

        if OutFile == None:

            # rename the input file to .bak to preserve it, freeing the input
            # filename to accept our modifed xml.

            try:

                os.rename (InFile, InFile + '.bak')

            except os.error as e:

                Errors.append('Error 1: Can not rename {0:s} {1:s} ({2:s})\n'.format(str( e.filename), e.strerror, str(e.errno)))

                # Couldn't rename the file, can't proceed so set the error
                # and return.

                Doc = None

                return

            else:

                # Set the output file to the Input file name (now renamed)

                OutFile = InFile

            # End of try:

        # End of if OutFile == None:
 
        # now open the output file 

        logger.debug('OutputTree\n     opening OutFile\n       \'%s\'\n', OutFile)

        try:

            f = open(OutFile, 'w')

        except os.error as e:

            logger.debug('OutputTree\n     open error \'%s\'\n', e.strerror)

            Errors.append('Error 2: Can not open {0:s} {1:s} ({2:s})\n'.format(str( e.filename), e.strerror, str(e.errno)))

        else:

            try:

                logger.debug('OutputTree\n     write\n')

                # and write the xml to it.

                f.write(XmlPP)

            except os.error as e:

                logger.debug('OutputTree\n     write error \'%s\'\n', e.strerror)

                Errors.append('Error 3: Can not write {0:s} {1:s} ({2:s})\n'.format(str( e.filename), e.strerror, str(e.errno)))

            else:

                try:

                    logger.debug('OutputTree\n     write\n')

                    f.close()

                except os.error as e:

                    logger.debug('OutputTree\n     close error \'%s\'\n', e.strerror)

                    Errors.append('Error 4: Can not close {0:s} {1:s} ({2:s})\n'.format(str( e.filename), e.strerror, str(e.errno)))

                # End of try f.close()

            # End of try f.write(XmlPP)

        # End of try f.open((OutFile, 'w')

    # End of if Debug != 0:

    logger.info ('Exiting OutputTree\n')

# End of def OutputTree(Doc, Root, FileType, InFile, OutFile, Errors, Warnings, Info, Debug):

def ParseFile (File, Errors):

#  Parse the xml document and return either the root of the document or None
#  and the error message(s) in Errors.

    logger.info ('Entering ParseFile\n')

    # Set Doc and Root to none in case of error.

    Doc = None

    Root = None

    try:

        parser = etree.XMLParser(remove_blank_text=True)

        Doc = etree.parse(File, parser)

    except IOError:

        Errors.append('Error 5: ParseFile can\'t read file {0:s}\n'.format(str(File)))    

        logger.info ('Exiting ParseFile on no file error\n')

        return None, Root

    except etree.XMLSyntaxError:

        Errors.append('Error 6: ParseFile error parsing the input xml file {0:s}\n'.format(str(File)))

        logger.debug ('ParseFile\n parse error\n     parser.error_log\n       \'%s\'\n', parser.error_log)

        if len(parser.error_log):

            for error in parser.error_log:

                # Extract and log the errors the parser is reporting. 

                Errors.append('{0:s}\n'.format(str(error)))

            # End of for error in parser.error_log:

        # End of if len(parser.error_log):

        logger.info ('Exiting ParseFile on parser error\n')

        # Then return Doc as None to indicate an error occurred.

        return None, Root

    # End of try:

    # If we got here we have successfully parsed the document so get it's
    # root. 

    Root = Doc.getroot()

    logger.info ('Exiting ParseFile with doc parsed\n')

    return Doc, Root

# End of def ParseFile (File, Errors):

def PrintInfo(Info):

    logger.info ('Entering PrintInfo\n')

    if len(Info) != 0:

        for Infodata in Info:

            # There is Info so print them to the console.

            print (Infodata)

        # End of for Infodata in Info:

    # End of if len(Info) != 0:

    logger.info ('Exiting PrintInfo\n')

# end of def PrintInfo(Info):

def PrintWarnings(Warnings):

    logger.info ('Entering PrintWarnings\n')

    if len(Warnings) != 0:

        for Warning in Warnings:

            # There are warnings so print them to the console.

            print (Warning)

        # End of for Warning in Warnings:

    # End of if len(Warnings != 0):

    logger.info ('Exiting PrintWarnings\n')

# End of def PrintWarnings(Warnings):

def PrintErrors(Errors):

    logger.info ('Entering PrintErrors\n')

    if len(Errors) != 0:

        # First print a line to space the error messages.

        print('\n')

        for Error in Errors:

            # There are errors so print them to the console.

            print (Error)

        # End of for Error in Errors:

    # End of if len(Errors != 0):

    logger.info ('Exiting PrintErrors\n')

# End of def PrintErrors(Errors):

def ProcessArgs (Argv, Errors):

    # Process the input arguments on the command line. 

    logger.info ('Entering ProcessArgs\n')

    # Create an empty InFile list (in case of more than one input file)

    InFile = []

    if len(sys.argv) < 2:

        # No input file so print a usage message and exit.

        Errors.append('Usage: {0:s} filename (filename ...)\n'.format(str(sys.argv[0])))

        return(InFile)

    # End of if len(sys.argv) < 2:

    for File in sys.argv:

        # Skip the program name entry

        if File != sys.argv[0]:

            if not os.path.isfile(File):

                # Input file isn't valid, note that, ignore it and proceed. 

                Errors.append('Error 8: {0:s} isn\'t a file: ignored\n'.format(str(File)))

            else:

                InFile.append(File)

            # End of if not os.path.isfile(File):

        # End of if File not sys.argv[0]:

    # End of for File in sys.argv:

    logger.debug ('ProcessArgs\n     return\n      InFile\n       \'%s\'\n', InFile)

    logger.info ('Exiting ProcessArgs\n')

    return InFile 

# End of def ProcessArgs (Argv, Errors):
