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
