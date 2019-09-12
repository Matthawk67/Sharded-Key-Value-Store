# Error Handling Class
import json


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, response, status_code=None):
        Exception.__init__(self)
        if isinstance(response, dict):
            self.response = json.dumps(response)
        else:
            self.response = response
        if status_code is not None:
            self.status_code = status_code
