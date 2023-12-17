import inspect
import logging


def get_caller_function_name():
    return inspect.currentframe().f_back.f_code.co_name


def log_message_from_caller(message: str) -> object:
    function_name = get_caller_function_name()
    logging.debug(f"{function_name}: {message}")
