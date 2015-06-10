import logging
from logging.handlers import TimedRotatingFileHandler

FORMAT = '[%(asctime)s] [%(levelname)s] [%(module)s.%(funcName)s] %(message)s'

def init_logging(app):
    # init gunicorn logging
    level = logging.DEBUG if app.debug else logging.INFO
    logging.basicConfig(level=level, format='%(message)s')

    # init flask app logging
    file_path = app.config.get('ERU_OPLOG_PATH', '/tmp/eru-op.log')
    handler = TimedRotatingFileHandler(file_path, when='W0')
    handler.setFormatter(logging.Formatter(FORMAT))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
    app.logger.propagate = False
