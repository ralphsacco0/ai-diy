"""
Patch to fix the SPRINT_REVIEW_ALEX bounded tool loop to ensure it always provides a meaningful response.

To use this patch:
1. Copy and paste the final_summary_step function into ai_gateway.py
2. Replace the code block at line ~593-634 with the commented section below
"""

async def final_summary_step(bounded_messages, model, headers, ssl_context, persona_key, persona_name):
    """Generate a final summary if the bounded loop didn't produce meaningful content"""
    import aiohttp
    import json
    import logging

    logger = logging.getLogger("ai_diy.ai_gateway")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    final_messages = bounded_messages + [
        {"role": "user", "content": "Based on your investigation above, provide a complete summary of what you found and any recommendations or fixes needed. Be specific about the 404 error, its cause, and how to fix it. Include file paths and what needs to be modified."}
    ]
    
    final_payload = {
        "model": model,
        "messages": final_messages,
        "temperature": 0.7,
        "max_tokens": 1500,
        "stream": False
    }
    
    try:
        async with aiohttp.ClientSession() as session3:
            async with session3.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=final_payload,
                timeout=aiohttp.ClientTimeout(total=30),
                ssl=ssl_context
            ) as final_response:
                if final_response.status == 200:
                    final_text = await final_response.text()
                    final_data = json.loads(final_text)
                    final_content = final_data["choices"][0]["message"].get("content", "")
                    if final_content:
                        logger.info(f"Generated final summary: {len(final_content)} chars")
                        return final_content
                else:
                    logger.error(f"Final summary API call failed: {final_response.status}", character=persona_key)
    except Exception as e:
        logger.error(f"Final summary exception: {str(e)}", character=persona_key)
    
    return "I investigated the 404 error issue but encountered a problem generating the final report."

"""
# Replace this block in ai_gateway.py:

# If we've reached the end of the loop without meaningful content, get a final summary
if not running_content or len(running_content.strip()) < 10:
    logger.info(f"No meaningful content after {current_pass-1} passes, generating final summary")
    running_content = await final_summary_step(bounded_messages, model, headers, ssl_context, persona_key, persona_name)

# Set final content from accumulated running_content
content = running_content
logger.info(f"Bounded loop complete after {current_pass-1} passes for {persona_name}: {len(content)} chars")
"""
