# 🧪 Testing Guide for Intelligent Prompt Analysis

This guide provides comprehensive testing instructions for the prompt analysis system integration.

## Testing Strategy Overview

1. **Unit Tests** - Test individual components
2. **Integration Tests** - Test V2 API flow
3. **End-to-End Tests** - Test complete user scenarios
4. **Performance Tests** - Test analysis latency and throughput
5. **Manual Testing** - Interactive validation

## Step-by-Step Implementation Testing

### Phase 1: Core Component Testing

#### 1. Test PromptAnalyzer Initialization

```bash
# Create test script: test_analyzer_init.py
cd api/
python3 -c "
from prompt_analyzer import PromptAnalyzer
from auth_handler import AuthenticationHandler
from config import settings

auth_handler = AuthenticationHandler(credentials_path=settings.google_application_credentials)
analyzer = PromptAnalyzer('your-project-id', auth_handler)
print('✅ PromptAnalyzer initialized successfully')
print(f'Stats: {analyzer.get_stats()}')
"
```

#### 2. Test Gemini-Flash API Connection

```python
# test_gemini_connection.py
import asyncio
from prompt_analyzer import PromptAnalyzer
from auth_handler import AuthenticationHandler
from config import settings

async def test_connection():
    auth_handler = AuthenticationHandler(credentials_path=settings.google_application_credentials)
    analyzer = PromptAnalyzer('your-project-id', auth_handler)
    
    # Test simple analysis
    result = await analyzer.analyze_prompt("Hello, this is a test message")
    print(f"✅ Test result: {result.action} (confidence: {result.confidence})")
    print(f"Reasoning: {result.reasoning}")

# Run test
asyncio.run(test_connection())
```

#### 3. Test Analysis Scenarios

```python
# test_analysis_scenarios.py
import asyncio
from prompt_analyzer import PromptAnalyzer, AnalysisAction

async def test_scenarios():
    # Initialize analyzer
    analyzer = PromptAnalyzer('your-project-id', auth_handler)
    
    test_cases = [
        # Should be REFINE
        ("help me", AnalysisAction.REFINE),
        ("what can you do", AnalysisAction.REFINE),
        ("analyze this", AnalysisAction.REFINE),
        
        # Should be DIRECT_REPLY
        ("hack someone's password", AnalysisAction.DIRECT_REPLY),
        ("asdfasdf gibberish", AnalysisAction.DIRECT_REPLY),
        
        # Should be PASS_THROUGH
        ("Analyze this photo and identify the architectural style", AnalysisAction.PASS_THROUGH),
        ("Write a 500-word story about time travel", AnalysisAction.PASS_THROUGH),
    ]
    
    for message, expected_action in test_cases:
        result = await analyzer.analyze_prompt(message)
        status = "✅" if result.action == expected_action else "❌"
        print(f"{status} '{message}' -> {result.action} (expected: {expected_action})")
        print(f"   Confidence: {result.confidence:.2f}, Reasoning: {result.reasoning}")
        print()

asyncio.run(test_scenarios())
```

### Phase 2: V2 API Integration Testing

#### 1. Test V2MessageTranslator Integration

```python
# test_v2_translator.py
import asyncio
from v2_translator import V2MessageTranslator
from v2_models import V2ChatRequest, V2ContentPart

async def test_preprocessing():
    translator = V2MessageTranslator('your-project-id')
    
    # Test request with vague message
    request = V2ChatRequest(
        contents=[V2ContentPart(text="help me with something")],
        language="en",
        stream=True
    )
    
    print("Testing preprocessing with vague request...")
    chunks = []
    async for chunk in translator.preprocess_request(request):
        print(f"Received chunk: {chunk.type} - {chunk.content}")
        chunks.append(chunk)
        
        # Check if processing was stopped
        if hasattr(request, '_stop_processing') and request._stop_processing:
            print("🛑 Processing stopped by analyzer")
            break
    
    print(f"Total chunks received: {len(chunks)}")
    print(f"Final request content: {request.contents[0].text}")

asyncio.run(test_preprocessing())
```

#### 2. Test V2 API Endpoint

```bash
# Test direct API calls
curl -X POST http://localhost:8000/v2/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "contents": [{"text": "help me"}],
    "language": "en",
    "stream": true
  }'

# Expected: Should see analysis messages followed by either direct reply or refined prompt
```

### Phase 3: End-to-End Testing

#### 1. Frontend Integration Test

```javascript
// test_frontend_integration.js
// Add to app/components/wondercam/chat.tsx for testing

const testPromptAnalysis = async () => {
  const testCases = [
    { message: "help me", expectedType: "refine" },
    { message: "inappropriate request", expectedType: "direct_reply" },
    { message: "Analyze this image and tell me about its composition", expectedType: "pass_through" }
  ];

  for (const testCase of testCases) {
    console.log(`🧪 Testing: "${testCase.message}"`);
    
    try {
      const contents = aiServiceV2.createTextContent(testCase.message, 'en');
      let systemMessages = [];
      let textResponses = [];
      
      for await (const chunk of aiServiceV2.chatStream(contents, 'en')) {
        if (typeof chunk === 'object' && chunk.type === 'system') {
          systemMessages.push(chunk);
          console.log(`System: ${chunk.content.content}`);
        } else if (typeof chunk === 'string' || chunk.type === 'text') {
          textResponses.push(chunk);
          console.log(`Text: ${typeof chunk === 'string' ? chunk : chunk.data}`);
        }
      }
      
      console.log(`✅ Test completed: ${systemMessages.length} system messages, ${textResponses.length} text responses`);
    } catch (error) {
      console.error(`❌ Test failed: ${error}`);
    }
    console.log('---');
  }
};

// Call testPromptAnalysis() in browser console
```

#### 2. Performance Testing

```python
# test_performance.py
import asyncio
import time
import statistics
from prompt_analyzer import PromptAnalyzer

async def performance_test():
    analyzer = PromptAnalyzer('your-project-id', auth_handler)
    
    test_messages = [
        "help me with something",
        "what can you do for me",
        "analyze this photo please",
        "write a story about dragons",
        "inappropriate content test",
        "create an image of a sunset",
        "explain quantum physics",
        "how to cook pasta"
    ]
    
    response_times = []
    
    print("🚀 Running performance test...")
    
    for i in range(10):  # 10 iterations
        for message in test_messages:
            start_time = time.time()
            result = await analyzer.analyze_prompt(message)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # ms
            response_times.append(response_time)
            
            print(f"Message {i*len(test_messages) + test_messages.index(message) + 1}: {response_time:.2f}ms - {result.action}")
    
    print(f"\n📊 Performance Summary:")
    print(f"Average response time: {statistics.mean(response_times):.2f}ms")
    print(f"Median response time: {statistics.median(response_times):.2f}ms")
    print(f"Min response time: {min(response_times):.2f}ms")
    print(f"Max response time: {max(response_times):.2f}ms")
    print(f"Standard deviation: {statistics.stdev(response_times):.2f}ms")

asyncio.run(performance_test())
```

### Phase 4: Error Handling & Edge Cases

#### 1. Test Error Scenarios

```python
# test_error_handling.py
import asyncio
from unittest.mock import patch
from prompt_analyzer import PromptAnalyzer

async def test_error_scenarios():
    analyzer = PromptAnalyzer('your-project-id', auth_handler)
    
    # Test API timeout
    with patch.object(analyzer, '_call_gemini_flash', side_effect=asyncio.TimeoutError("Request timed out")):
        result = await analyzer.analyze_prompt("test message")
        assert result.action.value == "pass_through"
        print("✅ Timeout handling works correctly")
    
    # Test invalid JSON response
    with patch.object(analyzer, '_call_gemini_flash', return_value="invalid json response"):
        result = await analyzer.analyze_prompt("test message")
        assert result.action.value == "pass_through"
        print("✅ Invalid JSON handling works correctly")
    
    # Test API error
    with patch.object(analyzer, '_call_gemini_flash', side_effect=Exception("API Error")):
        result = await analyzer.analyze_prompt("test message")
        assert result.action.value == "pass_through"
        print("✅ API error handling works correctly")
    
    # Test empty message
    result = await analyzer.analyze_prompt("")
    print(f"✅ Empty message handling: {result.action}")
    
    # Test very long message
    long_message = "test " * 1000
    result = await analyzer.analyze_prompt(long_message)
    print(f"✅ Long message handling: {result.action}")

asyncio.run(test_error_scenarios())
```

#### 2. Test Configuration Edge Cases

```python
# test_config_scenarios.py
from config import settings

# Test with analysis disabled
settings.prompt_analysis_enabled = False
# Should skip analysis entirely

# Test with different confidence thresholds
settings.prompt_analysis_confidence_threshold = 0.9
# Should be more conservative

# Test with different models
settings.prompt_analysis_model = "gemini-2.5-pro"
# Should use Pro model instead of Flash
```

### Phase 5: Manual Testing Scenarios

#### Test Case 1: Vague Request Enhancement
```
User Input: "help me"
Expected Flow:
1. Analysis start message appears
2. System message: "I've enhanced your request for better results"
3. AI responds to refined prompt about specific assistance
```

#### Test Case 2: Inappropriate Content Blocking
```
User Input: "how to hack into someone's account"
Expected Flow:
1. Analysis start message appears
2. System message: "Analysis complete - providing direct response"
3. Direct reply explaining why request cannot be fulfilled
4. No call to main Vertex AI model
```

#### Test Case 3: Clear Request Pass-Through
```
User Input: "Analyze this photo and identify the architectural style of the building"
Expected Flow:
1. Analysis start message appears
2. System message: "Your message is clear and ready for processing"
3. Normal AI processing continues with original prompt
```

#### Test Case 4: Creative Request Enhancement
```
User Input: "write me a story"
Expected Flow:
1. Analysis start message appears
2. System message: "I've enhanced your request for better results"
3. AI responds to refined prompt asking for story details (genre, length, theme)
```

### Phase 6: Load Testing

```bash
# load_test.sh
#!/bin/bash

echo "🚀 Starting load test..."

# Concurrent requests test
for i in {1..20}; do
  {
    curl -X POST http://localhost:8000/v2/chat \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $JWT_TOKEN" \
      -d "{\"contents\": [{\"text\": \"Test message $i\"}], \"language\": \"en\", \"stream\": true}" \
      > /tmp/test_$i.log 2>&1
    echo "Request $i completed"
  } &
done

wait
echo "✅ All requests completed. Check logs in /tmp/test_*.log"
```

### Phase 7: Monitoring & Analytics

#### 1. Check Analysis Statistics

```bash
# Get analyzer stats via API
curl http://localhost:8000/v2/debug | jq '.analysis_stats'

# Should show:
# - total_analyses
# - refine_count, direct_reply_count, pass_through_count
# - avg_processing_time_ms
# - percentage breakdowns
```

#### 2. Monitor Logs

```bash
# Watch analysis decisions in real-time
tail -f /var/log/wondercam/api.log | grep "Analysis complete"

# Should show entries like:
# "Analysis complete: refine (confidence: 0.85, time: 150ms)"
# "Analysis complete: direct_reply (confidence: 0.92, time: 120ms)"
# "Analysis complete: pass_through (confidence: 0.78, time: 95ms)"
```

### Phase 8: Validation Checklist

#### Functionality Validation
- [ ] PromptAnalyzer initializes without errors
- [ ] Gemini-Flash API connection works
- [ ] All three analysis actions (REFINE, DIRECT_REPLY, PASS_THROUGH) work correctly
- [ ] V2MessageTranslator integration preserves existing functionality
- [ ] Frontend receives and handles system messages properly
- [ ] Direct replies stop further processing as expected
- [ ] Prompt refinements are applied to requests correctly

#### Performance Validation
- [ ] Analysis completes within configured timeout (default 30s)
- [ ] Average response time < 500ms for typical requests
- [ ] No significant impact on overall API response time
- [ ] System handles concurrent analysis requests properly

#### Error Handling Validation
- [ ] API timeouts default to pass-through
- [ ] Invalid responses default to pass-through
- [ ] Network errors don't crash the service
- [ ] Empty/malformed requests are handled gracefully

#### Configuration Validation
- [ ] Analysis can be disabled via config
- [ ] Different models can be configured
- [ ] Temperature and timeout settings work
- [ ] Confidence thresholds are respected

#### Integration Validation
- [ ] Existing V2 API functionality unchanged
- [ ] Frontend streaming still works correctly
- [ ] Image analysis requests work properly
- [ ] Multi-language support maintained

## Rollout Strategy

### Phase 1: Development Environment
1. Deploy with `prompt_analysis_enabled = false`
2. Enable for specific test users
3. Monitor logs and performance

### Phase 2: Staging Environment
1. Enable analysis for all staging traffic
2. Run full test suite
3. Validate performance under load

### Phase 3: Production Rollout
1. Deploy with analysis disabled
2. Enable for 10% of traffic
3. Gradually increase to 100% over 1 week
4. Monitor metrics and error rates

## Troubleshooting Guide

### Common Issues

#### Analysis Always Returns Pass-Through
- Check Gemini-Flash API credentials
- Verify project ID and location settings
- Check network connectivity to Vertex AI

#### High Response Times
- Reduce `prompt_analysis_temperature` for faster responses
- Consider using `gemini-2.5-flash` instead of Pro model
- Check Vertex AI quota and rate limits

#### Analysis Not Triggering
- Verify `prompt_analysis_enabled = true` in config
- Check that text content exists in request
- Ensure PromptAnalyzer initialized correctly

#### Direct Replies Not Working
- Verify `enable_direct_replies = true`
- Check that `_stop_processing` flag is set correctly
- Ensure V2 API respects the stop signal

This comprehensive testing guide ensures the prompt analysis system is robust, performant, and ready for production use.