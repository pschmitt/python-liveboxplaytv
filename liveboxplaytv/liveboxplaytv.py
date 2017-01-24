#!/usr/bin/env python
# coding: utf-8


from fuzzywuzzy import process
import argparse
import json
import logging
import requests
import time


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


KEYS = {
    'POWER': 116,
    '0': 512,
    '1': 513,
    '2': 514,
    '3': 515,
    '4': 516,
    '5': 517,
    '6': 518,
    '7': 519,
    '8': 520,
    '9': 521,
    'CH+': 402,
    'CH-': 403,
    'VOL+': 115,
    'VOL-': 114,
    'MUTE': 113,
    'UP': 103,
    'DOWN': 108,
    'LEFT': 105,
    'RIGHT': 106,
    'OK': 352,
    'BACK': 158,
    'MENU': 139,
    'PLAY/PAUSE': 164,
    'FBWD': 168,
    'FFWD': 159,
    'REC': 167,
    'VOD': 393,
}


CHANNEL_EPG_IDS = {'Mosaique': '0'}


class LiveboxPlayTv(object):
    def __init__(self, hostname):
        self.hostname = hostname
        self.CHANNELS = None

    @property
    def channel(self):
        return self.get_current_channel_name()

    @channel.setter
    def channel(self, value):
        self.set_channel(value)

    @property
    def epg_id(self):
        return self.info['playedMediaId']

    @epg_id.setter
    def epg_id(self, value):
        self.set_epg_id(value)

    @property
    def osd_context(self):
        return self.info['osdContext']

    @property
    def media_state(self):
        return self.info['playedMediaState']

    @property
    def media_position(self):
        return self.info['playedMediaPosition']

    @property
    def media_type(self):
        return self.info['playedMediaType']

    @property
    def timeshift_state(self):
        return self.info['timeShiftingState']

    @property
    def mac_address(self):
        return self.info['macAddress']

    @property
    def name(self):
        return self.info['friendlyName']

    @property
    def wol_support(self):
        return self.info['wolSupport'] == '0'

    @property
    def is_on(self):
        return self.state()

    @property
    def info(self):
        return self.get_info()

    # TODO
    @staticmethod
    def discover():
        pass

    def rq(self, operation, params=None):
        url = 'http://{}:8080/remoteControl/cmd'.format(self.hostname)
        get_params = {'operation': operation}
        if params:
            get_params.update(params)
        r = requests.get(url, params=get_params)
        r.raise_for_status()
        return r.json()

    def get_info(self):
        return self.rq(10)['result']['data']

    def state(self):
        return self.info['activeStandbyState'] == '0'

    def turn_on(self):
        if not self.state():
            self.press_key(key=KEYS['POWER'])
            time.sleep(.8)
            self.press_key(key=KEYS['OK'])

    def turn_off(self):
        if self.state():
            return self.press_key(key=KEYS['POWER'])

    def get_current_channel(self):
        epg_id = self.info['playedMediaId']
        return self.get_channel_from_epg_id(epg_id)

    def get_current_channel_name(self):
        try:
            return self.get_current_channel()['name']
        except KeyError:
            # http://forum.eedomus.com/viewtopic.php?f=50&t=2914&start=40#p36721
            info = self.info
            if info['osdContext'] == 'VOD':
                return 'VOD'

    def get_channels(self):
        # Return cached results if available
        if self.CHANNELS:
            return self.CHANNELS
        url = 'http://lsm-rendezvous040413.orange.fr/API/?api_token=be906750a3cd20d6ddb47ec0b50e7a68&output=json&withChannels=1'
        r = requests.get(url)
        r.raise_for_status()
        self.CHANNELS = r.json()['channels']['channel']
        return self.CHANNELS

    def get_channel_names(self, json_output=False):
        channels = [x['name'] for x in self.get_channels()]
        if json_output:
            return json.dumps(channels)
        for c in channels:
            print(c)

    def get_channel_epg_id(self, channel):
        # If the channel start with '#' search by channel number
        channel_index = None
        if channel.startswith('#'):
            channel_index = channel.split('#')[1]
        # Look for an exact match first
        for c in self.get_channels():
            if channel_index:
                if c['tvIndex'] == channel_index:
                    return c['epgId']
            else:
                if c['name'].lower() == channel.lower():
                    return c['epgId']
        # Try fuzzy matching it that did not give any result
        c = process.extractOne(channel, self.get_channels())[0]
        return c['epgId']

    def get_channel_from_epg_id(self, epg_id):
        if epg_id == '0':
            return {'name': 'Mosaique'}
        return [x for x in self.get_channels() if x['epgId'] == epg_id][0]

    def set_epg_id(self, epg_id):
        # The EPG ID needs to be 10 chars long, padded with '*' chars
        epg_id_str = str(epg_id).rjust(10, '*')
        logger.info('Tune to {}'.format(
            self.get_channel_from_epg_id(epg_id)['name']
        ))
        logger.debug('EPG ID string: {}'.format(epg_id_str))
        # FIXME We cannot use rq here since requests automatically urlencodes
        # the '*' characters
        # return self.rq('09', {'epg_id': epg_id_str, 'uui': 1})
        url = 'http://{}:8080/remoteControl/cmd?operation=09&epg_id={}&uui=1'.format(
            self.hostname, epg_id_str
        )
        r = requests.get(url)
        r.raise_for_status()
        return r.json()

    def set_channel(self, channel):
        if channel in CHANNEL_EPG_IDS:
            epg_id = CHANNEL_EPG_IDS[channel]
        else:
            epg_id = self.get_channel_epg_id(channel)
        return self.set_epg_id(epg_id)

    def __get_key_name(self, key_id):
        for key_name, k_id in KEYS.items():
            if k_id == key_id:
                return key_name

    def press_key(self, key, mode=0):
        '''
        modes:
            0 -> simple press
            1 -> long press
            2 -> release after long press
        '''
        if type(key) is str:
            assert key in KEYS, 'No such key: {}'.format(key)
            key = KEYS[key]
        logger.info('Press key {}'.format(self.__get_key_name(key)))
        return self.rq('01', {'key': key, 'mode': mode})

    def volume_up(self):
        return self.press_key(key=KEYS['VOL+'])

    def volume_down(self):
        return self.press_key(key=KEYS['VOL-'])

    def mute(self):
        return self.press_key(key=KEYS['MUTE'])

    def channel_up(self):
        return self.press_key(key=KEYS['CH+'])

    def channel_down(self):
        return self.press_key(key=KEYS['CH-'])

    def event_notify(self):
        # https://www.domotique-fibaro.fr/topic/4444-tv-commande-decodeur-livebox-play-et-gestion-d%C3%A3%C2%A9tat-temps-r%C3%A3%C2%A9el/
        url = 'http://{}:8080/remoteControl/notifyEvent'.format(self.hostname)
        r = requests.get(url)
        r.raise_for_status()
        return r.json()


def parse_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='action', help='Action')
    parser.add_argument(
        '-H', '--hostname',
        required=True,
        help='IP address or hostname of the Livebox Play'
    )
    parser.add_argument(
        '-j', '--json',
        action='store_true',
        default=False,
        required=False,
        help='Format output as JSON'
    )
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        default=False,
        required=False,
        help='Debug mode'
    )
    key_parser = subparsers.add_parser('key', help='Press an arbitrary key')
    key_parser.add_argument('key', help='Name or ID of the key to press')
    vol_parser = subparsers.add_parser('vol', help='Volume Control')
    vol_parser.add_argument('volume_action', choices=['up', 'down', 'mute'])
    subparsers.add_parser('info', help='Get info')
    subparsers.add_parser('state', help='Get the current state (on or off)')
    subparsers.add_parser('on', help='Turn the Livebox Play appliance on')
    subparsers.add_parser('off', help='Turn the Livebox Play appliance off')
    channel_parser = subparsers.add_parser(
        'channel', help='Get or set the current channel'
    )
    channel_parser.add_argument('CHANNEL', nargs='?')
    # Debuggign methods
    subparsers.add_parser('notify', help='Wait and notify of new events')
    op_parser = subparsers.add_parser('op', help='[DEBUG] Send request')
    op_parser.add_argument('OPERATION', help='Operation')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    output = ''
    l = LiveboxPlay(args.hostname)

    if args.action == 'info':
        output = l.info
    elif args.action == 'state':
        output = 'on' if l.state() else 'off'
    elif args.action == 'on':
        output = l.turn_on()
    elif args.action == 'off':
        output = l.turn_off()
    elif args.action == 'key':
        output = l.press_key(args.key)
    elif args.action == 'vol':
        if args.volume_action == 'up':
            output = l.volume_up()
        elif args.volume_action == 'down':
            output = l.volume_down()
        elif args.volume_action == 'mute':
            output = l.mute()
    elif args.action == 'channel':
        if args.CHANNEL:
            if args.CHANNEL.lower() == 'list':
                output = l.get_channel_names(args.json)
            else:
                output = l.set_channel(args.CHANNEL)
        else:
            output = l.get_current_channel_name()
    elif args.action == 'notify':
        output = l.event_notify()
    elif args.action == 'op':
        output = l.rq(args.OPERATION)

    if output:
        if args.json:
            from pprint import pprint
            pprint(output)
        else:
            print(output)
