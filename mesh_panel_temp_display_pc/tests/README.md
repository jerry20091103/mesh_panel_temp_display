# Tests

This folder contains lightweight regression checks for the PC app.

## Source selection regression

The file `test_source_selection.py` guards the behavior where the selected temperature sources should remain highlighted when switching between the General and Display Tuning tabs.

This covers the bug where the saved source IDs were still correct, but the listbox UI lost its active selection after a tab change.
