# Sublime Text plugin helper

# This is specifically to make plugins that
# run executables on the file being edited easier
# to write.

import os
import shlex
import subprocess
import sys
import textwrap

import sublime

try:
    from shutil import which
except ImportError:
    from backports.shutil_which import which

SUBLIME_GTE_3 = sys.version_info >= (3, 0)

if not SUBLIME_GTE_3:
    # backport from python 3.3
    # (https://hg.python.org/cpython/file/3.3/Lib/textwrap.py)
    def indent(text, prefix, predicate=None):
        """Add 'prefix' to the beginning of selected lines in 'text'.

        If 'predicate' is provided, 'prefix' will only be added to the lines
        where 'predicate(line)' is True. If 'predicate' is not provided,
        it will default to adding 'prefix' to all non-empty lines that do not
        consist solely of whitespace characters.
        """
        if predicate is None:

            def predicate(line):
                return line.strip()

        def prefixed_lines():
            for line in text.splitlines(True):
                yield (prefix + line if predicate(line) else line)

        return ''.join(prefixed_lines())

    textwrap.indent = indent


def dedent_text(text):
    """Strip initial whitespace from text but note how wide it is."""
    new_text = textwrap.dedent(text)
    if not new_text:
        return new_text, '', False

    # determine original indentation
    old_first = text.splitlines()[0]
    new_first = new_text.splitlines()[0]
    assert old_first.endswith(new_first), 'PyYapf: Dedent logic flawed'
    indent = old_first[:len(old_first) - len(new_first)]

    # determine if have trailing newline (when using the "yapf_selection"
    # command, it can happen that there is none)
    trailing_nl = text.endswith('\n')

    return new_text, indent, trailing_nl


def indent_text(text, indent, trailing_nl):
    """Reindent text by `indent` characters."""
    text = textwrap.indent(text, indent)

    # remove trailing newline if so desired
    if not trailing_nl and text.endswith('\n'):
        text = text[:-1]

    return text


class Plugin:

    def __init__(self, view):
        """We are tied to a specific view (an open file in sublime)."""
        self.view = view
        self.key = None
        self.plugin_name = None
        self.settings_file = None
        self.settings_key = None
        self.encoding = None
        self.popen_cwd = None
        self.popen_args = []
        self.popen_env = {}
        self.popen_startupinfo = None
        self.errors = []
        self.custom_style_fname = None

    def initialize(self, key, plugin_name, settings_file, settings_key):
        self.key = key
        self.plugin_name = plugin_name
        self.settings_file = settings_file
        self.settings_key = settings_key
        self._set_encoding()

    def _set_encoding(self):
        # determine encoding
        self.encoding = self.view.encoding()
        if self.encoding in ['Undefined', None]:
            self.encoding = self.get_setting('default_encoding')
            self.debug('Encoding is not specified, falling back to default %r', self.encoding)
        else:
            self.debug('Encoding is %r', self.encoding)

    def __enter__(self):
        self.errors = []
        self.build_popen_cwd()
        self.build_popen_env()
        self.hide_console()
        self.clear_regions()

    def __exit__(self, type, value, traceback):
        return

    def find_command(self, settings_key, executables):
        """Find the executable."""
        # default to what is in the settings file
        cmd = self.get_setting(settings_key)
        cmd = os.path.expanduser(cmd)

        # sublime 2.x support per https://github.com/jason-kane/PyYapf/issues/53
        if hasattr(sublime, "expand_variables"):
            cmd = sublime.expand_variables(cmd, sublime.active_window().extract_variables())

        save_settings = not cmd

        for maybe_cmd in executables:
            if not cmd:
                cmd = which(maybe_cmd)
            if cmd:
                self.debug('Found command: %s', cmd)
                break

        if cmd and save_settings:
            settings = sublime.load_settings(self.settings_file)
            settings.set(settings_key, cmd)
            sublime.save_settings(self.settings_file)

        return cmd

    def debug(self, msg, *args):
        """Logger that will be caught by sublimes ~ output screen."""
        if self.get_setting('debug'):
            print(self.plugin_name + ': ', msg % args)

    def error(self, msg, *args):
        """Logger to make errors as obvious as we can make them."""
        msg = msg % args

        # add to status bar
        self.errors.append(msg)
        self.view.set_status(self.key, 'PyYapf: %s' % ', '.join(self.errors))
        if self.get_setting('popup_errors'):
            sublime.error_message(msg)

    def get_setting(self, key, default_value=None):
        """Wrapper to return a single setting."""
        return get_setting(
            key=key, default_value=default_value, settings_key=self.settings_key, settings_file=self.settings_file
        )

    def build_popen_args(self, settings_key, executables):
        # use shlex.split because we should honor embedded quoted arguments
        self.popen_args = shlex.split(
            self.find_command(settings_key=settings_key, executables=executables), posix=False
        )

    def get_popen_args(self):
        return self.popen_args

    def add_popen_args(self, newargs):
        self.popen_args += newargs

    def build_popen_cwd(self):
        # use directory of current file so that custom styles are found
        # properly
        fname = self.view.file_name()
        self.popen_cwd = os.path.dirname(fname) if fname else None

    def build_popen_env(self):
        """specify encoding in environment"""
        self.popen_env = os.environ.copy()
        self.popen_env['LANG'] = str(self.encoding)

    def clear_regions(self):
        """clear marked regions and status."""
        self.view.erase_regions(self.key)
        self.view.erase_status(self.key)

    def hide_console(self):
        """win32: hide console window."""
        if sys.platform in ('win32', 'cygwin'):
            self.popen_startupinfo = subprocess.STARTUPINFO()
            self.popen_startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
            self.popen_startupinfo.wShowWindow = subprocess.SW_HIDE
        else:
            self.popen_startupinfo = None


if not SUBLIME_GTE_3:

    class PreserveSelectionAndView:
        """
        Context manager to preserve selection and view when text is replaced.

        Sublime Text 2 sucks at this, hence the manual lifting.
        """

        def __init__(self, view):
            """Preserve the view (single open document)."""
            self.view = view
            self.sel = None
            self.visible_region_begin = None
            self.viewport_position = None

        def __enter__(self):
            """Save selection and view."""
            self.sel = list(self.view.sel())
            self.visible_region_begin = self.view.visible_region().begin()
            self.viewport_position = self.view.viewport_position()
            return self

        def __exit__(self, type, value, traceback):
            """Restore selection."""
            self.view.sel().clear()
            for sel in self.sel:
                self.view.sel().add(sel)

            # restore view (this is somewhat cargo cultish, not sure why a
            # single statement does not suffice)
            self.view.show(self.visible_region_begin)
            self.view.set_viewport_position(self.viewport_position)
else:

    class PreserveSelectionAndView:
        """
        Context manager to preserve selection and view when text is replaced.

        Sublime Text 3 already does a good job preserving the view.
        """

        def __init__(self, view):
            """Preserve view."""
            self.view = view
            self.sel = None

        def __enter__(self):
            """Save selection."""
            self.sel = list(self.view.sel())
            return self

        def __exit__(self, type, value, traceback):
            """Restore selection."""
            self.view.sel().clear()
            for sel in self.sel:
                self.view.sel().add(sel)


def get_setting(key, default_value=None, settings_key=None, settings_file=None):
    """Retrieve a key from the settings file."""
    # 1. check sublime settings (this includes project settings)
    settings = sublime.active_window().active_view().settings()
    try:
        config = settings.get(settings_key)
    except TypeError as err:
        print('Unable to settings.get(%s)' % (settings_key))
        raise
    if config is not None and key in config:
        return config[key]

    # 2. check plugin settings
    settings = sublime.load_settings(settings_file)
    return settings.get(key, default_value)
