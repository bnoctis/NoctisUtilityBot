from bot import bot, updater, app, _send_debug
from bot import add_command, add_inline_query, update_inline_queries
from bot import replyMessage, answerInlineQueryInText
from modules.bilibili import b23_to_full_clear


@add_command('start')
def c_start(update, context):
	user = update.effective_user
	replyMessage(update, text='Hello, {}'.format(
		user.first_name or user.last_name or user.username))


@add_command('me', 'Show information about your account.')
def c_who(update, context):
	user = update.effective_user
	not_set = lambda i: i or '_not set_'
	replyMessage(update, text='''Information of your account:
ID:\t{}
First name:\t{}
Last name:\t{}
Username:\t{}
Lang code:\t{}'''.format(user.id,
		not_set(user.first_name), not_set(user.last_name),
		not_set(user.username), not_set(user.language_code)), parse_mode='md')


@add_inline_query(title='b23.tv',
	description='Transform b23.tv links to normal bilibili.com links',
	pattern='https://b23.tv/([a-zA-Z0-9]{6,16})')
def on_inline_query(update, context):
	answerInlineQueryInText(update, {
		'title': 'b23.tv',
		'text': b23_to_full_clear(update.inline_query.query.strip())})

update_inline_queries()
