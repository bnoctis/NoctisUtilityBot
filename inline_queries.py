from bot import add_inline_query, answerInlineQueryInText
from modules.bilibili import b23_to_full_clear


@add_inline_query(title='b23.tv',
	description='Transform b23.tv links to normal bilibili.com links',
	pattern='https://b23.tv/([a-zA-Z0-9]{6,16})')
def iq_b23link(update, context):
	answerInlineQueryInText(update, {
		'title': 'b23.tv',
		'text': b23_to_full_clear(update.inline_query.query.strip())})
