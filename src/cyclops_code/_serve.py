"""textual serve entry point. Run directly: python _serve.py"""
import os
from cyclops_code.repl import CyclopsApp
from cyclops_code.config import Config


def app():
    config = Config(model="ollama/qwen2.5:14b", stream=False)
    return CyclopsApp(config=config, cwd=os.path.expanduser("~"))


if __name__ == "__main__":
    app().run()
