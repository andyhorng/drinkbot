# -*- coding: utf-8 -*-
import argparse
from string import Template


def gen_config(**args):
    template = Template(r'''

[program:$bot_name]
command = python /var/drinkbot/program/slack.py
environment = TOKEN="$slack_token",COMMAND_CHANNEL="$command_channel"
redirect_stderr=true

    ''')

    with open("/var/drinkbot/runtime/supervisord/slack/{}.conf".format(args["bot_name"]), "w") as f:
        f.write(template.substitute(**args))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gen bot supervisd config')
    parser.add_argument('bot_name', metavar='BOT', help='The bot name')
    parser.add_argument('slack_token', metavar='TOKEN', help='Slack token')
    parser.add_argument('command_channel', metavar='CHANNEL',
                        help='Slack command channel')

    args = vars(parser.parse_args())
    gen_config(**args)
