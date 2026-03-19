"""
Load prompt
"""

from pathlib import Path

srcPath = Path(__file__).parent

def loadPrompt(name):
    return open(f"{srcPath}/prompt/{name}").read()