# pytest-litter

Pytest plugin that, when installed, will fail test cases which
create or delete files. Tests should not modify the file tree,
because it can be a cause of test pollution as well as accidental
committing of files to the repo.

To use it, simply run
```
pip install pytest-litter
```
The only dependency is `pytest` itself.