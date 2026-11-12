from flask import Blueprint

claims_bp = Blueprint('claims', __name__)

from . import routes  # noqa: E402, F401
