from click import Context
from typer.core import TyperCommand


class TerminalRunCommand(TyperCommand):
    def parse_args(self, ctx: Context, args: list[str]) -> list[str]:
        normalized_args: list[str] = []
        for index, argument in enumerate(args):
            normalized_args.append(argument)
            if argument == "--":
                normalized_args.extend(args[index + 1:])
                break
            if argument in {"-l", "--choose-layouts", "-t", "--choose-tabs"} and (
                index + 1 == len(args)
                or (args[index + 1].startswith("-") and len(args[index + 1]) > 1)
            ):
                normalized_args.append("")
        return super().parse_args(ctx, normalized_args)
