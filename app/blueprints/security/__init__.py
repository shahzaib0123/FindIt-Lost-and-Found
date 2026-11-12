from flask import Blueprint

security_bp = Blueprint('security', __name__)

from . import routes  # noqa: E402, F401
