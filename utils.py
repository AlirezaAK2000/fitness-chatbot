import functools


def log_function_call(func):
    """Decorator to log function calls and their output."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Function '{func.__name__}'")
        result = func(*args, **kwargs)
        print(f"Returned: {result} \n ======================================================")

        return result
    return wrapper