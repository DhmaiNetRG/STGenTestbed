#!/bin/bash
# tools/run_all_scenarios.sh
# Execute all scenarios across all available protocols

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"  # <--- ADD THIS LINE

RESULTS_DIR="$SCRIPT_DIR/results"
SCENARIOS_DIR="$SCRIPT_DIR/configs/scenarios"
TIMESTAMP=$(date +%s)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}STGen Batch Test Runner${NC}"
echo "Timestamp: $TIMESTAMP"
echo "Results directory: $RESULTS_DIR"
echo ""

# Get available protocols
PROTOCOLS=$(PYTHONPATH=$SCRIPT_DIR python3 -c "from stgen.utils import list_available_protocols; print(','.join(list_available_protocols()))")
if [ -z "$PROTOCOLS" ]; then
    echo -e "${RED}Error: No protocols found${NC}"
    exit 1
fi

echo "Available protocols: $PROTOCOLS"
echo ""

# Get available scenarios
SCENARIOS=$(ls "$SCENARIOS_DIR"/*.json 2>/dev/null | xargs -n1 basename -s .json)

if [ -z "$SCENARIOS" ]; then
    echo -e "${RED}Error: No scenarios found in $SCENARIOS_DIR${NC}"
    exit 1
fi

echo "Available scenarios:"
for scenario in $SCENARIOS; do
    echo "  - $scenario"
done
echo ""

# Run tests
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

for scenario in $SCENARIOS; do
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Scenario: $scenario${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    for protocol in $(echo $PROTOCOLS | tr ',' '\n'); do
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        
        echo -n "Testing $protocol... "
        
        if python3 -m stgen.main --scenario "$scenario" --protocol "$protocol" \
            > "$RESULTS_DIR/test_${scenario}_${protocol}_${TIMESTAMP}.log" 2>&1; then
            echo -e "${GREEN}✓${NC}"
        
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo -e "${RED}✗${NC}"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            echo "  Error log: $RESULTS_DIR/test_${scenario}_${protocol}_${TIMESTAMP}.log"
        fi
    done
    
    echo ""
done

# Summary
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "Test Summary"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "Total: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed${NC}"
    exit 1
fi

