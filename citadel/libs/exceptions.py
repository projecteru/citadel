class ActionError(Exception):

    def __init__(self, code, message):
        self.code = code
        self.message = message
        # required by
        # http://docs.celeryproject.org/en/latest/userguide/tasks.html#creating-pickleable-exceptions
        super(ActionError, self).__init__(code, message)

    def __str__(self):
        return self.message


class URLPrefixError(Exception):
    pass


class ModelDeleteError(Exception):
    pass


class ModelCreateError(Exception):
    pass
