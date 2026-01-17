#!/bin/bash

# 1. Create standard directories if they don't exist
echo "📂 Creating Directory Structure..."
mkdir -p Orchestrator/app
mkdir -p A5-Planner/app
mkdir -p UI
mkdir -p A1-DietRules/app
mkdir -p A2-Gaps/app
mkdir -p A3-Targets/app
mkdir -p A4-Conflicts/app

# 2. Move and Rename Critical Files
echo "🚚 Moving Files..."

# Move Orchestrator logic
if [ -f "orchestrator-main.py" ]; then
    mv orchestrator-main.py Orchestrator/app/main.py
    echo "✅ Moved orchestrator-main.py -> Orchestrator/app/main.py"
fi

# Move A5 logic (Assuming the 'main.py' you uploaded is A5)
if [ -f "main.py" ]; then
    cp main.py A5-Planner/app/main.py
    echo "✅ Moved main.py -> A5-Planner/app/main.py"
fi

# Move UI
if [ -f "app.py" ]; then
    mv app.py UI/app.py
    echo "✅ Moved app.py -> UI/app.py"
fi

# Move Configs
if [ -f "requirements.txt" ]; then
    cp requirements.txt Orchestrator/
    cp requirements.txt A5-Planner/
    cp requirements.txt UI/
    echo "✅ Distributed requirements.txt"
fi

# 3. Create dummy files for other agents if missing (to prevent Docker build errors)
touch A1-DietRules/app/main.py
touch A2-Gaps/app/main.py
touch A3-Targets/app/main.py
touch A4-Conflicts/app/main.py

echo "🎉 Cleanup Complete! Your folder structure is now standard."