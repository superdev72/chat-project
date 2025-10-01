#!/bin/bash

# Code Quality Script for Chat Project
echo "🔍 Running code quality checks..."

# Create scripts directory if it doesn't exist
mkdir -p scripts

# Run Black (code formatting)
echo "📝 Running Black formatter..."
black --check --diff .

# Run isort (import sorting)
echo "📦 Running isort (import sorting)..."
isort --check-only --diff .

# Run flake8 (linting)
echo "🔍 Running flake8 (linting)..."
flake8 .

# Run djlint (Django template linting)
echo "🎨 Running djlint (template linting)..."
djlint --check .

echo "✅ Code quality checks completed!"
