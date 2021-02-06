import os
import re
import json
import logging
import datetime
from sys import exit
from flask import Flask, request
from telegram import Message, Update
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, InlineQueryHandler
import db
from utils import _dict_map, timestamp8601


###
### Preperations
###
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_ID = BOT_TOKEN.split(':')[0]
if not BOT_TOKEN:
	exit(logging.error('BOT_TOKEN not set.'))
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')
if not WEBHOOK_SECRET:
	exit(logging.error('WEBHOOK_SECRET not set.'))
CONTROL_SECRET = os.getenv('CONTROL_SECRET')
DEBUG_CHAT = os.getenv('DEBUG_CHAT')
# Chat IDs may be int or str.
if DEBUG_CHAT:
	try:
		DEBUG_CHAT = int(DEBUG_CHAT)
	except: pass
# NOTE: This count is changeable, through a control command.
COMMAND_LIST_COUNT = os.getenv('COMMAND_LIST_COUNT', 5)


updater = Updater(token=os.getenv('BOT_TOKEN'))
dispatcher = updater.dispatcher
bot = updater.bot
app = Flask(__name__)
# All below are all lists of (name/title, description) pairs.
commands = []
inline_queries = []
control_commands = []


###
### Helper classes and functions
###


def _increment_usage_count(kind, id):
	db.r.hincrby('bot-{}/usage/{}'.format(BOT_ID, kind), id, 1)


# Update 2021-02-06: Changed command list handling. A dict is added.
# Because I don't want to maintain another dict.
# Was discussed in
# https://github.com/python-telegram-bot/python-telegram-bot/issues/1859 and
# https://github.com/python-telegram-bot/python-telegram-bot/pull/1911
# Perhaps make a PR to https://github.com/python-telegram-bot/ptbcontrib
class DescribedCountedCommandHandler(CommandHandler):
	'''`telegram.ext.CommandHandler` with a description and usage count.

	Use `updateCommands` to `setMyCommands` all registered commands.
	'''

	SPACE_RE = re.compile(r'\s')
	def __init__(self, *args, description=None, **kwargs):
		super().__init__(*args, **kwargs)
		self.description = description

	def handle_update(self, update, *args, **kwargs):
		super().handle_update(update, *args, **kwargs)
		# Convenience attribute for text after the command.
		text = update.effective_message.text
		update.effective_message.after_text = text[self.SPACE_RE.search(text).end():]

		_increment_usage_count('command', self.command)


class InvalidInlineQueryHandler(Exception): pass
class DescribedCountedInlineQueryHandler(InlineQueryHandler):
	'''`telegram.ext.InlineQueryHandler` with a title and/or a description/help.

	Due to restrictions of Telegram, a title must be set.
	'''
	def __init__(self, *args, title, description=None, **kwargs):
		super().__init__(*args, **kwargs)
		self.title = title
		self.description = description

	def handle_update(self, *args, **kwargs):
		super().handle_update(*args, **kwargs)
		_increment_usage_count('inline_query', self.title)


# Update 2021-02-06: Deprecated. Use a more friendly command list mechanism.
def updateCommands(deleteUnused=False):
	'''Invoke `setMyCommands` using registered command handlers.

	:param deleteUnused: Delete those not registered in this bot instance.
	'''
	registered = []
	for group in dispatcher.handlers.values():
		for handler in group:
			if not isinstance(handler, DescribedCountedCommandHandler):
				continue
			if handler.description:
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
				if item[0] == lastItem.command:
					unused = False
					break
			if unused:
				registered.append(lastItem)

	return bot.setMyCommands(commands=registered)


def add_command(command, description=None):
	'''Convenience decorator to add a command handler.

	Usage:
	```
	@add_command('start')
	def c_start(update, context):
		replyMessage(update, 'Hello, {}'.format(update.effective_user.first_name))
	```

	:param command: The same as of `telegram.ext.CommandHandler`.
	:param description: Optional. Add a description for the command. Effective
		only after `updateCommands()`.
	'''

	# Don't repeat the same commands.
	if isinstance(command, str) and command in commands:
		return
	elif False not in map(lambda c: c in commands, command):
		return

	def _add_command(handler_func):
		dispatcher.add_handler(DescribedCountedCommandHandler(
			command, handler_func, description=description))
		if isinstance(command, str):
			commands.append((command, description))
		else:
			for c in command:
				commands.append((c, description))
		return handler_func

	return _add_command


def get_admins(id_only=False):
	'''Get 'admins' of this bot.

	For now, we'll take the admins of its debug chat.

	:param id_only: Optional. Return only their IDs if `True`. Default `False`.
	'''
	if not DEBUG_CHAT:
		return ()
	admins = []
	for admin in bot.getChatAdministrators(DEBUG_CHAT):
		if id_only:
			admins.append(admin.user.id)
		else:
			admins.append(admin.user.to_dict())
	return admins


def add_control_command(command, description=''):
	'''Convenience decorator to add a control (admin) command handler.

	Usage is the same as `add_command`.
	Admins are set in `control.py`.
	'''
	from functools import wraps
	def _add_control_command(handler_func):
		@wraps(handler_func)
		def _control_command(update, context):
			if update.effective_user.id not in get_admins(id_only=True):
				return replyMessage(
					update,
					text='_This command is for admins only._',
					parse_mode='md')
			handler_func(update, context)
		dispatcher.add_handler(DescribedCountedCommandHandler(
			command, _control_command, description='CONTROL {}'.format(
				description)))
		return _control_command
	return _add_control_command


def add_inline_query(title, description='', **kwargs):
	'''Convenience decorator to add an inline query handler.
	For (keyword) arguments, see `telegram.ext.InlineQueryHandler`.
	For arguments `title` and `description`,
	see `DescribedCountedInlineQueryHanlder`.

	:param pattern:
	:param **kwargs:
	'''
	def _add_inline_query(callback):
		dispatcher.add_handler(DescribedCountedInlineQueryHandler(callback,
			title=title,
			description=description,
			**kwargs))
		inline_queries.append((title, description))
	return _add_inline_query


def get_usage_counts(kind, reverse=False):
	'''Get usage counts from Redis for specified `kind`.
	Beware that, due to the nature of Redis, it's not perfectly accurate.

	:param kind: Can be either `command` or `inline_query`.
	:param reverse: Use counts as dict keys if `True`, otherwise _the_ keys.
		Default `False`.
	'''
	raw = db.r.hgetall('bot-{}/usage/{}'.format(BOT_ID, kind))
	if reverse:
		counts = {}
		for key, count in raw.items():
			count = int(count)
			if count not in counts:
				counts[count] = [key.decode()]
			else:
				counts[count].append(key.decode())
		return counts
	else:
		return { key.decode(): int(count) for key, count in raw.items() }


def get_most_used(kind, n):
	'''Get `n` most used commands or inline queries.

	:param kind: `command` or `inline_query`.
	:param n: '*' for all, otherwise a positive integer.
	'''

	if n == '*':
		n = -1
	counts = get_usage_counts(kind, reverse=True)
	muc = []
	n_muc = 0
	if kind == 'command':
		descriptions = commands
	elif kind == 'inline_query':
		descriptions = inline_queries
	sorted_counts = sorted(counts.keys(), reverse=True)
	for count, counted in sorted_counts.items():
		for item in counted:
			for described in descriptions:
				if described[0] == item:
					muc.append({
						'count': count,
						'command': item,
						'description': described[1]
					})
					n_muc += 1
					if n_muc == n:
						break
			if n_muc == n:
				break
		if n_muc == n:
			break
	return muc


def update_most_used_commands(n=None):
	'''`setMyCommands` only the most used `n` commands, plus 'help'.

	This helps reduce the accumulated command list pop-up of chats.

	:param n: The number of commands to show in list pop-up. Set n to `False` for all.
	'''
	if not n:
		n = COMMAND_LIST_COUNT

	update = get_most_used('commands', n)
	if n < len(commands):
		desc = '{}/{} commands listed. See all.'.format(n, len(commands))
	else:
		desc = 'See all commands, inline queries, and control commands.'
	update.append(({
		'command': 'help',
		'description': desc
	}))

	bot.setMyCommands(commands=get_most_used_commands)


def set_command_list_count(count):
	global COMMAND_LIST_COUNT
	COMMAND_LIST_COUNT = count


@add_command('help')
def c_help(update, context):
	replyMessage(update, text='''List of all commands, inline queries, and control commands.
_Commands_
{}
_Inline queries_
{}
_Control commands_
{}'''.format(
		'\n'.join('*{}* {}'.format(i[0], i[0]) for i in commands),
		'\n'.join('*{}* {}'.format(i[0], i[1]) for i in inline_queries),
		'\n'.join('*{}* {}'.format(i[0], i[1]) for i in control_commands),
	), parse_mode='md')


@add_command('most_used')
def c_most_used(update, context):
	text = 'Most used commands:'
	for count, commands in get_most_used('command', '*').items():
		for command in commands:
			text += '\n{}\t{}'.format(count, command)
	text += 'Most used inline queries:'
	for count, queries in get_most_used('inline_queries', '*').items():
		for query in inline_queries:
			text += '\n{}\t{}'.format(count, query)


def sendMessage(**kwargs):
	'''Patched `telegram.Bot.send_message`.
	Currently provides a shorthand for `parse_mode='MarkdownV2'`.

	:param parse_mode: Optional. Pass `md` for `MarkdownV2`.
	:param **kwargs: The same as of `telegram.Bot.send_message`.
	'''
	if kwargs.get('parse_mode', None) == 'md':
		kwargs['parse_mode'] = 'MarkdownV2'
	bot.sendMessage(**kwargs)


def replyMessage(update, **kwargs):
	'''Reply to the message brought by `update`.

	:param update: The update containing the message to reply to.
	:param **kwargs: The same as of `sendMessage`.
	'''
	sendMessage(chat_id=update.effective_chat.id,
		reply_to_message_id=update.effective_message.message_id,
		**kwargs)


def _iq_text_reply(**kwargs):
	return InlineQueryResultArticle(id=kwargs.get('id', timestamp8601()),
		title=kwargs.get('title'),
		input_message_content=InputTextMessageContent(kwargs.get('text'),
			parse_mode=kwargs.get('parse_mode', None),
			disable_web_page_preview=kwargs.get('disable_preview', None)))


def answerInlineQueryInText(update, replies, **kwargs):
	'''Answer inline query in text only.

	:param update: The update containing the inline query to answer.
	:param replies: A list or tuple of replies. Each is a dict of the format
		`{ title, text, id, parse_mode, disable_preview }`. Only `title` and
		`text` are required.
		:param id: Optional. If not set, an ISO 8601 timestamp will be set instead.
		:param parse_mode: Optional. Pass `md` for `MarkdownV2`.
		:param disable_preview: Optional. Only works if a link is present.
	:param **kwargs: See https://core.telegram.org/bots/api#inlinequery
	'''
	if not isinstance(replies, (list, tuple)):
		replies = (replies,)
	update.inline_query.answer(
		results=[_iq_text_reply(**r) for r in replies],
		**kwargs)


# Update 2021-02-06: Deprecated. Use a more friendly command list mechanism.
def update_inline_queries():
	iq = []
	helps = []

	for group in dispatcher.handlers.values():
		for handler in group:
			if isinstance(handler, DescribedCountedInlineQueryHandler):
				iq.append((handler.title, handler.description))
				helps.append(_iq_text_reply(title=handler.title, text=handler.description))

	def inline_query_help(update, context):
		answerInlineQueryInText(update, helps)
	add_inline_query(title='Inline queries help list', pattern=r'^\s*$')(
		inline_query_help)


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

