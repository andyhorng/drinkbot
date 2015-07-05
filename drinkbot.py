# -*- coding: utf-8 -*-

import logging


class Feed(object):
    def __init__(self, *args, **kwargs):
        self._source = kwargs['source']
        self._message = kwargs['message']

    @property
    def source(self):
        return self._source

    @property
    def message(self):
        return self._message

    def __repr__(self):
        return "from: {}, msg: {}".format(self.source, self.message)


class Response(object):
    def __init__(self, *args, **kwargs):
        self._to = kwargs['to']
        self._message = kwargs['message']

    @property
    def to(self):
        return self._to

    @property
    def message(self):
        return self._message

    def __repr__(self):
        return "to: {}, msg: {}".format(self.to, self.message)


class BotException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

class Channel(object):
    def __init__(self, **kwargs):
        self._id = kwargs['id']

    @property
    def id(self):
        return self._id

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return "channel/user id: {}".format(self.id)

class Reaction(object):
    def __init__(self, next_state, response):
        self._next_state = next_state
        self._response = response

    @property
    def next_state(self):
        return self._next_state

    @property
    def response(self):
        return self._response

class AbstractBot(object):
    def register_fetch_channels(self, func):
        self.fetch_channels = func

    def register_send(self, func):
        self.send = func

    def send_response(self, response):
        if not response:
            return
        self.send(response.to, response.message)

    def log(func):
        def wrapper(*args, **kwargs):
            import pprint
            logging.info("Enter: {}".format(func.__name__))
            logging.info("Args: {}, {}".format(pprint.pformat(args),
                                               pprint.pformat(kwargs)))
            result = func(*args, **kwargs)
            logging.info("Return: {}".format(pprint.pformat(result)))
            logging.info("Leave: {}".format(func.__name__))

            return result

        return wrapper

    @log
    def hey(self, feed):
        logging.info("{} status: {}".format(self.__class__.__name__,
                                            self.state))
        action = getattr(self, "state_{}".format(self.state))
        if action:
            rt = self.all(feed)
            if not rt:
                rt = action(feed)

            if not rt:
                return None

            self.state = rt.next_state
            return self.send_response(rt.response)

    def is_equal(self, expected, s):
        from Levenshtein import distance
        import math
        edit_dist = distance(unicode(expected, 'utf-8'), unicode(s, 'utf-8'))
        threshold = math.ceil(len(unicode(expected, 'utf-8')) * 2 / 5)

        if edit_dist <= threshold:
            return True
        else:
            return False

    def all(self, feed):
        '''Triggered on every action transistion
        '''
        return None

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value
        return self._state

class TinyBot(AbstractBot):
    '''This bot responses for the order of each user. When the bot entered the
    waiting user orders, which will spawn many tiny bots to maintain
    the user orders.
    '''
    def __init__(self, **kwargs):
        self.user = kwargs['user']
        self.menu = kwargs['menu']
        self.state = "send_menu"
        self._items = []

    def state_send_menu(self, feed):
        self.send(self.user, '''
訂飲料囉！
{}，菜單如下。
{}'''.format(self.menu.name, self.menu.message()))

        return Reaction("waiting", None)

    def state_waiting(self, feed):
        ids = ["{:03d}".format(item.id) for item in self.menu.items]

        selecteds = {}
        for id in ids:
            ix = feed.message.find(id)
            if ix >= 0:
                selecteds[ix] = id

        if not len(selecteds.keys()):
            return None

        import operator
        import re
        items = sorted(selecteds.items(), key=operator.itemgetter(0))
        rx = ""
        for item in items:
            rx += ".*({})(.*)".format(item[1])

        order = ""
        matched = re.match(rx, feed.message)
        groups = matched.groups()
        items = []
        for i in range(0, len(groups), 2):
            item = self.menu.get_item(int(groups[i]))
            custom = groups[i+1].strip()
            item.custom = custom
            items.append(item)
            order += ("一杯 {} {}，{} 元。"
                      .format(item.name, item.custom, item.price))

        self._items = items

        return Reaction("done",
                        Response(to=feed.source,
                                 message='好的，已為您點了{}'
                                 .format(order)))

    def state_done(self, feed):
        return Reaction("done", None)

    def all(self, feed):
        if self.is_equal("取消", feed.message):
            return Reaction("send_menu", Response(to=feed.source,
                                                  message="已取消"))
        return None

    @property
    def items(self):
        return self._items


class Bot(AbstractBot):

    def __init__(self, **kwargs):
        '''
        menu: {1: {name: xxx, items: {}}}
        '''
        self._state = "nothing"
        self.menus_getter = kwargs['menus_getter']

        self.shop_id = None
        self.tiny_bots = {}

    @property
    def menus(self):
        return self.menus_getter()

    def all(self, feed):
        possibles = ["取消", "閉嘴", "關掉"]
        for possible in possibles:
            if self.is_equal(possible, feed.message):
                return Reaction("nothing", Response(to=feed.source,
                                                  message="好的"))
        return None

    def register_send(self, send):
        for tiny in self.tiny_bots.values():
            tiny.register_send(send)

        return super(Bot, self).register_send(send)


    def state_nothing(self, feed):
        if self.is_equal("我要喝飲料", feed.message):
            return Reaction("select_shop",
                            Response(to=feed.source, message='''\
好，請輸入飲料店 ID，\
或輸入list來列出所有飲料店。\
或直接輸入您的訂單編號。'''))
        elif "背菜單" in feed.message:
            pass

    def state_select_shop(self, feed):
        if 'list' in feed.message:
            return Reaction('select_shop', Response(
                to=feed.source,
                message=", ".join("{}: {}".format(m.id, m.name)
                                  for m in self.menus.values())))

        shop_ids = self.menus.keys()
        try:
            selection = int(feed.message)
            if selection in shop_ids:
                self.shop_id = selection
                return Reaction('confirm_shop', Response(to=feed.source,
                                message='''\
您要訂的是 {}，\
確定請輸入Y，\
重選請重新輸入飲料店 ID'''.format(self.menus[selection].name)))
            else:
                return Reaction('select_shop',
                                Response(to=feed.source,
                                         message='Unavailable Shop ID'))
        except:
            return Reaction('select_shop',
                            Response(to=feed.source,
                                     message='Invalid Shop ID'))

    def state_confirm_shop(self, feed):
        if "y" == feed.message.strip().lower():
            for user in self.fetch_channels():
                if user.id not in self.tiny_bots:
                    # create the tiny bot to serve people
                    tiny = TinyBot(user=user, menu=self.menus[self.shop_id])
                    tiny.register_send(self.send)
                    self.tiny_bots[user.id] = tiny
                    # dummy msg to trigger process
                    tiny.hey(Feed(source=user, message=""))

            return Reaction("waiting_user_order", Response(to=feed.source,
                                                    message="好"))
        elif "n" == feed.message.strip().lower():
            return Reaction("select_shop", Response(to=feed.source,
                                                    message="好，請重新選擇"))

    def state_waiting_user_order(self, feed):
        if feed.source.id in self.tiny_bots:
            # dispatch feed to tiny bots
            tiny_bot = self.tiny_bots[feed.source.id]
            tiny_bot.hey(feed)

            return Reaction('waiting_user_order', None)

        elif self.is_equal("點餐結束", feed.message):
            total = count = 0
            order_summary_str = ""
            for tiny in self.tiny_bots.values():
                for item in tiny.items:
                    total += item.price
                    count += 1
                    order_summary_str += ("{} {} x 1\n"
                                          .format(item.name, item.custom))

            return Reaction("nothing",
                            Response(to=feed.source,
                                     message='''\
好，以下是本次的訂單統計
{}
共計 {} 杯，{} 元
'''.format(order_summary_str, count, total)))
