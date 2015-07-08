# -*- coding: utf-8 -*-

import logging
from functools import wraps


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


class R(object):

    ''' Response Object '''

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

class BotTool(object):
    @staticmethod
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

    @staticmethod
    def helper(func):
        @wraps(func)
        def wrapper(self, feed):
            if feed.message == "???":
                doc = func.__doc__
                if not doc:
                    doc = "暫時說不明白"
                return self.state, R(to=feed.source, message=doc)

            return func(self, feed)

        return wrapper

    @staticmethod
    def cancelable(keywords, return_state, msg):

        def wrapper(func):

            @wraps(func)
            def wrapper2(self, feed):
                if self.if_contains(keywords, feed.message):
                    self.reset()
                    return return_state, R(to=feed.source, message=msg)

                return func(self, feed)

            return wrapper2

        return wrapper


class AbstractBot(object):

    def register_fetch_channels(self, func):
        self.fetch_channels = func

    def register_send(self, func):
        self.send = func

    def send_response(self, response):
        if not response:
            return
        self.send(response.to, response.message)

    def reset(self):
        pass

    @BotTool.log
    def hey(self, feed):
        logging.info("{} status: {}".format(self.__class__.__name__,
                                            self.state))
        action = getattr(self, "state_{}".format(self.state))
        if action:
            rt = action(feed)
            if not rt:
                return None

            next_state, response = rt

            self.state = next_state
            return self.send_response(response)

    def is_equal(self, expected, s):
        from Levenshtein import distance
        import math
        edit_dist = distance(unicode(expected, 'utf-8'), unicode(s, 'utf-8'))
        threshold = math.ceil(len(unicode(expected, 'utf-8')) * 2 / 5)

        if edit_dist <= threshold:
            return True
        else:
            return False

    def if_contains(self, possibles, s):
        for p in possibles:
            if self.is_equal(p, s):
                return True
        return False

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
        self._args = kwargs
        self.reset()

    def reset(self):
        self.user = self._args['user']
        self.menu = self._args['menu']
        self.state = "send_menu"
        self._items = []

    def state_send_menu(self, feed):
        self.send(self.user, (
            "訂飲料囉！\n"
            "{}，菜單如下。\n"
            "{}").format(self.menu.name, self.menu.message()))

        return "waiting", None

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
            custom = groups[i + 1].strip()
            item.custom = custom
            items.append(item)
            order += ("一杯 {} {}，{} 元。"
                      .format(item.name, item.custom, item.price))

        self._items = items

        return "done", R(to=feed.source,
                         message='好的，已為您點了{}'
                         .format(order))

    @BotTool.cancelable(["取消"], "waiting", "好的，已取消了")
    def state_done(self, feed):
        return "done", None


    @property
    def items(self):
        return self._items


class Bot(AbstractBot):

    CANCEL_KEYWORDS = ["取消", "閉嘴", "關掉"]
    CANCEL_MSG = "好的"

    def __init__(self, **kwargs):
        '''
        menu: {1: {name: xxx, items: {}}}
        '''
        self._args = kwargs
        self.reset()

    def reset(self):
        self._state = "nothing"
        self.menus_getter = self._args['menus_getter']

        self.shop_id = None
        self.tiny_bots = {}

    def dispatch_to_tinybot(func):
        @wraps(func)
        def wrapper(self, feed):
            if feed.source.id in self.tiny_bots:
                # dispatch feed to tiny bots
                tiny_bot = self.tiny_bots[feed.source.id]
                tiny_bot.hey(feed)

                return 'waiting_user_order', None

            return func(self, feed)

        return wrapper

    @property
    def menus(self):
        return self.menus_getter()

    def all(self, feed):
        possibles = ["取消", "閉嘴", "關掉"]
        for possible in possibles:
            if self.is_equal(possible, feed.message):
                return "nothing", R(to=feed.source,
                                    message="好的")
        return None

    def register_send(self, send):
        for tiny in self.tiny_bots.values():
            tiny.register_send(send)

        return super(Bot, self).register_send(send)

    @BotTool.helper
    @BotTool.cancelable(CANCEL_KEYWORDS, "nothing", CANCEL_MSG)
    def state_nothing(self, feed):
        '''
        我沒事。想喝飲料就跟我說：”我要喝飲料“，我會幫大家統計。
        '''
        if self.is_equal("我要喝飲料", feed.message):
            self.shop_id = None
            self.tiny_bots = {}
            return "select_shop", R(
                to=feed.source,
                message=('好，請輸入飲料店 ID，或輸入list來列出所有飲料店。或直接輸入您的訂單編號。'))

        elif "背菜單" in feed.message:
            pass

    @BotTool.helper
    @BotTool.cancelable(CANCEL_KEYWORDS, "nothing", CANCEL_MSG)
    def state_select_shop(self, feed):
        '''
        我正在等您決定要喝哪一家。 list 可以得到店家清單。
        '''
        if 'list' in feed.message:
            return 'select_shop', R(
                to=feed.source,
                message=", ".join("{}: {}".format(m.id, m.name)
                                  for m in self.menus.values()))

        shop_ids = self.menus.keys()
        try:
            selection = int(feed.message)
            if selection in shop_ids:
                self.shop_id = selection
                return 'confirm_shop', R(
                    to=feed.source,
                    message='您要訂的是 {}，確定請輸入Y，重選請重新輸入飲料店 ID' .format(
                            self.menus[selection].name))
            else:
                return 'select_shop', R(to=feed.source,
                                        message='Unavailable Shop ID')
        except:
            return 'select_shop', R(to=feed.source,
                                    message='Invalid Shop ID')

    @BotTool.helper
    @BotTool.cancelable(CANCEL_KEYWORDS, "nothing", CANCEL_MSG)
    def state_confirm_shop(self, feed):
        '''
        我正在等您確認店家，輸入 y/n 做決定。
        '''
        if "y" == feed.message.strip().lower():
            for user in self.fetch_channels():
                if user.id not in self.tiny_bots:
                    # create the tiny bot to serve people
                    tiny = TinyBot(user=user, menu=self.menus[self.shop_id])
                    tiny.register_send(self.send)
                    self.tiny_bots[user.id] = tiny
                    # dummy msg to trigger process
                    tiny.hey(Feed(source=user, message=""))

            return "waiting_user_order", R(to=feed.source, message="好")
        elif "n" == feed.message.strip().lower():
            return "select_shop", R(to=feed.source, message="好，請重新選擇")

    @BotTool.helper
    @dispatch_to_tinybot
    @BotTool.cancelable(CANCEL_KEYWORDS, "nothing", CANCEL_MSG)
    def state_waiting_user_order(self, feed):
        '''
        我正在等大家點餐，輸入“點餐結束“，我會幫您做統計。輸入“點餐狀況”，我會回報點餐狀況。
        '''

        def get_summary():
            total = count = 0
            order_summary_str = ""
            for tiny in self.tiny_bots.values():
                for item in tiny.items:
                    total += item.price
                    count += 1
                    order_summary_str += ("{} {} x 1\n"
                                          .format(item.name, item.custom))

            return order_summary_str, total, count

        if self.is_equal("點餐結束", feed.message):
            order_summary_str, total, count = get_summary()

            # TODO refactoring to a helper
            return "nothing", R(
                to=feed.source,
                message=(
                    "好，以下是本次的訂單統計\n"
                    "{}\n"
                    "共計 {} 杯，{} 元\n").format(
                    order_summary_str,
                    count,
                    total))

        elif self.is_equal("點餐狀況", feed.message):
            order_summary_str, total, count = get_summary()
            return "waiting_user_order", R(
                to=feed.source,
                message=(
                    "目前訂單統計\n"
                    "{}\n"
                    "共計 {} 杯，{} 元\n").format(
                    order_summary_str,
                    count,
                    total))
