import json
import urllib2


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
        import copy
        for item in self.items:
            if item.id == id:
                return copy.copy(item)

    def message(self):
        rt = ""
        for item in self.items:
            rt += ("{:03d} {} NT$ {}\n"
                   .format(item.id, item.name, item.price))
        return rt


class Item(object):

    def __init__(self, *args, **kwargs):
        self._id = kwargs['id']
        self._name = kwargs['name']
        self._price = kwargs['price']
        self._custom = kwargs['custom'] if 'custom' in kwargs else ''

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def price(self):
        return self._price

    @property
    def custom(self):
        return self._custom

    @custom.setter
    def custom(self, custom):
        self._custom = custom
        return self._custom


def fetch_menus():
    raw_menus = json.loads(
        urllib2.urlopen("https://alva-land.appspot.com/api/menu").read())

    menus = {}
    id = 0
    for raw in raw_menus:
        id += 1
        menus[id] = Menu(id=id, name=raw['name'])
        item_id = 0
        for item in raw['items']:
            item_id += 1
            menus[id].add_item(Item(id=item_id,
                                    name=item['name'], price=item['price']))

    return menus
