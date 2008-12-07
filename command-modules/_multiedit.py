﻿#
# This file is a command-module for Dragonfly.
# (c) Copyright 2008 by Christo Butcher
# Licensed under the LGPL, see <http://www.gnu.org/licenses/>
#

"""
Command-module for cursor movement and **editing**
============================================================================

This module allows the user to control the cursor and 
efficiently perform multiple text editing actions within a 
single phrase.


Example commands
----------------------------------------------------------------------------

*Note the "/" characters in the examples below are simply 
to help the reader see the different parts of each voice 
command.  They are not present in the actual command and 
should not be spoken.*

Example: **"up 4 / down 1 page / home / space 2"**
   This command will move the cursor up 4 lines, down 1 page,
   move to the beginning of the line, and then insert 2 spaces.

Example: **"left 7 words / backspace 3 / insert hello Cap world"**
   This command will move the cursor left 7 words, then delete
   the 3 characters before the cursor, and finally insert
   the text "hello World".

Example: **"home / space 4 / down / 43 times"**
   This command will insert 4 spaces at the beginning of 
   of this and the next 42 lines.  The final "43 times" 
   repeats everything in front of it that many times.


Discussion of this module
----------------------------------------------------------------------------

This command-module creates a powerful voice command for 
editing and cursor movement.  This command's structure can 
be represented by the following simplified language model:

 - *CommandRule* -- top-level rule which the user can say
    - *repetition* -- sequence of actions (name = "sequence")
       - *KeystrokeRule* -- rule that maps a single 
         spoken-form to an action
    - *optional* -- optional specification of repeat count
       - *integer* -- repeat count (name = "n")
       - *literal* -- "times"

The top-level command rule has a callback method which is 
called when this voice command is recognized.  The logic 
within this callback is very simple:

1. Retrieve the sequence of actions from the element with 
   the name "sequence".
2. Retrieve the repeat count from the element with the name
   "n".
3. Execute the actions the specified number of times.

"""


#---------------------------------------------------------------------------

from dragonfly.all import (Grammar, CompoundRule, MappingRule,
                           Dictation, RuleRef, Repetition,
                           Key, Text, Integer,
                           Config, Section, Item)


#---------------------------------------------------------------------------
# Here we define the keystroke rule.

# This rule maps spoken-forms to actions.  Some of these 
#  include special elements like the number with name "n" 
#  or the dictation with name "text".  This rule is not 
#  exported, but is referenced by other elements later on. 
#  It is derived from MappingRule, so that its "value" when 
#  processing a recognition will be the right side of the 
#  mapping: an action.
# Note that this rule does not execute these actions, it
#  simply returns them when it's value() method is called.
#  For example "up 4" will give the value Key("up:4").
class KeystrokeRule(MappingRule):

    exported = False
    mapping  = {
                "up [<n>]":                         Key("up:%(n)d"),
                "down [<n>]":                       Key("down:%(n)d"),
                "left [<n>]":                       Key("left:%(n)d"),
                "right [<n>]":                      Key("right:%(n)d"),
                "page up [<n>]":                    Key("pgup:%(n)d"),
                "page down [<n>]":                  Key("pgdown:%(n)d"),
                "up <n> (page | pages)":            Key("pgup:%(n)d"),
                "down <n> (page | pages)":          Key("pgdown:%(n)d"),
                "left <n> (word | words)":          Key("c-left:%(n)d"),
                "right <n> (word | words)":         Key("c-right:%(n)d"),
                "home":                             Key("home"),
                "end":                              Key("end"),
                "doc home":                         Key("c-home"),
                "doc end":                          Key("c-end"),

                "space [<n>]":                      Key("space:%(n)d"),
                "enter [<n>]":                      Key("enter:%(n)d"),
                "tab [<n>]":                        Key("tab:%(n)d"),
                "delete [<n>]":                     Key("del:%(n)d"),
                "delete [<n> | this] (line|lines)": Key("home, s-down:%(n)d, del"),
                "backspace [<n>]":                  Key("backspace:%(n)d"),

                "insert <text>":                    Text("%(text)s"),
                "paste":                            Key("c-v"),
               }
    extras   = [
                Integer("n", 1, 100),
                Dictation("text"),
               ]
    defaults = {
                "n": 1,
               }
    # Note: when processing a recognition, the *value* of 
    #  this rule will be an action object from the right side 
    #  of the mapping given above.  This is default behavior 
    #  of the MappingRule class' value() method.  It also 
    #  substitutes any "%(...)." within the action spec
    #  with the appropriate spoken values.

#---------------------------------------------------------------------------
# Here we create an element which is the sequence of keystrokes.

# First we create an element that references the keystroke rule.
#  Note: when processing a recognition, the *value* of this element
#  will be the value of the referenced rule: an action.
keystroke = RuleRef(rule=KeystrokeRule())

# Second we create a repetition of keystroke elements.
#  This element will match anywhere between 1 and 16 repetitions
#  of the keystroke elements.  Note that we give this element
#  the name "sequence" so that it can be used as an extra in
#  the rule definition below.
# Note: when processing a recognition, the *value* of this element
#  will be a sequence of the contained elements: a sequence of
#  actions.
sequence = Repetition(keystroke, min=1, max=16, name="sequence")


#---------------------------------------------------------------------------
# Here we define the top-level rule which the user can say.

# This is the rule that actually handles recognitions. 
#  When a recognition occurs, it's _process_recognition() 
#  method will be called.  It receives information about the 
#  recognition in the "extras" argument: the sequence of 
#  actions and the number of times to repeat them.
class RepeatRule(CompoundRule):

    # Here we define this rule's spoken-form and special elements.
    spec     = "<sequence> [[[and] repeat [that]] <n> times]"
    extras   = [
                sequence,             # Sequence of actions defined above.
                Integer("n", 1, 100), # Times to repeat the sequence.
               ]
    defaults = {
                "n": 1,               # Default repeat count.
               }

    # This method gets called when this rule is recognized.
    # Arguments:
    #  - node -- root node of the recognition parse tree.
    #  - extras -- dict of the "extras" special elements:
    #     . extras["sequence"] gives the sequence of actions.
    #     . extras["n"] gives the repeat count.
    def _process_recognition(self, node, extras):
        sequence = extras["sequence"]   # A sequence of actions.
        count = extras["n"]             # An integer repeat count.
        for i in range(count):
            for action in sequence:
                action.execute()


#---------------------------------------------------------------------------
# Create and load this module's grammar.

grammar = Grammar("multi edit")   # Create this module's grammar.
grammar.add_rule(RepeatRule())    # Add the top-level rule.
grammar.load()                    # Load the grammar.

# Unload function which will be called at unload time.
def unload():
    global grammar
    if grammar: grammar.unload()
    grammar = None
