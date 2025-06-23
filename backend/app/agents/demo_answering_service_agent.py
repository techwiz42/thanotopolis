"""
Demo Answering Service Agent - A specialized telephone receptionist for the demo organization.
This agent handles incoming calls with web search capabilities and multi-language support.
"""
from typing import Dict, Any, Optional, List
import logging
import json
from datetime import datetime
from agents import function_tool, RunContextWrapper, WebSearchTool
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class DemoAnsweringServiceAgentHooks(BaseAgentHooks):
    """Custom hooks for the Demo Answering Service Agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the Demo Answering Service Agent."""
        await super().init_context(context)
        # Initialize call tracking
        if not hasattr(context, 'call_summary_points'):
            context.call_summary_points = []
        if not hasattr(context, 'current_language'):
            context.current_language = 'en'
        logger.info("Initialized Demo Answering Service Agent context")

class DemoAnsweringServiceAgent(BaseAgent):
    """
    Specialized telephone answering agent for the Demo organization.
    Handles incoming calls with friendliness, curiosity, and efficiency.
    """
    
    # Proprietary to demo organization only
    OWNER_DOMAINS = ["demo"]
    
    # Mark as telephony-only agent
    TELEPHONY_ONLY = True
    
    def __init__(self, name="DEMO_ANSWERING_SERVICE"):
        # Brief, conversational instructions optimized for voice interaction
        answering_instructions = """You are Barney, a friendly AI telephone receptionist working for Cyberiad.ai, the agentic framework organization. You're currently helping with the Demo organization's calls. Keep responses BRIEF and conversational for phone calls.

## YOUR IDENTITY
- Your name is Barney
- You work for Cyberiad.ai, a company that creates agentic AI frameworks
- You're helping the Demo organization with their telephone support
- You're enthusiastic about AI technology but keep explanations simple

## CORE BEHAVIORS
- Introduce yourself by name: "Hi! This is Barney from Cyberiad.ai"
- Be curious about their needs without being intrusive
- Speak naturally, as if in a phone conversation
- Keep responses under 2-3 sentences for low latency
- Offer language switching early in the conversation

## SPECIAL HANDLING
- When you receive "CALL_START", immediately respond with your initial greeting
- Initial greeting should be: "Hello! This is Barney from Cyberiad.ai. I'm helping with the Demo organization's calls today. How can I assist you?"

## KEY RESPONSIBILITIES
1. **Initial Greeting**: "Hello! This is Barney from Cyberiad.ai. I'm helping with Demo's calls today. How can I assist you?"
2. **Language Check**: After initial exchange, ask: "I'm currently speaking in English. Would you prefer another language?"
3. **Understand Needs**: Ask clarifying questions to understand what the caller wants
4. **Explain Our Technology**: When relevant, explain Cyberiad.ai's agentic framework and how it helps organizations
5. **Collaborate**: Connect callers with specialized agents when needed
6. **Summarize**: At call end, provide a brief summary of key points

## ABOUT CYBERIAD.AI & OUR PLATFORM
- Cyberiad.ai creates advanced agentic AI frameworks
- Our platform provides multi-agent AI systems with specialized experts
- Fully customizable for any industry or use case  
- Integrates seamlessly with existing phone systems and workflows
- Supports multiple languages and 24/7 availability
- Agents can collaborate to handle complex queries
- Organizations can have their own proprietary agents alongside free agents

## CONVERSATION STYLE
- Use natural speech patterns: "Sure!", "Absolutely!", "I'd be happy to help"
- Acknowledge what you hear: "I understand you're looking for..."
- Be enthusiastic but professional - show pride in Cyberiad.ai's technology
- Use the caller's name if provided
- Reference yourself as "Barney" when appropriate

## IMPORTANT REMINDERS
- This is a PHONE CALL - keep it conversational
- Brevity is key - long responses frustrate callers
- Always introduce yourself as Barney from Cyberiad.ai
- Always track main points for the summary
- Switch languages smoothly when requested"""

        super().__init__(
            name=name,
            instructions=answering_instructions,
            max_tokens=150,  # Keep responses short for low latency
            tool_choice="auto",
            parallel_tool_calls=True,
            hooks=DemoAnsweringServiceAgentHooks()
        )
        
        # Initialize web search tool
        try:
            self.web_search_tool = WebSearchTool(
                search_context_size="low"  # Low for quick responses
            )
            self.tools.append(self.web_search_tool)
        except Exception as e:
            logger.warning(f"Could not initialize WebSearchTool: {e}")
        
        # Initialize other tools
        self.tools.extend([
            self.track_conversation_point,
            self.switch_language,
            self.generate_call_summary
        ])
    
    @function_tool
    async def track_conversation_point(
        context: RunContextWrapper[Any],
        point: str
    ) -> str:
        """
        Track important points from the conversation for the final summary.
        
        Args:
            point: Key point to remember
            
        Returns:
            Confirmation
        """
        if not hasattr(context, 'call_summary_points'):
            context.call_summary_points = []
        
        context.call_summary_points.append(point)
        return f"Noted: {point}"
    
    @function_tool
    async def switch_language(
        context: RunContextWrapper[Any],
        language_code: str
    ) -> str:
        """
        Switch the conversation to a different language.
        
        Args:
            language_code: Language code (e.g., 'es' for Spanish, 'fr' for French)
            
        Returns:
            Confirmation in the new language
        """
        language_map = {
            'es': 'Spanish',
            'fr': 'French', 
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'ru': 'Russian'
        }
        
        if language_code in language_map:
            context.current_language = language_code
            
            # Provide confirmation in the new language with Barney's identity
            confirmations = {
                'es': "¡Perfecto! Soy Barney de Cyberiad.ai. Continuaré en español. ¿En qué puedo ayudarle?",
                'fr': "Parfait! Je suis Barney de Cyberiad.ai. Je continuerai en français. Comment puis-je vous aider?",
                'de': "Ausgezeichnet! Ich bin Barney von Cyberiad.ai. Ich werde auf Deutsch fortfahren. Wie kann ich Ihnen helfen?",
                'it': "Perfetto! Sono Barney di Cyberiad.ai. Continuerò in italiano. Come posso aiutarla?",
                'pt': "Perfeito! Sou Barney da Cyberiad.ai. Continuarei em português. Como posso ajudá-lo?",
                'zh': "好的！我是Cyberiad.ai的Barney。我会用中文继续。请问有什么可以帮助您？",
                'ja': "わかりました！私はCyberiad.aiのBarneyです。日本語で続けます。どのようにお手伝いできますか？",
                'ko': "알겠습니다! 저는 Cyberiad.ai의 Barney입니다. 한국어로 계속하겠습니다. 무엇을 도와드릴까요?",
                'ar': "ممتاز! أنا بارني من Cyberiad.ai. سأتابع بالعربية. كيف يمكنني مساعدتك؟",
                'hi': "बढ़िया! मैं Cyberiad.ai का Barney हूं। मैं हिंदी में जारी रखूंगा। मैं आपकी कैसे मदद कर सकता हूं?",
                'ru': "Отлично! Я Барни из Cyberiad.ai. Я продолжу на русском языке. Чем могу помочь?"
            }
            
            return confirmations.get(language_code, f"Switched to {language_map[language_code]}")
        else:
            return "I'm not familiar with that language code. I can speak Spanish (es), French (fr), German (de), Italian (it), Portuguese (pt), Chinese (zh), Japanese (ja), Korean (ko), Arabic (ar), Hindi (hi), or Russian (ru)."
    
    @function_tool
    async def generate_call_summary(
        context: RunContextWrapper[Any]
    ) -> str:
        """
        Generate a brief summary of the call's main points.
        
        Returns:
            Brief summary of the conversation
        """
        if not hasattr(context, 'call_summary_points') or not context.call_summary_points:
            return "We discussed how I, Barney from Cyberiad.ai, can help you with the Demo organization's services and our agentic AI framework."
        
        points = context.call_summary_points[-3:]  # Last 3 points max
        
        # Generate summary based on current language
        if hasattr(context, 'current_language') and context.current_language != 'en':
            lang = context.current_language
            if lang == 'es':
                return f"Para resumir nuestra llamada: {', '.join(points)}. Soy Barney de Cyberiad.ai. ¿Hay algo más en lo que pueda ayudarle?"
            elif lang == 'fr':
                return f"Pour résumer notre appel: {', '.join(points)}. Je suis Barney de Cyberiad.ai. Y a-t-il autre chose que je puisse faire pour vous?"
            # Add more languages as needed
        
        return f"To summarize our call: {', '.join(points)}. This is Barney from Cyberiad.ai. Is there anything else I can help you with?"
    
    def get_handoff_agent(self, query: str) -> Optional[str]:
        """Determine if the query should be handed off to a specialist agent."""
        query_lower = query.lower()
        
        # Quick keyword matching for handoffs
        if any(word in query_lower for word in ['payment', 'cost', 'price', 'insurance', 'billing']):
            return 'FINANCIAL_SERVICES'
        elif any(word in query_lower for word in ['inventory', 'facilities', 'equipment', 'supplies']):
            return 'INVENTORY'
        elif any(word in query_lower for word in ['compliance', 'regulation', 'legal', 'documentation']):
            return 'COMPLIANCE'
        elif any(word in query_lower for word in ['emergency', 'urgent', 'crisis', 'immediate']):
            return 'EMERGENCY'
        
        return None


# Create singleton instance
demo_answering_service_agent = DemoAnsweringServiceAgent()

# Export for discovery
__all__ = ["demo_answering_service_agent", "DemoAnsweringServiceAgent"]