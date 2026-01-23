#!/bin/bash

# Push D2D to GitHub repository
# Run this after creating the repository at https://github.com/chrisgermon/d2d

REPO_URL="https://github.com/chrisgermon/d2d.git"

echo "====================================="
echo "Pushing D2D to GitHub"
echo "====================================="
echo ""

# Check if we're in the right directory
if [ ! -d ".git" ]; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Check if origin already exists
if git remote get-url origin > /dev/null 2>&1; then
    echo "Remote 'origin' already exists. Removing it..."
    git remote remove origin
fi

# Add the remote
echo "Adding remote: $REPO_URL"
git remote add origin "$REPO_URL"

# Show what will be pushed
echo ""
echo "Repository status:"
git log --oneline | head -5
echo ""
echo "Files to be pushed:"
git ls-files | wc -l
echo "files"
echo ""

# Push to GitHub
echo "Pushing to GitHub..."
git push -u origin master

if [ $? -eq 0 ]; then
    echo ""
    echo "====================================="
    echo "✅ Successfully pushed to GitHub!"
    echo "====================================="
    echo ""
    echo "Repository URL: https://github.com/chrisgermon/d2d"
    echo ""
else
    echo ""
    echo "====================================="
    echo "❌ Push failed"
    echo "====================================="
    echo ""
    echo "Make sure you have:"
    echo "1. Created the repository: https://github.com/new"
    echo "2. Set up authentication (SSH key or Personal Access Token)"
    echo ""
fi
