# Code Quality Configuration

This document describes the code quality tools and configurations used in this project.

## Tools

### Python Code Quality

1. **Black** - Code formatter

   - Configuration: `pyproject.toml`
   - Line length: 100 characters
   - Target Python version: 3.11

2. **isort** - Import sorter

   - Configuration: `pyproject.toml`
   - Profile: black
   - Line length: 100 characters
   - Custom section ordering: FUTURE, STDLIB, THIRDPARTY, DJANGO, FIRSTPARTY, LOCALFOLDER

3. **flake8** - Linter
   - Configuration: `.flake8`
   - Max line length: 100 characters
   - Max complexity: 10
   - Ignored errors: E203, W503, E501

### Template Quality

4. **djlint** - Django template linter and formatter
   - Configuration: `.djlintrc`
   - Profile: django
   - Indent: 2 spaces
   - Max line length: 100 characters

## Usage

### Check Code Quality

Run the lint script to check for code quality issues:

```bash
./scripts/lint.sh
```

This will run all code quality checks without making any changes.

### Auto-fix Code Quality Issues

Run the format script to automatically fix code quality issues:

```bash
./scripts/format.sh
```

This will:

- Format Python code with Black
- Sort imports with isort
- Format Django templates with djlint

After running the format script, run the lint script again to verify all issues are fixed.

### Individual Tool Usage

You can also run each tool individually:

```bash
# Black - format Python code
black .
black --check --diff .  # Check only, don't modify

# isort - sort imports
isort .
isort --check-only --diff .  # Check only, don't modify

# flake8 - lint Python code
flake8 .

# djlint - lint and format Django templates
djlint --check .  # Check only
djlint --reformat .  # Format templates
```

## Configuration Files

### pyproject.toml

Contains configuration for:

- Black (code formatter)
- isort (import sorter)
- djlint (template linter)

### .flake8

Contains configuration for flake8 linter.

### .djlintrc

Contains additional configuration for djlint template linter.

## Continuous Integration

The GitHub Actions CI pipeline (`./github/workflows/ci.yml`) runs all code quality checks on every push and pull request. Make sure to run `./scripts/lint.sh` locally before pushing to catch issues early.

## Pre-commit Hook (Optional)

You can set up a pre-commit hook to automatically check code quality before committing:

```bash
# Create .git/hooks/pre-commit file
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
./scripts/lint.sh
EOF

chmod +x .git/hooks/pre-commit
```

## Configuration Changes

All tools are configured with a consistent line length of 100 characters for Python and HTML files. This provides a good balance between readability and code density.

### Black Configuration

- Line length: 100
- Excludes: migrations, venv, build directories

### isort Configuration

- Line length: 100
- Compatible with Black
- Custom Django section

### flake8 Configuration

- Max line length: 100
- Max complexity: 10
- Ignores Black-incompatible rules (E203, W503)

### djlint Configuration

- Max line length: 100
- Django profile
- 2-space indentation
