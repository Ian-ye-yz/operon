"""
Construct a LLM class
Also parse the response
"""
from openai import OpenAI
import yaml
import os
from dotenv import load_dotenv
import time

from . import loadSystemPrompt

load_dotenv()

def SYSTEM(message: str = ""): return {"role": "system", "content": message}
def USER(message: str = ""): return {"role": "user", "content": message}
def ASSISTANT(message: str = ""): return {"role": "assistant", "content": message}

class LLM:
    def __init__(self, apikey: str, model: str, url: str = "https://api.deepseek.com"):
        self.client = OpenAI(api_key=apikey, base_url=url)
        self.model = model
        self.messages = [
            SYSTEM(loadSystemPrompt())
        ]
    def setMessages(self, messages):
        self.messages = messages
    def __call__(self, userMessage = None, saveMessage: bool = True):
        if userMessage != None: self.messages.append(userMessage)
        for attempt in range(3):
            try:
                res = self.client.chat.completions.create(
                    model = self.model,
                    messages = self.messages,
                    stream = False,
                    temperature=0.3
                ).choices[0].message.content
                # print("Raw LLM Response: ", res)
                # print("---")
                if saveMessage:
                    self.messages.append(ASSISTANT(res))
                try:
                    print("Parsed LLM Response: ", yaml.safe_load(res))
                    return yaml.safe_load(res)
                except:
                    return {
                        "type": "Error",
                        "data": """Yaml Error because of incorrect format, please try again
Here's an example of valid Yaml
type: "Print"
data: "This is an example of Print tool, to print messages to user"
"""
                    }
            except Exception as e:
                last_err = e
                print(f"SYSTEM: LLM call failed, attempt {attempt + 1}/3: {e}")
                if attempt < 2:
                    time.sleep(1)

        return {
            "type": "MetaError",
            "data": f"LLM API Error after 3 retries: {last_err}"
        }

defaultLLM = LLM(apikey = os.getenv("DEEPSEEK_API_KEY"), model = "deepseek-chat")