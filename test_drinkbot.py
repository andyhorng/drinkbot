# coding: utf-8
import unittest
import drinkbot
from mock import Mock, call


class TestBot(unittest.TestCase):

    # This unit test is flow-based

    def test_normal_flow(self):
        menus = {1: drinkbot.Menu(id=1, name="drinking a"),
                 2: drinkbot.Menu(id=2, name="drinking b"), }

        menus[1].add_item(drinkbot.Item(id=1, name="drink1", price=10))
        menus[1].add_item(drinkbot.Item(id=2, name="drink2", price=20))

        bot = drinkbot.Bot(menus=menus)

        # bot.register_fetch_users()

        ##################
        feed = drinkbot.Feed(source=drinkbot.Channel(id="someone"), message="我要飲料")
        mock = Mock(return_value=None)
        bot.register_send(mock)
        bot.hey(feed)
        mock.assert_called_once_with(drinkbot.Channel(id="someone"), '''\
好，請輸入飲料店 ID，\
或輸入list來列出所有飲料店。\
或直接輸入您的訂單編號。''')
        ##################

        ##################
        feed = drinkbot.Feed(source=drinkbot.Channel(id="someone"), message="閉嘴")
        mock = Mock(return_value=None)
        bot.register_send(mock)
        bot.hey(feed)
        mock.assert_called_once_with(drinkbot.Channel(id="someone"), '好的')
        ##################

        ##################
        feed = drinkbot.Feed(source=drinkbot.Channel(id="someone"), message="我要飲料")
        mock = Mock(return_value=None)
        bot.register_send(mock)
        bot.hey(feed)
        mock.assert_called_once_with(drinkbot.Channel(id="someone"), '''\
好，請輸入飲料店 ID，\
或輸入list來列出所有飲料店。\
或直接輸入您的訂單編號。''')
        ##################

        ##################
        feed = drinkbot.Feed(source=drinkbot.Channel(id="someone"), message="list")
        mock = Mock(return_value=None)
        bot.register_send(mock)
        bot.hey(feed)
        mock.assert_called_once_with(drinkbot.Channel(id="someone"), '1: drinking a, 2: drinking b')
        ##################

        ##################
        feed = drinkbot.Feed(source=drinkbot.Channel(id="someone"), message="1")
        mock = Mock(return_value=None)
        bot.register_send(mock)
        bot.hey(feed)
        mock.assert_called_once_with(drinkbot.Channel(id="someone"), '''\
您要訂的是 drinking a，\
確定請輸入Y，\
重選請重新輸入飲料店 ID''')
        ##################

        ##################
        feed = drinkbot.Feed(source=drinkbot.Channel(id="someone"), message="n")
        mock = Mock(return_value=None)
        bot.register_send(mock)
        bot.hey(feed)
        mock.assert_called_once_with(drinkbot.Channel(id="someone"), '好，請重新選擇')
        ##################

        ##################
        feed = drinkbot.Feed(source=drinkbot.Channel(id="someone"), message="1")
        mock = Mock(return_value=None)
        bot.register_send(mock)
        bot.hey(feed)
        mock.assert_called_once_with(drinkbot.Channel(id="someone"), '''\
您要訂的是 drinking a，\
確定請輸入Y，\
重選請重新輸入飲料店 ID''')
        ##################

        ##################
        feed = drinkbot.Feed(source=drinkbot.Channel(id="someone"), message="Y")
        mock = Mock(return_value=None)
        bot.register_send(mock)

        users = ["DM01", "DM02"]

        fetch_users_mock = Mock(return_value=
                                [drinkbot.Channel(id=v) for v in users])
        bot.register_fetch_channels(fetch_users_mock)

        bot.hey(feed)

        fetch_users_mock.assert_called_once_with()

        expected = []
        for user in users:
            expected.append(call(drinkbot.Channel(id=user), '''
訂飲料囉！
drinking a，菜單如下。
001 drink1 NT$ 10
002 drink2 NT$ 20
'''))
        expected.append(call(drinkbot.Channel(id="someone"), '好'))

        self.assertListEqual(expected, mock.call_args_list)

        ##################

        # user 1
        feed = drinkbot.Feed(source=drinkbot.Channel(id="DM01"),
                             message="001 少糖 去冰 002 去冰")
        mock = Mock(return_value=None)
        bot.register_send(mock)
        bot.hey(feed)
        mock.assert_called_once_with(drinkbot.Channel(id="DM01"), '''\
好的，已為您點了一杯 drink1 少糖 去冰，10 元。一杯 drink2 去冰，20 元。''')

        # user 2
        feed = drinkbot.Feed(source=drinkbot.Channel(id="DM02"),
                             message="002 少糖 去冰")
        mock = Mock(return_value=None)
        bot.register_send(mock)
        bot.hey(feed)
        mock.assert_called_once_with(drinkbot.Channel(id="DM02"), '''\
好的，已為您點了一杯 drink2 少糖 去冰，20 元。''')

        feed = drinkbot.Feed(source=drinkbot.Channel(id="someone"), message="點餐結束")
        mock = Mock(return_value=None)
        bot.register_send(mock)
        bot.hey(feed)
        mock.assert_called_once_with(drinkbot.Channel(id="someone"), '''\
好，以下是本次的訂單統計
drink1 少糖 去冰 x 1
drink2 去冰 x 1
drink2 少糖 去冰 x 1

共計 3 杯，50 元
''')


if __name__ == '__main__':
    unittest.main()
