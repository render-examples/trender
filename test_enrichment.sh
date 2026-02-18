#!/bin/bash
# Test script for Render enrichment feature

set -e  # Exit on any error

echo "=========================================="
echo "  Testing Render Enrichment Feature"
echo "=========================================="
echo ""

# Validate DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL environment variable not set"
    exit 1
fi

# Step 1: Run the workflow
echo "Step 1: Running workflow..."
echo ""
python bin/local_dev.py

echo ""
echo "=========================================="
echo "  Step 2: Verifying Enrichment Results"
echo "=========================================="
echo ""

# Count total enriched repos
echo "→ Total enriched repos:"
psql "$DATABASE_URL" -t -c "
    SELECT COUNT(*) FROM stg_render_enrichment;
"

echo ""
echo "→ Category breakdown (all should be 'community'):"
psql "$DATABASE_URL" -c "
    SELECT render_category, COUNT(*) as count
    FROM stg_render_enrichment
    GROUP BY render_category;
"

echo ""
echo "→ Sample enriched repos:"
psql "$DATABASE_URL" -c "
    SELECT repo_full_name, render_category, loaded_at
    FROM stg_render_enrichment
    ORDER BY repo_full_name
    LIMIT 10;
"

echo ""
echo "=========================================="
echo "  Step 3: Medallion Architecture Check"
echo "=========================================="
echo ""

echo "→ Verify all Render repos have enrichment data:"
psql "$DATABASE_URL" -c "
    SELECT
        COUNT(*) FILTER (WHERE e.repo_full_name IS NOT NULL) as enriched,
        COUNT(*) FILTER (WHERE e.repo_full_name IS NULL) as missing,
        COUNT(*) as total
    FROM stg_repos_validated s
    LEFT JOIN stg_render_enrichment e ON s.repo_full_name = e.repo_full_name
    WHERE s.language = 'render';
"

echo ""
echo "→ Top 10 enriched repos by stars:"
psql "$DATABASE_URL" -c "
    SELECT s.repo_full_name, s.stars, e.render_category
    FROM stg_repos_validated s
    JOIN stg_render_enrichment e ON s.repo_full_name = e.repo_full_name
    WHERE s.language = 'render'
    ORDER BY s.stars DESC
    LIMIT 10;
"

echo ""
echo "=========================================="
echo "  ✓ Test Complete"
echo "=========================================="
echo ""
echo "Expected: ~25-31 repos, all 'community', no missing enrichments"
