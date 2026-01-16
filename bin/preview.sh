#!/bin/bash

# Navigate to the dashboard directory from project root
cd "$(dirname "$0")/../dashboard" || exit 1

# Run the Next.js development server
npm run dev

