import os
import json
import logging
import datetime
from sys import exit
from flask import Flask, request
from telegram import Message, Update
from telegram.ext import Updater, CommandHandler
from utils import _dict_map


###
### Preperations
###
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
	exit(logging.error('BOT_TOKEN not set.'))
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')
if not WEBHOOK_SECRET:
	exit(logging.error('WEBHOOK_SECRET not set.'))
CONTROL_SECRET = os.getenv('CONTROL_SECRET')
DEBUG_CHAT = os.getenv('DEBUG_CHAT')
updater = Updater(token=os.getenv('BOT_TOKEN'))
dispatcher = updater.dispatcher
bot = updater.bot
app = Flask(__name__)


###
### Helper classes and functions
###


# Because I don't want to maintain another dict.
# Was discussed in
# https://github.com/python-telegram-bot/python-telegram-bot/issues/1859 and
# https://github.com/python-telegram-bot/python-telegram-bot/pull/1911
# Perhaps make a PR to https://github.com/python-telegram-bot/ptbcontrib
class DescribedCommandHandler(CommandHandler):
	'''`telegram.ext.CommandHandler` with a description.

	Use `updateCommands` to `setMyCommands` all registered commands.
	'''
	def __init__(self, *args, description=None, **kwargs):
		super().__init__(*args, **kwargs)
		self.description = description
DCommandHandler = DescribedCommandHandler


def updateCommands(deleteUnused=False):
	'''Invoke `setMyCommands` using registered command handlers.

	:param deleteUnused: Delete those not registered in this bot instance.
	'''
	registered = []
	for handler in dispatcher.handlers:
		if isinstance(handler, DCommandHandler) and handler.description:
			if isinstance(handler.command, str):
				registered.append((handler.command, handler.description))
			else:
				# XXX: Is there a better way to specify one description for
				# each command of a handler? A dict?
				for command in handler.command:
					registered.append((command, handler.description))

	if not deleteUnused:
		lastSet = _dict_map(bot.commands)
		for lastItem in lastSet:
			unused = True
			for item in registered:
				if item['command'] == lastItem['command']:
					unused = False
					break
			if unused:
				registered.append(lastItem)

	bot.setMyCommands(commands=registered)


def add_command(command, description=None):
	'''Convenience decorator to add a command handler.

	Usage:
	```
	@add_command('start')
	def c_start(update, context):
		replyMessage(update, 'Hello, {}'.format(update.effective_user.first_name))
	```

	:param command: The same as `telegram.ext.CommandHandler`.
	:param description: Optional. Add a description for the command. Effective
		only after `updateCommands()`.
	'''

	def _add_command(handler_func):
		dispatcher.add_handler(
			DCommandHandler(command, handler_func, description=description))
	return _add_command


def sendMessage(**kwargs):
	'''Patched `telegram.Bot.send_message`.
	Currently provides a shorthand for `parse_mode='MarkdownV2'`.

	:param parse_mode: Optional. Pass `md` for `MarkdownV2`.
	:param **kwargs: The same as `telegram.Bot.send_message`.
	'''
	if kwargs.get('parse_mode', None) == 'md':
		kwargs['parse_mode'] = 'MarkdownV2'
	bot.sendMessage(**kwargs)


def replyMessage(update, **kwargs):
	'''Reply to the message brought by `update`.

	:param update: The update containing the message to reply to.
	:param **kwargs: The same as `sendMessage`.
	'''
	sendMessage(chat_id=update.effective_chat.id,
		reply_to_message_id=update.effective_message.message_id,
		**kwargs)


def _send_debug(kind, content):
	sendMessage(chat_id=DEBUG_CHAT,
		text='{}\n\n```{}\n```'.format(kind, content), parse_mode='md')


def on_webhook(request):
	data = request.get_json(force=True)
	update = Update.de_json(data, bot)
	if DEBUG_CHAT:
		_send_debug('webhook update', json.dumps(data, indent=2))
		try:
			dispatcher.process_update(update)
		except Exception as e:
			_send_debug('webhook exception: upd {}'.format(update.update_id), e)
			raise e
	else:
		dispatcher.process_update(update)



@app.route('/', methods=('GET', 'POST'))
def on_request():
	if request.args.get('whs', '') == WEBHOOK_SECRET:
		on_webhook(request)
		return 'OK'
	elif CONTROL_SECRET and request.args.get('ctrl', '') == CONTROL_SECRET:
		from control import on_control
		return on_control(request.args.get('action'), request)
	else:
		from info import on_info
		return on_info(request.args.get('action'), request)

