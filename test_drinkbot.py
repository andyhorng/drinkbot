# coding: utf-8
import unittest
import damnit


class TestBot(unittest.TestCase):

    # This unit test is flow-based

    def test_normal_flow(self):
        menus = {1: damnit.Menu(id=1, name="drinking a"),
                 2: damnit.Menu(id=2, name="drinking b"), }

        bot = damnit.Bot(menus=menus)
        feed = damnit.Feed(source="someone", message="我要喝飲料")
        result = bot.hey(feed)

        self.assertEquals(result.message, '''\
好，請輸入飲料店 ID，\
或輸入list來列出所有飲料店。\
或直接輸入您的訂單編號。''')

        feed = damnit.Feed(source="someone", message="list")
        result = bot.hey(feed)
        self.assertEquals(result.message, '1: drinking a, 2: drinking b')

        feed = damnit.Feed(source="someone", message="1")
        result = bot.hey(feed)
        self.assertEquals(result.message, '''\
您要訂的是 drinking a，\
確定請輸入Y，\
重選請重新輸入飲料店 ID''')

        feed = damnit.Feed(source="someone", message="Y")

if __name__ == '__main__':
    unittest.main()
