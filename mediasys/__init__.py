import logging

log = logging.getLogger("mediasys")

class Error(Exception):
    pass

class CliError(Error):
    pass
