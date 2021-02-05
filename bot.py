import os
import json
import datetime
from flask import Flask, request
from telegram import Message, Update
from telegram.ext import Updater, CommandHandler
from control import on_control
from info import on_info
import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


###
### Preperations
###
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
	exit(logging.error('BOT_TOKEN not set.'))
CONTROL_SECRET = os.getenv('CONTROL_SECRET')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')
if not WEBHOOK_SECRET:
	exit(logging.error('WEBHOOK_SECRET not set.'))
updater = Updater(token=os.getenv('BOT_TOKEN'))
dispatcher = updater.dispatcher
bot = updater.bot


###
### Helper functions
###


def add_command(command):
	'''Convenience decorator to add a command handler.

	Usage:
	```
	@add_command('start')
	def c_start(update, context):
		replyMessage(update, 'Hello, {}'.format(update.effective_user.first_name))
	```

	:param command: The same as `telegram.ext.CommandHandler`.
	'''

	def _add_command(handler_func):
		dispatcher.add_handler(CommandHandler(command, handler_func))
	return _add_command


def sendMessage(**args):
	'''Patched `telegram.Bot.send_message`.
	Currently provides a shorthand for `parse_mode='MarkdownV2'`.

	:param parse_mode: Optional. Pass `md` for `MarkdownV2`.
	:param **args: The same as `telegram.Bot.send_message`.
	'''
	if args.get('parse_mode', None) == 'md':
		args['parse_mode'] = 'MarkdownV2'
	bot.sendMessage(**args)


def replyMessage(update, **args):
	'''Reply to the message brought by `update`.

	:param update: The update containing the message to reply to.
	:param **args: The same as `sendMessage`.
	'''
	sendMessage(chat_id=update.effective_chat.id,
		reply_to_message_id=update.effective_message.message_id,
		**args)


def on_webhook(request):
	update = Update.de_json(request.get_json(force=True), bot)
	dispatcher.process_update(update)


app = Flask(__name__)


@app.route('/', methods=('GET', 'POST'))
def on_request():
	if request.args.get('whs', '') == WEBHOOK_SECRET:
		on_webhook(request)
		return 'OK'
	elif CONTROL_SECRET and request.args.get('ctrl', '') == CONTROL_SECRET:
		return on_control(request.args.get('action'), request)
	else:
		return on_info(request.args.get('action'), request)

