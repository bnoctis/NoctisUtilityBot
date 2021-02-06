from bot import update_most_used_commands
from db import redis_dump


update_most_used_commands()
redis_dump()
