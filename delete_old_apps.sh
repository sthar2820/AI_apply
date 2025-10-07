#!/bin/bash

# Delete old application directories (before August 7, 2025)
# This script will immediately delete directories without confirmation!

echo "=== Deleting Old Application Directories ==="
echo "Target: Directories older than 2 months (before Aug 7, 2025)"
echo ""

cd applications || { echo "Error: Cannot access applications directory"; exit 1; }

# Calculate which directories are older than 2 months (before August 7, 2025)
THRESHOLD_DATE="2025-08-07"
DELETED_COUNT=0
TOTAL_SIZE_FREED=0

echo "Scanning for directories modified before $THRESHOLD_DATE..."
echo ""

# First pass: Identify directories to delete (preview mode)
DIRS_TO_DELETE=()
DIRS_TO_KEEP=()
PREVIEW_SIZE=0

for dir in */; do
    if [ -d "$dir" ]; then
        # Get modification date of directory
        MOD_DATE=$(stat -f "%Sm" -t "%Y-%m-%d" "$dir" 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            # Check if directory is older than threshold
            if [[ "$MOD_DATE" < "$THRESHOLD_DATE" ]]; then
                SIZE=$(du -sk "$dir" 2>/dev/null | cut -f1 || echo "0")
                DIRS_TO_DELETE+=("$dir:$MOD_DATE:$SIZE")
                PREVIEW_SIZE=$((PREVIEW_SIZE + SIZE))
            else
                DIRS_TO_KEEP+=("$dir:$MOD_DATE")
            fi
        else
            echo "Warning: Could not get modification date for $dir"
        fi
    fi
done

# Show preview of what will be deleted
echo "=== PREVIEW: Directories to be DELETED ==="
if [ ${#DIRS_TO_DELETE[@]} -eq 0 ]; then
    echo "No directories found that need deletion."
    echo ""
    echo "=== All directories are newer than $THRESHOLD_DATE ==="
    for item in "${DIRS_TO_KEEP[@]}"; do
        IFS=':' read -r dir mod_date <<< "$item"
        echo "  $dir (modified: $mod_date)"
    done
    exit 0
fi

for item in "${DIRS_TO_DELETE[@]}"; do
    IFS=':' read -r dir mod_date size <<< "$item"
    echo "  ❌ $dir (modified: $mod_date, size: ${size}KB)"
done

echo ""
echo "=== PREVIEW: Directories to be KEPT ==="
for item in "${DIRS_TO_KEEP[@]}"; do
    IFS=':' read -r dir mod_date <<< "$item"
    echo "  ✅ $dir (modified: $mod_date)"
done

echo ""
echo "=== SUMMARY ==="
echo "Directories to delete: ${#DIRS_TO_DELETE[@]}"
echo "Directories to keep: ${#DIRS_TO_KEEP[@]}"
echo "Total space to free: ${PREVIEW_SIZE}KB"
echo ""

# Confirmation prompt
read -p "Do you want to proceed with deletion? (type 'DELETE' to confirm): " confirmation

if [ "$confirmation" != "DELETE" ]; then
    echo "Deletion cancelled. No directories were modified."
    exit 0
fi

echo ""
echo "=== Starting deletion... ==="

# Second pass: Actually delete the directories
for item in "${DIRS_TO_DELETE[@]}"; do
    IFS=':' read -r dir mod_date size <<< "$item"
    if [ -d "$dir" ]; then
        echo "Deleting: $dir (modified: $mod_date, size: ${size}KB)"
        rm -rf "$dir"
        DELETED_COUNT=$((DELETED_COUNT + 1))
        TOTAL_SIZE_FREED=$((TOTAL_SIZE_FREED + size))
    else
        echo "Warning: $dir no longer exists"
    fi
done

cd ..

echo ""
echo "=== CLEANUP COMPLETE ==="
echo "Directories deleted: $DELETED_COUNT"
echo "Space freed: ${TOTAL_SIZE_FREED}KB"
echo "Remaining applications: $(ls -1 applications | wc -l | tr -d ' ')"
echo "Current applications directory size: $(du -sh applications | cut -f1)"