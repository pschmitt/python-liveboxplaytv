#!/usr/bin/env python
# coding: utf-8


from .channels import CHANNELS
from .keys import KEYS
from fuzzywuzzy import process
import json
import logging
import requests
import time


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


CHANNEL_EPG_IDS = {'Mosaique': '0'}


class LiveboxPlayTv(object):
    def __init__(self, hostname, port=8080):
        self.hostname = hostname
        self.port = port
        self.CHANNELS = None
        self.CHANNEL_IMG = {}

    @property
    def channel(self):
        return self.get_current_channel_name()

    @property
    def channel_img(self):
        return self.get_channel_image()

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
        url = 'http://{}:{}/remoteControl/cmd'.format(self.hostname, self.port)
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
        epg_id = self.info.get('playedMediaId', None)
        return self.get_channel_from_epg_id(epg_id)

    def get_current_channel_name(self):
        channel = self.get_current_channel()['name']
        if channel == 'N/A':
            # Unable to determine current channel, let's try something else to
            # get a string representing what's on screen
            # http://forum.eedomus.com/viewtopic.php?f=50&t=2914&start=40#p36721
            osd = self.osd_context  # Avoid multiple lookups
            if osd == 'VOD':
                return 'VOD'
            elif osd == 'AdvPlayer':
                return 'Replay'
        return channel

    def get_current_channel_image(self, img_size=300):
        channel = self.channel
        if self.channel == 'N/A':
            return
        return self.get_channel_image(channel=channel, img_size=img_size)

    def get_channel_image(self, channel, img_size=300, skip_cache=False):
        """Get the logo for a channel"""
        from bs4 import BeautifulSoup
        import re
        import wikipedia
        from wikipedia.exceptions import PageError
        wikipedia.set_lang('fr')

        if channel is None:
            logger.error('Channel is not set. Could not retrieve image.')
            return

        # Check if the image is in cache
        if channel in self.CHANNEL_IMG and not skip_cache:
            img = self.CHANNEL_IMG[channel]
            logger.debug('Cache hit: {} -> {}'.format(channel, img))
            return img

        channel_info = self.get_channel_info(channel)
        query = channel_info['wiki_page']
        if not query:
            logger.debug('Wiki page is not set for channel {}'.format(channel))
            return
        logger.debug('Query: {}'.format(query))
        # If there is a max image size defined use it.
        if 'max_img_size' in channel_info:
            if img_size > channel_info['max_img_size']:
                logger.info(
                    'Requested image size is bigger than the max, '
                    'setting it to {}'.format(channel_info['max_img_size'])
                )
                img_size = channel_info['max_img_size']
        try:
            p = wikipedia.page(query)
            logger.debug('Wikipedia article title: {}'.format(p.title))
            s = BeautifulSoup(p.html(), 'html.parser')
            images = s.find_all('img')
            img_src = None
            for i in images:
                if i['alt'].startswith('Image illustrative'):
                    img_src = re.sub('\d+px', '{}px'.format(img_size), i['src'])
            img = 'https:{}'.format(img_src) if img_src else None
            # Cache result
            self.CHANNEL_IMG[channel] = img
            return img
        except PageError:
            logger.error('Could not fetch channel image for {}'.format(channel))

    def update_channels(self):
        # Return cached results if available
        if self.CHANNELS:
            return self.CHANNELS
        url = 'http://lsm-rendezvous040413.orange.fr/API/?output=json&withChannels=1'
        r = requests.get(url)
        r.raise_for_status()
        self.CHANNELS = r.json()['channels']['channel']
        return self.CHANNELS

    def get_channel_names(self, json_output=False):
        channels = [x['name'] for x in CHANNELS]
        return json.dumps(channels) if json_output else channels

    def get_channel_info(self, channel):
        # If the channel start with '#' search by channel number
        channel_index = None
        if channel.startswith('#'):
            channel_index = channel.split('#')[1]
        # Look for an exact match first
        for c in CHANNELS:
            if channel_index:
                if c['index'] == channel_index:
                    return c
            else:
                if c['name'].lower() == channel.lower():
                    return c
        # Try fuzzy matching it that did not give any result
        c = process.extractOne(channel, CHANNELS)[0]
        return c

    def get_channel_epg_id(self, channel):
        return self.get_channel_info(channel)['epg_id']

    def get_channel_from_epg_id(self, epg_id):
        res = [c for c in CHANNELS if c['epg_id'] == epg_id]
        return res[0] if len(res) > 0 else None

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
        url = 'http://{}:{}/remoteControl/cmd?operation=09&epg_id={}&uui=1'.format(
            self.hostname, self.port, epg_id_str
        )
        r = requests.get(url)
        r.raise_for_status()
        return r.json()

    def set_channel(self, channel):
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

    def play_pause(self):
        return self.press_key(key=KEYS['PLAY/PAUSE'])

    def play(self):
        if self.info.media_state == 'PAUSE':
            self.play_pause()

    def pause(self):
        if self.info.get('timeShiftingState', None) == 'LIVE':
            self.play_pause()

    def event_notify(self):
        # https://www.domotique-fibaro.fr/topic/4444-tv-commande-decodeur-livebox-play-et-gestion-d%C3%A3%C2%A9tat-temps-r%C3%A3%C2%A9el/
        url = 'http://{}:{}/remoteControl/notifyEvent'.format(self.hostname, self.port)
        r = requests.get(url)
        r.raise_for_status()
        return r.json()
