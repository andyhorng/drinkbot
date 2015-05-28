# -*- coding: utf-8 -*-
from slackclient import SlackClient
import yaml
import logging
import json
import drinkbot
import time

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

config = yaml.load(open('config.yaml', 'r').read())
formatting = '[%(levelname)s] (%(threadName)-10s) %(message)s'
logging.basicConfig(format=formatting,
                    level=getattr(logging, config['loglevel']))

slack = SlackClient(config['token'])

raw_menu = json.load(open('./menu.json', 'r'))
menus = {}
id = 0
for shop_name, items in raw_menu.items():
    id += 1
    menus[id] = drinkbot.Menu(id=id, name=shop_name)
    item_id = 0
    for item in items:
        item_id += 1
        menus[id].add_item(drinkbot
                           .Item(id=item_id,
                                 name=item['name'], price=item['price']))

bot = drinkbot.Bot(menus=menus)


def handle_message(event):
    # get channel name
    channel = slack.server.channels.find(event['channel'])
    print "channel name: " + channel.name

    if channel.name == config['command_channel'] or channel.name.startswith('D'):
        feed = drinkbot.Feed(source=event['channel'],
                             message=event['text'].encode('utf-8'))
        result = bot.hey(feed)
        if not result:
            return

        channel.send_message(result.message)

        if result.message == '好':
            rt = slack.api_call('groups.info', channel=event['channel'])
            data = json.loads(rt)
            for member in data['group']['members']:
                time.sleep(1)
                imopen = json.loads(slack.api_call('im.open', user=member))
                if not imopen['ok']:
                    continue

                feed = drinkbot.Feed(source="#slack",
                                     message=imopen['channel']['id'])
                result = bot.hey(feed)
                if not result:
                    continue

                slack.api_call('chat.postMessage',
                               channel=result.to,
                               text=result.message)

            feed = drinkbot.Feed(source="#slack",
                                 message="done")


connected = slack.rtm_connect()

if not connected:
    logging.error('unable to establish rtm')
    sys.exit(-1)

while True:
    try:
        for event in slack.rtm_read():
            logging.info(event)
            if 'type' not in event:
                continue

            if event['type'] == 'message':
                handle_message(event)

        time.sleep(.1)

    except:
        import traceback
        import sys
        traceback.print_exc(file=sys.stdout)
