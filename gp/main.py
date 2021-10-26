import argparse

version = "0.0.1"


def main(argv: list[str]):
    parser = argparse.ArgumentParser(
        prog="git-publish", description="Publish atomic Git commits."
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {version}"
    )

    args = parser.parse_args(argv)
