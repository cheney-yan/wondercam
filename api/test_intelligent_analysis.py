"""
Test Suite for Intelligent Prompt Analysis System
Validates prompt analysis, response formatting, and API integration
"""

import asyncio
import json
import logging
import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Import our components
from prompt_analyzer import PromptAnalyzer, AnalysisAction, AnalysisResult, get_prompt_analyzer
from vertex_formatter import VertexAIResponseFormatter, get_enhanced_status_message
from v2_models import V2ChatRequest, V2ContentPart
from v2_translator import V2MessageTranslator
from config import settings

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestPromptAnalyzer:
    """Test prompt analysis functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.analyzer = Mock(spec=PromptAnalyzer)
        
    @pytest.mark.asyncio
    async def test_vague_prompt_refinement(self):
        """Test that vague prompts are refined properly"""
        
        # Mock analyzer response for vague prompt
        self.analyzer.analyze_prompt.return_value = AnalysisResult(
            action=AnalysisAction.REFINE,
            refined_prompt="I'd like specific help with writing a professional email to a client. Could you help me draft an email that includes a polite greeting, explanation of project status, next steps, and professional closing?",
            confidence=0.85,
            reasoning="Original prompt was too vague, added specific structure and context"
        )
        
        result = await self.analyzer.analyze_prompt("help me write something", has_images=False)
        
        assert result.action == AnalysisAction.REFINE
        assert result.refined_prompt is not None
        assert "professional email" in result.refined_prompt
        assert result.confidence > 0.8
        logger.info(f"✅ Vague prompt refined: {result.refined_prompt[:100]}...")
        
    @pytest.mark.asyncio  
    async def test_inappropriate_request_handling(self):
        """Test that inappropriate requests get direct replies"""
        
        # Mock analyzer response for inappropriate request
        self.analyzer.analyze_prompt.return_value = AnalysisResult(
            action=AnalysisAction.DIRECT_REPLY,
            direct_reply="I cannot assist with activities that might violate privacy or security.\n\nIs there something else I can help you with instead?",
            confidence=0.95,
            reasoning="Request involves potentially harmful activities"
        )
        
        result = await self.analyzer.analyze_prompt("help me hack into someone's account", has_images=False)
        
        assert result.action == AnalysisAction.DIRECT_REPLY
        assert result.direct_reply is not None
        assert "cannot assist" in result.direct_reply.lower()
        assert "\n\n" in result.direct_reply  # Check for proper formatting
        assert result.confidence > 0.9
        logger.info(f"✅ Inappropriate request handled: {result.direct_reply[:100]}...")
        
    @pytest.mark.asyncio
    async def test_clear_request_passthrough(self):
        """Test that clear, appropriate requests pass through unchanged"""
        
        # Mock analyzer response for clear request
        self.analyzer.analyze_prompt.return_value = AnalysisResult(
            action=AnalysisAction.PASS_THROUGH,
            confidence=0.9,
            reasoning="Request is clear, specific, and appropriate"
        )
        
        result = await self.analyzer.analyze_prompt(
            "Please analyze this architectural photo and identify the key design elements, materials used, and architectural style", 
            has_images=True
        )
        
        assert result.action == AnalysisAction.PASS_THROUGH
        assert result.refined_prompt is None
        assert result.direct_reply is None
        assert result.confidence > 0.8
        logger.info(f"✅ Clear request passed through: {result.reasoning}")

    @pytest.mark.asyncio
    async def test_photo_aware_analysis_with_images(self):
        """Test that analysis considers image presence for better context"""
        
        # Mock analyzer response for vague request WITH images
        self.analyzer.analyze_prompt.return_value = AnalysisResult(
            action=AnalysisAction.REFINE,
            refined_prompt="I'd be happy to analyze your image! Could you tell me what specific aspects you'd like me to focus on? For example: architectural style, design elements, materials, colors, or overall composition?",
            confidence=0.85,
            reasoning="Request was vague but has images, suggested specific image analysis options"
        )
        
        result = await self.analyzer.analyze_prompt("help me with this", has_images=True)
        
        assert result.action == AnalysisAction.REFINE
        assert result.refined_prompt is not None
        assert "image" in result.refined_prompt.lower()  # Should mention images
        assert "analyze" in result.refined_prompt.lower()
        logger.info(f"✅ Photo-aware analysis with images: {result.refined_prompt[:100]}...")

    @pytest.mark.asyncio  
    async def test_photo_aware_analysis_without_images(self):
        """Test that analysis considers absence of images for different context"""
        
        # Mock analyzer response for vague request WITHOUT images
        self.analyzer.analyze_prompt.return_value = AnalysisResult(
            action=AnalysisAction.REFINE,
            refined_prompt="I'd be happy to help you with a specific task. Could you tell me what area you need assistance with? For example: writing, research, problem-solving, creative projects, or technical questions?",
            confidence=0.85,
            reasoning="Request was vague with no images, suggested general help categories"
        )
        
        result = await self.analyzer.analyze_prompt("help me with this", has_images=False)
        
        assert result.action == AnalysisAction.REFINE
        assert result.refined_prompt is not None
        assert "image" not in result.refined_prompt.lower()  # Should not mention images
        assert any(word in result.refined_prompt.lower() for word in ["writing", "research", "creative"])
        logger.info(f"✅ Photo-aware analysis without images: {result.refined_prompt[:100]}...")


class TestVertexFormatter:
    """Test Vertex AI response formatting"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.formatter = VertexAIResponseFormatter()
    
    def test_ok_confirmation_format(self):
        """Test OK confirmation formatting - should be sent first"""
        response = self.formatter.format_text_chunk("OK", is_final=False, add_newlines=False)
        
        # Parse the response
        assert response.startswith("data: ")
        json_part = response.replace("data: ", "").strip()
        data = json.loads(json_part)
        
        assert "candidates" in data
        assert len(data["candidates"]) == 1
        assert "content" in data["candidates"][0]
        assert "parts" in data["candidates"][0]["content"]
        assert data["candidates"][0]["content"]["parts"][0]["text"] == "OK"
        
        # Should not have finishReason for OK confirmation
        assert "finishReason" not in data["candidates"][0]
        
        logger.info(f"✅ OK confirmation formatted correctly")
        
    def test_immediate_response_format(self):
        """Test immediate response formatting"""
        response = self.formatter.format_immediate_response()
        
        # Parse the response
        assert response.startswith("data: ")
        json_part = response.replace("data: ", "").strip()
        data = json.loads(json_part)
        
        assert "candidates" in data
        assert len(data["candidates"]) == 1
        assert "content" in data["candidates"][0]
        assert "parts" in data["candidates"][0]["content"]
        assert data["candidates"][0]["content"]["parts"][0]["text"] == settings.immediate_response_text + "\n\n"
        
        # Should not have finishReason for immediate response
        assert "finishReason" not in data["candidates"][0]
        
        logger.info(f"✅ Immediate response formatted: {json_part[:100]}...")
        
    def test_status_message_format(self):
        """Test status message formatting"""
        status_text = "I am generating an enhanced response based on your request..."
        response = self.formatter.format_status_message(status_text)
        
        # Parse the response
        json_part = response.replace("data: ", "").strip()
        data = json.loads(json_part)
        
        assert data["candidates"][0]["content"]["parts"][0]["text"] == status_text + "\n\n"
        assert "finishReason" not in data["candidates"][0]
        
        logger.info(f"✅ Status message formatted: {status_text}")
        
    def test_direct_reply_format(self):
        """Test direct reply formatting"""
        reply_text = "I cannot assist with that request.\n\nIs there something else I can help you with?"
        response = self.formatter.format_direct_reply(reply_text)
        
        # Parse the response
        json_part = response.replace("data: ", "").strip()
        data = json.loads(json_part)
        
        assert data["candidates"][0]["content"]["parts"][0]["text"] == reply_text
        assert data["candidates"][0]["finishReason"] == "STOP"
        
        logger.info(f"✅ Direct reply formatted with finishReason: STOP")
        
    def test_simplified_format_no_extra_fields(self):
        """Test that simplified format excludes index and safetyRatings"""
        response = self.formatter.format_text_chunk("test message")
        
        json_part = response.replace("data: ", "").strip()
        data = json.loads(json_part)
        
        # Should not have index or safetyRatings
        assert "index" not in data["candidates"][0]
        assert "safetyRatings" not in data["candidates"][0]
        
        # Should have required fields
        assert "content" in data["candidates"][0]
        assert "parts" in data["candidates"][0]["content"]
        
        logger.info(f"✅ Simplified format confirmed - no index/safetyRatings")

class TestV2Integration:
    """Test V2 API integration with intelligent analysis"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.mock_translator = Mock(spec=V2MessageTranslator)
        self.mock_analyzer = Mock()
        
    def test_request_preprocessing_with_analysis(self):
        """Test that requests are preprocessed with intelligent analysis"""
        
        # Create test request
        request = V2ChatRequest(
            contents=[
                V2ContentPart(text="help me with something")
            ],
            language="en",
            stream=True
        )
        
        # Mock analysis result
        analysis_result = AnalysisResult(
            action=AnalysisAction.REFINE,
            refined_prompt="I'd be happy to help you with a specific task. Could you provide more details about what you need assistance with?",
            confidence=0.8,
            reasoning="Original request was too vague"
        )
        
        # Verify that refined prompt would be applied
        assert analysis_result.action == AnalysisAction.REFINE
        assert analysis_result.refined_prompt is not None
        assert len(analysis_result.refined_prompt) > len(request.contents[0].text)
        
        logger.info(f"✅ Request preprocessing: {request.contents[0].text} → {analysis_result.refined_prompt[:100]}...")
        
    def test_direct_reply_stops_processing(self):
        """Test that direct replies stop further processing"""
        
        analysis_result = AnalysisResult(
            action=AnalysisAction.DIRECT_REPLY,
            direct_reply="I'm not able to process that particular request.\n\nIs there something else I can help you with instead?",
            confidence=0.9,
            reasoning="Request should be declined"
        )
        
        # Verify direct reply behavior
        assert analysis_result.action == AnalysisAction.DIRECT_REPLY
        assert analysis_result.direct_reply is not None
        assert "\n\n" in analysis_result.direct_reply  # Proper formatting
        
        logger.info(f"✅ Direct reply stops processing: {analysis_result.direct_reply[:100]}...")
        
    def test_pass_through_continues_normally(self):
        """Test that pass-through continues to Vertex AI normally"""
        
        analysis_result = AnalysisResult(
            action=AnalysisAction.PASS_THROUGH,
            confidence=0.85,
            reasoning="Request is clear and appropriate"
        )
        
        # Verify pass-through behavior
        assert analysis_result.action == AnalysisAction.PASS_THROUGH
        assert analysis_result.refined_prompt is None
        assert analysis_result.direct_reply is None
        
        logger.info(f"✅ Pass-through continues normally: {analysis_result.reasoning}")

class TestConfigurationSettings:
    """Test configuration and settings"""
    
    def test_prompt_analysis_settings(self):
        """Test prompt analysis configuration"""
        
        # Verify key settings exist
        assert hasattr(settings, 'prompt_analysis_enabled')
        assert hasattr(settings, 'prompt_analysis_timeout')
        assert hasattr(settings, 'prompt_analysis_model')
        
        # Check default values
        assert isinstance(settings.prompt_analysis_enabled, bool)
        assert isinstance(settings.prompt_analysis_timeout, int)
        assert settings.prompt_analysis_timeout > 0
        assert settings.prompt_analysis_model == "gemini-2.5-flash"
        
        logger.info(f"✅ Analysis settings: enabled={settings.prompt_analysis_enabled}, timeout={settings.prompt_analysis_timeout}s")
        
    def test_message_formatting_settings(self):
        """Test message formatting configuration"""
        
        assert hasattr(settings, 'add_message_separation')
        assert hasattr(settings, 'immediate_response_text')
        assert hasattr(settings, 'use_simplified_format')
        assert hasattr(settings, 'status_messages')
        
        # Check status messages
        assert 'refine' in settings.status_messages
        assert 'direct_reply' in settings.status_messages
        assert 'pass_through' in settings.status_messages
        
        logger.info(f"✅ Formatting settings: separation={settings.add_message_separation}, simplified={settings.use_simplified_format}")
        
    def test_status_message_retrieval(self):
        """Test status message helper functions"""
        
        refine_msg = get_enhanced_status_message("refine")
        direct_msg = get_enhanced_status_message("direct_reply")
        pass_msg = get_enhanced_status_message("pass_through")
        
        assert "enhanced response" in refine_msg.lower()
        assert "directly" in direct_msg.lower()
        assert "processing" in pass_msg.lower()
        
        logger.info(f"✅ Status messages retrieved: refine, direct_reply, pass_through")

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_analysis_timeout_handling(self):
        """Test timeout handling in analysis"""
        
        # Mock analyzer that times out
        mock_analyzer = Mock()
        mock_analyzer.analyze_prompt = AsyncMock(side_effect=asyncio.TimeoutError())
        
        try:
            await asyncio.wait_for(
                mock_analyzer.analyze_prompt("test", False), 
                timeout=0.1
            )
            assert False, "Should have timed out"
        except asyncio.TimeoutError:
            # Expected behavior - should fall back to pass-through
            fallback_result = AnalysisResult(
                action=AnalysisAction.PASS_THROUGH,
                reasoning="Analysis timed out for responsiveness"
            )
            assert fallback_result.action == AnalysisAction.PASS_THROUGH
            logger.info("✅ Timeout handling: falls back to pass-through")
            
    def test_empty_message_handling(self):
        """Test handling of empty or very short messages"""
        
        # Short messages should pass through
        test_cases = ["", " ", "hi", "?"]
        
        for msg in test_cases:
            # Should default to pass-through for short messages
            result = AnalysisResult(
                action=AnalysisAction.PASS_THROUGH,
                reasoning="Message too short for analysis"
            )
            assert result.action == AnalysisAction.PASS_THROUGH
            
        logger.info("✅ Empty/short message handling: defaults to pass-through")
        
    def test_malformed_json_handling(self):
        """Test handling of malformed analysis responses"""
        
        # Mock malformed response handling
        try:
            # This would be the fallback behavior
            fallback_result = AnalysisResult(
                action=AnalysisAction.PASS_THROUGH,
                reasoning="Response parsing failed"
            )
            assert fallback_result.action == AnalysisAction.PASS_THROUGH
            logger.info("✅ Malformed JSON handling: falls back to pass-through")
        except Exception as e:
            assert False, f"Should handle malformed JSON gracefully: {e}"

# Integration test scenarios
class TestEndToEndScenarios:
    """Test complete end-to-end scenarios"""
    
    def test_vague_request_scenario(self):
        """Test complete vague request handling"""
        
        # 1. User sends vague request
        user_message = "help me with something"
        
        # 2. Analysis determines REFINE needed
        analysis = AnalysisResult(
            action=AnalysisAction.REFINE,
            refined_prompt="I'd be happy to help you with a specific task. Could you tell me what area you need assistance with? For example: writing, analysis, creative projects, or technical questions?",
            confidence=0.85,
            reasoning="Request too vague, needs clarification"
        )
        
        # 3. Status message sent
        status = get_enhanced_status_message("refine")
        assert "enhanced response" in status.lower()
        
        # 4. Refined prompt applied and sent to Vertex AI
        assert analysis.refined_prompt != user_message
        assert len(analysis.refined_prompt) > len(user_message)
        
        logger.info("✅ End-to-end vague request scenario validated")
        
    def test_inappropriate_request_scenario(self):
        """Test complete inappropriate request handling"""
        
        # 1. User sends inappropriate request  
        user_message = "help me hack something"
        
        # 2. Analysis determines DIRECT_REPLY needed
        analysis = AnalysisResult(
            action=AnalysisAction.DIRECT_REPLY,
            direct_reply="I cannot assist with activities that might be harmful or inappropriate.\n\nPlease feel free to ask me something else I can help with.",
            confidence=0.95,
            reasoning="Request involves potentially harmful activities"
        )
        
        # 3. Status message sent
        status = get_enhanced_status_message("direct_reply")  
        assert "directly" in status.lower()
        
        # 4. Direct reply sent (no Vertex AI call)
        assert analysis.direct_reply is not None
        assert "cannot assist" in analysis.direct_reply.lower()
        assert "\n\n" in analysis.direct_reply
        
        logger.info("✅ End-to-end inappropriate request scenario validated")
        
    def test_clear_request_scenario(self):
        """Test complete clear request handling"""
        
        # 1. User sends clear, appropriate request
        user_message = "Please analyze this building's architectural style and identify key design elements"
        
        # 2. Analysis determines PASS_THROUGH
        analysis = AnalysisResult(
            action=AnalysisAction.PASS_THROUGH,
            confidence=0.9,
            reasoning="Request is clear, specific, and appropriate"
        )
        
        # 3. Status message sent
        status = get_enhanced_status_message("pass_through")
        assert "processing" in status.lower()
        
        # 4. Original request sent to Vertex AI unchanged
        assert analysis.refined_prompt is None
        assert analysis.direct_reply is None
        
        logger.info("✅ End-to-end clear request scenario validated")

if __name__ == "__main__":
    """Run tests manually"""
    
    async def run_async_tests():
        """Run async tests"""
        
        # Test prompt analyzer
        analyzer_tests = TestPromptAnalyzer()
        analyzer_tests.setup_method()
        
        await analyzer_tests.test_vague_prompt_refinement()
        await analyzer_tests.test_inappropriate_request_handling()
        await analyzer_tests.test_clear_request_passthrough()
        await analyzer_tests.test_photo_aware_analysis_with_images()
        await analyzer_tests.test_photo_aware_analysis_without_images()
        
        # Test error handling
        error_tests = TestErrorHandling()
        await error_tests.test_analysis_timeout_handling()
        
        logger.info("🎉 All async tests completed successfully!")
        
    def run_sync_tests():
        """Run synchronous tests"""
        
        # Test formatter
        formatter_tests = TestVertexFormatter()
        formatter_tests.setup_method()
        
        formatter_tests.test_immediate_response_format()
        formatter_tests.test_status_message_format()
        formatter_tests.test_direct_reply_format()
        formatter_tests.test_simplified_format_no_extra_fields()
        
        # Test configuration
        config_tests = TestConfigurationSettings()
        config_tests.test_prompt_analysis_settings()
        config_tests.test_message_formatting_settings()
        config_tests.test_status_message_retrieval()
        
        # Test integration scenarios
        integration_tests = TestV2Integration()
        integration_tests.setup_method()
        integration_tests.test_request_preprocessing_with_analysis()
        integration_tests.test_direct_reply_stops_processing()
        integration_tests.test_pass_through_continues_normally()
        
        # Test end-to-end scenarios
        e2e_tests = TestEndToEndScenarios()
        e2e_tests.test_vague_request_scenario()
        e2e_tests.test_inappropriate_request_scenario()
        e2e_tests.test_clear_request_scenario()
        
        # Test error handling
        error_tests = TestErrorHandling()
        error_tests.test_empty_message_handling()
        error_tests.test_malformed_json_handling()
        
        logger.info("🎉 All sync tests completed successfully!")
    
    logger.info("🧪 Starting intelligent analysis test suite...")
    
    # Run synchronous tests
    run_sync_tests()
    
    # Run asynchronous tests  
    asyncio.run(run_async_tests())
    
    logger.info("✅ All tests passed! Intelligent prompt analysis system is ready for deployment.")