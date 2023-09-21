from __future__ import annotations
from types import TracebackType
from typing import Any, Awaitable, Callable, Coroutine, Optional, Set, Type, TypeVar, Union, TYPE_CHECKING, Tuple, Dict, cast
from typing_extensions import ParamSpec

if TYPE_CHECKING:
    TParams = ParamSpec('TParams')
else:
    TParams = TypeVar('TParams')

from functools import wraps, partial
import asyncio
from asyncio import Lock, Task, Condition
from contextlib import AbstractAsyncContextManager, AbstractContextManager

from .. import botState
from ..logging import LogCategory


TReturn = TypeVar("TReturn", covariant=True)

def asyncWrap(func: Callable[TParams, TReturn]) -> Callable[TParams, Coroutine[Any, Any, TReturn]]:
    """Function decorator wrapping a synchronous function into an asynchronous executor call.
    This is a last-resort expensive operation, as a new process is spawned off for each call of the function.
    Where possible, use natively asynchronous code, e.g aiohttp instead of requests.

    Author:
    https://stackoverflow.com/a/50450553/11754606

    :param Callable func: Function to wrap. Cannot be a coroutine. (any signature)
    :return: An awaitable wrapping func
    :rtype: Coroutine
    """
    @wraps(func)
    async def run(*args, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()
        pfunc = partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, pfunc)
    
    # TODO: Ignoring here because I'm not sure how to type `run`, but it appears to be correct in practise
    return run # type: ignore


def extractFuncName(f: Union[Awaitable, Callable]) -> Tuple[str, str]:
    # https://stackoverflow.com/a/63933827
    if hasattr(f, "__qualname__"):
        name: str = f.__qualname__ # type: ignore
    else:
        name = str(f).split(" ", 3)[-2]
    
    if "." in name:
        i = len(name) - name[::-1].index(".")
        return name[:i-1], name[i:]
    else:
        if hasattr(f, "__module__"):
            return f.__module__, name
        return "main", name


def logException(task: Task, exception: BaseException, logCategory: Optional[LogCategory] = None, className: Optional[str] = None,
                    funcName: Optional[str] = None, noPrintEvent: bool = False, noPrint: bool = False):
    """Convenience method to log an exception that occurred on `task`, using `botState.client.logger`.
    This method is intended to be called by `logExceptionsOnTask`. 
    All parameters other than `task` and `exception` are optional. If not given, they will be inferred from `task`.

    :param logCategory: The category to log into (Default None)
    :type logCategory: Optional[str]
    :param className: Override for the class name to log exceptions as. When excluded, this is inferred (Default None)
    :type className: Optional[str]
    :param funcName: Override for the function name to log exceptions as. When excluded, this is inferred (Default None)
    :type funcName: Optional[str]
    :param noPrintEvent: Give True to skip printing the event string (will still be logged to file) (Default False)
    :type noPrintEvent: Optional[bool]
    :param noPrint: Give True to skip printing the exception entirely (will still be logged to file) (Default False)
    :type noPrint: Optional[bool]
    """
    if logCategory is None:
        logCategory = LogCategory.misc

    if className is None or funcName is None:
        # TODO: Ignoring warning here on incorrect type return from get_coro
        # Theoretically this can return a Generator, but I can't see where in the code that would happen!
        # Also, Task.__init__ will validate that the task's coro is a Coroutine
        extractedClass, extractedFunc = extractFuncName(task.get_coro()) # type: ignore[reportGeneralTypeIssues]
        className = extractedClass if className is None else className
        funcName = extractedFunc if funcName is None else funcName

    botState.client.logger.log(className, funcName, str(exception), category=logCategory, exception=exception,
                                noPrint=noPrint, noPrintEvent=noPrintEvent)


def logExceptionsOnTask(task: Task, logCategory: Optional[LogCategory] = None, className: Optional[str] = None, funcName: Optional[str] = None,
                        noPrintEvent: bool = False, noPrint: bool = False):
    """See if any exceptions occurred in `task`. If they did, then log them using `botState.client.logger`.
    If `task` has not finished execution, this is treated as an exception and is logged.
    If `task` has no exceptions set, do nothing.
    All parameters other than `task` are optional. If not given, they will be inferred from `task`.

    :param logCategory: The category to log into (Default None)
    :type logCategory: Optional[str]
    :param className: Override for the class name to log exceptions as. When excluded, this is inferred (Default None)
    :type className: Optional[str]
    :param funcName: Override for the function name to log exceptions as. When excluded, this is inferred (Default None)
    :type funcName: Optional[str]
    :param noPrintEvent: Give True to skip printing the event string (will still be logged to file) (Default False)
    :type noPrintEvent: Optional[bool]
    :param noPrint: Give True to skip printing the exception entirely (will still be logged to file) (Default False)
    :type noPrint: Optional[bool]
    """
    if e := cast(Optional[Exception], task.exception()):
        logException(task, e, logCategory=logCategory, className=className, funcName=funcName,
                        noPrintEvent=noPrintEvent, noPrint=noPrint)


class BasicScheduler:
    """A very basic handler for parallelizing coroutine executions and handling their exceptions.
    """
    def __init__(self) -> None:
        self.tasks: Set[Task] = set()


    def any(self) -> bool:
        return bool(self.tasks)


    def add(self, coro: Union[Coroutine, Task]) -> Task:
        """Schedule a coroutine execution onto the event loop.
        Pass a normal parenthesized call to a coroutine, but without awaiting it.
        Execution begins immediately.

        :param coro: The coroutine execution to parallelize
        :type coro: Awaitable
        :return: A task wrapping the execution
        :rtype: Task
        """
        t = asyncio.create_task(coro) if isinstance(coro, Coroutine) else coro
        self.tasks.add(t)
        return t


    async def wait(self):
        """Wait for all registered tasks to complete
        """
        if self.tasks:
            await asyncio.wait(self.tasks)


    def logExceptions(self, logCategory: Optional[LogCategory] = None, className: Optional[str] = None, funcName: Optional[str] = None, noPrintEvent: bool = False,
                        noPrint: bool = False):
        """See if any exceptions occurred in the registered tasks. If they did, then log them using `botState.client.logger`.

        :param logCategory: The category to log into (Default None)
        :type logCategory: Optional[str]
        :param className: Override for the class name to log exceptions as. When excluded, this is inferred (Default None)
        :type className: Optional[str]
        :param funcName: Override for the function name to log exceptions as. When excluded, this is inferred (Default None)
        :type funcName: Optional[str]
        :param noPrintEvent: Give True to skip printing the event string (will still be logged to file) (Default False)
        :type noPrintEvent: Optional[bool]
        :param noPrint: Give True to skip printing the exception entirely (will still be logged to file) (Default False)
        :type noPrint: Optional[bool]
        """
        for t in self.tasks:
            logExceptionsOnTask(t, logCategory=logCategory, className=className, funcName=funcName, noPrintEvent=noPrintEvent,
                                noPrint=noPrint)


    def raiseExceptions(self):
        """Raise any exceptions on the registered tasks.
        Since this operation is a raise, it will halt on the first encountered exception.
        To handle all exceptions, call repeatedly or use getExceptions.

        :raises Exception: When an exception is encountered on any registered task
        """
        for t in self.tasks:
            if e := t.exception():
                raise e


    def getExceptions(self) -> Dict[Coroutine, BaseException]:
        """Get all exceptions set on the registered tasks. This does not raise the exceptions.
        Will also include CancelledError/InvalidStateError if raised on the task.

        :return: A mapping from coroutines to raised exceptions. Will be empty if no exceptions were raised
        :rtype: Dict[Coroutine, BaseException]
        """
        # TODO: Ignoring warning here on incorrect type return from get_coro
        # Theoretically this can return a Generator, but I can't see where in the code that would happen!
        # Also, Task.__init__ will validate that the task's coro is a Coroutine
        exceptions: Dict[Coroutine, BaseException] = {}
        for t in self.tasks:
            try:
                e = t.exception()
            except BaseException as ex:
                exceptions[t.get_coro()] = ex # type: ignore[reportGeneralTypeIssues]
            else:
                if e is not None:
                    exceptions[t.get_coro()] = e # type: ignore[reportGeneralTypeIssues]

        return exceptions


    def getResults(self) -> Dict[Coroutine, Tuple[Optional[BaseException], Any]]:
        """Get all results returned by the registered tasks.
        Results are returned as a mapping:
        {
            coro: (ex, result)
        }
        coro is the coroutine that was executed.
        ex is the exception that was set on the task if any, including CancelledError/InvalidStateError.
        result is the return value of the task.

        :return: A mapping from coroutines to their exceptions and returned values
        :rtype: Dict[Coroutine, Tuple[Optional[BaseException], Any]]
        """
        # TODO: Ignoring warning here on incorrect type return from get_coro
        # Theoretically this can return a Generator, but I can't see where in the code that would happen!
        # Also, Task.__init__ will validate that the task's coro is a Coroutine
        results: Dict[Coroutine, Tuple[Optional[BaseException], Any]] = {}
        for t in self.tasks:
            c = t.get_coro()
            try:
                results[c] = (None, t.result()) # type: ignore[reportGeneralTypeIssues]
            except BaseException as e:
                results[c] = (e, None) # type: ignore[reportGeneralTypeIssues]
        
        return results


    def clear(self):
        """Delete all recorded tasks
        """
        self.tasks.clear()

    
    def __bool__(self) -> bool:
        """Decide if the scheduler has any tasks registered

        :return: True if at least one task is scheduled, False otherwise
        :rtype: bool
        """
        return bool(self.tasks)


    def __len__(self) -> int:
        """Get the number of registered tasks

        :return: The number of tasks
        :rtype: int
        """
        return len(self.tasks)


async def awaitCoroAndLogExceptions(coro: Coroutine, logCategory: Optional[LogCategory] = None, className: Optional[str] = None, funcName: Optional[str] = None,
                        noPrintEvent: bool = False, noPrint: bool = False) -> Any:
    """Await `coro`, and then log any exceptions that occurred using `botState.client.logger`.
    All parameters other than `coro` are optional. If not given, they will be inferred from `coro`.

    :param coro: The coroutine whose exceptions to log
    :type coro: Awaitable
    :param logCategory: The category to log into (Default None)
    :type logCategory: Optional[str]
    :param className: Override for the class name to log exceptions as. When excluded, this is inferred (Default None)
    :type className: Optional[str]
    :param funcName: Override for the function name to log exceptions as. When excluded, this is inferred (Default None)
    :type funcName: Optional[str]
    :param noPrintEvent: Give True to skip printing the event string (will still be logged to file) (Default False)
    :type noPrintEvent: Optional[bool]
    :param noPrint: Give True to skip printing the exception entirely (will still be logged to file) (Default False)
    :type noPrint: Optional[bool]
    :return: A task wrapping the execution
    :rtype: Task
    """
    inner = asyncio.create_task(coro)
    await inner
    logExceptionsOnTask(inner, logCategory=logCategory, className=className, funcName=funcName,
                        noPrintEvent=noPrintEvent, noPrint=noPrint)
    return inner.result


def scheduleCoroWithLogging(coro: Coroutine, logCategory: Optional[LogCategory] = None, className: Optional[str] = None, funcName: Optional[str] = None,
                        noPrintEvent: bool = False, noPrint: bool = False) -> Task:
    """Schedule a coroutine execution onto the event loop, and log any exceptions that occur during
    execution with `botState.client.logger`.
    Very useful for synchronously scheduling a coroutine for execution without *completely* missing any exceptions.
    Pass a normal parenthesized call to a coroutine, but without awaiting it.
    The task that is contructed is returned, but you don't need to do anything with this for execution to complete.
    If your coroutine returned a value, this will be the result of the task once it completes.
    All parameters other than `coro` are optional. If not given, they will be inferred from `coro`.

    :param coro: The coroutine execution to parallelize
    :type coro: Awaitable
    :param logCategory: The category to log into (Default None)
    :type logCategory: Optional[str]
    :param className: Override for the class name to log exceptions as. When excluded, this is inferred (Default None)
    :type className: Optional[str]
    :param funcName: Override for the function name to log exceptions as. When excluded, this is inferred (Default None)
    :type funcName: Optional[str]
    :param noPrintEvent: Give True to skip printing the event string (will still be logged to file) (Default False)
    :type noPrintEvent: Optional[bool]
    :param noPrint: Give True to skip printing the exception entirely (will still be logged to file) (Default False)
    :type noPrint: Optional[bool]
    :return: A task wrapping the execution
    :rtype: Task
    """
    return asyncio.create_task(awaitCoroAndLogExceptions(coro, logCategory=logCategory, className=className, funcName=funcName,
                        noPrintEvent=noPrintEvent, noPrint=noPrint))


async def nullCoro(value: Optional[Any]):
    """Dummy coroutine function to return the given value. Acts as an analogue for C#'s Task.CompletedTask or Task.FromResult

    :param value: The value to immediately return
    :type value: Optional[Any]
    :return: `value`
    :rtype: Optional[Any]
    """
    return value


class CancellationToken:
    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self):
        self.cancelled = True
