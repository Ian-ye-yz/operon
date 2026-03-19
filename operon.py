import operon
import yaml

if __name__ == "__main__":
    llm = operon.defaultLLM
    server = operon.toolServer
    msg = operon.USER(yaml.dump({
        "type": "Message",
        "data": input(">>> ")
    }))
    while True:
        res = llm(msg)
        # print(res)
        if res["type"] == "Print":
            print("LLM: ", res["data"])
            msg = operon.USER(yaml.dump({
                "type": "None",
                "data": None
            }))
        elif res["type"] == "END":
            msg = operon.USER(yaml.dump({
                "type": "Message",
                "data": input(">>> ")
            }))
        else:
            msg = operon.USER(server(res))