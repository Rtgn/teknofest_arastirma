import os
from jinja2 import Environment, FileSystemLoader

def _get_env():
    # prompt_builder.py utils altında olduğu için bir üst klasöre çıkıp prompts klasörünü baz alıyoruz.
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, 'prompts')
    return Environment(loader=FileSystemLoader(template_dir))

def build_factory_prompt(metrics):
    env = _get_env()
    template = env.get_template('factory_prompt.jinja')
    return template.render(**metrics)

def build_osb_prompt(metrics):
    env = _get_env()
    template = env.get_template('osb_prompt.jinja')
    return template.render(**metrics)
