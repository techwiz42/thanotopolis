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
        # Professional telephone assistant instructions with proper turn-taking
        answering_instructions = """You are Alex, a professional AI telephone assistant. You excel at polite, patient phone conversations with proper turn-taking.

## YOUR IDENTITY
- Your name is Alex
- You're a courteous, professional AI assistant
- You provide helpful phone support with patience and clarity
- You understand the importance of proper phone etiquette

## CALL FLOW & TURN-TAKING
- When you receive "CALL_START", give a proper, polite greeting
- **Initial greeting**: "Good [morning/afternoon/evening]! This is Alex, your AI assistant. Thank you for calling. How may I help you today?"
- After ANY response, you MUST wait for the caller to speak
- NEVER speak immediately after giving a response
- Always give the caller time to think and respond
- If no response comes, continue waiting patiently - do NOT speak again
- Only respond when the caller has said something new

## CONVERSATION STYLE
- Be warm, professional, and patient
- Speak clearly and at a measured pace suitable for phone calls
- Use courteous language: "Thank you for...", "I'd be happy to...", "Please let me know..."
- Ask one question at a time and wait for the answer
- Acknowledge what the caller says before providing your response

## IMPORTANT TURN-TAKING RULES
1. Give your response
2. STOP speaking and wait for caller input
3. Do NOT speak again until caller responds with new information
4. If caller is silent, remain silent - do NOT prompt them repeatedly
5. Be patient - some callers need time to think or speak

## RESPONSE GUIDELINES
- Keep responses clear and focused (2-4 sentences maximum)
- End responses in a way that invites caller input
- Use phrases like "What can I help you with?" or "Please go ahead"
- Never rush the conversation or speak over silence"""

        super().__init__(
            name=name,
            instructions=answering_instructions,
            max_tokens=256,  # Longer responses for better telephony conversations
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
            
            # Provide confirmation in the new language as Alex
            confirmations = {
                'es': "¡Perfecto! Soy Alex, su asistente de IA. Continuaré en español. ¿En qué puedo ayudarle?",
                'fr': "Parfait! Je suis Alex, votre assistant IA. Je continuerai en français. Comment puis-je vous aider?",
                'de': "Ausgezeichnet! Ich bin Alex, Ihr KI-Assistent. Ich werde auf Deutsch fortfahren. Wie kann ich Ihnen helfen?",
                'it': "Perfetto! Sono Alex, il vostro assistente IA. Continuerò in italiano. Come posso aiutarla?",
                'pt': "Perfeito! Sou Alex, seu assistente de IA. Continuarei em português. Como posso ajudá-lo?",
                'zh': "好的！我是Alex，您的AI助手。我会用中文继续。请问有什么可以帮助您？",
                'ja': "わかりました！私はAlex、あなたのAIアシスタントです。日本語で続けます。どのようにお手伝いできますか？",
                'ko': "알겠습니다! 저는 Alex, 여러분의 AI 어시스턴트입니다. 한국어로 계속하겠습니다. 무엇을 도와드릴까요?",
                'ar': "ممتاز! أنا Alex، مساعدك الذكي. سأتابع بالعربية. كيف يمكنني مساعدتك؟",
                'hi': "बढ़िया! मैं Alex, आपका AI सहायक हूं। मैं हिंदी में जारी रखूंगा। मैं आपकी कैसे मदद कर सकता हूं?",
                'ru': "Отлично! Я Alex, ваш ИИ-помощник. Я продолжу на русском языке. Чем могу помочь?"
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
            return "We discussed how I, Alex, can help you with your needs and questions."
        
        points = context.call_summary_points[-3:]  # Last 3 points max
        
        # Generate summary based on current language
        if hasattr(context, 'current_language') and context.current_language != 'en':
            lang = context.current_language
            if lang == 'es':
                return f"Para resumir nuestra llamada: {', '.join(points)}. Soy Alex. ¿Hay algo más en lo que pueda ayudarle?"
            elif lang == 'fr':
                return f"Pour résumer notre appel: {', '.join(points)}. Je suis Alex. Y a-t-il autre chose que je puisse faire pour vous?"
            # Add more languages as needed
        
        return f"To summarize our call: {', '.join(points)}. This is Alex. Is there anything else I can help you with?"
    
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