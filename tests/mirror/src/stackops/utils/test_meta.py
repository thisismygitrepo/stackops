import pytest

from stackops.utils.meta import lambda_to_python_script


def first_target(x: int) -> None:
    print("first", x)


def second_target(y: int) -> None:
    print("second", y)


class Holder:
    @staticmethod
    def chained_target(z: int) -> None:
        print("chained", z)


def test_lambda_sharing_its_line_with_call_arguments_parses() -> None:
    script = lambda_to_python_script(lambda: first_target(x=1), in_global=True, import_module=False)
    assert "x: 'int' = 1" in script
    assert 'print("first", x)' in script


def test_lambdas_on_one_line_resolve_to_their_own_bodies() -> None:
    first, second = (lambda: first_target(x=2)), (lambda: second_target(y=3))
    assert "x: 'int' = 2" in lambda_to_python_script(first, in_global=True, import_module=False)
    assert "y: 'int' = 3" in lambda_to_python_script(second, in_global=True, import_module=False)


def test_lambda_body_spanning_lines_resolves() -> None:
    script = lambda_to_python_script(
        lambda: Holder
        .chained_target(z=4),
        in_global=True,
        import_module=False,
    )
    assert "z: 'int' = 4" in script


def test_named_function_is_rejected() -> None:
    def named() -> None:
        first_target(x=5)

    with pytest.raises(ValueError, match="Could not find a lambda"):
        lambda_to_python_script(named, in_global=True, import_module=False)
