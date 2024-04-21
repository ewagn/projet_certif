from logging.config import dictConfig
import atexit

from client.logging_models import LOGGING, LogContext

dictConfig(LOGGING)

context = LogContext()
context.open()
atexit.register(context.close)