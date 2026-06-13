import tenacity
import traceback
import logging

def after_func(retry_state: tenacity.RetryCallState) -> None:
    if retry_state.outcome.failed:
        exc = retry_state.outcome.exception()
        logging.warning(f"Retrying {retry_state.fn.__name__} due to {repr(exc)} (Attempt {retry_state.attempt_number})")
        logging.debug(traceback.format_exception(type(exc), exc, exc.__traceback__))


def format_exception(exc: BaseException) -> str:
    """Return a user-facing message, unwrapping tenacity RetryError when present."""
    if isinstance(exc, tenacity.RetryError):
        last = exc.last_attempt
        if last.failed:
            cause = last.exception()
            if cause is not None:
                return str(cause)
    return str(exc)
