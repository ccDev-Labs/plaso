#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests the plist parser."""

import unittest

from plaso.lib import errors
from plaso.parsers import plist
# Register all plugins.
from plaso.parsers import plist_plugins  # pylint: disable=unused-import

from tests.parsers import test_lib


class PlistParserTest(test_lib.ParserTestCase):
  """Tests the plist parser."""

  # pylint: disable=protected-access

  def testEnablePlugins(self):
    """Tests the EnablePlugins function."""
    parser = plist.PlistParser()
    parser.EnablePlugins(['airport'])

    self.assertIsNotNone(parser)
    self.assertIsNotNone(parser._default_plugin)
    self.assertNotEqual(parser._plugins, [])
    self.assertEqual(len(parser._plugins), 1)

  def testParse(self):
    """Tests the Parse function."""
    parser = plist.PlistParser()
    storage_writer = self._ParseFile(['plist_binary'], parser)

    self.assertEqual(storage_writer.number_of_warnings, 0)
    self.assertEqual(storage_writer.number_of_events, 12)

    keys = set()
    roots = set()
    timestamps = set()
    for event in storage_writer.GetEvents():
      event_data = self._GetEventDataOfEvent(storage_writer, event)
      keys.add(event_data.key)
      roots.add(event_data.root)
      timestamps.add(event.timestamp)

    expected_timestamps = frozenset([
        1345251192528750, 1351827808261762, 1345251268370453,
        1351818803000000, 1351819298997673, 1351818797324095,
        1301012201414766, 1302199013524275, 1341957900020117,
        1350666391557044, 1350666385239662, 1341957896010535])

    self.assertEqual(len(timestamps), 12)
    self.assertEqual(timestamps, expected_timestamps)

    expected_roots = frozenset([
        '/DeviceCache/00-0d-fd-00-00-00',
        '/DeviceCache/44-00-00-00-00-00',
        '/DeviceCache/44-00-00-00-00-01',
        '/DeviceCache/44-00-00-00-00-02',
        '/DeviceCache/44-00-00-00-00-03',
        '/DeviceCache/44-00-00-00-00-04'])
    self.assertEqual(len(roots), 6)
    self.assertEqual(roots, expected_roots)

    expected_keys = frozenset([
        'LastInquiryUpdate',
        'LastServicesUpdate',
        'LastNameUpdate'])
    self.assertEqual(len(keys), 3)
    self.assertTrue(keys, expected_keys)

  def testParseWithTruncatedFile(self):
    """Tests the Parse function on a truncated plist file."""
    parser = plist.PlistParser()

    with self.assertRaises(errors.UnableToParseFile):
      self._ParseFile(['truncated.plist'], parser)

  def testParseWithXMLFileLeadingWhitespace(self):
    """Tests the Parse function on an XML file with leading whitespace."""
    parser = plist.PlistParser()
    storage_writer = self._ParseFile(['leading_whitespace.plist'], parser)

    self.assertEqual(storage_writer.number_of_warnings, 1)
    self.assertEqual(storage_writer.number_of_events, 4)

  def testParseWithXMLFileExpatError(self):
    """Tests the Parse function on an XML file that causes an ExpatError."""
    parser = plist.PlistParser()

    with self.assertRaises(errors.UnableToParseFile):
      self._ParseFile(['WMSDKNS.DTD'], parser)

  def testParseWithXMLFileLookupError(self):
    """Tests the Parse function on an XML file that causes a LookupError."""
    parser = plist.PlistParser()
    storage_writer = self._ParseFile(['SAFStore.xml'], parser)

    self.assertEqual(storage_writer.number_of_warnings, 1)
    self.assertEqual(storage_writer.number_of_events, 0)

  def testParseWithXMLFileBinASCIIError(self):
    """Tests the Parse function on an XML file that causes a binascii.Error."""
    parser = plist.PlistParser()

    with self.assertRaises(errors.UnableToParseFile):
      self._ParseFile(['manageconsolidatedProviders.aspx.resx'], parser)

  def testParseWithXMLFileNoTopLevel(self):
    """Tests the Parse function on an XML file without top level object."""
    parser = plist.PlistParser()

    with self.assertRaises(errors.UnableToParseFile):
      test_path_segments = [
          'SettingsPane_{F8B5DB1C-D219-4bf9-A747-A1325024469B}'
          '.settingcontent-ms']
      self._ParseFile(test_path_segments, parser)

  def testParseWithPlistXMLFileNoTopLevel(self):
    """Tests the Parse function on a plist XML file without top level object."""
    parser = plist.PlistParser()
    storage_writer = self._ParseFile(['empty.plist'], parser)

    self.assertEqual(storage_writer.number_of_warnings, 1)
    self.assertEqual(storage_writer.number_of_events, 0)


if __name__ == '__main__':
  unittest.main()
