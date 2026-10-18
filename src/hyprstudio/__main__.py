import sys


def main() -> int:
    from .gui import main as gui_main
    return gui_main(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
