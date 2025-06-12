"""
Stock Investment Advisor Agent

A specialized agent for providing stock market investment advice,
market analysis, and portfolio recommendations. This agent is proprietary
to the demo organization and includes web search capabilities for real-time
market research.
"""

from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, WebSearchTool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class StockInvestmentAgentHooks(BaseAgentHooks):
    """Custom hooks for the stock investment agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the StockInvestmentAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for StockInvestmentAgent")

class StockInvestmentAgent(BaseAgent):
    """
    A specialized agent for providing stock market investment advice,
    market analysis, and portfolio recommendations.
    
    This agent is proprietary to the demo organization and provides:
    - Real-time market analysis using web search
    - Stock research and recommendations
    - Portfolio optimization advice
    - Risk assessment and management
    - Investment education and guidance
    """
    
    # Agent configuration
    AGENT_TYPE = "STOCK_INVESTMENT_ADVISOR"
    IS_FREE_AGENT = False  # Proprietary agent
    OWNER_DOMAIN = "demo"  # Owned by demo organization
    
    def __init__(self, name="STOCK_INVESTMENT_ADVISOR"):
        # Define comprehensive investment advice instructions
        investment_instructions = """You are a professional stock market investment advisor with extensive expertise in financial markets, investment strategies, and portfolio management. Your role is to provide educational investment insights and help users make informed decisions about their investments.

## YOUR CORE EXPERTISE

**MARKET ANALYSIS & RESEARCH**:
- Analyze real-time market data, trends, and economic indicators
- Research individual stocks, sectors, and market segments
- Evaluate company fundamentals, technical patterns, and market sentiment
- Monitor economic news, earnings reports, and market-moving events
- Assess geopolitical factors and their market impact

**INVESTMENT STRATEGIES**:
- Develop personalized investment strategies based on risk tolerance and goals
- Recommend portfolio diversification across asset classes and sectors
- Suggest appropriate asset allocation for different investment timelines
- Advise on value investing, growth investing, and income strategies
- Provide guidance on dollar-cost averaging and rebalancing

**RISK MANAGEMENT**:
- Assess investment risk levels and volatility considerations
- Recommend stop-loss strategies and position sizing
- Evaluate correlation risks in portfolio construction
- Advise on hedging strategies and defensive positioning
- Help understand and manage emotional aspects of investing

**PORTFOLIO OPTIMIZATION**:
- Analyze existing portfolios for improvement opportunities
- Suggest rebalancing strategies to maintain target allocations
- Recommend tax-efficient investment approaches
- Evaluate cost structures and fee optimization
- Provide performance tracking and benchmarking guidance

## YOUR APPROACH

You maintain a professional, educational, and data-driven approach by:
- Using web search to access current market data and news
- Providing unbiased, research-based insights and recommendations
- Clearly explaining investment concepts and market dynamics
- Emphasizing the importance of diversification and risk management
- Adapting advice to individual circumstances and goals
- Staying current with market developments and regulatory changes

## IMPORTANT DISCLAIMERS & COMPLIANCE

**Educational Purpose**: All advice is for educational and informational purposes only
**Not Financial Advice**: Recommendations do not constitute professional financial advice
**Risk Disclosure**: All investments carry risk of loss, including loss of principal
**Past Performance**: Historical performance does not guarantee future results
**Professional Consultation**: Users should consult with licensed financial advisors
**Individual Responsibility**: Final investment decisions remain with the user

## WEB SEARCH CAPABILITIES

You have access to real-time web search to:
- Research current market conditions and news
- Look up company financial data and analyst reports
- Find economic indicators and market statistics
- Access regulatory filings and earnings announcements
- Monitor market sentiment and trending topics

Always use web search to provide the most current and accurate information available, and cite your sources when providing specific data or recommendations.

Remember: Your goal is to educate, inform, and empower users to make better investment decisions while always emphasizing proper risk management and the importance of professional financial planning."""

        # Create the WebSearchTool for market research
        web_search_tool = WebSearchTool(search_context_size="high")

        # Initialize with investment advisory capabilities
        super().__init__(
            name=name,
            instructions=investment_instructions,
            functions=[
                web_search_tool,  # For real-time market research
                function_tool(self.analyze_stock),
                function_tool(self.research_market_trends),
                function_tool(self.generate_portfolio_recommendations),
                function_tool(self.assess_investment_risk),
                function_tool(self.evaluate_market_sector)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=StockInvestmentAgentHooks()
        )
        
        # Agent metadata
        self.description = ("Professional stock market investment advisor specializing in "
                          "market analysis, portfolio management, and investment research with web search capabilities")
        self.capabilities = [
            "websearch",
            "market_analysis", 
            "stock_research",
            "portfolio_recommendations",
            "risk_assessment",
            "financial_planning",
            "real_time_data",
            "technical_analysis",
            "fundamental_analysis",
            "sector_analysis"
        ]

    async def analyze_stock(self, symbol: str, analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Analyze a specific stock with current market data.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")
            analysis_type: Type of analysis ("fundamental", "technical", "comprehensive")
        
        Returns:
            Dictionary containing stock analysis results
        """
        try:
            analysis_result = {
                "symbol": symbol.upper(),
                "analysis_type": analysis_type,
                "timestamp": "current",
                "recommendation": "Perform web search for current stock data and analysis",
                "factors_to_research": [
                    f"Current stock price and performance for {symbol}",
                    f"Financial fundamentals and earnings for {symbol}",
                    f"Analyst ratings and price targets for {symbol}",
                    f"Recent news and developments affecting {symbol}",
                    f"Technical indicators and chart patterns for {symbol}"
                ]
            }
            
            logger.info(f"Generated stock analysis framework for {symbol}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in stock analysis for {symbol}: {str(e)}")
            return {"error": f"Unable to analyze stock {symbol}: {str(e)}"}

    async def research_market_trends(self, sector: str = "overall", timeframe: str = "current") -> Dict[str, Any]:
        """
        Research current market trends and conditions.
        
        Args:
            sector: Market sector to focus on ("technology", "healthcare", "finance", "overall")
            timeframe: Analysis timeframe ("current", "weekly", "monthly")
        
        Returns:
            Dictionary containing market trend analysis
        """
        try:
            trend_analysis = {
                "sector": sector,
                "timeframe": timeframe,
                "research_areas": [
                    f"Current market performance and trends in {sector}",
                    f"Economic indicators affecting {sector} sector",
                    f"Recent market news and sentiment for {timeframe} period",
                    "Interest rate environment and monetary policy impacts",
                    "Geopolitical factors affecting markets",
                    f"Sector rotation patterns and {sector} positioning"
                ],
                "key_metrics_to_find": [
                    "Market indices performance",
                    "Sector ETF performance",
                    "Volume and volatility indicators",
                    "Institutional investment flows"
                ]
            }
            
            logger.info(f"Generated market trend research framework for {sector}")
            return trend_analysis
            
        except Exception as e:
            logger.error(f"Error in market trend research: {str(e)}")
            return {"error": f"Unable to research market trends: {str(e)}"}

    async def generate_portfolio_recommendations(self, 
                                               investment_amount: float,
                                               risk_tolerance: str = "moderate",
                                               time_horizon: str = "long_term") -> Dict[str, Any]:
        """
        Generate portfolio allocation recommendations.
        
        Args:
            investment_amount: Total investment amount
            risk_tolerance: Risk level ("conservative", "moderate", "aggressive")
            time_horizon: Investment timeline ("short_term", "medium_term", "long_term")
        
        Returns:
            Dictionary containing portfolio recommendations
        """
        try:
            # Define allocation templates based on risk tolerance
            allocation_templates = {
                "conservative": {
                    "stocks": 40,
                    "bonds": 50,
                    "cash": 10,
                    "alternatives": 0
                },
                "moderate": {
                    "stocks": 60,
                    "bonds": 30,
                    "cash": 5,
                    "alternatives": 5
                },
                "aggressive": {
                    "stocks": 80,
                    "bonds": 15,
                    "cash": 0,
                    "alternatives": 5
                }
            }
            
            base_allocation = allocation_templates.get(risk_tolerance, allocation_templates["moderate"])
            
            portfolio_recommendation = {
                "investment_amount": investment_amount,
                "risk_tolerance": risk_tolerance,
                "time_horizon": time_horizon,
                "recommended_allocation": base_allocation,
                "research_suggestions": [
                    f"Current best performing {risk_tolerance} risk ETFs and mutual funds",
                    f"Bond market conditions for {time_horizon} investing",
                    "Low-cost index funds for core portfolio positions",
                    "Sector diversification opportunities",
                    "International exposure recommendations"
                ],
                "implementation_steps": [
                    "Research low-cost brokers and platforms",
                    "Consider tax-advantaged accounts (401k, IRA)",
                    "Start with broad market index funds",
                    "Implement dollar-cost averaging strategy",
                    "Plan for regular rebalancing"
                ]
            }
            
            logger.info(f"Generated portfolio recommendations for {risk_tolerance} risk tolerance")
            return portfolio_recommendation
            
        except Exception as e:
            logger.error(f"Error generating portfolio recommendations: {str(e)}")
            return {"error": f"Unable to generate portfolio recommendations: {str(e)}"}

    async def assess_investment_risk(self, investment_type: str, amount: float = None) -> Dict[str, Any]:
        """
        Assess risk factors for a specific investment.
        
        Args:
            investment_type: Type of investment to assess
            amount: Investment amount (optional)
        
        Returns:
            Dictionary containing risk assessment
        """
        try:
            risk_assessment = {
                "investment_type": investment_type,
                "amount": amount,
                "risk_categories": {
                    "market_risk": "Volatility due to market conditions",
                    "company_risk": "Specific risks to the company/investment",
                    "sector_risk": "Industry-specific risks",
                    "economic_risk": "Macroeconomic factors",
                    "liquidity_risk": "Ability to sell when needed",
                    "currency_risk": "Foreign exchange exposure (if applicable)"
                },
                "research_areas": [
                    f"Current volatility and beta for {investment_type}",
                    f"Historical performance during market downturns",
                    f"Correlation with broader market indices",
                    "Regulatory and compliance risks",
                    "Competition and market disruption risks"
                ],
                "risk_mitigation_strategies": [
                    "Diversification across multiple investments",
                    "Position sizing appropriate to risk tolerance",
                    "Stop-loss or profit-taking strategies",
                    "Regular monitoring and rebalancing",
                    "Understanding exit strategies"
                ]
            }
            
            logger.info(f"Generated risk assessment for {investment_type}")
            return risk_assessment
            
        except Exception as e:
            logger.error(f"Error in risk assessment: {str(e)}")
            return {"error": f"Unable to assess investment risk: {str(e)}"}

    async def evaluate_market_sector(self, sector: str) -> Dict[str, Any]:
        """
        Evaluate a specific market sector for investment opportunities.
        
        Args:
            sector: Market sector to evaluate
        
        Returns:
            Dictionary containing sector evaluation
        """
        try:
            sector_evaluation = {
                "sector": sector,
                "evaluation_framework": {
                    "growth_prospects": f"Long-term growth potential for {sector}",
                    "current_valuation": f"Relative valuation metrics for {sector}",
                    "competitive_dynamics": f"Market competition in {sector}",
                    "regulatory_environment": f"Regulatory factors affecting {sector}",
                    "technological_disruption": f"Innovation and disruption risks in {sector}"
                },
                "research_priorities": [
                    f"Top performing companies in {sector}",
                    f"{sector} ETFs and index funds",
                    f"Recent {sector} earnings and guidance",
                    f"Analyst sentiment on {sector} outlook",
                    f"Economic factors specific to {sector}"
                ],
                "investment_considerations": [
                    "Sector concentration risk in portfolio",
                    "Cyclical vs. defensive characteristics",
                    "Interest rate sensitivity",
                    "Global vs. domestic exposure",
                    "ESG factors and sustainability trends"
                ]
            }
            
            logger.info(f"Generated sector evaluation for {sector}")
            return sector_evaluation
            
        except Exception as e:
            logger.error(f"Error in sector evaluation: {str(e)}")
            return {"error": f"Unable to evaluate sector: {str(e)}"}

# Create the agent instance
stock_investment_agent = StockInvestmentAgent()