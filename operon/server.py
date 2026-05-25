"""
Tool Server
Handle tool calls
"""

import yaml
from pathlib import Path
import json
import requests
import base64
from bs4 import BeautifulSoup
import shutil
import subprocess
import sys
import io
import contextlib

rootPath = Path(__file__).parent.parent / "file"
srcPath = Path(__file__).parent

TEXT_TYPES = (
    "text/",
    "application/json",
    "application/javascript",
    "application/xml",
)


def is_text_response(content_type: str) -> bool:
    if not content_type:
        return False

    content_type = content_type.lower()

    return any(
        content_type.startswith(t)
        for t in TEXT_TYPES
    )

class ToolServer:
    def __init__(self):
        self.tasks = json.loads(open(srcPath / "task.json").read())
        self.scratchPad = ""
    def __call__(self, value):
        if value["type"] == "Python":
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                exec(value["data"]["code"])
            return yaml.dump({
                "type": "Result",
                "data": repr(buffer.getvalue())
            })
        elif value["type"] == "Shell":
            res = value["data"]
            command = res["command"]
            cwd = res.get("cwd", ".")
            pth = rootPath / cwd.lstrip("/\\")
            if not pth.exists():
                return yaml.dump({
                    "type": "Error",
                    "data": f"cwd {cwd} doesn't exist"
                })
            if not pth.is_dir():
                return yaml.dump({
                    "type": "Error",
                    "data": f"cwd {cwd} is not a directory"
                })
            try:
                completed = subprocess.run(
                    command,
                    cwd=pth,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30
                )
                return yaml.dump({
                    "type": "Result",
                    "data": {
                        "returncode": completed.returncode,
                        "stdout": completed.stdout,
                        "stderr": completed.stderr,
                        "cwd": str(pth),
                    }
                })
            except subprocess.TimeoutExpired:
                return yaml.dump({
                    "type": "Error",
                    "data": "Shell command timed out"
                })
            except Exception as e:
                return yaml.dump({
                    "type": "Error",
                    "data": str(e)
                })
        elif value["type"] == "ReadFile":
            res = value["data"]
            name, start, end = res["name"], res.get("start", None), res.get("end", None)
            if not (rootPath / name.lstrip("/\\")).exists():
                return yaml.dump({
                    "type": "Error",
                    "data": f"File {name} doesn't exist"
                })
            if not (rootPath / name.lstrip("/\\")).is_file():
                return yaml.dump({
                    "type": "Error",
                    "data": f"{name} is not a file"
                })
            content = open(rootPath / name.lstrip("/\\"), encoding="UTF-8").read()
            lines = content.splitlines(keepends=True)
            if start is None: start = 0
            if end is None: end = len(lines)
            return yaml.dump({
                "type": "Result",
                "data": '\n'.join(lines[start:end])
            })
        elif value["type"] == "WriteFile":
            res = value["data"]
            name, content, typ = res["name"], res["content"], res["type"]
            print(rootPath / name.lstrip("/\\"))
            (rootPath / name.lstrip("/\\")).parent.mkdir(parents=True, exist_ok=True)
            open(rootPath / name.lstrip("/\\"), typ, encoding="UTF-8").write(content)
            return yaml.dump({
                "type": "Result",
                "data": None
            })
        elif value["type"] == "PatchFile":
            res = value["data"]
            name, start, end, content = res["name"], res["start"], res["end"], res["content"]
            pth = rootPath / name.lstrip("/\\")
            if not pth.exists():
                return yaml.dump({
                    "type": "Error",
                    "data": f"File {name} doesn't exist"
                })
            if not (rootPath / name.lstrip("/\\")).is_file():
                return yaml.dump({
                    "type": "Error",
                    "data": f"{name} is not a file"
                })
            if start < 0 or end < start:
                return yaml.dump({
                    "type": "Error",
                    "data": f"Invalid range [{start}, {end})"
                })
            lines = pth.read_text(
                encoding="utf-8"
            ).splitlines(keepends=True)
            if start > len(lines):
                return yaml.dump({
                    "type": "Error",
                    "data": "start exceeds file length"
                })
            replacement = content.splitlines(
                keepends=True
            )
            new_lines = (
                lines[:start]
                + replacement
                + lines[end:]
            )
            pth.write_text(
                "".join(new_lines),
                encoding="utf-8"
            )
            return yaml.dump({
                "type": "Result",
                "data": None
            })
        elif value["type"] == "Mkdir":
            res = value["data"]
            if not isinstance(res, str):
                return yaml.dump({
                    "type": "Error",
                    "data": "data entry of Mkdir should be a string, indicating the path"
                })
            path = rootPath / res.lstrip("/\\")
            Path(path).mkdir(parents = True, exist_ok = True)
            return yaml.dump({
                "type": "Result",
                "data": None
            })
        elif value["type"] == "Ls":
            res = value["data"]
            if not isinstance(res, str):
                return yaml.dump({
                    "type": "Error",
                    "data": "data entry of Ls should be a string, indicating the path"
                })
            path = rootPath / res.lstrip("/\\")
            return yaml.dump({
                "type": "Result",
                "data": [p.name for p in Path(path).iterdir()]
            })
        elif value["type"] == "Move":
            res = value["data"]
            src, dest = res["src"], res["dest"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dest)
            return yaml.dump({
                "type": "Result",
                "data": None
            })
        elif value["type"] == "Task":
            res = value["data"]
            if res["type"] == "Add":
                self.tasks[res["name"]] = {"content": res["content"], "plan": []}
                return yaml.dump({
                    "type": "Result",
                    "data": None
                })
            elif res["type"] == "View":
                data = {}
                for p, i in enumerate(self.tasks.keys()):
                    data["task" + str(p)] = self.tasks[i]["content"]
                return yaml.dump({
                    "type": "Result",
                    "data": data
                })
            elif res["type"] == "Tick":
                if not res["name"] in self.tasks.keys():
                    return yaml.dump({
                        "type": "Error",
                        "data": "The task the plan want to hook to didn't exist; Check for typo or create it"
                    })
                self.tasks.pop(res["name"])
                return yaml.dump({
                    "type": "Result",
                    "data": None
                })
        elif value["type"] == "Plan":
            res = value["data"]
            if res["type"] == "Add":
                if not res["hook"] in self.tasks.keys():
                    return yaml.dump({
                        "type": "Error",
                        "data": "The task the plan want to hook to didn't exist; Check for typo or create it"
                    })
                self.tasks[res["hook"]]["plan"].append(res["content"])
                return yaml.dump({
                    "type": "Result",
                    "data": None
                })
            elif res["type"] == "View":
                if not res["hook"] in self.tasks.keys():
                    return yaml.dump({
                        "type": "Error",
                        "data": "The task the plan want to hook to didn't exist; Check for typo or create it"
                    })
                data = self.tasks[res["hook"]]["plan"]
                return yaml.dump({
                    "type": "Result",
                    "data": data
                })
        elif value["type"] == "Memory":
            res = value["data"]
            if res["type"] == "Add":
                name, content = res["name"], res["content"]
                open(srcPath.parent / "memory" / name, "w").write(content)
            elif res["type"] == "View":
                name = res["name"]
                if name == None:
                    return yaml.dump({
                        "type": "Result",
                        "data": [p.name for p in Path(srcPath.parent / "memory").iterdir()]
                    })
                else:
                    if not (srcPath.parent / "memory" / name).exists():
                        return yaml.dump({
                            "type": "Error",
                            "data": f"Memory {name} doesn't exist"
                        })
                    return yaml.dump({
                        "type": "Result",
                        "data": open(srcPath.parent / "memory" / name, "r").read()
                    })
        elif value["type"] == "ScratchPad":
            append = value["data"]["append"]
            self.scratchPad += append
            return yaml.dump({
                "type": "Result",
                "data": self.scratchPad
            })
        elif value["type"] == "Fetch":
            try:
                data = value["data"]
                response = requests.request(
                    method=data.get("method", "GET"),
                    url=data["url"],
                    headers=data.get("headers"),
                    params=data.get("params"),
                    data=data.get("body"),
                    timeout=data.get("timeout", 10),
                    allow_redirects=True,
                )

                result = {
                    "type": "Result",
                    "data": {
                        "response": {
                            "status_code": response.status_code,
                            "reason": response.reason,
                            "url": response.url,
                            "headers": dict(response.headers),
                        }
                    }
                }
                content_type = response.headers.get("Content-Type", "")

                if is_text_response(content_type):
                    result["data"]["response"]["text"] = response.text

                else:
                    result["data"]["response"]["content_base64"] = (
                        base64.b64encode(response.content)
                        .decode("utf-8")
                    )

                return yaml.dump(result)
            except requests.Timeout:
                return yaml.dump({
                    "type": "Error",
                    "data": {
                        "error": {
                            "type": "Timeout",
                            "message": "Request timed out",
                        }
                    }
                })
            except requests.RequestException as e:
                return yaml.dump({
                    "type": "Error",
                    "data": {
                        "error": {
                            "type": type(e).__name__,
                            "message": str(e),
                        }
                    }
                })
        elif value["type"] == "SearchEngine":
            query, maxResults = value["data"]["query"], value["data"]["max_results"]
            url = "https://html.duckduckgo.com/html/"
            params = {"q": query}
            headers = {"User-Agent": "OperonAgent/0.1"}
            resp = requests.post(url, data=params, headers=headers)
            if resp.status_code != 200:
                return {"ok": False, "error": f"HTTP {resp.status_code}"}

            soup = BeautifulSoup(resp.text, "html.parser")
            results = []

            for a in soup.select("a.result__a")[:maxResults]:
                title = a.get_text()
                link = a['href']
                # DuckDuckGo sometimes wraps URL in redirects: /l/?kh=-1&uddg=URL
                if 'uddg=' in link:
                    import urllib.parse
                    link = urllib.parse.unquote(link.split('uddg=')[1])
                snippet_tag = a.find_parent("div", class_="result")
                snippet = snippet_tag.select_one("a.result__snippet")
                snippet_text = snippet.get_text() if snippet else ""
                results.append({
                    "title": title,
                    "snippet": snippet_text,
                    "url": link
                })

            return yaml.dump({
                "type": "Result",
                "data": results
            })

toolServer = ToolServer()