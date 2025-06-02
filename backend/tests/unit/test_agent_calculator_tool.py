import pytest
import json
from unittest.mock import patch, MagicMock
from app.agents.agent_calculator_tool import AgentCalculatorTool, get_calculator_tool, get_interpreter_tool


class TestAgentCalculatorTool:
    """Test cases for AgentCalculatorTool class."""

    # Number word replacement tests
    def test_replace_number_words_with_digits_basic(self):
        """Test basic number word replacement."""
        text = "the square root of sixteen"
        result = AgentCalculatorTool._replace_number_words_with_digits(text)
        assert "16" in result
        assert "sixteen" not in result

    def test_replace_number_words_with_digits_ordinals(self):
        """Test ordinal number replacement."""
        text = "find the ninth root of twenty"
        result = AgentCalculatorTool._replace_number_words_with_digits(text)
        assert "9" in result
        assert "20" in result
        assert "ninth" not in result
        assert "twenty" not in result

    def test_replace_number_words_with_digits_complex(self):
        """Test complex number phrase replacement."""
        text = "twenty-five percent of one hundred"
        result = AgentCalculatorTool._replace_number_words_with_digits(text)
        assert "25" in result or "twenty five" in result.lower()
        assert "100" in result

    def test_replace_number_words_with_digits_no_change(self):
        """Test text with no number words."""
        text = "calculate the result for me"
        result = AgentCalculatorTool._replace_number_words_with_digits(text)
        assert result == text

    # Root phrase normalization tests
    def test_normalize_root_phrases_square_root(self):
        """Test square root phrase normalization."""
        prompt = "find the square root of 16"
        result = AgentCalculatorTool.normalize_root_phrases_to_expressions(prompt)
        assert "evaluate 16**(1/2)" in result

    def test_normalize_root_phrases_cube_root(self):
        """Test cube root phrase normalization."""
        prompt = "calculate the cube root of 27"
        result = AgentCalculatorTool.normalize_root_phrases_to_expressions(prompt)
        assert "evaluate 27**(1/3)" in result

    def test_normalize_root_phrases_nth_root(self):
        """Test nth root phrase normalization."""
        prompt = "find the 4th root of 81"
        result = AgentCalculatorTool.normalize_root_phrases_to_expressions(prompt)
        assert "raise 81 to the 1/4 power" in result

    def test_normalize_root_phrases_with_number_words(self):
        """Test root phrases with number words."""
        prompt = "find the square root of fourteen"
        result = AgentCalculatorTool.normalize_root_phrases_to_expressions(prompt)
        assert "14" in result
        assert "evaluate" in result

    def test_normalize_root_phrases_no_change(self):
        """Test prompt with no root phrases."""
        prompt = "what is the weather like today"
        result = AgentCalculatorTool.normalize_root_phrases_to_expressions(prompt)
        assert result == prompt

    # Calculate method tests
    @pytest.mark.asyncio
    async def test_calculate_arithmetic_add(self):
        """Test arithmetic addition calculation."""
        # Create a mock context
        mock_context = MagicMock()
        
        result = await AgentCalculatorTool.calculate(
            context=mock_context,
            operation_type="arithmetic",
            operation="add",
            values="[1, 2, 3, 4]"
        )
        assert "result" in result
        assert result["result"] == 10

    @pytest.mark.asyncio
    async def test_calculate_arithmetic_power(self):
        """Test arithmetic power calculation."""
        # Create a mock context
        mock_context = MagicMock()
        
        result = await AgentCalculatorTool.calculate(
            context=mock_context,
            operation_type="arithmetic",
            operation="power",
            parameters="{\"base\": 2, \"exponent\": 3}"
        )
        assert "result" in result
        assert result["result"] == 8

    @pytest.mark.asyncio
    async def test_calculate_arithmetic_root(self):
        """Test arithmetic root calculation."""
        # Create a mock context
        mock_context = MagicMock()
        
        result = await AgentCalculatorTool.calculate(
            context=mock_context,
            operation_type="arithmetic",
            operation="root",
            values="[16, 2]"
        )
        assert "result" in result
        assert result["result"] == 4

    @pytest.mark.asyncio
    async def test_calculate_arithmetic_evaluate(self):
        """Test arithmetic expression evaluation."""
        # Create a mock context
        mock_context = MagicMock()
        
        result = await AgentCalculatorTool.calculate(
            context=mock_context,
            operation_type="arithmetic",
            operation="evaluate",
            expression="2 + 3 * 4"
        )
        assert "result" in result

    @pytest.mark.asyncio
    async def test_calculate_statistical_mean(self):
        """Test statistical mean calculation."""
        # Create a mock context
        mock_context = MagicMock()
        
        result = await AgentCalculatorTool.calculate(
            context=mock_context,
            operation_type="statistical",
            operation="mean",
            values="[1, 2, 3, 4, 5]"
        )
        assert "mean" in result
        assert result["mean"] == 3

    @pytest.mark.asyncio
    async def test_calculate_financial_compound_interest(self):
        """Test financial compound interest calculation."""
        # Create a mock context
        mock_context = MagicMock()
        
        result = await AgentCalculatorTool.calculate(
            context=mock_context,
            operation_type="financial",
            operation="compound_interest",
            parameters="{\"principal\": 1000, \"rate\": 5, \"time\": 2}"
        )
        assert "final_amount" in result
        assert result["final_amount"] > 1000

    @pytest.mark.asyncio
    async def test_calculate_health_bmi(self):
        """Test health BMI calculation."""
        # Create a mock context
        mock_context = MagicMock()
        
        result = await AgentCalculatorTool.calculate(
            context=mock_context,
            operation_type="health",
            operation="bmi",
            parameters="{\"weight_kg\": 70, \"height_cm\": 175}"
        )
        assert "bmi" in result
        assert result["bmi"] > 0

    @pytest.mark.asyncio
    async def test_calculate_business_profit_margin(self):
        """Test business profit margin calculation."""
        # Create a mock context
        mock_context = MagicMock()
        
        result = await AgentCalculatorTool.calculate(
            context=mock_context,
            operation_type="business",
            operation="profit_margin",
            parameters="{\"revenue\": 10000, \"costs\": 8000}"
        )
        assert "net_profit_margin" in result

    @pytest.mark.asyncio
    async def test_calculate_missing_operation_type(self):
        """Test calculation with missing operation type."""
        # Create a mock context
        mock_context = MagicMock()
        
        result = await AgentCalculatorTool.calculate(
            context=mock_context,
            operation_type=None,
            operation="add"
        )
        assert "error" in result
        assert "Operation type is required" in result["error"]

    @pytest.mark.asyncio
    async def test_calculate_missing_operation(self):
        """Test calculation with missing operation."""
        # Create a mock context
        mock_context = MagicMock()
        
        result = await AgentCalculatorTool.calculate(
            context=mock_context,
            operation_type="arithmetic",
            operation=None
        )
        assert "error" in result
        assert "Operation is required" in result["error"]

    @pytest.mark.asyncio
    async def test_calculate_unsupported_operation_type(self):
        """Test calculation with unsupported operation type."""
        # Create a mock context
        mock_context = MagicMock()
        
        result = await AgentCalculatorTool.calculate(
            context=mock_context,
            operation_type="invalid_type",
            operation="add"
        )
        assert "error" in result
        assert "Unsupported operation type" in result["error"]

    @pytest.mark.asyncio
    async def test_calculate_arithmetic_missing_values(self):
        """Test arithmetic operation without required values."""
        # Create a mock context
        mock_context = MagicMock()
        
        result = await AgentCalculatorTool.calculate(
            context=mock_context,
            operation_type="arithmetic",
            operation="add",
            values="[]"
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_calculate_with_exception(self):
        """Test calculation with exception handling."""
        # Create a mock context
        mock_context = MagicMock()
        
        with patch('app.agents.agent_calculator_tool.CalculatorUtility.basic_arithmetic',
                   side_effect=Exception("Test exception")):
            result = await AgentCalculatorTool.calculate(
                context=mock_context,
                operation_type="arithmetic",
                operation="add",
                values="[1, 2]"
            )
            assert "error" in result
            assert "Test exception" in result["error"]

    # Interpret calculation results tests
    @pytest.mark.asyncio
    async def test_interpret_calculation_results_basic(self):
        """Test basic interpretation of calculation results."""
        # Create a mock context
        mock_context = MagicMock()
        
        calculation_results = {"result": 42}
        result = await AgentCalculatorTool.interpret_calculation_results(
            context=mock_context,
            calculation_results=json.dumps(calculation_results)
        )
        assert "interpretation" in result
        assert "summary" in result["interpretation"]

    @pytest.mark.asyncio
    async def test_interpret_calculation_results_financial(self):
        """Test interpretation of financial calculation results."""
        # Create a mock context
        mock_context = MagicMock()
        
        calculation_results = {
            "final_amount": 1100,
            "interest_earned": 100
        }
        result = await AgentCalculatorTool.interpret_calculation_results(
            context=mock_context,
            calculation_results=json.dumps(calculation_results)
        )
        assert "interpretation" in result
        assert "key_findings" in result["interpretation"]
        assert "1,100" in result["interpretation"]["summary"]

    @pytest.mark.asyncio
    async def test_interpret_calculation_results_statistical(self):
        """Test interpretation of statistical calculation results."""
        # Create a mock context
        mock_context = MagicMock()
        
        calculation_results = {"mean": 25.5}
        result = await AgentCalculatorTool.interpret_calculation_results(
            context=mock_context,
            calculation_results=json.dumps(calculation_results)
        )
        assert "interpretation" in result
        assert "25.50" in result["interpretation"]["key_findings"][0]

    @pytest.mark.asyncio
    async def test_interpret_calculation_results_correlation(self):
        """Test interpretation of correlation results."""
        # Create a mock context
        mock_context = MagicMock()
        
        calculation_results = {"correlation": 0.85}
        result = await AgentCalculatorTool.interpret_calculation_results(
            context=mock_context,
            calculation_results=json.dumps(calculation_results)
        )
        assert "interpretation" in result
        assert "strong positive" in result["interpretation"]["key_findings"][0]

    @pytest.mark.asyncio
    async def test_interpret_calculation_results_bmi(self):
        """Test interpretation of BMI calculation results."""
        # Create a mock context
        mock_context = MagicMock()
        
        calculation_results = {
            "bmi": 22.5,
            "category": "Normal weight"
        }
        result = await AgentCalculatorTool.interpret_calculation_results(
            context=mock_context,
            calculation_results=json.dumps(calculation_results)
        )
        assert "interpretation" in result
        assert "22.5" in result["interpretation"]["summary"]
        assert "Normal weight" in result["interpretation"]["summary"]

    @pytest.mark.asyncio
    async def test_interpret_calculation_results_profit_margin(self):
        """Test interpretation of profit margin results."""
        # Create a mock context
        mock_context = MagicMock()
        
        calculation_results = {"profit_margin": 15.5}
        result = await AgentCalculatorTool.interpret_calculation_results(
            context=mock_context,
            calculation_results=json.dumps(calculation_results)
        )
        assert "interpretation" in result
        assert "15.50%" in result["interpretation"]["summary"]

    @pytest.mark.asyncio
    async def test_interpret_calculation_results_break_even(self):
        """Test interpretation of break-even results."""
        # Create a mock context
        mock_context = MagicMock()
        
        calculation_results = {
            "break_even_units": 500,
            "break_even_revenue": 25000
        }
        result = await AgentCalculatorTool.interpret_calculation_results(
            context=mock_context,
            calculation_results=json.dumps(calculation_results)
        )
        assert "interpretation" in result
        assert "500.0 units" in result["interpretation"]["summary"]

    @pytest.mark.asyncio
    async def test_interpret_calculation_results_error(self):
        """Test interpretation of error results."""
        # Create a mock context
        mock_context = MagicMock()
        
        calculation_results = {"error": "Division by zero"}
        result = await AgentCalculatorTool.interpret_calculation_results(
            context=mock_context,
            calculation_results=json.dumps(calculation_results)
        )
        assert "interpretation" in result
        assert "Error in calculation" in result["interpretation"]

    @pytest.mark.asyncio
    async def test_interpret_calculation_results_detailed_level(self):
        """Test detailed interpretation level."""
        # Create a mock context
        mock_context = MagicMock()
        
        calculation_results = {
            "result": 100,
            "calculation_steps": ["Step 1", "Step 2"],
            "parameters": {"value": 10}
        }
        result = await AgentCalculatorTool.interpret_calculation_results(
            context=mock_context,
            calculation_results=json.dumps(calculation_results),
            interpretation_level="detailed"
        )
        assert "interpretation" in result
        assert "calculation_steps" in result["interpretation"]
        assert "parameters_used" in result["interpretation"]

    @pytest.mark.asyncio
    async def test_interpret_calculation_results_basic_level(self):
        """Test basic interpretation level."""
        # Create a mock context
        mock_context = MagicMock()
        
        calculation_results = {"result": 100}
        result = await AgentCalculatorTool.interpret_calculation_results(
            context=mock_context,
            calculation_results=json.dumps(calculation_results),
            interpretation_level="basic"
        )
        assert "interpretation" in result
        # Should only return the summary string, not the full structure
        assert isinstance(result["interpretation"], str)

    @pytest.mark.asyncio
    async def test_interpret_calculation_results_empty(self):
        """Test interpretation with empty results."""
        # Create a mock context
        mock_context = MagicMock()
        
        result = await AgentCalculatorTool.interpret_calculation_results(
            context=mock_context
        )
        assert "interpretation" in result

    # Tool creation tests
    @patch('app.agents.agent_calculator_tool.function_tool')
    def test_get_calculator_tool(self, mock_function_tool):
        """Test calculator tool creation."""
        # Create a mock tool object
        mock_tool = MagicMock()
        mock_function_tool.return_value = mock_tool
        
        # Reset the cache for testing
        import app.agents.agent_calculator_tool as calc_module
        calc_module._calculator_tool = None
        
        tool = get_calculator_tool()
        assert tool is mock_tool
        
        # Test that it returns the same cached instance
        tool2 = get_calculator_tool()
        assert tool is tool2
        
        # Verify function_tool was called once with calculate
        mock_function_tool.assert_called_once_with(AgentCalculatorTool.calculate)

    @patch('app.agents.agent_calculator_tool.function_tool')
    def test_get_interpreter_tool(self, mock_function_tool):
        """Test interpreter tool creation."""
        # Create a mock tool object
        mock_tool = MagicMock()
        mock_function_tool.return_value = mock_tool
        
        # Reset the cache for testing
        import app.agents.agent_calculator_tool as calc_module
        calc_module._interpreter_tool = None
        
        tool = get_interpreter_tool()
        assert tool is mock_tool
        
        # Test that it returns the same cached instance
        tool2 = get_interpreter_tool()
        assert tool is tool2
        
        # Verify function_tool was called once with interpret_calculation_results
        mock_function_tool.assert_called_once_with(AgentCalculatorTool.interpret_calculation_results)

    @patch('app.agents.agent_calculator_tool.function_tool')
    def test_tool_caching(self, mock_function_tool):
        """Test that tools are properly cached."""
        # Create unique mock tools
        mock_calc_tool = MagicMock()
        mock_interp_tool = MagicMock()
        
        # Configure mock to return different tools on consecutive calls
        mock_function_tool.side_effect = [mock_calc_tool, mock_interp_tool]
        
        # Reset the global cache
        import app.agents.agent_calculator_tool as calc_module
        calc_module._calculator_tool = None
        calc_module._interpreter_tool = None
        
        # Get tools
        calc_tool = get_calculator_tool()
        interp_tool = get_interpreter_tool()
        
        # Verify they're cached
        assert calc_module._calculator_tool is calc_tool
        assert calc_module._interpreter_tool is interp_tool
        
        # Get them again and verify same instances
        calc_tool2 = get_calculator_tool()
        interp_tool2 = get_interpreter_tool()
        
        assert calc_tool is calc_tool2
        assert interp_tool is interp_tool2
        
        # Verify function_tool was called exactly twice (once for each tool)
        assert mock_function_tool.call_count == 2


class TestAgentCalculatorToolIntegration:
    """Integration tests for AgentCalculatorTool with actual calculations."""

    @pytest.mark.asyncio
    async def test_full_calculation_workflow(self):
        """Test a complete calculation workflow."""
        # Create a mock context
        mock_context = MagicMock()
        
        # Step 1: Perform calculation
        calc_result = await AgentCalculatorTool.calculate(
            context=mock_context,
            operation_type="arithmetic",
            operation="add",
            values="[10, 20, 30]"
        )
        
        assert calc_result["result"] == 60
        
        # Step 2: Interpret results
        interpretation = await AgentCalculatorTool.interpret_calculation_results(
            context=mock_context,
            calculation_results=json.dumps(calc_result),
            interpretation_level="standard"
        )
        
        assert "interpretation" in interpretation
        assert "60" in interpretation["interpretation"]["summary"]

    @pytest.mark.asyncio
    async def test_complex_financial_workflow(self):
        """Test complex financial calculation workflow."""
        # Create a mock context
        mock_context = MagicMock()
        
        # Calculate loan payment
        loan_result = await AgentCalculatorTool.calculate(
            context=mock_context,
            operation_type="financial",
            operation="loan_payment",
            parameters="{\"principal\": 200000, \"rate\": 4.5, \"time\": 30}"
        )
        
        assert "monthly_payment" in loan_result
        assert loan_result["monthly_payment"] > 0
        
        # Interpret the results
        interpretation = await AgentCalculatorTool.interpret_calculation_results(
            context=mock_context,
            calculation_results=json.dumps(loan_result),
            interpretation_level="detailed"
        )
        
        assert "interpretation" in interpretation

    @pytest.mark.asyncio
    async def test_text_processing_workflow(self):
        """Test text processing with root phrases."""
        # Create a mock context
        mock_context = MagicMock()
        
        # Test the complete workflow from text to calculation
        original_text = "What is the square root of twenty five?"
        
        # Step 1: Normalize the text
        normalized = AgentCalculatorTool.normalize_root_phrases_to_expressions(original_text)
        assert "25" in normalized
        assert "evaluate" in normalized
        
        # Step 2: Extract the calculation (would normally be done by LLM)
        # For this test, we'll simulate the extraction
        calc_result = await AgentCalculatorTool.calculate(
            context=mock_context,
            operation_type="arithmetic",
            operation="root",
            values="[25, 2]"
        )
        
        assert calc_result["result"] == 5

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self):
        """Test error handling in the workflow."""
        # Create a mock context
        mock_context = MagicMock()
        
        # Test with invalid parameters
        calc_result = await AgentCalculatorTool.calculate(
            context=mock_context,
            operation_type="arithmetic",
            operation="divide",
            values="[10, 0]"
        )
        
        assert "error" in calc_result
        
        # Test interpretation of error
        interpretation = await AgentCalculatorTool.interpret_calculation_results(
            context=mock_context,
            calculation_results=json.dumps(calc_result)
        )
        
        assert "Error in calculation" in interpretation["interpretation"]


if __name__ == "__main__":
    pytest.main([__file__])
