# -*- coding: utf-8 -*-
import logging
import time
import yaml
import json
import threading

from slackclient import SlackClient


class Input(object):
    def __init__(self, slack_event):
        self.slack_event = slack_event


class Bot(object):

    def __init__(self, config):
        self.config = config
        self.slack = SlackClient(config['token'])
        self.menu = json.load(open('./menu.json'))
        self.state = 'standby'
        self.shops = self.get_shops()
        self.shop_id = None
        self.orders = {}

    def get_shops(self):
        i = 0
        shops = {}
        for name in dir(self.menu):
            i += 1
            shops[i] = name

        return shops

    # states #
    def state_standby(self, event):
        if '我要喝飲料' in event['text'].encode('utf-8'):
            channel = self.slack.server.channels.find(event['channel'])
            channel.send_message('''
            好，請輸入飲料店 ID，
            或輸入list來列出所有飲料店。
            或直接輸入您的訂單編號。
            {}
            '''.format(','.join("{}: {}\n".format(k, v)
                                for k, v in self.get_shops().items())))
            return 'choice_shop'
        return 'standby'

    def state_choice_shop(self, event):
        text = event['text'].encode('utf-8')
        try:
            if int(text) in self.shops.keys():
                self.shop_id = int(text)
                return 'confirm_choice_shop'
        except:
            return 'choice_shop'

        return 'choice_shop'

    def state_confirm_choice_shop(self, event):
        text = event['text'].encode('utf-8')
        try:
            if int(text) == 1:
                return 'order_drink'
            else:
                return 'choice_shop'
        except:
            return 'choice_shop'

    def state_order_drink(self, event):
        self.orders = {}
        # dm everybody
        return 'order_drink'

    # states #

    def interact(self, e):
        logging.info("state: {} with {}".format(self.state, e))
        next_state = getattr(self, "state_{}".format(self.state))(e)
        logging.info("state becomes: {}".format(next_state))
        return next_state

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

    def handle_hello(self, event):
        print event

    def handle_message(self, event):
        # get channel name
        channel = self.slack.server.channels.find(event['channel'])
        logging.info(channel.name)

        if channel.name == self.config['command_channel']:
            self.state = self.interact(event)

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
