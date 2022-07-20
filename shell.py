from typing import *
import itertools
import shlex
import subprocess
import unittest


class Node:
    def __repr__(self) -> str:
        return "Node()"


class Program(Node):
    def __init__(self, args: List[str]) -> None:
        self.args = args

    def __repr__(self) -> str:
        return f"Program(args={self.args!r})"


class Operator(Node):
    def __init__(self, operator: str, left: Node, right: Node) -> None:
        self.operator = operator
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        return f"Operator(operator={self.operator!r}, left={self.left!r}, right={self.right!r})"


def is_word(token: str) -> bool:
    return not is_operator(token) and token not in ("(", ")")


def is_operator(token: str) -> bool:
    return token in (";", "||", "&&", "|", "<", ">")


def operator_precedence(operator: str) -> int:
    return {";": 0, "||": 1, "&&": 1, "|": 2, "<": 3, ">": 3}[operator]


def split(command: str) -> Iterable[str]:
    tokens = shlex.shlex(command, posix=True, punctuation_chars=";<>|&")
    tokens.wordchars += "@%+:,[]"
    return tokens


def parse(command: str) -> Node:
    def fold(next_operator: str = ";") -> None:
        while (
            operators
            and operators[-1] != "("
            and operator_precedence(operators[-1]) >= operator_precedence(next_operator)
        ):
            operator = operators.pop()
            right = operands.pop()
            left = operands.pop()
            operands.append(Operator(operator, left, right))

    operators: List[str] = []
    operands: List[Node] = []

    tokens = list(split(command))
    while tokens:
        token = tokens.pop(0)
        if token == "(":
            operators.append(token)
        elif token == ")":
            fold()
            assert operators.pop() == "("
        elif is_operator(token):
            fold(token)
            operators.append(token)
        else:
            args = list(itertools.takewhile(is_word, tokens))
            del tokens[: len(args)]
            operands.append(Program([token] + args))
    fold()
    return next(iter(operands), Node())


def main() -> int:
    while True:
        subprocess.run(input("$ "), shell=True)
        print()
    return 0


if __name__ == "__main__":
    exit(main())


class BashTestCase(unittest.TestCase):
    def test_parse(self) -> None:
        # fmt: off
        self.assertEqual(repr(parse(r"")), r"Node()")
        self.assertEqual(repr(parse(r"(date; cat /proc/interrupts) | md5sum | sed -r 's/^(.{10}).*$/\1/; s/([0-9a-f]{2})/\1:/g; s/:$//;'")), r"Operator(operator='|', left=Operator(operator='|', left=Operator(operator=';', left=Program(args=['date']), right=Program(args=['cat', '/proc/interrupts'])), right=Program(args=['md5sum'])), right=Program(args=['sed', '-r', 's/^(.{10}).*$/\\1/; s/([0-9a-f]{2})/\\1:/g; s/:$//;']))")
        self.assertEqual(repr(parse(r"cat /dev/urandom | tr -dc A-Za-z0-9 | head -c 32")), r"Operator(operator='|', left=Operator(operator='|', left=Program(args=['cat', '/dev/urandom']), right=Program(args=['tr', '-dc', 'A-Za-z0-9'])), right=Program(args=['head', '-c', '32']))")
        self.assertEqual(repr(parse(r"grep -v '^#' /etc/somefile.conf | grep .")), r"Operator(operator='|', left=Program(args=['grep', '-v', '^#', '/etc/somefile.conf']), right=Program(args=['grep', '.']))")
        self.assertEqual(repr(parse(r"date +%Y-%m-%d-%H.%M.%S")), r"Program(args=['date', '+%Y-%m-%d-%H.%M.%S'])")
        self.assertEqual(repr(parse(r"dd bs=256 count=1 if=/dev/urandom status=none | grep -ao [[:alnum:]] | head -n 32 | tr -d '\n'")), r"Operator(operator='|', left=Operator(operator='|', left=Operator(operator='|', left=Program(args=['dd', 'bs=256', 'count=1', 'if=/dev/urandom', 'status=none']), right=Program(args=['grep', '-ao', '[[:alnum:]]'])), right=Program(args=['head', '-n', '32'])), right=Program(args=['tr', '-d', '\\n']))")
        self.assertEqual(repr(parse(r"true && echo success || echo failure")), r"Operator(operator='||', left=Operator(operator='&&', left=Program(args=['true']), right=Program(args=['echo', 'success'])), right=Program(args=['echo', 'failure']))")
        self.assertEqual(repr(parse(r"curl -s http://whatthecommit.com/ | grep -o '<p>.*' | sed s,\</\\?p\>,,g")), r"Operator(operator='|', left=Operator(operator='|', left=Program(args=['curl', '-s', 'http://whatthecommit.com/']), right=Program(args=['grep', '-o', '<p>.*'])), right=Program(args=['sed', 's,</\\?p>,,g']))")

        self.assertEqual(repr(parse("()")), "Node()")
        self.assertEqual(repr(parse("(())")), "Node()")
        self.assertEqual(repr(parse("a")), "Program(args=['a'])")
        self.assertEqual(repr(parse("(a)")), "Program(args=['a'])")
        self.assertEqual(repr(parse("((a))")), "Program(args=['a'])")
        self.assertEqual(repr(parse("(a; b) || c && d")), "Operator(operator='&&', left=Operator(operator='||', left=Operator(operator=';', left=Program(args=['a']), right=Program(args=['b'])), right=Program(args=['c'])), right=Program(args=['d']))")
        self.assertEqual(repr(parse("a; (b || c) && d")), "Operator(operator=';', left=Program(args=['a']), right=Operator(operator='&&', left=Operator(operator='||', left=Program(args=['b']), right=Program(args=['c'])), right=Program(args=['d'])))")
        self.assertEqual(repr(parse("a; b || (c && d)")), "Operator(operator=';', left=Program(args=['a']), right=Operator(operator='||', left=Program(args=['b']), right=Operator(operator='&&', left=Program(args=['c']), right=Program(args=['d']))))")
        self.assertEqual(repr(parse("(a; b || c) && d")), "Operator(operator='&&', left=Operator(operator=';', left=Program(args=['a']), right=Operator(operator='||', left=Program(args=['b']), right=Program(args=['c']))), right=Program(args=['d']))")
        self.assertEqual(repr(parse("a; (b || c && d)")), "Operator(operator=';', left=Program(args=['a']), right=Operator(operator='&&', left=Operator(operator='||', left=Program(args=['b']), right=Program(args=['c'])), right=Program(args=['d'])))")
        self.assertEqual(repr(parse("((a; b) || c) && d")), "Operator(operator='&&', left=Operator(operator='||', left=Operator(operator=';', left=Program(args=['a']), right=Program(args=['b'])), right=Program(args=['c'])), right=Program(args=['d']))")
        self.assertEqual(repr(parse("(a; (b || c)) && d")), "Operator(operator='&&', left=Operator(operator=';', left=Program(args=['a']), right=Operator(operator='||', left=Program(args=['b']), right=Program(args=['c']))), right=Program(args=['d']))")
        self.assertEqual(repr(parse("a; ((b || c) && d)")), "Operator(operator=';', left=Program(args=['a']), right=Operator(operator='&&', left=Operator(operator='||', left=Program(args=['b']), right=Program(args=['c'])), right=Program(args=['d'])))")
        self.assertEqual(repr(parse("a; (b || (c && d))")), "Operator(operator=';', left=Program(args=['a']), right=Operator(operator='||', left=Program(args=['b']), right=Operator(operator='&&', left=Program(args=['c']), right=Program(args=['d']))))")
        self.assertEqual(repr(parse("(a; b) || c && (d | e)")), "Operator(operator='&&', left=Operator(operator='||', left=Operator(operator=';', left=Program(args=['a']), right=Program(args=['b'])), right=Program(args=['c'])), right=Operator(operator='|', left=Program(args=['d']), right=Program(args=['e'])))")
        self.assertEqual(repr(parse("a; (b || c && d) | e")), "Operator(operator=';', left=Program(args=['a']), right=Operator(operator='|', left=Operator(operator='&&', left=Operator(operator='||', left=Program(args=['b']), right=Program(args=['c'])), right=Program(args=['d'])), right=Program(args=['e'])))")
        # fmt: on
