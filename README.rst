liveboxplaytv
============

This library is intended for controlling an Orange Livebox Play TV appliance

.. code-block::

    from liveboxplaytv import LiveboxPlayTv

    # Init
    l = LiveboxPlayTv('livebox-play.lan')

    # Check if the box is on
    l.is_on

    # Turn the box off
    l.turn_off()

    # and back on
    l.turn_on()

    # Query current channel
    l.channel

    # Set current channel
    l.channel = 'Arte'

    # Switch to channel number 7
    l.channel = '#7'

    # Raise volume
    l.volume_up()

    # Lower volume
    l.volume_down()

    # Mute volume
    l.mute()

    # Next channel
    l.channel_up()

    # Previous channel
    l.channel_down()

    # Virtually press a key on the remote
    from liveboxplaytv import KEYS
    l.press_key(KEYS['LEFT'])

There also is a CLI script that ships with this package:

.. code-block::

    $ liveboxplaytv -h
    usage: liveboxplaytv [-h] -H HOSTNAME [-j] [-d]
                         {key,vol,info,state,on,off,channel,notify,op} ...

    positional arguments:
      {key,vol,info,state,on,off,channel,notify,op}
                            Action
        key                 Press an arbitrary key
        vol                 Volume Control
        info                Get info
        state               Get the current state (on or off)
        on                  Turn the Livebox Play appliance on
        off                 Turn the Livebox Play appliance off
        channel             Get or set the current channel
        notify              Wait and notify of new events
        op                  [DEBUG] Send request

    optional arguments:
      -h, --help            show this help message and exit
      -H HOSTNAME, --hostname HOSTNAME
                            IP address or hostname of the Livebox Play
      -j, --json            Format output as JSON
      -d, --debug           Debug mode
