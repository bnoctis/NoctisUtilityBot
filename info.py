from utils import _make_json


def on_info(action, request):
	if action == 'base_url':
		result = {
			'base_url': request.base_url
		}
	else:
		result = { 'hello': request.remote_addr }
	result['action'] = action
	return _make_json(result)

