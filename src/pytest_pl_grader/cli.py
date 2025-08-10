import argparse

from _pytest import pathlib
from _pytest.config.findpaths import locate_config

from . import plugin
from .plugin import add_csv_options

COMPARE_HELP = """examples:

    pytest-benchmark {0} 'Linux-CPython-3.5-64bit/*'

        Loads all benchmarks ran with that interpreter. Note the special quoting that disables your shell's glob
        expansion.

    pytest-benchmark {0} 0001

        Loads first run from all the interpreters.

    pytest-benchmark {0} /foo/bar/0001_abc.json /lorem/ipsum/0001_sir_dolor.json

        Loads runs from exactly those files."""


class HelpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values:
            make_parser().parse_args([values, "--help"])
        else:
            parser.print_help()
        parser.exit()


class CommandArgumentParser(argparse.ArgumentParser):
    commands = None
    commands_dispatch = None

    def __init__(self, *args, **kwargs):
        kwargs["add_help"] = False

        super().__init__(*args, formatter_class=argparse.RawDescriptionHelpFormatter, **kwargs)
        self.add_argument("-h", "--help", metavar="COMMAND", nargs="?", action=HelpAction, help="Display help and exit.")
        help_command = self.add_command("help", description="Display help and exit.")
        help_command.add_argument("command", nargs="?", action=HelpAction)

    def add_command(self, name, **opts):
        if self.commands is None:
            self.commands = self.add_subparsers(
                title="commands",
                dest="command",
                parser_class=argparse.ArgumentParser,
            )
            self.commands_dispatch = {}
        if "description" in opts and "help" not in opts:
            opts["help"] = opts["description"]

        command = self.commands.add_parser(name, formatter_class=argparse.RawDescriptionHelpFormatter, **opts)
        self.commands_dispatch[name] = command
        return command


def add_glob_or_file(addoption):
    addoption("glob_or_file", nargs="*", help="Glob or exact path for json files. If not specified all runs are loaded.")


def make_parser():
    parser = CommandArgumentParser("py.test-benchmark", description="pytest_benchmark's management commands.")

    parser.add_command("list", description="List saved runs.")

    compare_command = parser.add_command(
        "compare",
        description="Compare saved runs.",
        epilog="""examples:

    pytest-benchmark compare 'Linux-CPython-3.5-64bit/*'

        Loads all benchmarks ran with that interpreter. Note the special quoting that disables your shell's glob
        expansion.

    pytest-benchmark compare 0001

        Loads first run from all the interpreters.

    pytest-benchmark compare /foo/bar/0001_abc.json /lorem/ipsum/0001_sir_dolor.json

        Loads runs from exactly those files.""",
    )
    add_glob_or_file(compare_command.add_argument)
    add_csv_options(compare_command.add_argument, prefix="")

    return parser


class HookDispatch:
    def __init__(self, *, root, **kwargs):
        _, _, config = locate_config(invocation_dir=root, args=())
        conftest_file = pathlib.Path("conftest.py")
        if conftest_file.exists():
            self.conftest = pathlib.import_path(
                conftest_file,
                **kwargs,
                root=root,
                consider_namespace_packages=bool(config.get("consider_namespace_packages")),
            )
        else:
            self.conftest = None

    def __getattr__(self, item):
        default = getattr(plugin, item)
        return getattr(self.conftest, item, default)


def main():
    parser = make_parser()
    args = parser.parse_args()
    storage = None

    hook = HookDispatch(mode=args.importmode, root=pathlib.Path("."))

    if args.command == "list":
        for file in storage.query():
            print(file)
    elif args.command == "compare":
        pass

    elif args.command is None:
        parser.error("missing command (available commands: {})".format(", ".join(map(repr, parser.commands.choices))))
    else:
        parser.error(f"unexpected command {args.command!r}")
