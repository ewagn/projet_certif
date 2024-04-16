import logging as lg
from logging import StreamHandler, FileHandler, DEBUG, WARNING

from client.loggiging_models import ClientFilter, console_formatter, SQLHandler

root_logger = lg.getLogger('')
root_logger.setLevel(DEBUG)
client_filter = ClientFilter(name="client_filter")
root_logger.addFilter(client_filter)

console_handler = StreamHandler()
console_handler.setFormatter(console_formatter)
root_logger.addHandler(console_handler)

sql_handler = SQLHandler()
sql_handler.setLevel(WARNING)
root_logger.addHandler(sql_handler)