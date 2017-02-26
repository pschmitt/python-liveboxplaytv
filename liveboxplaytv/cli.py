#!/usr/bin/env python
# coding: utf-8

from liveboxplaytv import (LiveboxPlayTv, logger)
import logging
import argparse


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


def main():
    args = parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    output = ''
    l = LiveboxPlayTv(args.hostname)

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

if __name__ == '__main__':
    main()
