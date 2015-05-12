# -*- coding: utf-8 -*-
import logging
import time
import yaml
import threading
from fysom import Fysom

from slackclient import SlackClient


class Bot(object):

    def __init__(self, config):
        self.config = config
        self.slack = SlackClient(config['token'])
        self.fsm = Fysom({
            'initial': 'standby',
            'events': [
                {'name': 'start_to_order',
                    'src': 'standby', 'dst': 'ordering'},
                {'name': 'done', 'src': 'ordering', 'dst': 'summary'},
                {'name': 'confirm', 'src': 'summary', 'dst': 'standby'},
                ],
            })

    def up(self):
        connected = self.slack.rtm_connect()

        if not connected:
            logging.error('unable to establish rtm')
            return

        while True:
            try:
                for event in self.slack.rtm_read():
                    self.log(event)
                    if 'type' not in event:
                        continue

                    name = 'handle_{}'.format(event['type'])

                    if name in dir(self):
                        getattr(self, name)(event)
                time.sleep(.1)

            except Exception as e:
                logging.info(e)

    # def handle_hello(self, event):
    #     print event

    def handle_message(self, event):
        # get channel name
        channel = self.slack.server.channels.find(event['channel'])
        logging.info(channel.name)

        if channel.name == self.config['command_channel']:
            channel.send_message('好的')

    def log(self, event):
        logging.info(event)


class Main(object):
    def __init__(self):
        self.config = yaml.load(open('config.yaml', 'r').read())
        formatting = '[%(levelname)s] (%(threadName)-10s) %(message)s'
        logging.basicConfig(format=formatting,
                            level=getattr(logging, self.config['loglevel']))

    def run(self):

        def run_bot():
            bot = Bot(self.config)
            bot.up()

        t = threading.Thread(name='bot', target=run_bot)
        t.setDaemon(True)
        t.start()

        # main loop
        while True:
            # logging.info("running")
            time.sleep(10)


if __name__ == '__main__':
    Main().run()
