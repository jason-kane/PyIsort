# PyYapf

Sublime Text 2-4 plugin to run the [isort](https://github.com/PyCQA/isort) Python import sorter.

## Usage

* Right click in a python window, choose "PyIsort: Sort Imports".

To automatically run isort on the current document before saving, use the `on_save` setting.

## Installation

1.  Install isort (if you haven't already):
   ```
   pip install isort
   ```

2.  Install Sublime Package Control by following the instructions [here](https://packagecontrol.io/installation) (if you haven't already).

3.  `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and choose "Package Control: Install Package".

4.  Find "PyIsort" in the list (type in a few characters and you should see it).

Alternatively, install manually by navigating to Sublime's `Packages` folder and cloning this repository:

      git clone https://github.com/jason-kane/PyIsort.git "PyIsort"

## Problems?

If there is something wrong with this plugin, [add an issue](https://github.com/jason-kane/PyIsort/issues) on GitHub and I'll try to address it.

## Distribution

[Package Control](https://packagecontrol.io/packages/PyIsort)

## Alternatives

This isn't the only Sublime isort plugin.

https://github.com/asfaltboy/sublime-text-isort-plugin
https://github.com/thijsdezoete/sublime-text-isort-plugin
https://github.com/gsemet/python-fiximports/issues
https://github.com/alecthomas/SublimePythonImportMagic
https://github.com/vi4m/sublime_python_imports

None of these appear to be maintained, all either bake in a version of isort or use their own homebrew import sorting algorithm.

This plugin runs the isort you already have installed.  You can use any version you want.  You can upgrade isort whenever you want.  You can install isort extensions.  You can use .isort.cfg or pyproject.toml or any of the other supported isort configuration/customization approaches.

## LICENSE

Apache v2 per LICENSE.  Do what you want; if you fix something please share it.
