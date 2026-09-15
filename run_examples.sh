#!/bin/bash
# Helper script to run LLM Bittle examples

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}❌ Error: ANTHROPIC_API_KEY not set${NC}"
    echo "Set it with: export ANTHROPIC_API_KEY='your-key-here'"
    exit 1
fi

# Check dependencies
check_dependency() {
    if ! python3 -c "import $1" 2>/dev/null; then
        echo -e "${RED}❌ Missing: $1${NC}"
        return 1
    fi
    return 0
}

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     LLM-Controlled Petoi Bittle - Example Launcher         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"
deps_ok=true
check_dependency "bleak" || deps_ok=false
check_dependency "anthropic" || deps_ok=false

if [ "$deps_ok" = false ]; then
    echo -e "${RED}Installing missing dependencies...${NC}"
    pip install bleak anthropic
fi

echo -e "${GREEN}✓ Dependencies OK${NC}\n"

# Show menu
show_menu() {
    echo -e "${BLUE}Select an example:${NC}"
    echo ""
    echo "  0. Interactive Chat (Recommended for first-time users)"
    echo ""
    echo "  1. Dance Performance"
    echo "  2. Emotion Expression"
    echo "  3. Story Telling"
    echo "  4. Voice Commands"
    echo "  5. Creative Poses"
    echo "  6. Multi-Step Tasks"
    echo "  7. Testing & Validation"
    echo "  8. Advanced Integration"
    echo ""
    echo "  9. Quick Start Guide"
    echo " 10. Design Documentation"
    echo " 11. Full Examples README"
    echo ""
    echo "  q. Quit"
    echo ""
}

# Run example
run_example() {
    case $1 in
        0)
            echo -e "${GREEN}Starting Interactive Chat...${NC}\n"
            python3 "$SCRIPT_DIR/llm_bittle_controller.py"
            ;;
        1)
            echo -e "${GREEN}Running Dance Performance...${NC}\n"
            python3 "$SCRIPT_DIR/example_dance.py"
            ;;
        2)
            echo -e "${GREEN}Running Emotion Expression...${NC}\n"
            python3 "$SCRIPT_DIR/example_emotions.py"
            ;;
        3)
            echo -e "${GREEN}Running Story Telling...${NC}\n"
            python3 "$SCRIPT_DIR/example_story.py"
            ;;
        4)
            echo -e "${GREEN}Running Voice Commands...${NC}\n"
            python3 "$SCRIPT_DIR/example_voice_commands.py"
            ;;
        5)
            echo -e "${GREEN}Running Creative Poses...${NC}\n"
            python3 "$SCRIPT_DIR/example_creative_poses.py"
            ;;
        6)
            echo -e "${GREEN}Running Multi-Step Tasks...${NC}\n"
            python3 "$SCRIPT_DIR/example_multi_step_task.py"
            ;;
        7)
            echo -e "${GREEN}Running Testing & Validation...${NC}\n"
            python3 "$SCRIPT_DIR/example_testing.py"
            ;;
        8)
            echo -e "${GREEN}Running Advanced Integration...${NC}\n"
            python3 "$SCRIPT_DIR/example_advanced_integration.py"
            ;;
        9)
            echo -e "${GREEN}Showing Quick Start Guide...${NC}\n"
            less "$SCRIPT_DIR/QUICK_START.md"
            ;;
        10)
            echo -e "${GREEN}Showing Design Documentation...${NC}\n"
            less "$SCRIPT_DIR/LLM_CONTROLLER_DESIGN.md"
            ;;
        11)
            echo -e "${GREEN}Showing Full Examples README...${NC}\n"
            less "$SCRIPT_DIR/LLM_EXAMPLES_README.md"
            ;;
        q)
            echo "Goodbye! 👋"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            ;;
    esac
}

# Main loop
while true; do
    show_menu
    read -p "Enter your choice: " choice
    echo ""

    if [ -z "$choice" ]; then
        continue
    fi

    run_example "$choice"

    echo ""
    read -p "Press Enter to continue..."
    clear
done
