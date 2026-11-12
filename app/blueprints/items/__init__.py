from flask import Blueprint

items_bp = Blueprint('items', __name__)

from . import routes  # noqa: E402, F401
