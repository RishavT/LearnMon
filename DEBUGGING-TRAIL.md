# Tuxemon Debugging Trail

A short single-player web debugging campaign inside LearnMon, a Tuxemon fork. It uses the original City Park layout, sprites, movement, party, and Tuxepedia. The park variant hosts three scripted wild battles on Tuxemon’s combat screen, with animated moves and captures. Each successful diagnosis guarantees the capture when you choose **Throw Tuxeball**.

## Play on Linux

1. Extract the entire folder and open it.
2. Double-click **Play Debugging Trail.sh** and choose **Run** if prompted. If your i3 file manager opens shell scripts as text, run `./"Play Debugging Trail.sh"` from a terminal in the folder. To bind it to an i3 shortcut, use the script's full path in an `exec` binding.
3. The first launch needs internet access and Python 3 with `venv` and `pip`. Python 3.12 is the tested version. A source dependency may need a C compiler. The launcher keeps its environment in your user cache and its data and log in your user data directory. Set `TUXEMON_PYTHON` to select a different Python executable.

Use **arrow keys** to move or select and **Enter** to confirm. Walk right from the starting spot into the grass. In battle, choose **Fight** to use a move, **Tuxemon** to switch party members, or **Case Notes** to reread clues. After each capture, take another step in the grass.

The starter knows **Read Log**. Caught Tuxemon add tools, and the same move can have different effects depending on the state of the bug. The campaign keeps your party together so you retain each required move. The third capture concludes the trail. Relaunch to start a fresh run.

For the first launch, allow time for setup. If the game fails to start, see `${XDG_DATA_HOME:-~/.local/share}/tuxemon-debugging-trail/launcher.log`.

## Source and credits

This prototype is built on the [LearnMon fork of Tuxemon](https://github.com/RishavT/LearnMon). See [LICENSE](LICENSE) and [ATTRIBUTIONS.md](ATTRIBUTIONS.md) for upstream licensing and asset attribution. The web apps, network requests, and logs in the encounters are simulated.
