import asyncio
import logging
import time
import json
import re
import requests
import os
from playwright.async_api import async_playwright
from typing import Any, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class QuizSolver:
    def __init__(self, email: str, secret: str):
        self.email = email
        self.secret = secret
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.browser = None
        self.playwright = None
        self.page = None
    
    async def initialize_browser(self):
        if not self.browser:
            try:
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                context = await self.browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                self.page = await context.new_page()
                logger.info("Browser initialized")
            except Exception as e:
                logger.error(f"Browser init failed: {e}")
                raise
    
    async def close_browser(self):
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
    
    async def fetch_quiz_page(self, url: str) -> str:
        await self.initialize_browser()
        try:
            logger.info(f"Fetching: {url}")
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            content = await self.page.evaluate("() => document.body.innerText")
            if not content or len(content) < 50:
                content = await self.page.evaluate("() => document.body.innerHTML")
            logger.info(f"Content length: {len(content)}")
            return content
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            raise
    
    def extract_submit_url(self, content: str) -> Optional[str]:
        patterns = [
            r'Post your answer to\s+(https?://[^\s\)\]<>"]+)',
            r'(https?://[^\s\)\]<>"]+/submit[^\s\)\]<>"]*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                url = match.group(1).rstrip('.,;:)\'"')
                logger.info(f"Submit URL: {url}")
                return url
        logger.error("No submit URL found")
        return None
    
    def solve_with_llm(self, question: str) -> Any:
        try:
            prompt = f"""Analyze this quiz and provide ONLY the answer in the exact format requested.

{question}

Rules:
- If number requested, return ONLY the number
- If JSON requested, return ONLY valid JSON
- If text requested, return ONLY the text
- No explanations, no markdown, no code blocks
- Be precise

Answer:"""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            answer = response.choices[0].message.content.strip()
            answer = re.sub(r'^```
            answer = re.sub(r'\n?```$', '', answer)
            answer = answer.strip()
            
            try:
                return json.loads(answer)
            except:
                pass
            
            if answer.lower() in ['true', 'false']:
                return answer.lower() == 'true'
            
            try:
                if '.' in answer:
                    return float(answer)
                return int(answer)
            except:
                pass
            
            return answer
        except Exception as e:
            logger.error(f"LLM error: {e}")
            raise
    
    async def solve_single_quiz(self, url: str) -> Dict[str, Any]:
        content = await self.fetch_quiz_page(url)
        submit_url = self.extract_submit_url(content)
        if not submit_url:
            raise ValueError("No submit URL")
        answer = self.solve_with_llm(content)
        return {"submit_url": submit_url, "answer": answer}
    
    def submit_answer(self, submit_url: str, quiz_url: str, answer: Any) -> Dict[str, Any]:
        payload = {
            "email": self.email,
            "secret": self.secret,
            "url": quiz_url,
            "answer": answer
        }
        try:
            logger.info(f"Submitting to: {submit_url}")
            logger.info(f"Answer: {answer}")
            response = requests.post(submit_url, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()
            return {"correct": False}
        except Exception as e:
            logger.error(f"Submit error: {e}")
            return {"correct": False}
    
    async def solve_quiz_chain(self, initial_url: str):
        start_time = time.time()
        MAX_TIME = 175
        try:
            current_url = initial_url
            count = 0
            logger.info(f"Starting chain: {initial_url}")
            
            while current_url and time.time() - start_time < MAX_TIME:
                count += 1
                remaining = MAX_TIME - (time.time() - start_time)
                logger.info(f"Quiz #{count} | Time left: {remaining:.1f}s")
                
                try:
                    result = await self.solve_single_quiz(current_url)
                    sub_result = self.submit_answer(result["submit_url"], current_url, result["answer"])
                    
                    if sub_result.get("correct"):
                        logger.info("✅ CORRECT!")
                    else:
                        logger.warning("❌ WRONG")
                    
                    next_url = sub_result.get("url")
                    if next_url and next_url != current_url:
                        current_url = next_url
                    else:
                        break
                except Exception as e:
                    logger.error(f"Error: {e}")
                    break
            
            logger.info(f"Completed {count} quizzes in {time.time()-start_time:.1f}s")
        finally:
            await self.close_browser()
