import sys, inspect
from cmds.configs import Config
from cmds.archive import Archive, Unarchive


# Global run command
def run(cmd_class, args):
    if not args: return cmd_class.default()

    cmd = args.pop(0).lower()
    invalid_attr = f'Invalid sub-command: "{cmd}"'
    cmd = getattr(cmd_class, cmd, AttributeError(invalid_attr))

    if callable(cmd):
        if cmd.__name__ != "default": return cmd(args)
        raise AttributeError(invalid_attr)
    elif type(cmd) == Exception: raise cmd
    return cmd


class Help:
    """Help command:

    Type 'help' to print general information about yark.
    """
    def help(self, args): return self.__doc__
    def default(self): return """Yark:

    The Yark project (Youtube Archive) is a program for the archival
    of youtube videos, playlists and history, for private use.

    Command structure: <command> [method] [arguments]
    Eg.: archive video hAjhhGCC_BA

    Commands (use <command> help to print additional help):
      archive    - Archive something to the database
      unarchive  - Unarchive something from the database
      config     - Change your configurations
      help       - Print information about any command
    """

    def me(self, cmd):
        if not cmd: return self.default()
        cmd = cmd[0].capitalize()
        err = NameError(f"Command {cmd} does not exist.")

        # Get command docs
        cmd = getattr(sys.modules[__name__], cmd, err)
        if inspect.isclass(cmd):
            return cmd().__doc__
        raise err
