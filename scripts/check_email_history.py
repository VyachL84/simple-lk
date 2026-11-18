"""Look for a literal email in locally reachable Git history, without printing the address."""

import getpass
import subprocess
import sys
import warnings


def git(*args):
    return subprocess.check_output(["git", "--no-replace-objects", *args])


def matching_objects(address):
    needle = address.casefold()
    # Read each distinct object once (including old blobs, trees, commits and annotated tags).
    for oid in git("rev-list", "--all", "--objects", "--no-object-names").decode("ascii").splitlines():
        content = git("-c", "core.quotePath=false", "cat-file", "-p", oid)
        if needle in content.decode("utf-8", errors="replace").casefold():
            yield oid


def main():
    if git("rev-parse", "--is-shallow-repository").strip() == b"true":
        print("Нужна полная история. Сначала выполните git fetch --unshallow --tags.", file=sys.stderr)
        return 2
    if not sys.stdin.isatty():
        print("Запустите проверку в своём терминале: адрес вводится скрыто.", file=sys.stderr)
        return 2
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)  # Never fall back to visible input.
        try:
            address = getpass.getpass("Какой email искать? Ввод скрыт: ").strip()
        except (getpass.GetPassWarning, EOFError):
            print("Скрытый ввод недоступен. Проверка отменена.", file=sys.stderr)
            return 2
    if address.count("@") != 1 or not all(address.split("@")) or any(ch.isspace() for ch in address):
        print("Ожидался email без пробелов.", file=sys.stderr)
        return 2
    matches = list(matching_objects(address))
    for oid in matches:
        print("Совпадение в объекте Git:", oid)
    print("Объектов с адресом в доступной истории:", len(matches))
    return int(bool(matches))


if __name__ == "__main__":
    sys.exit(main())
