import os
import redis
import psycopg2
from bot import logging


r = redis.from_url(os.getenv('REDIS_URL'))
db = psycopg2.connect(os.getenv('DATABASE_URL'))


def exec(query, vars=None, cursor=False, fetch=None, commit=False):
	'''Create a cursor, execute, fetchall if specified, and close the cursor.

	`query` and `vars` are the same you pass to `cursor.execute()`.

	:param query:
	:param vars: Optional.
	:param cursor: Optional, return the cursor if `True`.
		Default is `False`.
	:param fetch: Optional. If set, return all rows if '*', or `fetch` rows.
	:param commit: Optional. Commit if set.
	'''
	c = db.cursor()
	c.execute(query, vars)
	if commit:
		db.commit()
	if cursor:
		return c
	elif fetch:
		if fetch == '*':
			return c.fetchall()
		elif fetch == 1:
			return c.fetchone()
		else:
			return c.fetchmany(fetch)


def redis_dump():
	try:
		for key in r.keys():
			exec(
				'INSERT INTO redis_persistence (key, data) VALUES (%s， %s) ON CONFLICT UPDATE SET data = EXCLUDED.data',
				(key, r.dump(key)), commit=True)
	except Exception as e:
		logging.error('Redis dump failed', e)


def redis_load():
	try:
		for r in exec('SELECT key, data FROM redis_persistence', fetch='*'):
			r.restore(r[0], r[1])
	except Exception as e:
		logging.error('Redis load failed', e)
