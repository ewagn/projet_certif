from random import random, randrange
from typing import Optional
import time
import asyncio

def wait_rand(size: str | None = None):
    """Fonction qui permet de créer un temps de latence aléatoire, simulant une navigation humaine."""
    if size == "small":
        start = 3
        end = 5
        factor = 1
    elif size == "medium" or not size:
        start = 5
        end = 10
        factor = 10
    elif size == "long":
        start = 20
        end = 60
        factor = 10
    time_to_wait = random() * factor
    time_to_wait += randrange(start, end, 1)

    time.sleep(time_to_wait)
