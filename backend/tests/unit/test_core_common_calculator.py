import pytest
import math
from decimal import Decimal
from unittest.mock import patch, MagicMock
from app.core.common_calculator import CalculatorUtility


class TestCalculatorUtility:
    """Test suite for CalculatorUtility mathematical operations."""

    # Test basic arithmetic operations
    def test_basic_arithmetic_addition(self):
        """Test addition operation."""
        result = CalculatorUtility.basic_arithmetic("add", [1, 2, 3, 4])
        
        assert result["result"] == 10
        assert result["operation"] == "add"
        assert "1 + 2 + 3 + 4 = 10" in result["calculation_steps"]

    def test_basic_arithmetic_subtraction(self):
        """Test subtraction operation."""
        result = CalculatorUtility.basic_arithmetic("subtract", [10, 3, 2])
        
        assert result["result"] == 5
        assert result["operation"] == "subtract"
        assert "10 - 3 - 2 = 5" in result["calculation_steps"]

    def test_basic_arithmetic_multiplication(self):
        """Test multiplication operation."""
        result = CalculatorUtility.basic_arithmetic("multiply", [2, 3, 4])
        
        assert result["result"] == 24
        assert result["operation"] == "multiply"
        assert "2 × 3 × 4 = 24" in result["calculation_steps"]

    def test_basic_arithmetic_division(self):
        """Test division operation."""
        result = CalculatorUtility.basic_arithmetic("divide", [20, 2, 2])
        
        assert result["result"] == 5
        assert result["operation"] == "divide"
        assert "20 ÷ 2 ÷ 2 = 5.0" in result["calculation_steps"]

    def test_basic_arithmetic_division_by_zero(self):
        """Test division by zero error handling."""
        result = CalculatorUtility.basic_arithmetic("divide", [10, 0])
        
        assert "error" in result
        assert "Cannot divide by zero" in result["error"]

    def test_basic_arithmetic_power(self):
        """Test power operation."""
        result = CalculatorUtility.basic_arithmetic("power", [], {"base": 2, "exponent": 3})
        
        assert result["result"] == 8
        assert "2^3 = 8.0" in result["calculation_steps"]

    def test_basic_arithmetic_root_square(self):
        """Test square root operation."""
        result = CalculatorUtility.basic_arithmetic("root", [9])
        
        assert result["result"] == 3
        assert result["success"] is True
        assert "2th root" in result["explanation"]

    def test_basic_arithmetic_root_cube(self):
        """Test cube root operation."""
        result = CalculatorUtility.basic_arithmetic("root", [27, 3])
        
        assert abs(result["result"] - 3) < 0.001
        assert result["success"] is True

    def test_basic_arithmetic_root_with_parameters(self):
        """Test root operation with parameters."""
        result = CalculatorUtility.basic_arithmetic("root", [], {"value": 16, "n": 4})
        
        assert abs(result["result"] - 2) < 0.001

    def test_basic_arithmetic_empty_values(self):
        """Test arithmetic with empty values."""
        result = CalculatorUtility.basic_arithmetic("add", [])
        
        assert "error" in result
        assert "No values provided" in result["error"]

    def test_basic_arithmetic_invalid_operation(self):
        """Test invalid operation."""
        result = CalculatorUtility.basic_arithmetic("invalid_op", [1, 2])
        
        assert "error" in result
        assert "Unsupported operation" in result["error"]

    # Test statistical operations
    def test_statistical_operations_mean(self):
        """Test mean calculation."""
        result = CalculatorUtility.statistical_operations("mean", [1, 2, 3, 4, 5])
        
        assert result["mean"] == 3

    def test_statistical_operations_median_odd(self):
        """Test median with odd number of values."""
        result = CalculatorUtility.statistical_operations("median", [1, 3, 5])
        
        assert result["median"] == 3

    def test_statistical_operations_median_even(self):
        """Test median with even number of values."""
        result = CalculatorUtility.statistical_operations("median", [1, 2, 3, 4])
        
        assert result["median"] == 2.5

    def test_statistical_operations_mode_single(self):
        """Test mode with single mode."""
        result = CalculatorUtility.statistical_operations("mode", [1, 2, 2, 3])
        
        assert result["mode"] == 2

    def test_statistical_operations_mode_multiple(self):
        """Test mode with multiple modes."""
        result = CalculatorUtility.statistical_operations("mode", [1, 1, 2, 2, 3])
        
        assert isinstance(result["mode"], list)
        assert set(result["mode"]) == {1, 2}

    def test_statistical_operations_stdev(self):
        """Test standard deviation calculation."""
        result = CalculatorUtility.statistical_operations("stdev", [1, 2, 3, 4, 5])
        
        assert "standard_deviation" in result
        assert result["standard_deviation"] > 0

    def test_statistical_operations_stdev_single_value(self):
        """Test standard deviation with single value."""
        result = CalculatorUtility.statistical_operations("stdev", [5])
        
        assert result["standard_deviation"] == 0

    def test_statistical_operations_variance(self):
        """Test variance calculation."""
        result = CalculatorUtility.statistical_operations("variance", [1, 2, 3, 4, 5])
        
        assert "variance" in result
        assert result["variance"] > 0

    def test_statistical_operations_range(self):
        """Test range calculation."""
        result = CalculatorUtility.statistical_operations("range", [1, 5, 3, 9, 2])
        
        assert result["range"] == 8
        assert result["min"] == 1
        assert result["max"] == 9

    def test_statistical_operations_summary(self):
        """Test summary statistics."""
        result = CalculatorUtility.statistical_operations("summary", [1, 2, 3, 4, 5])
        
        assert "mean" in result
        assert "median" in result
        assert "mode" in result
        assert "standard_deviation" in result
        assert "variance" in result
        assert "range" in result
        assert "count" in result
        assert "sum" in result
        assert result["count"] == 5
        assert result["sum"] == 15

    def test_statistical_operations_correlation(self):
        """Test correlation calculation."""
        result = CalculatorUtility.statistical_operations(
            "correlation", 
            [1, 2, 3, 4, 5], 
            {"values2": [2, 4, 6, 8, 10]}
        )
        
        assert "correlation" in result
        assert abs(result["correlation"] - 1.0) < 0.001  # Perfect positive correlation

    def test_statistical_operations_correlation_missing_values2(self):
        """Test correlation with missing second dataset."""
        result = CalculatorUtility.statistical_operations("correlation", [1, 2, 3])
        
        assert "error" in result
        assert "second list of values" in result["error"]

    def test_statistical_operations_percentile(self):
        """Test percentile calculation."""
        result = CalculatorUtility.statistical_operations(
            "percentile", 
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 
            {"percentile": 50}
        )
        
        assert "percentile" in result
        assert isinstance(result["percentile"], (int, float))

    def test_statistical_operations_empty_values(self):
        """Test statistical operations with empty values."""
        result = CalculatorUtility.statistical_operations("mean", [])
        
        assert "error" in result

    # Test financial calculations
    def test_financial_calculations_compound_interest(self):
        """Test compound interest calculation."""
        result = CalculatorUtility.financial_calculations(
            "compound_interest",
            {
                "principal": 1000,
                "rate": 5,  # 5%
                "time": 2   # 2 years
            }
        )
        
        assert "final_amount" in result
        assert "interest_earned" in result
        assert result["final_amount"] > 1000
        assert result["interest_earned"] > 0

    def test_financial_calculations_loan_payment(self):
        """Test loan payment calculation."""
        result = CalculatorUtility.financial_calculations(
            "loan_payment",
            {
                "principal": 100000,
                "rate": 5,    # 5% annual
                "time": 30    # 30 years
            }
        )
        
        assert "monthly_payment" in result
        assert "total_paid" in result
        assert "total_interest" in result
        assert "amortization_schedule" in result
        assert result["monthly_payment"] > 0
        assert result["total_paid"] > 100000  # Principal amount

    def test_financial_calculations_roi(self):
        """Test ROI calculation."""
        result = CalculatorUtility.financial_calculations(
            "roi",
            {
                "initial_investment": 1000,
                "final_value": 1200
            }
        )
        
        assert "roi_percentage" in result
        assert "total_gain" in result
        assert result["roi_percentage"] == 20
        assert result["total_gain"] == 200

    def test_financial_calculations_roi_with_time(self):
        """Test ROI calculation with time period."""
        result = CalculatorUtility.financial_calculations(
            "roi",
            {
                "initial_investment": 1000,
                "final_value": 1200,
                "time_period": 2
            }
        )
        
        assert "annualized_roi_percentage" in result
        assert result["annualized_roi_percentage"] > 0

    def test_financial_calculations_npv(self):
        """Test NPV calculation."""
        result = CalculatorUtility.financial_calculations(
            "npv",
            {
                "initial_investment": 1000,
                "cash_flows": [300, 400, 500],
                "discount_rate": 10
            }
        )
        
        assert "npv" in result
        assert isinstance(result["npv"], (int, float))

    def test_financial_calculations_missing_parameters(self):
        """Test financial calculations with missing parameters."""
        result = CalculatorUtility.financial_calculations("compound_interest", {"principal": 1000})
        
        assert "error" in result
        assert "requires" in result["error"]

    # Test health metrics
    def test_health_metrics_bmi(self):
        """Test BMI calculation."""
        result = CalculatorUtility.health_metrics(
            "bmi",
            {
                "weight_kg": 70,
                "height_cm": 175
            }
        )
        
        assert "bmi" in result
        assert "category" in result
        assert result["bmi"] > 0
        assert result["category"] in ["Underweight", "Normal weight", "Overweight", "Obese"]

    def test_health_metrics_bmi_zero_height(self):
        """Test BMI calculation with zero height."""
        result = CalculatorUtility.health_metrics(
            "bmi",
            {
                "weight_kg": 70,
                "height_cm": 0
            }
        )
        
        assert "error" in result
        assert "greater than zero" in result["error"]

    def test_health_metrics_bmr_male(self):
        """Test BMR calculation for male."""
        result = CalculatorUtility.health_metrics(
            "bmr",
            {
                "weight_kg": 80,
                "height_cm": 180,
                "age": 30,
                "gender": "male"
            }
        )
        
        assert "bmr_calories" in result
        assert result["bmr_calories"] > 0
        assert result["formula_used"] == "mifflin_st_jeor"

    def test_health_metrics_bmr_female(self):
        """Test BMR calculation for female."""
        result = CalculatorUtility.health_metrics(
            "bmr",
            {
                "weight_kg": 60,
                "height_cm": 165,
                "age": 25,
                "gender": "female"
            }
        )
        
        assert "bmr_calories" in result
        assert result["bmr_calories"] > 0

    def test_health_metrics_bmr_harris_benedict(self):
        """Test BMR calculation with Harris-Benedict formula."""
        result = CalculatorUtility.health_metrics(
            "bmr",
            {
                "weight_kg": 70,
                "height_cm": 170,
                "age": 35,
                "gender": "male",
                "formula": "harris_benedict"
            }
        )
        
        assert "bmr_calories" in result
        assert result["formula_used"] == "harris_benedict"

    def test_health_metrics_tdee(self):
        """Test TDEE calculation."""
        result = CalculatorUtility.health_metrics(
            "tdee",
            {
                "bmr": 1800,
                "activity_level": "moderate"
            }
        )
        
        assert "tdee_calories" in result
        assert result["tdee_calories"] > 1800

    def test_health_metrics_invalid_gender(self):
        """Test health metrics with invalid gender."""
        result = CalculatorUtility.health_metrics(
            "bmr",
            {
                "weight_kg": 70,
                "height_cm": 170,
                "age": 30,
                "gender": "invalid"
            }
        )
        
        assert "error" in result

    # Test business metrics
    def test_business_metrics_profit_margin_gross(self):
        """Test gross profit margin calculation."""
        result = CalculatorUtility.business_metrics(
            "profit_margin",
            {
                "revenue": 10000,
                "cogs": 6000,
                "margin_type": "gross"
            }
        )
        
        assert "gross_profit" in result
        assert "gross_profit_margin" in result
        assert result["gross_profit"] == 4000
        assert result["gross_profit_margin"] == 40

    def test_business_metrics_profit_margin_net(self):
        """Test net profit margin calculation."""
        result = CalculatorUtility.business_metrics(
            "profit_margin",
            {
                "revenue": 10000,
                "costs": 8000,
                "margin_type": "net"
            }
        )
        
        assert "net_profit" in result
        assert "net_profit_margin" in result
        assert result["net_profit"] == 2000
        assert result["net_profit_margin"] == 20

    def test_business_metrics_break_even(self):
        """Test break-even analysis."""
        result = CalculatorUtility.business_metrics(
            "break_even",
            {
                "fixed_costs": 10000,
                "unit_price": 50,
                "unit_variable_cost": 30
            }
        )
        
        assert "break_even_units" in result
        assert "break_even_revenue" in result
        assert "contribution_margin" in result
        assert result["contribution_margin"] == 20
        assert result["break_even_units"] == 500

    def test_business_metrics_cagr(self):
        """Test CAGR calculation."""
        result = CalculatorUtility.business_metrics(
            "cagr",
            {
                "initial_value": 1000,
                "final_value": 2000,
                "periods": 5
            }
        )
        
        assert "cagr_percentage" in result
        assert result["cagr_percentage"] > 0

    def test_business_metrics_customer_ltv(self):
        """Test Customer Lifetime Value calculation."""
        result = CalculatorUtility.business_metrics(
            "customer_ltv",
            {
                "average_purchase_value": 100,
                "purchase_frequency": 12,  # 12 times per year
                "customer_lifespan": 3,    # 3 years
                "profit_margin": 20        # 20%
            }
        )
        
        assert "customer_ltv" in result
        assert "annual_customer_value" in result
        assert result["customer_ltv"] == 720  # 100 * 12 * 3 * 0.2
        assert result["annual_customer_value"] == 1200  # 100 * 12

    # Test helper methods
    def test_normalize_root_phrases_basic(self):
        """Test basic root phrase normalization."""
        input_text = "What is the square root of 25?"
        result = CalculatorUtility.normalize_root_phrases_to_expressions(input_text)
        
        assert "evaluate 25**(1/2)" in result

    def test_normalize_root_phrases_cube_root(self):
        """Test cube root phrase normalization."""
        input_text = "Find the cube root of 8"
        result = CalculatorUtility.normalize_root_phrases_to_expressions(input_text)
        
        assert "evaluate 8**(1/3)" in result

    def test_normalize_root_phrases_number_words(self):
        """Test number word replacement."""
        input_text = "What is two plus three?"
        result = CalculatorUtility.normalize_root_phrases_to_expressions(input_text)
        
        assert "2 plus 3" in result

    def test_normalize_root_phrases_mortgage_pattern(self):
        """Test mortgage pattern detection."""
        input_text = "Calculate mortgage payment for $300,000 at 4.5% for 30 years"
        result = CalculatorUtility.normalize_root_phrases_to_expressions(input_text)
        
        assert "Calculate loan payment with principal=300000" in result
        assert "principal=300000" in result
        assert "rate=4.5" in result
        assert "time=30" in result

    def test_normalize_root_phrases_compound_interest_pattern(self):
        """Test compound interest pattern detection."""
        input_text = "Calculate compound interest on $5000 at 6% for 10 years"
        result = CalculatorUtility.normalize_root_phrases_to_expressions(input_text)
        
        assert "Calculate compound interest with principal=5000" in result
        assert "principal=5000" in result

    def test_correlation_calculation_helper(self):
        """Test correlation helper method."""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        
        correlation = CalculatorUtility._calculate_correlation(x, y)
        
        assert abs(correlation - 1.0) < 0.001  # Perfect correlation

    def test_correlation_calculation_no_variance(self):
        """Test correlation with no variance."""
        x = [1, 1, 1, 1]
        y = [2, 3, 4, 5]
        
        correlation = CalculatorUtility._calculate_correlation(x, y)
        
        assert correlation == 0

    def test_bmi_category_determination(self):
        """Test BMI category determination."""
        assert CalculatorUtility._determine_bmi_category(17) == "Underweight"
        assert CalculatorUtility._determine_bmi_category(22) == "Normal weight"
        assert CalculatorUtility._determine_bmi_category(27) == "Overweight"
        assert CalculatorUtility._determine_bmi_category(32) == "Obese"

    def test_activity_multiplier_determination(self):
        """Test activity multiplier determination."""
        assert CalculatorUtility._get_activity_multiplier("sedentary") == 1.2
        assert CalculatorUtility._get_activity_multiplier("light") == 1.375
        assert CalculatorUtility._get_activity_multiplier("moderate") == 1.55
        assert CalculatorUtility._get_activity_multiplier("active") == 1.9
        assert CalculatorUtility._get_activity_multiplier("very active") == 1.9
        assert CalculatorUtility._get_activity_multiplier("unknown") == 1.55  # Default

    def test_error_handling_division(self):
        """Test error handling in calculations."""
        result = CalculatorUtility.basic_arithmetic("divide", [10, 2])
        assert "error" not in result
        assert result["result"] == 5

    def test_error_handling_insufficient_values(self):
        """Test error handling with insufficient values."""
        result = CalculatorUtility.basic_arithmetic("subtract", [5])
        
        assert "error" in result
        assert "at least two values" in result["error"]

    def test_root_handler_edge_cases(self):
        """Test root handler with edge cases."""
        # Test with invalid root degree
        result = CalculatorUtility._root_handler(parameters={"value": 16, "n": 0})
        
        assert "error" in result
        assert "Invalid root degree" in result["error"]

        # Test with negative root degree
        result = CalculatorUtility._root_handler(parameters={"value": 16, "n": -2})
        
        assert "error" in result

    @patch('app.core.common_calculator.logger')
    def test_error_logging(self, mock_logger):
        """Test that errors are properly logged."""
        # Test with invalid operation
        result = CalculatorUtility.basic_arithmetic("invalid", [1, 2])
        
        # Should return error result
        assert "error" in result
        assert "Unsupported operation" in result["error"]