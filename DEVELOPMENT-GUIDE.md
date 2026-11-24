# LearnMon development guidebook

Keep this guide current when playtests, implementation, or releases establish a rule that should carry forward. Record the durable lesson here and link to issues or PRs for details.

## Game and learning

- Apply the player-experience questions in [AGENTS.md](AGENTS.md) when shaping and reviewing a change. During playtesting, follow the choice into the next turn to see how the player can use what they discovered or earned.
- Preserve the Tuxemon world, exploration, party progression, and capture loop. LearnMon’s encounters turn debugging techniques into moves. Each required case must be solvable with the moves the player has earned.
- Keep the case objective, evidence, and next choice in the battle. Show a full stack trace or request and response together. Explain an outcome through the evidence that changed when the player acted.
- Give each move a recognizable effect. A scan uncovers a log, a request travels and returns, and a patch changes the line it acts on. Keep effects short enough to support turn rhythm.
- Keep recoverable mistakes meaningful. For example, a premature retry can create a simulated duplicate order, and a wrong diagnosis still leaves the original clues available.
- Keep a captured problem’s name visible from the wild encounter through the Backpack, party, and save/load. When a case uses a contextual technique name, show how it relates to the technique the companion learned.

## Review and release

- Run automated rules tests and a real, normal-speed keyboard playthrough. Check readability and focus at laptop resolutions, including the longest evidence, wrong-answer recovery, party switching, and capture.
- Check the actual player experience in addition to state transitions and event logs. The v0.2 native combat experiment validated the animations but broke the reading flow into too many prompts. Use the earlier side-by-side battle layout as the reference.
- Release a self-contained x86-64 AppImage via the manual GitHub Actions workflow. Verify the public download and checksum, and test the no-FUSE launch path. Record any hardware or OS coverage gaps in the release notes.
