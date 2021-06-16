## GitHub workflows
Plio development ensures the best coding standards are followed and proper checks are measured when a code change gets published.

Here's a summary of all the GitHub workflows (or GitHub actions) this repository contains:

  - [Pre-commit](#pre-commit)
  - [Test cases](#test-cases)


### Pre-commit
The `pre-commit` job inside the [CI GitHub Action](../.github/workflows/ci.yml) checks for basic linting and coding errors on anything that got merged or is proposed to merge (through Pull Request) into the `master` branch.

For more details about pre-commit action, visit [pre-commit/action](https://github.com/pre-commit/action)

For more details on GitHub actions, visit [GitHub Actions docs](https://docs.github.com/en/actions)


### Test cases
The `test-cases` job inside the [CI GitHub Action](../.github/workflows/ci.yml) runs the test cases within the codebase. After the test cases have been executed, it then also uploads the coverage report to [CodeCov](https://codecov.io/gh/avantifellows/plio-backend).
