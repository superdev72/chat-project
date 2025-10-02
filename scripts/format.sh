#!/bin/bash

# Code Formatting Script for Chat Project
echo "🔧 Running code formatters..."

# Set exit on error (but continue through formatters)
set +e

# Run Black (code formatting)
echo "📝 Running Black formatter..."
black .

# Run isort (import sorting)
echo "📦 Running isort (import sorting)..."
isort .

# Run djlint (Django template formatting)
echo "🎨 Running djlint (template formatting)..."
djlint --reformat .

echo "✅ Code formatting completed!"
echo "💡 Run ./scripts/lint.sh to check if there are any remaining issues."

