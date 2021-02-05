'''Bilibili related functions.

'''


import httpx


# Following are BV - AV transform functions, courtesy of mcfx,
# https://www.zhihu.com/question/381784377/answer/1099438784
_ab_table = 'fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF'
_ab_tr = {}
for i in range(58):
	_ab_tr[_ab_table[i]] = i
_ab_s = [11, 10, 3, 8, 4, 6]
_ab_xor = 177451812
_ab_add = 8728348608


def bv2av(x):
	r = 0
	for i in range(6):
		r += _ab_tr[x[_ab_s[i]]] * 58 ** i
	return (r - _ab_add ) ^ _ab_xor


def av2bv(x):
	x = (x ^ _ab_xor) + _ab_add
	r = list('BV1  4 1 7  ')
	for i in range(6):
		r[_ab_s[i]] = _ab_table[x // 58 ** i % 58]
	return ''.join(r)


def b23_to_full_clear(b23, to_av=True):
	'''Transform b23.tv short links, and clear tracking params.

	:param to_av: If `True`, transform the BVn in the link to AVn.
	'''
	if 'b23.tv/' not in b23:
		b23 = 'https://b23.tv/{}'.format(b23)
	full = httpx.get(b23, allow_redirects=False).headers['location']
	full = full[:full.index('?')]
	if to_av:
		bv = full[full.index('BV'):]
		full = full.replace(bv, 'av{}'.format(bv2av(bv)))
	return full
