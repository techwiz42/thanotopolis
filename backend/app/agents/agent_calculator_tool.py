from typing import Dict, Any, List, Optional, Union
import logging
from app.core.common_calculator import CalculatorUtility
from agents import function_tool, RunContextWrapper
from agents.run_context import RunContextWrapper
import inspect
from typing_extensions import get_type_hints
import traceback
import re

logger = logging.getLogger(__name__)

class AgentCalculatorTool:
    """
    A tool class that integrates the CalculatorUtility with the agent framework.
    This provides all agents with access to robust calculation capabilities.
    """
    @staticmethod
    def _replace_number_words_with_digits(text: str) -> str:
        """
        Converts number words (including ordinals) into digits.
        E.g. "ninth root of fourteen" → "9th root of 14"
        """
        WORDS_TO_NUM = {
            "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
            "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
            "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
            "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
            "ninety": 90, "hundred": 100, "thousand": 1000, "million": 1_000_000
        }

        ORDINALS = {
            "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
            "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
            "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
            "fifteenth": 15, "sixteenth": 16, "seventeenth": 17,
            "eighteenth": 18, "nineteenth": 19, "twentieth": 20,
            "twenty-first": 21, "twenty-second": 22, "twenty-third": 23,
            "twenty-fourth": 24, "twenty-fifth": 25
        }

        # Replace simple ordinal words
        for word, num in ORDINALS.items():
            text = re.sub(rf"\b{word}\b", str(num), text, flags=re.IGNORECASE)

        # Replace cardinal number sequences (basic)
        def convert_cardinals(match):
            words = match.group(0).lower().replace('-', ' ').split()
            total = 0
            current = 0
            for word in words:
                val = WORDS_TO_NUM.get(word)
                if val == 100:
                    current *= 100
                elif val == 1000 or val == 1_000_000:
                    current *= val
                    total += current
                    current = 0
                elif val is not None:
                    current += val
            return str(total + current)

        pattern = r'\b(?:' + '|'.join(WORDS_TO_NUM.keys()) + r')(?:[\s-](?:' + '|'.join(WORDS_TO_NUM.keys()) + r'))*\b'
        return re.sub(pattern, convert_cardinals, text, flags=re.IGNORECASE)


    @staticmethod
    def normalize_root_phrases_to_expressions(prompt: str) -> str:
        """
        Convert natural language root phrases to mathematical expressions.
        
        Args:
            prompt: The input text containing natural language math expressions
            
        Returns:
            String with root expressions converted to mathematical notation
        """
        # Create a temporary instance to use instance methods
        calculator = AgentCalculatorTool()
        normalized_prompt = calculator._replace_number_words_with_digits(prompt)
        replacements = [
            (r"(?:the )?cube root of (\d+(?:\.\d+)?)", r"evaluate \1**(1/3)"),
            (r"(?:the )?third root of (\d+(?:\.\d+)?)", r"evaluate \1**(1/3)"),
            (r"(?:the )?square root of (\d+(?:\.\d+)?)", r"evaluate \1**(1/2)"),
            (r"(?:the )?second root of (\d+(?:\.\d+)?)", r"evaluate \1**(1/2)"),
            (r"find the (\d+)(?:st|nd|rd|th) root of (\d+(?:\.\d+)?)", r"raise \2 to the 1/\1 power"),
            (r"(?:the )?(\d+)[a-z]{2} root of (\d+(?:\.\d+)?)", r"raise \2 to the 1/\1 power"),
        ]
        for pattern, replacement in replacements:
            normalized_prompt = re.sub(pattern, replacement, normalized_prompt, flags=re.IGNORECASE)

        return normalized_prompt

    @staticmethod
    async def calculate(
        operation_type: Optional[str] = None,
        operation: Optional[str] = None,
        expression: Optional[str] = None,
        values: Optional[List[Union[int, float]]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Performs a wide range of calculations. Supports the following operation types:

    - Arithmetic: add, subtract, multiply, divide, power (e.g., 2^3), root (e.g., square root of 16), 
      and evaluate mathematical expressions like '2 + 3 * 4'. For root, 'n' defaults to 2 unless specified.

    - Statistical: compute mean, median, mode, standard deviation, variance, and summary stats.

    - Financial: calculate compound interest, loan payments, ROI. Requires 'principal', 'rate', 'time', etc.

    - Health: compute BMI, BMR, caloric needs. Parameters may include 'height', 'weight', 'age', 'sex'.

    - Business: calculate break-even points, profit margins, markups. Use 'fixed_costs', 'unit_price', etc.

    Use this tool for structured or quantitative analysis queries.
        Args:
            operation_type: The type of operation ("arithmetic", "statistical", "financial", "health", "business").
            operation: The specific operation to perform.
            expression: A mathematical expression to evaluate (for arithmetic operations).
            values: List of numeric values for calculations.
            parameters: Dictionary of parameters for the calculation.
                
        Returns:
            Dictionary containing the calculation results.
        """
        # Required parameters with validation
        if operation_type is None:
            return {"error": "Operation type is required"}
        if operation is None:
            return {"error": "Operation is required"}
        
        # Handle optional parameters
        if values is None:
            values = []
        if expression is None:
            expression = ""
        if parameters is None:
            parameters = {}
            
        # Only add expression to parameters if it has a value
        if expression:
            parameters["expression"] = expression
                
        logger.info(f"Performing {operation_type} calculation: {operation} with parameters: {parameters}")
        
        try:
            # Delegate to the appropriate method based on operation type
            if operation_type == "arithmetic":
                normalized_op = {
                    "add": "add", "addition": "add", "sum": "add", "total": "add",
                    "subtract": "subtract", "difference": "subtract",
                    "multiply": "multiply", "multiplication": "multiply", "product": "multiply", "times": "multiply",
                    "divide": "divide", "division": "divide", "quotient": "divide", "fraction": "divide",
                    # Power operations
                    "power": "power", "exponent": "power", "raised": "power", "raise": "power",
                    # Root operations
                    "root": "root", "sqrt": "root", "square root": "root", "square_root": "root", "cube root": "root",
                   # Evaluate expressions
                   "eval": "evaluate", "evaluate": "evaluate", "calculation": "evaluate", "compute": "evaluate", "expression": "evaluate",
                }.get(operation.lower())
                if normalized_op in ["add", "subtract", "multiply", "divide"]:
                    # These operations expect values
                    if not values:
                        return {"error": f"{operation} requires numeric values"}
                    return CalculatorUtility.basic_arithmetic(operation, values, parameters)
                elif operation == "power":
                    # For power operation
                    base = None
                    exponent = None
                    if len(values) == 2:
                        base = values[0]
                        exponent = values[1]
                    elif parameters.get("base", None) and parameters.get("exponent", None):
                        base = parameters.get("base")
                        exponent = parameters.get("exponent")
                    if base is None or exponent is None:
                        return {"error": "Power operation requires 'base' and 'exponent' parameters"}
                    power_params = {"base": base, "exponent": exponent}
                    return CalculatorUtility.basic_arithmetic("power", [1], power_params)
                elif operation == "root":
                    # For root operation
                    if len(values) == 2:
                        value = values[0]
                        n = values[1]
                    elif len(values) == 1:
                        value = values[0]
                        n = 2
                    else:
                        value = parameters.get("value")
                        n = parameters.get("n", 2)  # Default to square root
                    if value is None:
                        return {"error": "Root operation requires 'value' parameter"}
                    root_params = {"value": value, "n": n}
                    return CalculatorUtility.basic_arithmetic("root", [1], root_params)
                elif operation == "evaluate" and expression:
                    # For direct expression evaluation
                    return CalculatorUtility.basic_arithmetic("evaluate", [], parameters)
                else:
                    return {"error": f"Unsupported arithmetic operation: {operation}"}
            
            elif operation_type == "statistical":
                if not values:
                    return {"error": f"Statistical operations require numeric values"}
                # Pass values positionally, but parameters as a dictionary
                return CalculatorUtility.statistical_operations(operation, values, parameters)
            
            elif operation_type == "financial":
                # Financial calculations don't need values in parameters
                return CalculatorUtility.financial_calculations(operation, parameters)
            
            elif operation_type == "health":
                # Health metrics don't need values in parameters
                return CalculatorUtility.health_metrics(operation, parameters)
            
            elif operation_type == "business":
                # Business metrics don't need values in parameters
                return CalculatorUtility.business_metrics(operation, parameters)
            
            else:
                return {"error": f"Unsupported operation type: {operation_type}"}
        
        except Exception as e:
            logger.error(f"Error in calculator tool: {str(e)}", exc_info=True)
            traceback.print_exc()
            return {"error": f"Calculation error: {str(e)}"}
    
    @staticmethod
    async def interpret_calculation_results(
        calculation_results: Optional[Dict[str, Any]] = None,
        interpretation_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Interpret calculation results in a human-friendly way.
        
        Args:
            calculation_results: The results from a calculation.
            interpretation_level: Level of detail for interpretation ("basic", "standard", "detailed").
                
        Returns:
            Dictionary containing the interpreted results.
        """
        # Handle default values
        if calculation_results is None:
            calculation_results = {}
        if interpretation_level is None:
            interpretation_level = "standard"
        if "error" in calculation_results:
            return {"interpretation": f"Error in calculation: {calculation_results['error']}"}
        
        # Create a basic interpretation structure
        interpretation = {
            "summary": "Results of the calculation.",
            "key_findings": [],
            "recommendations": []
        }
        
        # Analyze the calculation results to provide meaningful interpretation
        
        # Extract main result value if present
        main_result = None
        if "result" in calculation_results:
            main_result = calculation_results["result"]
            interpretation["summary"] = f"The calculation resulted in {main_result}."
        
        # Interpret financial calculations
        if "final_amount" in calculation_results:
            interpretation["summary"] = f"The investment grows to {calculation_results['final_amount']:,.2f}."
            interpretation["key_findings"].append(
                f"Total interest/growth: {calculation_results.get('interest_earned', 0):,.2f}"
            )
        
        # Interpret statistical calculations
        if "mean" in calculation_results:
            interpretation["key_findings"].append(f"Average (mean) value: {calculation_results['mean']:,.2f}")
        
        if "correlation" in calculation_results:
            corr = calculation_results["correlation"]
            if corr > 0.7:
                strength = "strong positive"
            elif corr > 0.3:
                strength = "moderate positive"
            elif corr > -0.3:
                strength = "weak or no"
            elif corr > -0.7:
                strength = "moderate negative"
            else:
                strength = "strong negative"
            interpretation["key_findings"].append(f"There is a {strength} correlation of {corr:.2f}.")
        
        # Interpret health metrics
        if "bmi" in calculation_results:
            bmi = calculation_results["bmi"]
            category = calculation_results.get("category", "")
            interpretation["summary"] = f"BMI is {bmi:.1f}, categorized as {category}."
            
            if category == "Underweight":
                interpretation["recommendations"].append("Consider consulting a healthcare provider about healthy weight gain strategies.")
            elif category == "Overweight" or category == "Obese":
                interpretation["recommendations"].append("Consider consulting a healthcare provider about healthy weight management strategies.")
        
        # Interpret business metrics
        if "profit_margin" in calculation_results or "net_profit_margin" in calculation_results:
            margin = calculation_results.get("profit_margin", calculation_results.get("net_profit_margin", 0))
            interpretation["summary"] = f"Profit margin is {margin:.2f}%."
            
            if margin < 0:
                interpretation["key_findings"].append("The business is operating at a loss.")
                interpretation["recommendations"].append("Urgent action needed to reduce costs or increase revenue.")
            elif margin < 10:
                interpretation["key_findings"].append("Profit margin is relatively low.")
                interpretation["recommendations"].append("Consider strategies to improve margins by reducing costs or increasing prices.")
            elif margin > 20:
                interpretation["key_findings"].append("Profit margin is healthy.")
                interpretation["recommendations"].append("Focus on maintaining competitive advantage and growth opportunities.")
        
        if "break_even_units" in calculation_results:
            be_units = calculation_results["break_even_units"]
            be_revenue = calculation_results.get("break_even_revenue", 0)
            interpretation["summary"] = f"Break-even point is {be_units:.1f} units (${be_revenue:,.2f} revenue)."
            interpretation["key_findings"].append(f"The business needs to sell at least {be_units:.1f} units to cover fixed costs.")
        
        # Adjust detail level based on requested interpretation_level
        if interpretation_level == "basic":
            # Simplify to just summary
            return {"interpretation": interpretation["summary"]}
        elif interpretation_level == "detailed":
            # Add calculation steps if available
            if "calculation_steps" in calculation_results:
                interpretation["calculation_steps"] = calculation_results["calculation_steps"]
            # Add all parameters used
            if "parameters" in calculation_results:
                interpretation["parameters_used"] = calculation_results["parameters"]
        
        return {"interpretation": interpretation}


# Create patched tool functions
_calculator_tool = None
_interpreter_tool = None

def get_calculator_tool():
    """
    Create and return the calculator tool for use in agents.
    
    Returns:
        The calculator function tool.
    """
    global _calculator_tool
    
    # Return cached version if already created
    if _calculator_tool is not None:
        return _calculator_tool
    
    calculator_tool = AgentCalculatorTool()
    # Create the function tool - will automatically await since calculate is async
    tool = function_tool(calculator_tool.calculate)
    
    # Cache the fixed tool
    _calculator_tool = tool
    return tool

def get_interpreter_tool():
    """
    Create and return the result interpreter tool for use in agents.
    
    Returns:
        The interpreter function tool.
    """
    global _interpreter_tool
    
    # Return cached version if already created
    if _interpreter_tool is not None:
        return _interpreter_tool
    
    calculator_tool = AgentCalculatorTool()
    # Create the function tool - will automatically await since interpret_calculation_results is async
    tool = function_tool(calculator_tool.interpret_calculation_results)
    
    # Cache the fixed tool
    _interpreter_tool = tool
    return tool
