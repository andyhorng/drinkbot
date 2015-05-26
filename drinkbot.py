# -*- coding: utf-8 -*-


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
        self.state = "nothing"
        self.menus = kwargs['menus']

    def hey(self, feed):
        action = getattr(self, "state_{}".format(self.state))
        if action:
            rt = action(feed)
            self.state = rt.next_state
            return rt.response

    def state_nothing(self, feed):
        if "我要喝飲料" in feed.message:
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
        if "Y" in feed.message:
            return Reaction(
                    "order_drink",
                    "好"
                    )



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
