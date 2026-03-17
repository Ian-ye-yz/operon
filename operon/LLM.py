"""
Construct a LLM class
Also parse the response
"""
from openai import OpenAI
import yaml
import os

from . import prompt

def SYSTEM(message: str = ""): return {"role": "system", "content": message}
def USER(message: str = ""): return {"role": "user", "content": message}
def ASSISTANT(message: str = ""): return {"role": "assistant", "content": message}

class LLM:
    def __init__(self, apikey: str, model: str, url: str = ""):
        self.client = OpenAI(api_key=apikey, base_url=url)
        self.model = model
        self.messages = [
            {SYSTEM(prompt.loadPrompt("SYSTEM"))}
        ]
    def __call__(self, userMessage, saveMessage: bool = True):
        self.messages.append(userMessage)
        res = self.client.chat.completions.create(
            model = self.model,
            messages = self.messages,
            stream = False
        )
        value = yaml.safe_load(res)
        print(value)
        if saveMessage:
            self.messages.append(ASSISTANT(res))

defaultLLM = LLM(apikey = os.getenv("DEEPSEEK_API_KEY"))