# -*- coding: utf-8 -*-
"""
Sublime Text 2-3 Plugin to invoke YAPF on a Python file.
"""
from __future__ import print_function

import fnmatch
import os
import subprocess
import sys
import tempfile

import sublime
import sublime_plugin

from .plugin_helper import Plugin, PreserveSelectionAndView, get_setting

SUBLIME_GTE_3 = sys.version_info >= (3, 0)
KEY = "pyisort"

PLUGIN_SETTINGS_FILE = "PyIsort.sublime-settings"
SUBLIME_SETTINGS_KEY = "PyIsort"


class Isort(Plugin):
    """
    This class wraps isort invocation.

    Includes encoding/decoding and error handling.
    """
    def __enter__(self):
        """Sublime calls plugins 'with' a context manager."""
        self.initialize(
            key=KEY,
            plugin_name="PyIsort",
            settings_file=PLUGIN_SETTINGS_FILE,
            settings_key=SUBLIME_SETTINGS_KEY,
        )

        super().__enter__()

        self.build_popen_args(
            settings_key="isort_command", executables=[
                'isort',
                'isort.exe',
            ]
        )
        self.add_popen_args(["--apply"])

        return self

    def format(self, edit):
        """
        Format imports
        """
        # determine selection to format
        selection = sublime.Region(0, self.view.size())
        self.debug('Formatting selection %r', selection)

        # retrieve selected text
        text = self.view.substr(selection)

        # encode text
        try:
            encoded_text = text.encode(self.encoding)
        except UnicodeEncodeError as err:
            msg = (
                "You may need to re-open this file with a different encoding."
                " Current encoding is %r." % self.encoding
            )
            self.error("UnicodeEncodeError: %s\n\n%s", err, msg)
            return

        file_obj, temp_filename = tempfile.mkstemp(suffix=".py")
        try:
            temp_handle = os.fdopen(file_obj, 'wb' if SUBLIME_GTE_3 else 'w')
            temp_handle.write(encoded_text)
            temp_handle.close()

            self.add_popen_args([temp_filename])
            self.debug('Running %s in %s', self.get_popen_args(), self.popen_cwd)
            try:
                popen = subprocess.Popen(
                    self.get_popen_args(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=self.popen_cwd,
                    env=self.popen_env,
                    startupinfo=self.popen_startupinfo
                )
            except OSError as err:
                # always show error in popup
                msg = "You may need to install isort and/or configure 'isort_command' in PyIsort Settings."
                sublime.error_message("OSError: %s\n\n%s" % (err, msg))
                return

            _, encoded_stderr = popen.communicate()

            if SUBLIME_GTE_3:
                open_encoded = open
            else:
                import codecs
                open_encoded = codecs.open

            with open_encoded(temp_filename, encoding=self.encoding) as fp:
                text = fp.read()
        finally:
            os.unlink(temp_filename)

        self.debug('Exit code %d', popen.returncode)

        # handle errors (since yapf>=0.3, exit code 2 means changed, not error)
        if popen.returncode not in (0, ):
            stderr = encoded_stderr.decode(self.encoding)
            stderr = stderr.replace(os.linesep, '\n')
            self.debug('Error:\n%s', stderr)

            # report error
            err_lines = stderr.splitlines()
            msg = err_lines[-1]
            self.error('%s', msg)
            return

        self.view.replace(edit, selection, text)

        # return region containing modified text
        if selection.a <= selection.b:
            return sublime.Region(selection.a, selection.a + len(text))
        else:
            return sublime.Region(selection.b + len(text), selection.b)


def is_python(view):
    """Cosmetic sugar."""
    return view.score_selector(0, 'source.python') > 0


class IsortDocumentCommand(sublime_plugin.TextCommand):
    """The "yapf_document" command formats the current document."""

    def is_enabled(self):
        """
        Only allow isort for python documents.
        """
        return is_python(self.view)

    def run(self, edit):
        """Sublime Text executes this when you trigger the TextCommand."""
        with PreserveSelectionAndView(self.view):
            with Isort(self.view) as isort:
                isort.format(edit)


class EventListener(sublime_plugin.EventListener):
    """Hook in to detect when a file is saved."""

    def on_pre_save(self, view):  # pylint: disable=no-self-use
        """Before we let ST save the file, run yapf on it."""
        if get_setting('on_save'):
            if view.file_name() and get_setting("onsave_ignore_fn_glob"):
                for pattern in get_setting("onsave_ignore_fn_glob"):
                    if fnmatch.fnmatch(view.file_name(), pattern):
                        print('PyIsort: Skipping sort, matches pattern {}'.format(pattern))
                        return

            view.run_command('isort_document')
