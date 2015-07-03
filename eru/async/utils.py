# coding: utf-8

import re

ports_pattern = re.compile(r'\$port(?P<port>\d+)')

def replace_ports(cmd, ports):

    def repl(match):
        p = match.group('port')
        r = ports.get(p, '')
        if r:
            return r
        return match.group()

    ports = {str(i): str(port) for i, port in enumerate(ports, 1)}
    return ports_pattern.sub(repl, cmd)
