"""
Tool Server
Handle tool calls
"""

import yaml

class ToolServer:
    def __init__(self):
        pass
    def __call__(self, value):
        if value["type"] == "Calculator":
            return yaml.dump({
                "type": "Result",
                "data": eval(value["data"])
            })

toolServer = ToolServer()