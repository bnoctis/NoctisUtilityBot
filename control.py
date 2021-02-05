import os
from utils import _dict_map, _make_json
from bot import bot, WEBHOOK_SECRET


def on_control(action, request):
	result = None
	if action == 'on':
		endpoint = '{}?whs={}'.format(request.base_url, WEBHOOK_SECRET)
		result = {
			'setWebhook': bot.setWebhook('{}?whs={}'.format(
				request.base_url, WEBHOOK_SECRET)),
			'endpoint': endpoint,
			'setMyCommands': bot.setMyCommands(bot.commands),
			'commands': _dict_map(bot.commands)
		}
	elif action == 'off':
		result = {
			'deleteWebhook': bot.deleteWebhook()
		}
	elif action == 'hookInfo':
		result = {
			'hookInfo': bot.getWebhookInfo().to_dict()
		}
	elif action == 'env':
		result = { 'env': os.environ.copy() }

	if not result:
		result = {}
	result['action'] = action
	return _make_json(result)
