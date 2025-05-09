<!--
 | Theme based on GitHub Pages slate theme
 |
 | @see https://github.com/pages-themes/slate
 | @see https://github.com/pages-themes/slate/blob/master/LICENSE
-->

---
layout: default
---

<div id="header_wrap" class="outer">
  <header class="inner">
    <a id="forkme_banner" href="https://github.com/RAPTOR7762/setbb-E2fRemoveUnusedConnectors">View on GitHub</a>
    <img src="assets/fritzing.svg" style="float: left; box-shadow: none; border: none; padding-right: 2em" />
    <h1 id="project_title">Fritzing Parts Graphics-Python Scripts</h1>
    <h2 id="project_tagline">Make changes to an svg file</h2>
  </header>
</div>

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
