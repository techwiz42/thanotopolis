#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[*]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if we're in the backend directory
if [ ! -f "pytest.ini" ]; then
    print_error "Please run this script from the backend directory"
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "Virtual environment not activated"
    print_status "Attempting to activate venv..."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        print_error "Virtual environment not found. Please create and activate it first."
        exit 1
    fi
fi

# Parse command line arguments
COMMAND=${1:-"all"}

case $COMMAND in
    "setup")
        print_status "Setting up test database..."
        python setup_test_db.py
        ;;
    
    "all")
        print_status "Setting up test database..."
        python setup_test_db.py
        
        print_status "Running all tests..."
        pytest tests/ -v
        ;;
    
    "unit")
        print_status "Setting up test database..."
        python setup_test_db.py
        
        print_status "Running unit tests..."
        pytest tests/unit/ -v
        ;;
    
    "integration")
        print_status "Setting up test database..."
        python setup_test_db.py
        
        print_status "Running integration tests..."
        pytest tests/integration/ -v
        ;;
    
    "coverage")
        print_status "Setting up test database..."
        python setup_test_db.py
        
        print_status "Running tests with coverage..."
        pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
        
        print_status "Coverage report generated in htmlcov/index.html"
        ;;
    
    "watch")
        print_status "Setting up test database..."
        python setup_test_db.py
        
        print_status "Running tests in watch mode..."
        if ! command -v pytest-watch &> /dev/null; then
            print_warning "pytest-watch not installed. Installing..."
            pip install pytest-watch
        fi
        pytest-watch tests/ -- -v
        ;;
    
    "clean")
        print_status "Cleaning up test artifacts..."
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
        find . -type f -name "*.pyc" -delete
        rm -rf .pytest_cache htmlcov .coverage
        print_status "Clean complete!"
        ;;
    
    "help"|*)
        echo "Usage: ./run_tests.sh [command]"
        echo ""
        echo "Commands:"
        echo "  setup       - Create test database only"
        echo "  all         - Run all tests (default)"
        echo "  unit        - Run unit tests only"
        echo "  integration - Run integration tests only"
        echo "  coverage    - Run tests with coverage report"
        echo "  watch       - Run tests in watch mode"
        echo "  clean       - Clean up test artifacts"
        echo "  help        - Show this help message"
        ;;
esac
