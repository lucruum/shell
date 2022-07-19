import subprocess


def main() -> int:
    while True:
        subprocess.run(input("$ "), shell=True)
        print()
    return 0


if __name__ == "__main__":
    exit(main())
