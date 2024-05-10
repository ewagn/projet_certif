from logging.config import dictConfig
import atexit

from search_app.core.logging.models import LOGGING, LogContext

dictConfig(LOGGING)

context = LogContext()
context.open()
atexit.register(context.close)