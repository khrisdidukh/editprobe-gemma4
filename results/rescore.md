# Rescoring edit_file attempts with anchor repair

Replay of logged edits. `base` = plain replacement (what was scored). `repair` = if the plain result does not compile, expand the replaced span to the first/last lines of new_string when found uniquely within 80 lines; then run tests.

| model | protocol | N | base resolved | syntax errors | repair attempted | repaired compiles | repaired resolved | resolved with repair |
|---|---|---|---|---|---|---|---|---|
| e2b | edit_file | 35 | 9 | 5 | 4 | 3 | 1 | **10** |
| e2b | edit_file+hint | 35 | 34 | 1 | 0 | 0 | 0 | **34** |
| e2b | edit_file_v | 35 | 10 | 3 | 1 | 1 | 0 | **10** |
| e2b | edit_file_v+hint | 35 | 33 | 0 | 0 | 0 | 0 | **33** |
