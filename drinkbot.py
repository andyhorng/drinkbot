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


class Menu(object):
    def __init__(self, *args, **kwargs):
        self._items = []
        self._name = kwargs['name']
        self._id = kwargs['id']

    def add_item(self, item):
        self._items.append(item)

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def items(self):
        return self._items

    def get_item(self, id):
        for item in self.items:
            if item.id == id:
                return item


class Item(object):
    def __init__(self, *args, **kwargs):
        self._id = kwargs['id']
        self._name = kwargs['name']
        self._price = kwargs['price']

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def price(self):
        return self._price


class Bot(object):

    def __init__(self, *args, **kwargs):
        '''
        menu: {1: {name: xxx, items: {}}}
        '''
        self._state = "nothing"
        self.menus = kwargs['menus']

        self.shop_id = None
        self.user_orders = {}

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

    def is_equal(self, a, b):
        from Levenshtein import distance
        edit_dist = distance(unicode(a, 'utf-8'), unicode(b, 'utf-8'))
        if edit_dist <= 2:
            return True
        else:
            return False

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value
        return self._state

    @log
    def hey(self, feed):
        logging.info("Status: {}".format(self.state))
        action = getattr(self, "state_{}".format(self.state))
        if action:
            rt = action(feed)
            if not rt:
                return None

            self.state = rt.next_state
            return rt.response

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
            return Reaction("order_drink", Response(to=feed.source,
                                                    message="好"))
        elif "n" == feed.message.strip().lower():
            return Reaction("select_shop", Response(to=feed.source,
                                                    message="好，請重新選擇"))



    def state_order_drink(self, feed):
        '''Stateful state which will hold a global state that records
        the status of user order
        '''
        if feed.source == '#slack':

            if feed.message == 'done':
                return Reaction('waiting_user_order', None)

            user = feed.message
            menu_str = ""
            self.user_orders[user] = dict(state='waiting')
            for item in self.menus[self.shop_id].items:
                menu_str += ("{:03d} {} NT$ {}\n"
                             .format(item.id, item.name, item.price))

            return Reaction('order_drink',
                            Response(to=user,
                                     message='''
訂飲料囉！
{}，菜單如下。
{}'''.format(self.menus[self.shop_id].name, menu_str)))

    def state_waiting_user_order(self, feed):
        # not order yet
        menu = self.menus[self.shop_id]

        if feed.source in self.user_orders.keys() and \
                self.user_orders[feed.source]['state'] == 'waiting':
            # parsing
            ids = ["{:03d}".format(item.id) for item in menu.items]

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
                item = menu.get_item(int(groups[i]))
                custom = groups[i+1].strip()
                items.append((item, custom))
                order += ("一杯 {} {}，{} 元。"
                          .format(item.name, custom, item.price))

            self.user_orders[feed.source]['state'] = 'done'
            self.user_orders[feed.source]['items'] = items

            return Reaction("waiting_user_order",
                            Response(to=feed.source,
                                     message='好的，已為您點了{}'
                                     .format(order)))
        elif self.is_equal("點餐結束", feed.message):
            total = count = 0
            order_summary_str = ""
            for (user_id, data) in self.user_orders.items():

                if data['state'] != 'done':
                    continue

                for (item, custom) in data['items']:
                    total += item.price
                    count += 1
                    order_summary_str += ("{} {} x 1\n"
                                          .format(item.name, custom))

            return Reaction("nothing",
                            Response(to=feed.source,
                                     message='''\
好，以下是本次的訂單統計
{}
共計 {} 杯，{} 元
'''.format(order_summary_str, count, total)))


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
