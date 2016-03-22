#!/usr/bin/env python
# coding: utf-8
import atexit
import os
import sys

import IPython

from eru.app import create_app_with_celery


def hook_readline_hist():
    try:
        # Try to set up command history completion/saving/reloading
        import readline
    except ImportError:
        return

    # The place to store your command history between sessions
    histfile = os.environ["HOME"] + "/.eru_history"
    readline.parse_and_bind('tab: complete')
    try:
        readline.read_history_file(histfile)
    except IOError:
        pass  # It doesn't exist yet.

    def savehist():
        try:
            readline.write_history_file(histfile)
        except:
            print 'Unable to save Python command history'
    atexit.register(savehist)

def get_banner():
    return 'ERU shell.'

def pre_imports():
    from eru.models.base import Base
    from eru.models.host import Core, Host, _create_cores_on_host
    from eru.models.pod import Pod
    from eru.models.app import App, Version
    from eru.models.appconfig import AppConfig, ResourceConfig
    from eru.models.container import Container
    from eru.models.task import Task
    from eru.models.network import Network, IP
    from eru.models import db
    from eru.connection import rds, get_docker_client
    return locals()

def ipython_shell(user_ns):
    if getattr(IPython, 'version_info', None) and IPython.version_info[0] >= 1:
        from IPython.terminal.ipapp import TerminalIPythonApp
        from IPython.terminal.interactiveshell import TerminalInteractiveShell
    else:
        from IPython.frontend.terminal.ipapp import TerminalIPythonApp
        from IPython.frontend.terminal.interactiveshell import TerminalInteractiveShell

    class ShireIPythonApp(TerminalIPythonApp):
        def init_shell(self):
            self.shell = TerminalInteractiveShell.instance(
                config=self.config,
                display_banner=False,
                profile_dir=self.profile_dir,
                ipython_dir=self.ipython_dir,
                banner1=get_banner(),
                banner2=''
            )
            self.shell.configurables.append(self)

    app = ShireIPythonApp.instance()
    app.initialize()
    app.shell.user_ns.update(user_ns)

    eru_app, _ = create_app_with_celery()
    with eru_app.app_context():
        sys.exit(app.start())

def main():
    hook_readline_hist()
    ipython_shell(pre_imports())

if __name__ == '__main__':
    main()
