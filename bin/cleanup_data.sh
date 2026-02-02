#!/bin/bash
# Manual Data Retention Cleanup Script
# Purpose: Standalone script for manual cleanup of old data
# Usage: ./bin/cleanup_data.sh [--dry-run]
#
# This script mirrors the automated cleanup logic that runs after each workflow execution.
# It's useful for:
# - One-off maintenance
# - Testing retention policies
# - Recovering from cleanup failures
# - Manual storage management

set -e  # Exit on error

# ====================================
# Configuration
# ====================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SQL_SCRIPT="$PROJECT_ROOT/database/data_retention_cleanup.sql"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ====================================
# Functions
# ====================================
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# ====================================
# Check Prerequisites
# ====================================
check_prerequisites() {
    print_header "Data Retention Cleanup"
    
    # Check if DATABASE_URL is set
    if [ -z "$DATABASE_URL" ]; then
        # Try to load from .env file
        if [ -f "$PROJECT_ROOT/.env" ]; then
            print_info "Loading DATABASE_URL from .env file..."
            # Safely load DATABASE_URL from .env (avoid shell injection)
            set -a
            # shellcheck source=/dev/null
            source <(grep -E '^DATABASE_URL=' "$PROJECT_ROOT/.env")
            set +a
        fi
        
        if [ -z "$DATABASE_URL" ]; then
            print_error "DATABASE_URL environment variable not set"
            echo ""
            echo "Please set DATABASE_URL or create a .env file with:"
            echo "  DATABASE_URL=postgresql://..."
            echo ""
            exit 1
        fi
    fi
    
    print_success "DATABASE_URL is set"
    
    # Check if psql is available
    if ! command -v psql &> /dev/null; then
        print_error "psql command not found"
        echo ""
        echo "Please install PostgreSQL client:"
        echo "  macOS: brew install postgresql"
        echo "  Ubuntu: sudo apt-get install postgresql-client"
        echo ""
        exit 1
    fi
    
    print_success "psql is available"
    
    # Check if cleanup script exists
    if [ ! -f "$SQL_SCRIPT" ]; then
        print_error "Cleanup script not found: $SQL_SCRIPT"
        exit 1
    fi
    
    print_success "Cleanup script found: $SQL_SCRIPT"
    echo ""
}

# ====================================
# Test Database Connection
# ====================================
test_connection() {
    print_info "Testing database connection..."
    
    if psql "$DATABASE_URL" -c "SELECT 1;" &> /dev/null; then
        print_success "Database connection successful"
        echo ""
    else
        print_error "Cannot connect to database"
        echo ""
        echo "Please check your DATABASE_URL and ensure the database is accessible."
        exit 1
    fi
}

# ====================================
# Show Current Data Stats
# ====================================
show_stats() {
    print_header "Current Data Statistics"
    
    psql "$DATABASE_URL" -c "
    SELECT 
        'raw_github_repos' as table_name,
        COUNT(*) as row_count,
        TO_CHAR(MIN(fetch_timestamp), 'YYYY-MM-DD HH24:MI') as oldest_record,
        TO_CHAR(MAX(fetch_timestamp), 'YYYY-MM-DD HH24:MI') as newest_record,
        ROUND(EXTRACT(EPOCH FROM (MAX(fetch_timestamp) - MIN(fetch_timestamp))) / 86400, 1) as age_days
    FROM raw_github_repos
    UNION ALL
    SELECT 
        'raw_repo_metrics',
        COUNT(*),
        TO_CHAR(MIN(fetch_timestamp), 'YYYY-MM-DD HH24:MI'),
        TO_CHAR(MAX(fetch_timestamp), 'YYYY-MM-DD HH24:MI'),
        ROUND(EXTRACT(EPOCH FROM (MAX(fetch_timestamp) - MIN(fetch_timestamp))) / 86400, 1)
    FROM raw_repo_metrics
    UNION ALL
    SELECT 
        'stg_repos_validated',
        COUNT(*),
        TO_CHAR(MIN(loaded_at), 'YYYY-MM-DD HH24:MI'),
        TO_CHAR(MAX(loaded_at), 'YYYY-MM-DD HH24:MI'),
        ROUND(EXTRACT(EPOCH FROM (MAX(loaded_at) - MIN(loaded_at))) / 86400, 1)
    FROM stg_repos_validated
    UNION ALL
    SELECT 
        'fact_repo_snapshots',
        COUNT(*),
        TO_CHAR(MIN(snapshot_date)::timestamptz, 'YYYY-MM-DD'),
        TO_CHAR(MAX(snapshot_date)::timestamptz, 'YYYY-MM-DD'),
        (MAX(snapshot_date) - MIN(snapshot_date))::numeric
    FROM fact_repo_snapshots
    UNION ALL
    SELECT 
        'fact_render_usage',
        COUNT(*),
        TO_CHAR(MIN(snapshot_date)::timestamptz, 'YYYY-MM-DD'),
        TO_CHAR(MAX(snapshot_date)::timestamptz, 'YYYY-MM-DD'),
        (MAX(snapshot_date) - MIN(snapshot_date))::numeric
    FROM fact_render_usage
    ORDER BY table_name;
    "
    
    echo ""
}

# ====================================
# Dry Run Mode
# ====================================
dry_run() {
    print_header "DRY RUN MODE - Preview Only"
    
    print_info "This will show what would be deleted without actually deleting anything."
    echo ""
    
    # Show what would be deleted from raw layer
    print_info "Raw layer records older than 7 days:"
    psql "$DATABASE_URL" -c "
    SELECT 
        'raw_github_repos' as table_name,
        COUNT(*) as records_to_delete,
        TO_CHAR(MIN(fetch_timestamp), 'YYYY-MM-DD HH24:MI') as oldest,
        TO_CHAR(MAX(fetch_timestamp), 'YYYY-MM-DD HH24:MI') as newest
    FROM raw_github_repos
    WHERE fetch_timestamp < NOW() - INTERVAL '7 days'
    UNION ALL
    SELECT 
        'raw_repo_metrics',
        COUNT(*),
        TO_CHAR(MIN(fetch_timestamp), 'YYYY-MM-DD HH24:MI'),
        TO_CHAR(MAX(fetch_timestamp), 'YYYY-MM-DD HH24:MI')
    FROM raw_repo_metrics
    WHERE fetch_timestamp < NOW() - INTERVAL '7 days';
    "
    echo ""
    
    # Show what would be deleted from staging layer
    print_info "Staging layer records older than 7 days:"
    psql "$DATABASE_URL" -c "
    SELECT 
        'stg_repos_validated' as table_name,
        COUNT(*) as records_to_delete,
        TO_CHAR(MIN(loaded_at), 'YYYY-MM-DD HH24:MI') as oldest,
        TO_CHAR(MAX(loaded_at), 'YYYY-MM-DD HH24:MI') as newest
    FROM stg_repos_validated
    WHERE loaded_at < NOW() - INTERVAL '7 days'
    UNION ALL
    SELECT 
        'stg_render_enrichment',
        COUNT(*),
        TO_CHAR(MIN(loaded_at), 'YYYY-MM-DD HH24:MI'),
        TO_CHAR(MAX(loaded_at), 'YYYY-MM-DD HH24:MI')
    FROM stg_render_enrichment
    WHERE loaded_at < NOW() - INTERVAL '7 days';
    "
    echo ""
    
    # Show what would be deleted from analytics layer
    print_info "Analytics layer snapshots older than 30 days:"
    psql "$DATABASE_URL" -c "
    SELECT 
        'fact_repo_snapshots' as table_name,
        COUNT(*) as records_to_delete,
        TO_CHAR(MIN(snapshot_date)::timestamptz, 'YYYY-MM-DD') as oldest,
        TO_CHAR(MAX(snapshot_date)::timestamptz, 'YYYY-MM-DD') as newest
    FROM fact_repo_snapshots
    WHERE snapshot_date < CURRENT_DATE - INTERVAL '30 days'
    UNION ALL
    SELECT 
        'fact_render_usage',
        COUNT(*),
        TO_CHAR(MIN(snapshot_date)::timestamptz, 'YYYY-MM-DD'),
        TO_CHAR(MAX(snapshot_date)::timestamptz, 'YYYY-MM-DD')
    FROM fact_render_usage
    WHERE snapshot_date < CURRENT_DATE - INTERVAL '30 days';
    "
    echo ""
    
    print_success "Dry run completed - no data was deleted"
    echo ""
    print_info "To perform actual cleanup, run without --dry-run flag"
}

# ====================================
# Execute Cleanup
# ====================================
execute_cleanup() {
    print_header "Executing Data Retention Cleanup"
    
    print_warning "This will permanently delete old data according to retention policy:"
    echo "  - Raw layer: 7 days"
    echo "  - Staging layer: 7 days"
    echo "  - Analytics layer: 30 days"
    echo ""
    
    # Ask for confirmation
    read -p "Are you sure you want to proceed? (yes/no): " -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        print_warning "Cleanup cancelled by user"
        exit 0
    fi
    
    print_info "Running cleanup script..."
    echo ""
    
    # Execute cleanup
    if psql "$DATABASE_URL" -f "$SQL_SCRIPT"; then
        echo ""
        print_success "Cleanup completed successfully"
        echo ""
        
        print_info "Updated data statistics:"
        show_stats
    else
        echo ""
        print_error "Cleanup failed - see errors above"
        exit 1
    fi
}

# ====================================
# Main Script
# ====================================
main() {
    # Parse arguments
    DRY_RUN=false
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [--dry-run]"
                echo ""
                echo "Options:"
                echo "  --dry-run    Show what would be deleted without actually deleting"
                echo "  --help       Show this help message"
                echo ""
                echo "Retention Policy:"
                echo "  Raw layer:     7 days"
                echo "  Staging layer: 7 days"
                echo "  Analytics:     30 days"
                echo ""
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Run checks
    check_prerequisites
    test_connection
    show_stats
    
    # Execute or dry run
    if [ "$DRY_RUN" = true ]; then
        dry_run
    else
        execute_cleanup
    fi
}

# Run main function
main "$@"

