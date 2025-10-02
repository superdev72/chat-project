#!/bin/bash

# Code Quality Script for Chat Project
echo "🔍 Running code quality checks..."

# Create scripts directory if it doesn't exist
mkdir -p scripts

# Set exit on error
set -e

# Run Black (code formatting)
echo "📝 Running Black formatter..."
black --check --diff . --exclude="test_venv|venv|.venv"

# Run isort (import sorting)
echo "📦 Running isort (import sorting)..."
isort --check-only --diff . --skip-glob="test_venv/*" --skip-glob="venv/*" --skip-glob=".venv/*" --skip-glob="*/migrations/*"

# Run flake8 (linting)
echo "🔍 Running flake8 (linting)..."
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=test_venv,venv,.venv
flake8 . --count --exit-zero --max-complexity=10 --statistics --exclude=test_venv,venv,.venv

# Run djlint (Django template linting)
echo "🎨 Running djlint (template linting)..."
djlint --check . --exclude="test_venv/*" --exclude="venv/*" --exclude=".venv/*"

echo "✅ Code quality checks completed!"
