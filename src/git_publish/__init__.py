def main() -> None:
    import sys

    from git_publish.main import main

    sys.exit(main(sys.argv[1:]))
