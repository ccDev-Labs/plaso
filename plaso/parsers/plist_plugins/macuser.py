# -*- coding: utf-8 -*-
"""Plist parser plugin for MacOS user plist files."""

# TODO: Only plists from MacOS 10.8 and 10.9 were tested. Look at other
#       versions as well.

import codecs
import plistlib

from xml.parsers import expat

from defusedxml import ElementTree
from dfdatetime import time_elements as dfdatetime_time_elements

from plaso.containers import plist_event
from plaso.containers import time_events
from plaso.lib import definitions
from plaso.parsers import logger
from plaso.parsers import plist
from plaso.parsers.plist_plugins import interface


class MacUserPlugin(interface.PlistPlugin):
  """Plist parser plugin for MacOS user plist files.

  Further details about the extracted fields.
    name:
      string with the system user.
    uid:
      user ID.
    passwordpolicyoptions:
      XML Plist structures with the timestamp.
    passwordLastSetTime:
      last time the password was changed.
    lastLoginTimestamp:
      last time the user was authenticated depending on the situation,
      these timestamps are reset (0 value). It is translated by the
      library as a 2001-01-01 00:00:00 (Cocoa zero time representation).
      If this happens, the event is not yield.
    failedLoginTimestamp:
      last time the user passwd was incorrectly(*).
    failedLoginCount:
      times of incorrect passwords.
  """

  NAME = 'macuser'
  DATA_FORMAT = 'MacOS user plist file'

  # The PLIST_PATH is dynamic, "user".plist is the name of the
  # MacOS user.
  PLIST_KEYS = frozenset([
      'name', 'uid', 'home', 'passwordpolicyoptions', 'ShadowHashData'])

  _ROOT = '/'

  # pylint: disable=arguments-differ
  def GetEntries(self, parser_mediator, match=None, **unused_kwargs):
    """Extracts relevant user timestamp entries.

    Args:
      parser_mediator (ParserMediator): mediates interactions between parsers
          and other components, such as storage and dfvfs.
      match (Optional[dict[str: object]]): keys extracted from PLIST_KEYS.
    """
    if 'name' not in match or 'uid' not in match:
      return

    account = match['name'][0]
    uid = match['uid'][0]

    for policy in match.get('passwordpolicyoptions', []):
      try:
        xml_policy = ElementTree.fromstring(policy)
      except (LookupError, ElementTree.ParseError,
              expat.ExpatError) as exception:
        logger.error((
            'Unable to parse XML structure for an user policy, account: '
            '{0:s} and uid: {1!s}, with error: {2!s}').format(
                account, uid, exception))
        continue

      for dict_elements in xml_policy.iterfind('dict'):
        key_values = [value.text for value in dict_elements]
        # Taking a list and converting it to a dict, using every other item
        # as the key and the other one as the value.
        policy_dict = dict(zip(key_values[0::2], key_values[1::2]))

      time_string = policy_dict.get('passwordLastSetTime', None)
      if time_string and time_string != '2001-01-01T00:00:00Z':
        try:
          date_time = dfdatetime_time_elements.TimeElements()
          date_time.CopyFromStringISO8601(time_string)
        except ValueError:
          date_time = None
          parser_mediator.ProduceExtractionWarning(
              'unable to parse password last set time string: {0:s}'.format(
                  time_string))

        shadow_hash_data = match.get('ShadowHashData', None)
        if date_time and isinstance(shadow_hash_data, (list, tuple)):
          # Extract the hash password information, which is stored in
          # the attribute ShadowHashData which is a binary plist data.
          try:
            property_list = plistlib.loads(shadow_hash_data[0])
          except plistlib.InvalidFileException as exception:
            parser_mediator.ProduceExtractionWarning(
                'unable to parse ShadowHashData with error: {0!s}'.format(
                    exception))
            property_list = {}

          password_hash = 'N/A'

          salted_hash = property_list.get('SALTED-SHA512-PBKDF2', None)
          if salted_hash:
            salt_hex_bytes = codecs.encode(salted_hash['salt'], 'hex')
            salt_string = codecs.decode(salt_hex_bytes, 'ascii')
            entropy_hex_bytes = codecs.encode(salted_hash['entropy'], 'hex')
            entropy_string = codecs.decode(entropy_hex_bytes, 'ascii')
            password_hash = '$ml${0:d}${1:s}${2:s}'.format(
                salted_hash['iterations'], salt_string, entropy_string)

          event_data = plist_event.PlistTimeEventData()
          event_data.desc = (
              'Last time {0:s} ({1!s}) changed the password: {2!s}').format(
                  account, uid, password_hash)
          event_data.key = 'passwordLastSetTime'
          event_data.root = self._ROOT

          event = time_events.DateTimeValuesEvent(
              date_time, definitions.TIME_DESCRIPTION_WRITTEN)
          parser_mediator.ProduceEventWithEventData(event, event_data)

      time_string = policy_dict.get('lastLoginTimestamp', None)
      if time_string and time_string != '2001-01-01T00:00:00Z':
        try:
          date_time = dfdatetime_time_elements.TimeElements()
          date_time.CopyFromStringISO8601(time_string)
        except ValueError:
          date_time = None
          parser_mediator.ProduceExtractionWarning(
              'unable to parse last login time string: {0:s}'.format(
                  time_string))

        if date_time:
          event_data = plist_event.PlistTimeEventData()
          event_data.desc = 'Last login from {0:s} ({1!s})'.format(
              account, uid)
          event_data.key = 'lastLoginTimestamp'
          event_data.root = self._ROOT

          event = time_events.DateTimeValuesEvent(
              date_time, definitions.TIME_DESCRIPTION_WRITTEN)
          parser_mediator.ProduceEventWithEventData(event, event_data)

      time_string = policy_dict.get('failedLoginTimestamp', None)
      if time_string and time_string != '2001-01-01T00:00:00Z':
        try:
          date_time = dfdatetime_time_elements.TimeElements()
          date_time.CopyFromStringISO8601(time_string)
        except ValueError:
          date_time = None
          parser_mediator.ProduceExtractionWarning(
              'unable to parse failed login time string: {0:s}'.format(
                  time_string))

        if date_time:
          event_data = plist_event.PlistTimeEventData()
          event_data.desc = (
              'Last failed login from {0:s} ({1!s}) ({2!s} times)').format(
                  account, uid, policy_dict.get('failedLoginCount', 0))
          event_data.key = 'failedLoginTimestamp'
          event_data.root = self._ROOT

          event = time_events.DateTimeValuesEvent(
              date_time, definitions.TIME_DESCRIPTION_WRITTEN)
          parser_mediator.ProduceEventWithEventData(event, event_data)


plist.PlistParser.RegisterPlugin(MacUserPlugin)
