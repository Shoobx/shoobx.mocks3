###############################################################################
#
# Copyright 2016 by Shoobx, Inc.
#
###############################################################################
"""Server
"""
import argparse
import os
import sys
import werkzeug.serving

from shoobx.mocks3 import config

class ShoobxRequestHandler(werkzeug.serving.WSGIRequestHandler):

    def log_request(self, code='-', size=None):
        size = size or self.environ.get('shoobx.response_size', '-')
        self.log(
            'info', '"%s" %s %s - %s',
            self.requestline, code, size,
            self.environ.get('HTTP_USER_AGENT', '-').split(' ')[0])

    def log(self, type, message, *args):
        werkzeug.serving._log(
            type, '%s - %s [%s] %s\n' % (
                self.address_string(),
                self.environ.get('shoobx.user', '-'),
                self.log_date_time_string(),
                message % args))


parser = argparse.ArgumentParser(
    prog="serve",
    usage=("serve [-c|--config-file <path-to-config>]"),
    description="Shoobx Mock S3 Server")

parser.add_argument(
    '-c', '--config-file', dest='config_file',
    default=os.path.join(config.SHOOBX_MOCKS3_HOME, 'config', 'mocks3.cfg'),
    help='The location of the configuration file.')


def serve(argv=sys.argv[1:]):
    args = parser.parse_args(argv)
    app = config.configure(args.config_file)

    # Start the server.
    conf = config.load_config(args.config_file)
    host = conf.get('shoobx:server', 'host-ip')
    port = int(conf.get('shoobx:server', 'host-port'))
    app.run(
        host=host, port=port,
        request_handler=ShoobxRequestHandler,
        use_reloader=conf.getboolean('shoobx:mocks3', 'reload'),
        use_debugger=conf.getboolean('shoobx:mocks3', 'debug'),
    )
