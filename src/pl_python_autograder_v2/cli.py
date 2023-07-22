from jsonargparse import ActionConfigFile, ArgumentParser

# TODO use this https://dev.to/bowmanjd/build-command-line-tools-with-python-poetry-4mnc
# https://pypi.org/project/cli-test-helpers/
# https://medium.com/clarityai-engineering/how-to-create-and-distribute-a-minimalist-cli-tool-with-python-poetry-click-and-pipx-c0580af4c026
# https://www.pluralsight.com/tech-blog/python-cli-utilities-with-poetry-and-typer/


def main() -> None:
    parser = ArgumentParser(
        prog="pl_python_autograder",
        description="Command line interface for the PrairieLearn Python autograder.",
    )

    parser.add_argument("--opt1", type=int, help="Help for option 1.", required=True)
    parser.add_argument("--config", action=ActionConfigFile)

    cfg = parser.parse_args()
    print(f"Your number was {cfg.opt1}")


if __name__ == "__main__":
    main()
