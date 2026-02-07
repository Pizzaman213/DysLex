#!/bin/bash

# Progress Dashboard Implementation Verification Script

echo "🔍 DysLex AI - Progress Dashboard Verification"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
PASS=0
FAIL=0

# Helper function
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} $2 (missing: $1)"
        ((FAIL++))
    fi
}

echo "1. Backend Files"
echo "----------------"
check_file "backend/app/db/repositories/progress_repo.py" "Progress repository"
check_file "backend/tests/test_progress_repo.py" "Repository tests"
echo ""

echo "2. Backend Models & Routes"
echo "-------------------------"
if grep -q "ErrorFrequencyWeek" backend/app/models/progress.py; then
    echo -e "${GREEN}✓${NC} New Pydantic models added"
    ((PASS++))
else
    echo -e "${RED}✗${NC} New Pydantic models missing"
    ((FAIL++))
fi

if grep -q "get_dashboard" backend/app/api/routes/progress.py; then
    echo -e "${GREEN}✓${NC} Dashboard endpoint added"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Dashboard endpoint missing"
    ((FAIL++))
fi
echo ""

echo "3. Frontend Types & API"
echo "----------------------"
check_file "frontend/src/types/progress.ts" "TypeScript types"
check_file "frontend/src/hooks/useProgressDashboard.ts" "Custom hook"

if grep -q "getProgressDashboard" frontend/src/services/api.ts; then
    echo -e "${GREEN}✓${NC} API method added"
    ((PASS++))
else
    echo -e "${RED}✗${NC} API method missing"
    ((FAIL++))
fi
echo ""

echo "4. Frontend Components"
echo "---------------------"
check_file "frontend/src/components/Panels/WritingStreaksStats.tsx" "WritingStreaksStats component"
check_file "frontend/src/components/Panels/WordsMastered.tsx" "WordsMastered component"
check_file "frontend/src/components/Panels/ImprovementTrends.tsx" "ImprovementTrends component"
check_file "frontend/src/components/Panels/ErrorFrequencyCharts.tsx" "ErrorFrequencyCharts component"
echo ""

echo "5. Styles"
echo "--------"
if grep -q "writing-stats-grid" frontend/src/styles/global.css; then
    echo -e "${GREEN}✓${NC} Dashboard styles added"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Dashboard styles missing"
    ((FAIL++))
fi
echo ""

echo "6. Dependencies"
echo "--------------"
if grep -q "recharts" frontend/package.json; then
    echo -e "${GREEN}✓${NC} Recharts installed"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Recharts not installed"
    ((FAIL++))
fi

if grep -q "react-sparklines" frontend/package.json; then
    echo -e "${GREEN}✓${NC} React-sparklines installed"
    ((PASS++))
else
    echo -e "${RED}✗${NC} React-sparklines not installed"
    ((FAIL++))
fi
echo ""

echo "7. TypeScript Compilation"
echo "------------------------"
cd frontend
if npm run type-check > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} TypeScript compiles successfully"
    ((PASS++))
else
    echo -e "${RED}✗${NC} TypeScript compilation errors"
    ((FAIL++))
fi
cd ..
echo ""

echo "8. Backend Imports"
echo "-----------------"
cd backend
if python3 -c "from app.db.repositories import progress_repo" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Backend imports successfully"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Backend import errors"
    ((FAIL++))
fi
cd ..
echo ""

echo "=============================================="
echo "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Progress Dashboard is ready.${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some checks failed. Review the output above.${NC}"
    exit 1
fi
