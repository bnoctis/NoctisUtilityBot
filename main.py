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
CONTROL_SECRET = os.getenv('CONTROL_SECRET')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')
if not WEBHOOK_SECRET:
	logging.error('WEBHOOK_SECRET not set.')
	exit()


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
	elif action == 'env':
		result = { 'env': os.environ }

	if not result:
		result = {}
	result['action'] = action
	return _make_json(result)


def on_info(action, request):
	result = { 'hello': request.remote_addr }
	return _make_json(result)


def on_webhook(request):
	update = Update.de_json(request.get_json(force=True), bot)
	dispatcher.process_update(update)


app = Flask(__name__)


@app.route('/')
def on_request():
	if request.args.get('whs', '') == WEBHOOK_SECRET:
		on_webhook(request)
	elif CONTROL_SECRET and request.args.get('ctrl', '') == CONTROL_SECRET:
		on_control(args.get('action'), request)
	else:
		on_info(args.get('action'), request)


def main():
	updater.start_polling()
	app.run()
