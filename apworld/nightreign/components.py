"""
Nightreign's game-side client is the me3-loaded Rust DLL (see ../../mod/). It speaks the Archipelago
protocol directly (archipelago_rs), so there is no Python client to launch. We still register a
Launcher component that opens the setup guide / the me3 profile folder for convenience.
"""
from worlds.LauncherComponents import Component, Type, components


def open_setup(*args: str) -> None:
    import webbrowser
    webbrowser.open("https://archipelago.gg/tutorial/Elden%20Ring%20Nightreign/setup/en")


components.append(Component("Nightreign Setup Guide", func=open_setup, game_name="Elden Ring Nightreign",
                            component_type=Type.MISC))
