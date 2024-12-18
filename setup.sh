#!/bin/bash

# Create virtual environment
python3 -m venv venv

# Activate virtual environment (macOS/Linux path)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install the local package in development mode
pip install -e app/match-invoices/
