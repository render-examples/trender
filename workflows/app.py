"""
Shared Workflows app instance.

Imported by all task modules to register tasks with the same Workflows instance.
"""

from render_sdk import Workflows

app = Workflows()
