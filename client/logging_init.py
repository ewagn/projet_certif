from logging.config import dictConfig
import atexit

from client.logging_models import LOGGING, LogContext

dictConfig(LOGGING)

context = LogContext()
context.open()
atexit.register(context.close)


# root_logger = lg.getLogger('')
# root_logger.setLevel(DEBUG)
# client_filter = ClientFilter(name="client_filter")
# root_logger.addFilter(client_filter)

# console_handler = StreamHandler()
# console_handler.setFormatter(console_formatter)
# root_logger.addHandler(console_handler)

# sql_handler = SQLHandler()
# sql_handler.setLevel(WARNING)
# root_logger.addHandler(sql_handler)