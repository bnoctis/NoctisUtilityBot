from bot import add_command, replyMessage


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



