#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Chris Dekter
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
#from PyKDE4.kdeui import KApplication, KXmlGuiWindow, KStandardAction, KIcon, KTextEdit, KAction, KStandardShortcut
from PyKDE4.kdeui import *
from PyKDE4.kdecore import i18n
from PyQt4.QtGui import *
from PyQt4.QtCore import Qt



__all__ = ["validate", "EMPTY_FIELD_REGEX", "AbbrSettingsDialog", "HotkeySettingsDialog", "WindowFilterSettingsDialog", "RecordDialog"]

from . import abbrsettings, hotkeysettings, windowfiltersettings, recorddialog, detectdialog
from .. import model, iomediator
from ..iomediator.key import Key

WORD_CHAR_OPTIONS = {
                     "All non-word" : model.DEFAULT_WORDCHAR_REGEX,
                     "Space and Enter" : r"[^ \n]",
                     "Tab" : r"[^\t]"
                     }

from .common import EMPTY_FIELD_REGEX


def validate(expression, message, widget, parent):
    if not expression:
        QMessageBox.critical(parent, message, message)
        if widget is not None:
            widget.setFocus()
    return expression



AbbrSettings = abbrsettings.AbbrSettings
AbbrListItem = abbrsettings.AbbrListItem
WORD_CHAR_OPTIONS_ORDERED = abbrsettings.WORD_CHAR_OPTIONS_ORDERED



class AbbrSettingsDialog(KDialog):

    def __init__(self, parent):
        KDialog.__init__(self, parent)
        self.widget = AbbrSettings(self)
        self.setMainWidget(self.widget)
        self.setButtons(KDialog.ButtonCodes(KDialog.ButtonCode(KDialog.Ok | KDialog.Cancel)))
        self.setPlainCaption(i18n("Set Abbreviations"))
        self.setModal(True)
        #self.connect(self, SIGNAL("okClicked()"), self.on_okClicked)

    def load(self, item):
        self.targetItem = item
        self.widget.abbrListWidget.clear()

        if model.TriggerMode.ABBREVIATION in item.modes:
            for abbr in item.abbreviations:
                self.widget.abbrListWidget.addItem(AbbrListItem(abbr))
            self.widget.removeButton.setEnabled(True)
            self.widget.abbrListWidget.setCurrentRow(0)
        else:
            self.widget.removeButton.setEnabled(False)

        self.widget.removeTypedCheckbox.setChecked(item.backspace)

        self.__resetWordCharCombo()

        wordCharRegex = item.get_word_chars()
        if wordCharRegex in list(WORD_CHAR_OPTIONS.values()):
            # Default wordchar regex used
            for desc, regex in WORD_CHAR_OPTIONS.items():
                if item.get_word_chars() == regex:
                    self.widget.wordCharCombo.setCurrentIndex(WORD_CHAR_OPTIONS_ORDERED.index(desc))
                    break
        else:
            # Custom wordchar regex used
            self.widget.wordCharCombo.addItem(model.extract_wordchars(wordCharRegex))
            self.widget.wordCharCombo.setCurrentIndex(len(WORD_CHAR_OPTIONS))

        if isinstance(item, model.Folder):
            self.widget.omitTriggerCheckbox.setVisible(False)
        else:
            self.widget.omitTriggerCheckbox.setVisible(True)
            self.widget.omitTriggerCheckbox.setChecked(item.omitTrigger)

        if isinstance(item, model.Phrase):
            self.widget.matchCaseCheckbox.setVisible(True)
            self.widget.matchCaseCheckbox.setChecked(item.matchCase)
        else:
            self.widget.matchCaseCheckbox.setVisible(False)

        self.widget.ignoreCaseCheckbox.setChecked(item.ignoreCase)
        self.widget.triggerInsideCheckbox.setChecked(item.triggerInside)
        self.widget.immediateCheckbox.setChecked(item.immediate)

    def save(self, item):
        item.modes.append(model.TriggerMode.ABBREVIATION)
        item.clear_abbreviations()
        item.abbreviations = self.get_abbrs()

        item.backspace = self.widget.removeTypedCheckbox.isChecked()

        option = str(self.widget.wordCharCombo.currentText())
        if option in WORD_CHAR_OPTIONS:
            item.set_word_chars(WORD_CHAR_OPTIONS[option])
        else:
            item.set_word_chars(model.make_wordchar_re(option))

        if not isinstance(item, model.Folder):
            item.omitTrigger = self.widget.omitTriggerCheckbox.isChecked()

        if isinstance(item, model.Phrase):
            item.matchCase = self.widget.matchCaseCheckbox.isChecked()

        item.ignoreCase = self.widget.ignoreCaseCheckbox.isChecked()
        item.triggerInside = self.widget.triggerInsideCheckbox.isChecked()
        item.immediate = self.widget.immediateCheckbox.isChecked()

    def reset(self):
        self.widget.removeButton.setEnabled(False)
        self.widget.abbrListWidget.clear()
        self.__resetWordCharCombo()
        self.widget.omitTriggerCheckbox.setChecked(False)
        self.widget.removeTypedCheckbox.setChecked(True)
        self.widget.matchCaseCheckbox.setChecked(False)
        self.widget.ignoreCaseCheckbox.setChecked(False)
        self.widget.triggerInsideCheckbox.setChecked(False)
        self.widget.immediateCheckbox.setChecked(False)

    def __resetWordCharCombo(self):
        self.widget.wordCharCombo.clear()
        for item in WORD_CHAR_OPTIONS_ORDERED:
            self.widget.wordCharCombo.addItem(item)
        self.widget.wordCharCombo.setCurrentIndex(0)

    def get_abbrs(self):
        ret = []
        for i in range(self.widget.abbrListWidget.count()):
            text = self.widget.abbrListWidget.item(i).text()
            ret.append(str(text))

        return ret

    def get_abbrs_readable(self):
        abbrs = self.get_abbrs()
        if len(abbrs) == 1:
            return abbrs[0]
        else:
            return "[%s]" % ','.join(abbrs)

    def reset_focus(self):
        self.widget.addButton.setFocus()

    def __valid(self):
        if not validate(len(self.get_abbrs()) > 0, i18n("You must specify at least one abbreviation"),
                            self.widget.addButton, self): return False

        return True

    def slotButtonClicked(self, button):
        if button == KDialog.Ok:
            if self.__valid():
                KDialog.slotButtonClicked(self, button)
        else:
            self.load(self.targetItem)
            KDialog.slotButtonClicked(self, button)


HotkeySettings = hotkeysettings.HotkeySettings

class HotkeySettingsDialog(KDialog):
    
    KEY_MAP = {
               ' ' : "<space>",
               }
    
    REVERSE_KEY_MAP = {}
    for key, value in KEY_MAP.items():
        REVERSE_KEY_MAP[value] = key

    def __init__(self, parent):
        KDialog.__init__(self, parent)
        self.widget = HotkeySettings(self)
        self.setMainWidget(self.widget)
        self.setButtons(KDialog.ButtonCodes(KDialog.ButtonCode(KDialog.Ok | KDialog.Cancel)))
        self.setPlainCaption(i18n("Set Hotkey"))
        self.setModal(True)
        self.key = None

    def load(self, item):
        self.targetItem = item
        self.widget.setButton.setEnabled(True)
        if model.TriggerMode.HOTKEY in item.modes:
            self.widget.controlButton.setChecked(Key.CONTROL in item.modifiers)
            self.widget.altButton.setChecked(Key.ALT in item.modifiers)
            self.widget.shiftButton.setChecked(Key.SHIFT in item.modifiers)
            self.widget.superButton.setChecked(Key.SUPER in item.modifiers)
            self.widget.hyperButton.setChecked(Key.HYPER in item.modifiers)
            self.widget.metaButton.setChecked(Key.META in item.modifiers)

            key = item.hotKey
            if key in self.KEY_MAP:
                keyText = self.KEY_MAP[key]
            else:
                keyText = key
            self._setKeyLabel(keyText)
            self.key = keyText
            
        else:
            self.reset()
            
    def save(self, item):
        item.modes.append(model.TriggerMode.HOTKEY)
        
        # Build modifier list
        modifiers = self.build_modifiers()
            
        keyText = self.key
        if keyText in self.REVERSE_KEY_MAP:
            key = self.REVERSE_KEY_MAP[keyText]
        else:
            key = keyText

        assert key is not None, "Attempt to set hotkey with no key"
        item.set_hotkey(modifiers, key)
        
    def reset(self):
        self.widget.controlButton.setChecked(False)
        self.widget.altButton.setChecked(False)
        self.widget.shiftButton.setChecked(False)
        self.widget.superButton.setChecked(False)
        self.widget.hyperButton.setChecked(False)
        self.widget.metaButton.setChecked(False)

        self._setKeyLabel(i18n("(None)"))
        self.key = None
        self.widget.setButton.setEnabled(True)

    def set_key(self, key, modifiers: list=None):
        if modifiers is None:
            modifiers = []
        if key in self.KEY_MAP:
            key = self.KEY_MAP[key]
        self._setKeyLabel(key)
        self.key = key
        self.widget.controlButton.setChecked(Key.CONTROL in modifiers)
        self.widget.altButton.setChecked(Key.ALT in modifiers)
        self.widget.shiftButton.setChecked(Key.SHIFT in modifiers)
        self.widget.superButton.setChecked(Key.SUPER in modifiers)
        self.widget.hyperButton.setChecked(Key.HYPER in modifiers)
        self.widget.metaButton.setChecked(Key.META in modifiers)

        self.widget.setButton.setEnabled(True)
            
    def cancel_grab(self):
        self.widget.setButton.setEnabled(True)
        self._setKeyLabel(self.key)
        
    def build_modifiers(self):
        modifiers = []
        if self.widget.controlButton.isChecked():
            modifiers.append(Key.CONTROL)
        if self.widget.altButton.isChecked():
            modifiers.append(Key.ALT)
        if self.widget.shiftButton.isChecked():
            modifiers.append(Key.SHIFT)
        if self.widget.superButton.isChecked():
            modifiers.append(Key.SUPER)
        if self.widget.hyperButton.isChecked():
            modifiers.append(Key.HYPER)
        if self.widget.metaButton.isChecked():
            modifiers.append(Key.META)
        
        modifiers.sort()
        return modifiers
        
                
    def slotButtonClicked(self, button):
        if button == KDialog.Ok:
            if self.__valid():
                KDialog.slotButtonClicked(self, button)
        else:
            self.load(self.targetItem)
            KDialog.slotButtonClicked(self, button)
            
    def _setKeyLabel(self, key):
        self.widget.keyLabel.setText(i18n("Key: ") + key)
        
    def __valid(self):
        if not validate(self.key is not None, i18n("You must specify a key for the hotkey."),
                            None, self): return False
        
        return True
        
        
class GlobalHotkeyDialog(HotkeySettingsDialog):
    
    def load(self, item):
        self.targetItem = item
        if item.enabled:
            self.widget.controlButton.setChecked(Key.CONTROL in item.modifiers)
            self.widget.altButton.setChecked(Key.ALT in item.modifiers)
            self.widget.shiftButton.setChecked(Key.SHIFT in item.modifiers)
            self.widget.superButton.setChecked(Key.SUPER in item.modifiers)
            self.widget.hyperButton.setChecked(Key.HYPER in item.modifiers)
            self.widget.metaButton.setChecked(Key.META in item.modifiers)

            key = item.hotKey
            if key in self.KEY_MAP:
                keyText = self.KEY_MAP[key]
            else:
                keyText = key
            self._setKeyLabel(keyText)
            self.key = keyText
            
        else:
            self.reset()
        
        
    def save(self, item):
        # Build modifier list
        modifiers = self.build_modifiers()
            
        keyText = self.key
        if keyText in self.REVERSE_KEY_MAP:
            key = self.REVERSE_KEY_MAP[keyText]
        else:
            key = keyText

        assert key is not None, "Attempt to set hotkey with no key"
        item.set_hotkey(modifiers, key)
        
        
from .windowfiltersettings import WindowFilterSettingsDialog
from .detectdialog import DetectDialog


        
class RecordSettings(QWidget, recorddialog.Ui_Form):
    
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        recorddialog.Ui_Form.__init__(self)
        self.setupUi(self)
        
class RecordDialog(KDialog):

    def __init__(self, parent, closure):
        KDialog.__init__(self, parent)
        self.widget = RecordSettings(self)
        self.setMainWidget(self.widget)
        self.setButtons(KDialog.ButtonCodes(KDialog.ButtonCode(KDialog.Ok | KDialog.Cancel)))
        self.setPlainCaption(i18n("Record Script"))
        self.setModal(True)
        self.closure = closure
        
    def get_record_keyboard(self):
        return self.widget.recKeyboardButton.isChecked()
        
    def get_record_mouse(self):
        return self.widget.recMouseButton.isChecked()

    def get_delay(self):
        return self.widget.secondsSpinBox.value()
        
    def slotButtonClicked(self, button):
        if button == KDialog.Ok:
            KDialog.slotButtonClicked(self, button)
            self.closure(True, self.get_record_keyboard(), self.get_record_mouse(), self.get_delay())
        else:
            self.closure(False, self.get_record_keyboard(), self.get_record_mouse(), self.get_delay())
            KDialog.slotButtonClicked(self, button)

