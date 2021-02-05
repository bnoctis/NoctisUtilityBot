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
_WEBHOOK_PATH = '/' + WEBHOOK_SECRET


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


def on_control(action):
	result = None
	if action == 'on':
		endpoint = '{}?whs={}'.format(request.base_url, WEBHOOK_SECRET)
		if endpoint.startswith('http://'):
			endpoint = endpoint.replace('http://', 'https://')
		elif not endpoint.startswith('https'):
			endpoint = 'https://' + endpoint
		result = {
			'setWebhook': bot.setWebhook('{}?whs={}'.format(
				request.base_url, WEBHOOK_SECRET)),
			'endpoint': endpoint,
			'setMyCommands': bot.setMyCommands(bot.commands),
			'commands': bot.commands
		}
	elif action == 'env':
		result = { 'env': os.environ }
	return _make_json(result)


def on_info(action):
	result = { 'hello': request.remote_addr }
	return _make_json(result)


def on_webhook():
	update = Update.de_json(request.get_json(force=True), bot)
	dispatcher.process_update(update)


app = Flask(__name__)
app.route(_WEBHOOK_PATH)(on_webhook)
app.route('/info/<action>')(on_info)
if CONTROL_SECRET:
	app.route('/ctrl/{}/<action>'.format(CONTROL_SECRET))(on_info)


def main():
	updater.start_polling()
	app.run()
