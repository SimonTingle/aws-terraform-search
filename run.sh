#!/bin/bash

# --- CONFIGURATION ---
VENV_NAME="venv"
REQUIREMENTS="streamlit langchain langchain-community langchain-huggingface langchain-text-splitters chromadb>=0.5.0 sentence-transformers gitpython pydantic-settings"
PYTHON_CMD="/opt/homebrew/bin/python3.11" # Your stable python version

# Exit immediately if a command exits with a non-zero status
set -e

# Function to handle cleanup on exit (Ctrl+C)
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    # Deactivate isn't strictly necessary in a script execution context (it dies with the shell),
    # but strictly speaking, we announce we are done.
    echo "✅ Virtual environment closed."
    exit 0
}

# Trap SIGINT (Ctrl+C) to run the cleanup function
trap cleanup SIGINT

echo "=================================================="
echo "   AWS & Terraform Docs - Automated Launcher"
echo "=================================================="

# 1. Create/Check Virtual Environment
if [ ! -d "$VENV_NAME" ]; then
    echo "📦 Creating virtual environment ($VENV_NAME)..."
    ## OLD CODE: /opt/homebrew/bin/python3.11 -m venv $VENV_NAME
    $PYTHON_CMD -m venv $VENV_NAME
else
    echo "✅ Virtual environment found."
fi

# 2. Activate Virtual Environment
echo "🔌 Activating virtual environment..."
source $VENV_NAME/bin/activate

# 3. Install/Check Dependencies
# We check if a specific package is installed to avoid running pip every time
if ! pip show streamlit > /dev/null 2>&1; then
    echo "⬇️  Installing dependencies... (This may take a minute)"
    pip install $REQUIREMENTS
else
    echo "✅ Dependencies already installed."
fi

# 4. Run Ingestion (Database Build)
# I added a check here: If the database exists, we ask if you want to update.
# If you want it to run BLINDLY every time, remove the "read" logic.

## OLD CODE BLOCK START ------------------------------------------
# if [ -d "local_db" ]; then
#     echo "--------------------------------------------------"
#     read -p "🔄 Database exists. Do you want to re-ingest (update) docs? (y/n) " -n 1 -r
#     echo ""
#     if [[ $REPLY =~ ^[Yy]$ ]]; then
#         echo "🚀 Running ingest.py..."
#         python ingest.py
#     else
#         echo "⏩ Skipping ingestion."
#     fi
# else
#     # First run implies we must ingest
#     echo "🚀 Database not found. Running ingest.py..."
#     python ingest.py
# fi
## OLD CODE BLOCK END --------------------------------------------

## NEW LOGIC: Only ingest if missing. Updates happen inside the App UI now.
if [ ! -d "local_db" ]; then
    echo "🚀 Database missing. Initializing first-time setup..."
    python ingest.py
else
    echo "✅ Database found. Skipping CLI ingestion (use UI to update)."
fi

# 5. Run the UI Application
echo "--------------------------------------------------"
echo "🖥️  Starting Streamlit UI..."
streamlit run app.py

# Script ends here when Streamlit is closed
cleanup