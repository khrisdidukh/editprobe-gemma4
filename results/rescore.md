# Rescoring edit_file attempts with anchor repair

Replay of logged edits. `base` = plain replacement (what was scored). `repair` = if the plain result does not compile, expand the replaced span to the first/last lines of new_string when found uniquely within 80 lines; then run tests.

| model | protocol | N | base resolved | syntax errors | repair attempted | repaired compiles | repaired resolved | resolved with repair |
|---|---|---|---|---|---|---|---|---|
| e2b | edit_file | 19 | 4 | 3 | 3 | 3 | 1 | **5** |
