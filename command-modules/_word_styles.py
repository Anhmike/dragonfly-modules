﻿#
# This file is part of Dragonfly.
# (c) Copyright 2007, 2008 by Christo Butcher
# Licensed under the LGPL.
#
#   Dragonfly is free software: you can redistribute it and/or modify it 
#   under the terms of the GNU Lesser General Public License as published 
#   by the Free Software Foundation, either version 3 of the License, or 
#   (at your option) any later version.
#
#   Dragonfly is distributed in the hope that it will be useful, but 
#   WITHOUT ANY WARRANTY; without even the implied warranty of 
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU 
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public 
#   License along with Dragonfly.  If not, see 
#   <http://www.gnu.org/licenses/>.
#

"""
    This command module controls styles in Microsoft Word.

    The following commands are available:

    "set style <style>" -> format the current selection with 
    the given style.  The <style> extra is a literal name of 
    the style as is visible within Word.

    "(update | synchronize) styles" -> refresh the list of 
    styles known to this grammar.  This refresh action is also 
    done automatically every time the Word application comes 
    to the foreground.

    This command module makes use of various features of the 
    Dragonfly library.  It uses the ConnectionGrammar to 
    maintain a COM connection with Word when a Word window in 
    the foreground.  Every time this connection is set up, the 
    list of styles available in the current document is 
    retrieved and made available to the "set style <style>" 
    command.

    This command module uses Dragonfly's configuration 
    framework to allow multi-language support.
"""


#---------------------------------------------------------------------------

import os.path
from win32com.client                import Dispatch
from pywintypes                     import com_error

from dragonfly.grammar.grammar      import ConnectionGrammar
from dragonfly.grammar.context      import AppContext
from dragonfly.grammar.elements     import DictListRef
from dragonfly.grammar.compoundrule import CompoundRule
from dragonfly.grammar.list         import DictList
from dragonfly.config               import Config, Section, Item


#---------------------------------------------------------------------------
# Set up this module's configuration.

config = Config("Microsoft Word styles control")
config.lang                = Section("Language section")
config.lang.set_style      = Item("set style <style>", doc="Spec for setting a style; must contain the <style> extra.")
config.lang.update_styles  = Item("(update | synchronize) styles", doc="Spec for updating style list.")
#config.generate_config_file()
config.load()


#---------------------------------------------------------------------------
# StyleRule which keeps track of and can set available styles.

class StyleRule(CompoundRule):

    spec   = config.lang.set_style
    styles = DictList("styles")
    extras = [DictListRef("style", styles)]

    def _process_recognition(self, node, extras):
        try:
            document = self.grammar.application.ActiveDocument
            document.ActiveWindow.Selection.Style = extras["style"]
        except com_error, e:
            if self._log_proc: self._log_proc.warning("Rule %s:"
                    " failed to set style: %s." % (self, e))

    def reset_styles(self):
        self.styles.set({})

    def update_styles(self):
        # Retrieve available styles.
        try:
            document = self.grammar.application.ActiveDocument
            style_map = [(str(s), s) for s in  document.Styles]
            self.styles.set(dict(style_map))
        except com_error, e:
            if self._log_begin: self._log_begin.warning("Rule %s:"
                    " failed to retrieve styles: %s." % (self, e))
            self.styles.set({})

style_rule = StyleRule()


#---------------------------------------------------------------------------
# Synchronize styles rule for explicitly updating style list.

class SynchronizeStylesRule(CompoundRule):

    spec = config.lang.update_styles

    def _process_recognition(self, node, extras):
        style_rule.update_styles()


#---------------------------------------------------------------------------
# This module's main grammar.

class WordStylesGrammar(ConnectionGrammar):

    def __init__(self):
        name = self.__class__.__name__
        context = AppContext(executable="winword")
        app_name = "Word.Application"
        ConnectionGrammar.__init__(self, name=name,
            context=context, app_name=app_name)

    def connection_up(self):
        # Made connection with word -> retrieve available styles.
        style_rule.update_styles()

    def connection_down(self):
        # Lost connection with word -> empty style list.
        style_rule.reset_styles()

grammar = WordStylesGrammar()
grammar.add_rule(style_rule)
grammar.add_rule(SynchronizeStylesRule())


#---------------------------------------------------------------------------
# Load the grammar instance and define how to unload it.

grammar.load()

# Unload function which will be called by natlink at unload time.
def unload():
    global grammar
    if grammar: grammar.unload()
    grammar = None
