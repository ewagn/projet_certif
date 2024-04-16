import asyncio
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor


class AsyncCode(ABC):
    loop : asyncio.AbstractEventLoop = ""
    instances : int = 0

    def __init__(self) -> None:
        if not self.loop :
            try :
                self.loop = asyncio.get_running_loop()
            except :
                self.loop = asyncio.new_event_loop()
            self.loop.set_task_factory(asyncio.eager_task_factory)
        self.instances += 1
    
    def __del__(self):
        self.instances += -1
        if self.instances == 0:
            self.loop.close()


class ToThreadPool(AsyncCode):
    def __init__(self, func) -> None:
        super().__init__()
        self.func = func

    async def __call__(self, *args: asyncio.Any, **kwds: asyncio.Any) -> asyncio.Any:
        with ThreadPoolExecutor() as pool :
            result = await self.loop.run_in_executor(pool, self.func, *args, **kwds)
        return result