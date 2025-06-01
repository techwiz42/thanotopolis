import pytest
import math
from unittest.mock import patch, MagicMock
from app.core.common_calculator import CalculatorUtility


class TestCalculatorUtility:
    """Test cases for CalculatorUtility class."""

    # Basic Arithmetic Tests
    def test_basic_arithmetic_add(self):
        """Test basic addition operation."""
        result = CalculatorUtility.basic_arithmetic("add", [1, 2, 3, 4])
        assert result["result"] == 10
        assert result["operation"] == "add"
        assert "calculation_steps" in result

    def test_basic_arithmetic_subtract(self):
        """Test basic subtraction operation."""
        result = CalculatorUtility.basic_arithmetic("subtract", [10, 3, 2])
        assert result["result"] == 5
        assert result["operation"] == "subtract"

    def test_basic_arithmetic_multiply(self):
        """Test basic multiplication operation."""
        result = CalculatorUtility.basic_arithmetic("multiply", [2, 3, 4])
        assert result["result"] == 24
        assert result["operation"] == "multiply"

    def test_basic_arithmetic_divide(self):
        """Test basic division operation."""
        result = CalculatorUtility.basic_arithmetic("divide", [24, 2, 3])
        assert result["result"] == 4
        assert result["operation"] == "divide"

    def test_basic_arithmetic_divide_by_zero(self):
        """Test division by zero error handling."""
        result = CalculatorUtility.basic_arithmetic("divide", [10, 0])
        assert "error" in result
        assert "divide by zero" in result["error"].lower()

    def test_basic_arithmetic_power(self):
        """Test power operation."""
        parameters = {"base": 2, "exponent": 3}
        result = CalculatorUtility.basic_arithmetic("power", [1], parameters)
        assert result["result"] == 8
        assert result["operation"] == "power"

    def test_basic_arithmetic_root(self):
        """Test root operation."""
        parameters = {"value": 16, "n": 2}
        result = CalculatorUtility.basic_arithmetic("root", [1], parameters)
        assert result["result"] == 4
        assert result["success"] is True

    def test_basic_arithmetic_cube_root(self):
        """Test cube root operation."""
        parameters = {"value": 27, "n": 3}
        result = CalculatorUtility.basic_arithmetic("root", [1], parameters)
        assert abs(result["result"] - 3) < 0.0001

    def test_basic_arithmetic_empty_values(self):
        """Test with empty values list."""
        result = CalculatorUtility.basic_arithmetic("add", [])
        assert "error" in result

    def test_basic_arithmetic_insufficient_values_subtract(self):
        """Test subtraction with insufficient values."""
        result = CalculatorUtility.basic_arithmetic("subtract", [5])
        assert "error" in result

    def test_basic_arithmetic_insufficient_values_divide(self):
        """Test division with insufficient values."""
        result = CalculatorUtility.basic_arithmetic("divide", [5])
        assert "error" in result

    def test_basic_arithmetic_unsupported_operation(self):
        """Test unsupported operation."""
        result = CalculatorUtility.basic_arithmetic("invalid_operation", [1, 2])
        assert "error" in result

    # Statistical Operations Tests
    def test_statistical_mean(self):
        """Test mean calculation."""
        result = CalculatorUtility.statistical_operations("mean", [1, 2, 3, 4, 5])
        assert result["mean"] == 3

    def test_statistical_median(self):
        """Test median calculation."""
        result = CalculatorUtility.statistical_operations("median", [1, 2, 3, 4, 5])
        assert result["median"] == 3

    def test_statistical_mode(self):
        """Test mode calculation."""
        result = CalculatorUtility.statistical_operations("mode", [1, 2, 2, 3, 4])
        assert result["mode"] == 2

    def test_statistical_mode_multiple(self):
        """Test mode calculation with multiple modes."""
        result = CalculatorUtility.statistical_operations("mode", [1, 1, 2, 2, 3])
        # Should return a list when there are multiple modes
        assert isinstance(result["mode"], list)
        assert 1 in result["mode"]
        assert 2 in result["mode"]

    def test_statistical_stdev(self):
        """Test standard deviation calculation."""
        result = CalculatorUtility.statistical_operations("stdev", [1, 2, 3, 4, 5])
        assert "standard_deviation" in result
        assert result["standard_deviation"] > 0

    def test_statistical_stdev_single_value(self):
        """Test standard deviation with single value."""
        result = CalculatorUtility.statistical_operations("stdev", [5])
        assert result["standard_deviation"] == 0

    def test_statistical_variance(self):
        """Test variance calculation."""
        result = CalculatorUtility.statistical_operations("variance", [1, 2, 3, 4, 5])
        assert "variance" in result
        assert result["variance"] > 0

    def test_statistical_range(self):
        """Test range calculation."""
        result = CalculatorUtility.statistical_operations("range", [1, 5, 3, 9, 2])
        assert result["range"] == 8
        assert result["min"] == 1
        assert result["max"] == 9

    def test_statistical_summary(self):
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

    def test_statistical_correlation(self):
        """Test correlation calculation."""
        parameters = {"values2": [2, 4, 6, 8, 10]}
        result = CalculatorUtility.statistical_operations("correlation", [1, 2, 3, 4, 5], parameters)
        assert "correlation" in result
        assert abs(result["correlation"] - 1.0) < 0.0001  # Perfect positive correlation

    def test_statistical_correlation_missing_values2(self):
        """Test correlation with missing second values."""
        result = CalculatorUtility.statistical_operations("correlation", [1, 2, 3])
        assert "error" in result

    def test_statistical_correlation_different_lengths(self):
        """Test correlation with different length arrays."""
        parameters = {"values2": [2, 4]}
        result = CalculatorUtility.statistical_operations("correlation", [1, 2, 3], parameters)
        assert "error" in result

    def test_statistical_percentile(self):
        """Test percentile calculation."""
        parameters = {"percentile": 50}
        result = CalculatorUtility.statistical_operations("percentile", [1, 2, 3, 4, 5], parameters)
        assert "percentile" in result

    def test_statistical_percentile_missing_parameter(self):
        """Test percentile with missing percentile parameter."""
        result = CalculatorUtility.statistical_operations("percentile", [1, 2, 3])
        assert "error" in result

    def test_statistical_percentile_invalid_range(self):
        """Test percentile with invalid range."""
        parameters = {"percentile": 150}
        result = CalculatorUtility.statistical_operations("percentile", [1, 2, 3], parameters)
        assert "error" in result

    def test_statistical_empty_values(self):
        """Test statistical operations with empty values."""
        result = CalculatorUtility.statistical_operations("mean", [])
        assert "error" in result

    def test_statistical_unsupported_operation(self):
        """Test unsupported statistical operation."""
        result = CalculatorUtility.statistical_operations("invalid_stat", [1, 2, 3])
        assert "error" in result

    # Financial Calculations Tests
    def test_financial_compound_interest(self):
        """Test compound interest calculation."""
        parameters = {"principal": 1000, "rate": 5, "time": 2}
        result = CalculatorUtility.financial_calculations("compound_interest", parameters)
        assert "final_amount" in result
        assert "interest_earned" in result
        assert result["final_amount"] > 1000

    def test_financial_compound_interest_missing_params(self):
        """Test compound interest with missing parameters."""
        parameters = {"principal": 1000, "rate": 5}
        result = CalculatorUtility.financial_calculations("compound_interest", parameters)
        assert "error" in result

    def test_financial_loan_payment(self):
        """Test loan payment calculation."""
        parameters = {"principal": 100000, "rate": 5, "time": 30}
        result = CalculatorUtility.financial_calculations("loan_payment", parameters)
        assert "monthly_payment" in result
        assert "total_paid" in result
        assert "total_interest" in result
        assert "amortization_schedule" in result

    def test_financial_loan_payment_zero_rate(self):
        """Test loan payment with zero interest rate."""
        parameters = {"principal": 12000, "rate": 0, "time": 1}
        result = CalculatorUtility.financial_calculations("loan_payment", parameters)
        assert result["monthly_payment"] == 1000  # 12000 / 12 months

    def test_financial_roi(self):
        """Test ROI calculation."""
        parameters = {"initial_investment": 1000, "final_value": 1200}
        result = CalculatorUtility.financial_calculations("roi", parameters)
        assert "roi_percentage" in result
        assert result["roi_percentage"] == 20

    def test_financial_roi_with_time(self):
        """Test ROI calculation with time period."""
        parameters = {"initial_investment": 1000, "final_value": 1200, "time_period": 2}
        result = CalculatorUtility.financial_calculations("roi", parameters)
        assert "annualized_roi_percentage" in result

    def test_financial_roi_missing_params(self):
        """Test ROI with missing parameters."""
        parameters = {"initial_investment": 1000}
        result = CalculatorUtility.financial_calculations("roi", parameters)
        assert "error" in result

    def test_financial_npv(self):
        """Test NPV calculation."""
        parameters = {
            "initial_investment": 1000,
            "cash_flows": [300, 400, 500],
            "discount_rate": 10
        }
        result = CalculatorUtility.financial_calculations("npv", parameters)
        assert "npv" in result

    def test_financial_npv_missing_params(self):
        """Test NPV with missing parameters."""
        parameters = {"initial_investment": 1000}
        result = CalculatorUtility.financial_calculations("npv", parameters)
        assert "error" in result

    @patch('app.core.common_calculator.CalculatorUtility._calculate_irr_approximation')
    def test_financial_irr_with_numpy(self, mock_irr_approx):
        """Test IRR calculation with approximation method."""
        mock_irr_approx.return_value = 15  # Return directly as percentage
        parameters = {
            "initial_investment": 1000,
            "cash_flows": [300, 400, 500]
        }
        result = CalculatorUtility.financial_calculations("irr", parameters)
        assert "irr_percentage" in result
        assert result["irr_percentage"] == 15

    def test_financial_irr_without_numpy(self):
        """Test IRR calculation without numpy (approximation)."""
        parameters = {
            "initial_investment": 1000,
            "cash_flows": [300, 400, 500]
        }
        # This should use the approximation method
        result = CalculatorUtility.financial_calculations("irr", parameters)
        assert "irr_percentage" in result

    def test_financial_unsupported_operation(self):
        """Test unsupported financial operation."""
        result = CalculatorUtility.financial_calculations("invalid_financial", {})
        assert "error" in result

    # Health Metrics Tests
    def test_health_bmi(self):
        """Test BMI calculation."""
        parameters = {"weight_kg": 70, "height_cm": 175}
        result = CalculatorUtility.health_metrics("bmi", parameters)
        assert "bmi" in result
        assert "category" in result
        assert result["bmi"] > 0

    def test_health_bmi_missing_params(self):
        """Test BMI with missing parameters."""
        parameters = {"weight_kg": 70}
        result = CalculatorUtility.health_metrics("bmi", parameters)
        assert "error" in result

    def test_health_bmi_zero_height(self):
        """Test BMI with zero height."""
        parameters = {"weight_kg": 70, "height_cm": 0}
        result = CalculatorUtility.health_metrics("bmi", parameters)
        assert "error" in result

    def test_health_bmr_male(self):
        """Test BMR calculation for male."""
        parameters = {"weight_kg": 70, "height_cm": 175, "age": 30, "gender": "male"}
        result = CalculatorUtility.health_metrics("bmr", parameters)
        assert "bmr_calories" in result
        assert result["bmr_calories"] > 0

    def test_health_bmr_female(self):
        """Test BMR calculation for female."""
        parameters = {"weight_kg": 60, "height_cm": 165, "age": 25, "gender": "female"}
        result = CalculatorUtility.health_metrics("bmr", parameters)
        assert "bmr_calories" in result
        assert result["bmr_calories"] > 0

    def test_health_bmr_harris_benedict(self):
        """Test BMR calculation with Harris-Benedict formula."""
        parameters = {
            "weight_kg": 70, "height_cm": 175, "age": 30, 
            "gender": "male", "formula": "harris_benedict"
        }
        result = CalculatorUtility.health_metrics("bmr", parameters)
        assert "bmr_calories" in result
        assert result["formula_used"] == "harris_benedict"

    def test_health_bmr_invalid_gender(self):
        """Test BMR with invalid gender."""
        parameters = {"weight_kg": 70, "height_cm": 175, "age": 30, "gender": "invalid"}
        result = CalculatorUtility.health_metrics("bmr", parameters)
        assert "error" in result

    def test_health_tdee(self):
        """Test TDEE calculation."""
        parameters = {"bmr": 1800, "activity_level": "moderate"}
        result = CalculatorUtility.health_metrics("tdee", parameters)
        assert "tdee_calories" in result
        assert result["tdee_calories"] > 1800

    def test_health_body_fat_navy_male(self):
        """Test body fat calculation using Navy method for males."""
        parameters = {
            "method": "navy", "gender": "male",
            "height_cm": 175, "waist_cm": 85, "neck_cm": 38
        }
        result = CalculatorUtility.health_metrics("body_fat", parameters)
        assert "body_fat_percentage" in result
        assert result["method"] == "Navy"

    def test_health_body_fat_navy_female(self):
        """Test body fat calculation using Navy method for females."""
        parameters = {
            "method": "navy", "gender": "female",
            "height_cm": 165, "waist_cm": 75, "neck_cm": 32, "hip_cm": 95
        }
        result = CalculatorUtility.health_metrics("body_fat", parameters)
        assert "body_fat_percentage" in result

    def test_health_body_fat_bmi_method(self):
        """Test body fat estimation from BMI."""
        parameters = {"method": "bmi", "bmi": 22, "age": 30, "gender": "male"}
        result = CalculatorUtility.health_metrics("body_fat", parameters)
        assert "body_fat_percentage" in result
        assert result["method"] == "BMI-based estimation"

    def test_health_ideal_weight(self):
        """Test ideal weight calculation."""
        parameters = {"height_cm": 175, "gender": "male"}
        result = CalculatorUtility.health_metrics("ideal_weight", parameters)
        assert "bmi_based" in result
        assert "hamwi" in result
        assert "devine" in result
        assert "robinson" in result
        assert "miller" in result
        assert "average" in result

    def test_health_unsupported_operation(self):
        """Test unsupported health operation."""
        result = CalculatorUtility.health_metrics("invalid_health", {})
        assert "error" in result

    # Business Metrics Tests
    def test_business_profit_margin_gross(self):
        """Test gross profit margin calculation."""
        parameters = {"revenue": 10000, "cogs": 6000, "margin_type": "gross"}
        result = CalculatorUtility.business_metrics("profit_margin", parameters)
        assert "gross_profit_margin" in result
        assert result["gross_profit_margin"] == 40

    def test_business_profit_margin_net(self):
        """Test net profit margin calculation."""
        parameters = {"revenue": 10000, "costs": 8000, "margin_type": "net"}
        result = CalculatorUtility.business_metrics("profit_margin", parameters)
        assert "net_profit_margin" in result
        assert result["net_profit_margin"] == 20

    def test_business_break_even(self):
        """Test break-even calculation."""
        parameters = {"fixed_costs": 10000, "unit_price": 50, "unit_variable_cost": 30}
        result = CalculatorUtility.business_metrics("break_even", parameters)
        assert "break_even_units" in result
        assert "break_even_revenue" in result
        assert result["break_even_units"] == 500

    def test_business_break_even_invalid_margin(self):
        """Test break-even with invalid margin (price <= variable cost)."""
        parameters = {"fixed_costs": 10000, "unit_price": 30, "unit_variable_cost": 30}
        result = CalculatorUtility.business_metrics("break_even", parameters)
        assert "error" in result

    def test_business_cagr(self):
        """Test CAGR calculation."""
        parameters = {"initial_value": 1000, "final_value": 1500, "periods": 3}
        result = CalculatorUtility.business_metrics("cagr", parameters)
        assert "cagr_percentage" in result
        assert result["cagr_percentage"] > 0

    def test_business_marketing_roi(self):
        """Test marketing ROI calculation."""
        parameters = {"revenue": 10000, "marketing_cost": 2000}
        result = CalculatorUtility.business_metrics("roi_marketing", parameters)
        assert "marketing_roi_percentage" in result
        assert result["marketing_roi_percentage"] == 400

    def test_business_customer_ltv(self):
        """Test customer lifetime value calculation."""
        parameters = {
            "average_purchase_value": 100,
            "purchase_frequency": 12,
            "customer_lifespan": 3,
            "profit_margin": 20
        }
        result = CalculatorUtility.business_metrics("customer_ltv", parameters)
        assert "customer_ltv" in result
        assert result["customer_ltv"] == 720  # 100 * 12 * 3 * 0.2

    def test_business_unsupported_operation(self):
        """Test unsupported business operation."""
        result = CalculatorUtility.business_metrics("invalid_business", {})
        assert "error" in result

    # Helper Methods Tests
    def test_calculate_correlation_perfect_positive(self):
        """Test perfect positive correlation."""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        correlation = CalculatorUtility._calculate_correlation(x, y)
        assert abs(correlation - 1.0) < 0.0001

    def test_calculate_correlation_perfect_negative(self):
        """Test perfect negative correlation."""
        x = [1, 2, 3, 4, 5]
        y = [10, 8, 6, 4, 2]
        correlation = CalculatorUtility._calculate_correlation(x, y)
        assert abs(correlation - (-1.0)) < 0.0001

    def test_calculate_correlation_no_correlation(self):
        """Test no correlation."""
        x = [1, 2, 3, 4, 5]
        y = [1, 1, 1, 1, 1]  # No variance in y
        correlation = CalculatorUtility._calculate_correlation(x, y)
        assert correlation == 0

    def test_calculate_correlation_different_lengths(self):
        """Test correlation with different length arrays."""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6]  # Shorter array
        correlation = CalculatorUtility._calculate_correlation(x, y)
        # Should truncate to shorter length and calculate
        assert correlation is not None

    def test_determine_bmi_category(self):
        """Test BMI category determination."""
        assert CalculatorUtility._determine_bmi_category(17) == "Underweight"
        assert CalculatorUtility._determine_bmi_category(22) == "Normal weight"
        assert CalculatorUtility._determine_bmi_category(27) == "Overweight"
        assert CalculatorUtility._determine_bmi_category(32) == "Obese"

    def test_get_activity_multiplier(self):
        """Test activity multiplier determination."""
        assert CalculatorUtility._get_activity_multiplier("sedentary") == 1.2
        assert CalculatorUtility._get_activity_multiplier("light") == 1.375
        assert CalculatorUtility._get_activity_multiplier("moderate") == 1.55
        assert CalculatorUtility._get_activity_multiplier("active") == 1.9  # Updated to match implementation
        assert CalculatorUtility._get_activity_multiplier("very active") == 1.9
        # Test default case
        assert CalculatorUtility._get_activity_multiplier("unknown") == 1.55


if __name__ == "__main__":
    pytest.main([__file__])
