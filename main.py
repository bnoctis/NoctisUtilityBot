import os
import json
import datetime
from flask import Flask, request
from telegram import Message, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import httpx
import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


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


def _make_json(data, status=200, headers=None):
	data = data.copy()
	data['timestamp'] = datetime.datetime.now().isoformat()
	result = json.dumps(data, indent=2)
	if headers:
		headers = headers.copy()
		headers['content-type'] = 'application/json'
	else:
		headers = { 'content-type': 'application/json' }
	return (result, status, headers)


def on_control(action, request):
	result = None
	if action == 'on':
		endpoint = '{}?whs={}'.format(request.base_url, WEBHOOK_SECRET)
		result = {
			'setWebhook': bot.setWebhook('{}?whs={}'.format(
				request.base_url, WEBHOOK_SECRET)),
			'endpoint': endpoint,
			'setMyCommands': bot.setMyCommands(bot.commands),
			'commands': bot.commands
		}
	elif action == 'off':
		result = {
			'deleteWebhook': bot.deleteWebhook()
		}
	elif action == 'hookInfo':
		result = {
			'hookInfo': bot.getWebhookInfo()
		}
	elif action == 'env':
		result = { 'env': os.environ.copy() }

	if not result:
		result = {}
	result['action'] = action
	return _make_json(result)


def on_info(action, request):
	if action == 'base_url':
		result = {
			'base_url': request.base_url
		}
	else:
		result = { 'hello': request.remote_addr }
	result['action'] = action
	return _make_json(result)


def on_webhook(request):
	update = Update.de_json(request.get_json(force=True), bot)
	dispatcher.process_update(update)


app = Flask(__name__)


@app.route('/')
def on_request():
	if request.args.get('whs', '') == WEBHOOK_SECRET:
		on_webhook(request)
		return 'OK'
	elif CONTROL_SECRET and request.args.get('ctrl', '') == CONTROL_SECRET:
		return on_control(request.args.get('action'), request)
	else:
		return on_info(request.args.get('action'), request)


def local():
	updater.start_polling()
	app.run()
