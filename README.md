# setbb, E2fRemoveUnusedConnectors
Make changes to an svg file (usually renumber the connectors)

Set cfg.Debug to 0 for normal operation (rename the input file and write the pretty printed output to the input file name.

Set cfg.Debug to 1 to not rename the input file and write the output to stdout rather than the file for debugging but with no debug messages.

Set cfg.Debug to 2 to not rename the input file and write the output to stdout rather than the file for debugging with debug messages for entry and exit from routines.

Set cfg.Debug to 3 to not rename the input file and write the output to stdout rather than the file for debugging with verbous debug messages for detail debugging. This supresses messages from already debugged code to suppress clutter in the debug output.

Set cfg.Debug to 4 to output all the debug messages even those suppressed at 3.

Set the initial cfg.Debug value before getopt runs (which will override this value). Used to debug the getopt routines before a cfg.Debug value is set. For normal operation, set it to 0 to supress debugging until a debug value is set by getopt. To enable debugging getopt, set a value in cfg.Debug.

# Warning
These scripts are currently fairly rough but it works well enough. They may need to be modified to do what you want
