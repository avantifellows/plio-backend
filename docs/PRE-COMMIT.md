## Pre-commit
Plio utilizes the power of pre-commit to identify simple programming issues at the time of code check-in. This helps the reviewer to focus more on architectural and conceptual issues and reduce the overall time to market.

The pre-commit configurations are stored in [.pre-commit-config.yaml](../.pre-commit-config.yaml) file.

To know about the syntax, visit the [official documentation site](https://pre-commit.com/).

The pre-commit hook in this repository uses various plugins to run different kinds of checks.

1. [Pre-commit-hooks](https://github.com/pre-commit/pre-commit-hooks): Checks and fixes basic linting issues. All available hooks for pre-commit can be found [here](https://github.com/pre-commit/pre-commit-hooks#hooks-available).

2. [PSF Black](https://github.com/psf/black): Checks for code formatting issues within Python files (.py) and fixes if errors found, like indentation, extra lines and spaces, invalid syntax, etc.

### Installation
1. Install pre-commit
    Use `pip` to install pre-commit
    ```sh
    pip install pre-commit
    ```

    Or using homebrew on macOS
    ```sh
    brew install pre-commit
    ```

    For more installation alternatives, check out [Pre-commit official documentation](https://pre-commit.com/#install).
2. Verify pre-commit installation
    ```sh
    pre-commit --version
    ```

### Usage
1. Run command
    ```sh
    pre-commit .
    ```
