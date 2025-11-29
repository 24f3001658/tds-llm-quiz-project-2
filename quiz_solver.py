import asyncio
import logging
import time
import json
import re
import requests
import os
from playwright.async_api import async_playwright
from typing import Any, Dict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class QuizSolver:
    def __init__(self, email, secret):
        self.email = email
        self.secret = secret
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.browser = None
        self.page = None
    
    async def initialize_browser(self):
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            context = await self.browser.new_context()
            self.page = await context.new_page()
    
    async def close_browser(self):
        if self.browser:
            await self.browser.close()
    
    async def fetch_quiz_page(self, url):
        await self.initialize_browser()
        await self.page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        return await self.page.evaluate("() => document.body.innerText")
    
    def extract_submit_url(self, content):
        pattern = r'Post your answer to\s+(https?://\S+)'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            url = match.group(1)
            return url.rstrip('.,;:')
        return "https://tds-llm-analysis.s-anand.net/submit"
    
    def solve_with_llm(self, question):
        response = self.client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": "Answer ONLY:\n" + question}],
            temperature=0
        )
        answer = response.choices[0].message.content.strip()
        tick = chr(96)
        answer = answer.replace(tick+tick+tick, "")
        try:
            return json.loads(answer)
        except:
            try:
                return int(answer) if "." not in answer else float(answer)
            except:
                return answer
    
    async def solve_single_quiz(self, url):
        content = await self.fetch_quiz_page(url)
        return {"submit_url": self.extract_submit_url(content), "answer": self.solve_with_llm(content)}
    
    def submit_answer(self, submit_url, quiz_url, answer):
        payload = {"email": self.email, "secret": self.secret, "url": quiz_url, "answer": answer}
        response = requests.post(submit_url, json=payload, timeout=30)
        return response.json() if response.status_code == 200 else {"correct": False}
    
    async def solve_quiz_chain(self, initial_url):
        try:
            current_url = initial_url
            count = 0
            start = time.time()
            while current_url and time.time() - start < 180:
                count += 1
                result = await self.solve_single_quiz(current_url)
                sub_result = self.submit_answer(result["submit_url"], current_url, result["answer"])
                next_url = sub_result.get("url")
                if next_url and next_url != current_url:
                    current_url = next_url
                    start = time.time()
                else:
                    current_url = None
        finally:
            await self.close_browser()
