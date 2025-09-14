# 📝 Enhanced Message Formatting with Return Characters

## Overview

Adding return characters (`\n`) to separate different response phases creates better visual separation on the client side, making the conversation flow more natural and readable.

## Enhanced Message Flow

### **Before (Single Line)**
```
OK I am generating an enhanced response based on your request... Here's your enhanced response about...
```

### **After (Separated Messages)**
```
OK

I am generating an enhanced response based on your request...

Here's your enhanced response about...
```

## Implementation

### 1. **Enhanced Vertex AI Response Formatter**

```python
# Enhanced api/v2_api.py

class VertexAIResponseFormatter:
    """Enhanced formatter with proper message separation"""
    
    @staticmethod
    def format_text_chunk(text: str, is_final: bool = False, add_newlines: bool = True) -> str:
        """Format text as Vertex AI streaming chunk with optional newlines"""
        
        # Add newlines for better message separation
        formatted_text = f"{text}\n\n" if add_newlines and not is_final else text
        
        vertex_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": formatted_text}
                        ]
                    },
                    "finishReason": "STOP" if is_final else None,
                    "index": 0,
                    "safetyRatings": [
                        {
                            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            "probability": "NEGLIGIBLE"
                        },
                        {
                            "category": "HARM_CATEGORY_HATE_SPEECH", 
                            "probability": "NEGLIGIBLE"
                        },
                        {
                            "category": "HARM_CATEGORY_HARASSMENT",
                            "probability": "NEGLIGIBLE"
                        },
                        {
                            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                            "probability": "NEGLIGIBLE"
                        }
                    ]
                }
            ]
        }
        
        if not is_final:
            del vertex_response["candidates"][0]["finishReason"]
        
        return f"data: {json.dumps(vertex_response)}\n\n"
    
    @staticmethod
    def format_immediate_response() -> str:
        """Format immediate acknowledgment with newlines"""
        return VertexAIResponseFormatter.format_text_chunk("OK", is_final=False, add_newlines=True)
    
    @staticmethod  
    def format_status_message(status_text: str) -> str:
        """Format status message with newlines for separation"""
        return VertexAIResponseFormatter.format_text_chunk(status_text, is_final=False, add_newlines=True)
    
    @staticmethod
    def format_direct_reply(reply_text: str) -> str:
        """Format direct reply as final response without extra newlines"""
        return VertexAIResponseFormatter.format_text_chunk(reply_text, is_final=True, add_newlines=False)
    
    @staticmethod
    def format_transition_message() -> str:
        """Format transition message before Vertex AI response"""
        return VertexAIResponseFormatter.format_text_chunk("", is_final=False, add_newlines=False)
```

### 2. **Enhanced V2 API Handler with Message Separation**

```python
# Enhanced api/v2_api.py streaming function

async def stream_v2_response(request: V2ChatRequest, user: dict) -> AsyncGenerator[str, None]:
    """Enhanced streaming with proper message separation"""
    
    try:
        current_translator = get_translator()
        
        # Step 1: IMMEDIATE response with separation
        logger.info("🚀 Sending immediate acknowledgment...")
        yield formatter.format_immediate_response()  # "OK\n\n"
        
        # Step 2: Start background analysis
        logger.info("🧠 Starting background prompt analysis...")
        
        analysis_task = asyncio.create_task(
            run_background_analysis(request, current_translator)
        )
        
        # Step 3: Wait for analysis
        try:
            analysis_result = await asyncio.wait_for(analysis_task, timeout=2.0)
            logger.info(f"✅ Background analysis completed: {analysis_result.action}")
        except asyncio.TimeoutError:
            logger.warning("⏰ Analysis timeout, proceeding with pass-through")
            analysis_result = AnalysisResult(
                action=AnalysisAction.PASS_THROUGH,
                reasoning="Analysis timed out for responsiveness"
            )
        
        # Step 4: Stream status update with separation
        status_message = get_enhanced_status_message(analysis_result)
        yield formatter.format_status_message(status_message)  # "Status message\n\n"
        
        # Step 5: Handle analysis result
        if analysis_result.action == AnalysisAction.DIRECT_REPLY:
            # Stream direct reply as final response (no extra newlines)
            logger.info("🛑 Streaming direct reply")
            yield formatter.format_direct_reply(analysis_result.direct_reply)
            return
        
        # Step 6: Apply refined prompt if needed
        if analysis_result.action == AnalysisAction.REFINE:
            logger.info("✨ Applying refined prompt")
            apply_refined_prompt(request, analysis_result.refined_prompt)
        
        # Step 7: Stream from Vertex AI (native format, already has proper formatting)
        logger.info("🎯 Starting Vertex AI streaming...")
        vertex_request = current_translator.v2_to_vertex(request)
        
        # Optional: Add transition separator before Vertex AI response
        yield formatter.format_transition_message()
        
        async for vertex_chunk in stream_from_vertex_ai(vertex_request, current_translator):
            yield vertex_chunk
        
        logger.info("✅ Streaming completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Streaming error: {e}")
        error_message = f"I apologize, but I encountered an error processing your request.\n\nPlease try again."
        yield formatter.format_direct_reply(error_message)

def get_enhanced_status_message(analysis_result: AnalysisResult) -> str:
    """Get enhanced status messages with better formatting"""
    
    if analysis_result.action == AnalysisAction.REFINE:
        return "I am generating an enhanced response based on your request..."
    elif analysis_result.action == AnalysisAction.DIRECT_REPLY:
        return "Let me help you with that directly..."
    else:  # PASS_THROUGH
        return "Processing your request..."
```

### 3. **Configuration for Message Formatting**

```python
# api/config.py additions

class Settings(BaseSettings):
    # ... existing settings
    
    # Message formatting settings
    add_message_separation: bool = True
    immediate_response_text: str = "OK"
    
    # Enhanced status messages with better formatting
    status_messages: Dict[str, str] = {
        "refine": "I am generating an enhanced response based on your request...",
        "direct_reply": "Let me help you with that directly...",
        "pass_through": "Processing your request...",
    }
    
    # Direct reply templates with proper formatting
    direct_reply_templates: Dict[str, str] = {
        "inappropriate": "I cannot assist with requests that might be harmful or inappropriate.\n\nPlease feel free to ask me something else I can help with.",
        "unclear": "I'm having trouble understanding what you'd like me to help with.\n\nCould you please provide more specific details about your request?",
        "general": "I'm not able to process that particular request.\n\nIs there something else I can help you with instead?"
    }
```

### 4. **Enhanced Prompt Analysis with Better Replies**

```python
# Enhanced api/prompt_analyzer.py

class PromptAnalyzer:
    """Enhanced with better formatted responses"""
    
    def _load_analysis_prompts(self) -> Dict[str, str]:
        """Enhanced prompts that generate better formatted responses"""
        return {
            "main_analysis": """You are a smart prompt refinement AI. Analyze the user's message and decide:

1. **REFINE**: If unclear, vague, or could benefit from enhancement
2. **DIRECT_REPLY**: If inappropriate, nonsensical, or should be declined  
3. **PASS_THROUGH**: If clear, specific, and appropriate

User message: "{user_message}"

For DIRECT_REPLY responses, be polite, helpful, and offer alternatives when possible.
For REFINE responses, make prompts specific and actionable.

Respond in JSON format:
{{
  "action": "refine|direct_reply|pass_through",
  "refined_prompt": "Enhanced specific prompt (only if action=refine)",
  "direct_reply": "Polite, helpful response with alternatives (only if action=direct_reply)", 
  "confidence": 0.85,
  "reasoning": "Brief explanation"
}}""",

            # ... other prompts enhanced similarly
        }
    
    def _parse_analysis_response(self, response: str) -> PromptAnalysisResult:
        """Enhanced parsing with better direct reply formatting"""
        try:
            # ... existing parsing logic
            
            # Enhance direct replies with better formatting
            if result.action == AnalysisAction.DIRECT_REPLY and result.direct_reply:
                # Ensure direct replies are well-formatted with proper line breaks
                direct_reply = result.direct_reply.strip()
                
                # Add proper paragraph separation if not already present
                if '\n' not in direct_reply and '. ' in direct_reply:
                    # Split long sentences into paragraphs for better readability
                    sentences = direct_reply.split('. ')
                    if len(sentences) > 2:
                        mid_point = len(sentences) // 2
                        part1 = '. '.join(sentences[:mid_point]) + '.'
                        part2 = '. '.join(sentences[mid_point:])
                        if not part2.endswith('.'):
                            part2 += '.'
                        direct_reply = f"{part1}\n\n{part2}"
                
                result.direct_reply = direct_reply
            
            return result
            
        except Exception as e:
            # ... existing error handling
```

## Example Message Flows

### **Vague Request Enhancement**
```
Client receives:
1. "OK\n\n"
2. "I am generating an enhanced response based on your request...\n\n"  
3. [Vertex AI response with enhanced prompt]
```

**Display:**
```
OK

I am generating an enhanced response based on your request...

I'd be happy to help you with a specific task. Could you tell me what area you need assistance with? For example:

• Creative writing and storytelling
• Technical questions and problem-solving
• Analysis and research
• General information and explanations

What sounds most relevant to what you had in mind?
```

### **Inappropriate Request Handling**
```
Client receives:
1. "OK\n\n"
2. "Let me help you with that directly...\n\n"
3. "I cannot assist with activities that might violate privacy or security.\n\nIs there something else I can help you with instead?"
```

**Display:**
```
OK

Let me help you with that directly...

I cannot assist with activities that might violate privacy or security.

Is there something else I can help you with instead?
```

### **Clear Request Pass-Through**  
```
Client receives:
1. "OK\n\n"
2. "Processing your request...\n\n"
3. [Vertex AI response with original prompt]
```

**Display:**
```
OK

Processing your request...

This building exhibits characteristics of Neo-Classical architecture, which was popular in the late 18th and early 19th centuries. Key features I can identify include:

• Symmetrical facade with balanced proportions
• Classical columns with Corinthian capitals
• Triangular pediment above the entrance
• Clean, geometric lines and minimal ornamentation

The style draws inspiration from ancient Greek and Roman architecture...
```

## Benefits of Enhanced Formatting

### 1. **Better Visual Separation**
- Each response phase is clearly distinct
- Easier for users to follow the conversation flow
- Professional, polished appearance

### 2. **Improved Readability**
- Proper paragraph breaks in longer responses
- Clear separation between system messages and content
- Better mobile and desktop display

### 3. **Enhanced User Experience**
- Natural conversation rhythm
- Clear indication of processing stages
- Professional, AI assistant feel

### 4. **Maintained Compatibility**
- Still uses identical Vertex AI format
- Frontend parsing unchanged
- Newlines are just part of the text content

This enhancement creates a much more polished and readable conversation experience while maintaining full technical compatibility.