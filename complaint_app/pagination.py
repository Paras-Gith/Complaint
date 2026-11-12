from flask import request

from config import Config


def page_number() -> int:
    value = request.args.get("page")
    if not isinstance(value, str):
        return 1
    try:
        requested = int(value)
    except ValueError:
        return 1
    return max(1, min(requested, Config.MAX_PAGE))
