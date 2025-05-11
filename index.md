---
layout: default
---

# What is Fritzing?

* * *

[Fritzing](https://fritzing.org) is an [open source initiative](http://www.opensource.org/docs/osd) to develop amateur or hobby CAD software for the design of electronics hardware, intended to allow designers and artists to build more permanent circuits from prototypes. It was developed at the University of Applied Sciences Potsdam. Fritzing is free software under the [GPL 3.0](https://www.gnu.org/licenses/gpl-3.0.en.html) or later license, with the source code available on [GitHub](https://github.com/fritzing/fritzing-app) and the binaries at a monetary cost, which is allowed by the GPL.

# About the python scripts

* * *

## Running the scripts
There are a few ways to run the script, and I'll list three of them:

### Windows (Python Interpreter)
In command prompt (assuming you have installed python and added it to path!), run

```
pip install lxml
```

With the LXML library installed, cd to the location where you have stored the scripts, and run

```
python [ScriptName].py [Filename].svg
```

### Windows (cygwin)
For cygwin you need to install [cygwin](https://cygwin.org). Use the setup program as detailed on cygwin website. The basic install with the following additions does fine:

```
python3: Py3K language interpreter 
python3-lxml: Python XML2/XSLT bindings
```

(and all their associated dependencies)
with that in place from a cygwin terminal copy the python scripts

```
FritzingCheckPartCfg.py
setbb.py
setsch.py
E2fRemoveUnusedConnectors.py
FritzingToolsw.py
PPw.py
PPToolsw.py
```

to `/usr/local/bin`
`chmod ugo+x /usr/local/bin/*.py`

### Linux (Ubuntu 16.04 LTS)
It appears that there are different instructions to installing this, so I'll list both ways

**Peter Van Epp**: copy the py scripts to /usr/local/bin via sudo:

```
sudo cp FritzingCheckPartCfg.py /usr/local/bin 
sudo cp setbb.py /usr/local/bin
sudo cp setsch.py /usr/local/bin
sudo cp E2fRemoveUnusedConnectors.py /usr/local/bin
sudo cp FritzingToolsw.py /usr/local/bin 
sudo cp PPw.py /usr/local/bin 
sudo cp PPToolsw.py /usr/local/bin
```

`chmod ugo+x /usr/local/bin/*.py`

The Ubuntu install appears to have lxml and python 3 already installed
Note the script has problems with unicode under python 2.7 and probably won't run there without modification (which I don't know how to make). 
