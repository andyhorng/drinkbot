# -*- coding: utf-8 -*-
from slackclient import SlackClient
import logging
import json
import drinkbot
from drinkbot import menu
import time
import os

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

config = {
    'command_channel': os.environ.get('COMMAND_CHANNEL'),
    'token': os.environ.get('TOKEN'),
    'loglevel': "INFO",
}

formatting = '[%(levelname)s] (%(threadName)-10s) %(message)s'
logging.basicConfig(format=formatting,
                    level=getattr(logging, config['loglevel']))

slack = SlackClient(config['token'])

bot = drinkbot.Bot(menus_getter=menu.fetch_menus)


def handle_message(event):
    # get channel name
    channel = slack.server.channels.find(event['channel'])
    logging.info("channel name: {}".format(channel.name))
    if channel.name == config['command_channel'] or\
            channel.name.startswith('D'):
        feed = drinkbot.Feed(source=drinkbot.Channel(id=event['channel']),
                             message=event['text'].encode('utf-8'))

        def send(channel, message):
            channel = slack.server.channels.find(channel.id)
            channel.send_message(message)

        def fetch_users():
            channel = 'channels'
            if event['channel'].startswith('G'):
                channel = 'groups'

            rt = slack.api_call('{}.info'.format(channel),
                                channel=event['channel'])
            data = json.loads(rt)
            if 'group' in data:
                members = data['group']['members']
            elif 'channel' in data:
                members = data['channel']['members']

            channels = []
            for member in members:
                imopen = json.loads(slack.api_call('im.open', user=member))
                if not imopen['ok']:
                    continue
                channels.append(drinkbot.Channel(id=imopen['channel']['id']))

            return channels

        bot.register_send(send)
        bot.register_fetch_channels(fetch_users)
        bot.hey(feed)


connected = slack.rtm_connect()

if not connected:
    logging.error('unable to establish rtm')
    sys.exit(-1)

me = json.loads(slack.api_call("auth.test"))

while True:
    try:
        for event in slack.rtm_read():
            logging.info(event)
            if 'type' not in event:
                continue

            if event['type'] == 'message':
                if 'subtype' in event:
                    continue
                if me['user_id'] == event['user']:
                    continue

                handle_message(event)

        time.sleep(.1)

    except:
        import traceback
        import sys
        traceback.print_exc(file=sys.stdout)
        # slack.api_call('chat.postMessage',
        #                channel=config['command_channel'],
        #                as_user=True,
        #                text="Oops! 我好像被玩壞了 (last state: {})".format(bot.state))
