import json
import datetime


def timestamp8601():
	'''Returns a timestamp in ISO 8601 format.'''
	return datetime.datetime.now().isoformat()


def _make_json(data, status=200, headers=None):
	'''Make a Flask (Werkzeug) response with JSON data and content-type.
	A `timestamp` field with the time of invocation in ISO 8601 format will be
	appended if not present.

	:param data: JSON data. Transform custom types beforehand!
	:param status: `int` or `str`, the same required by Werkzeug.
	:param headers: Optional custom headers. `content-type` will be overwritten
		as `application/json`.
	'''
	data = data.copy()
	if 'timestamp' not in data:
		data['timestamp'] = timestamp8601()
	result = json.dumps(data, indent=2)
	if headers:
		headers = headers.copy()
		headers['content-type'] = 'application/json'
	else:
		headers = { 'content-type': 'application/json' }
	return (result, status, headers)


def _dict_map(iterable):
	'''Turn an iterable of `telegram` objects into a list of dicts.

	This is `python-telegram-bot` specific.'''
	return [i for i in map(lambda v: v.to_dict(), iterable)]
