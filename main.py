from bot import bot, updater, app
from bot import add_command, replyMessage


@add_command('start')
def c_start(update, context):
	user = update.effective_user
	replyMessage(update, text='Hello, {}'.format(
		user.first_name or user.last_name or user.username))


@add_command('me', 'Show information about your account.')
def c_who(update, context):
	user = update.effective_user
	unset = lambda i: i or '\\_unset_\\'
	replyMessage(update, text='''Information of your account:
ID:\t{}
First name:\t{}
Last name:\t{}
Username:\t{}
Lang code:\t{}'''.format(user.id,
		unset(user.first_name), unset(user.last_name),
		unset(user.username), unset(user.language_code)), parse_mode='md')


def local():
	updater.start_polling()
	app.run()
