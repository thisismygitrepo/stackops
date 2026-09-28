from typer.core import TyperGroup


def ordered_group(command_order: tuple[str, ...]) -> type[TyperGroup]:
    positions = {name: index for index, name in enumerate(command_order)}

    class OrderedGroup(TyperGroup):
        def list_commands(self, ctx: object) -> list[str]:
            command_names = list(self.commands)
            return sorted(command_names, key=lambda name: positions.get(name, len(positions)))

    return OrderedGroup
