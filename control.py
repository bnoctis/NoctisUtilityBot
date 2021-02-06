import os
from utils import _dict_map, _make_json
from bot import bot, add_control_command, replyMessage, WEBHOOK_SECRET
from bot import set_command_list_count, update_most_used_commands


@add_control_command('commandlistcount', 'Change the number of commands in command list pop-up.')
def cc_command_list_count(update, context):
	try:
		count = int(update.effective_message.after_text)
		set_command_list_count(count)
		update_most_used_commands(count)
		replyMessage(update, text='Changed command list count to {}.'.format(count))
	except:
		replyMessage(update, text='Change failed.')


def on_control(action, request):
	result = None
	if action == 'on':
		endpoint = '{}?whs={}'.format(request.base_url, WEBHOOK_SECRET)
		result = {
			'setWebhook': bot.setWebhook(endpoint),
			'endpoint': endpoint,
			# 'setMyCommands': updateCommands(deleteUnused=True),
			# 'commands': _dict_map(bot.commands)
			# Don't set all; have a cron job periodically set several most used.
			# See cron.py
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
