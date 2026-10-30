"""Gera os notebooks do Colab (sem outputs nem segredos). Rode depois de editar o código:

    python analise-mercado-yt/extras/colab/build_notebook.py

Saída, ao lado deste arquivo: DarkNiche.ipynb (análise completa com IA) e DarkNiche-Retomar.ipynb (modo dados: consulta
uma análise já coletada, sem IA e sem novas buscas). Depois gere o ZIP que o notebook pede: package_colab.py.
"""
import copy
import json
import textwrap
from pathlib import Path

cells = []


def md(text):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": textwrap.dedent(text).strip().splitlines(True)})


def code(text):
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": textwrap.dedent(text).strip().splitlines(True)})


md('''
# DarkNiche no Colab: triagem com dados e escolha do aprofundamento
Use runtime **CPU**. Preencha os campos e use Executar tudo. Configure uma IA disponível no Colab ou a Gemini API (faixa gratuita, conforme o projeto).
A IA conectada interpreta referência e mercado, propõe opções com evidências e escreve o relatório automaticamente. A coleta inicial usa até 24 buscas; o aprofundamento só vem depois da sua escolha.
O Colab gratuito não aumenta a cota do YouTube e pode interromper a sessão. O Drive é opcional e guarda o estado.
Os seletores começam vazios. "Executar tudo" não autoriza o aprofundamento por conta própria.
Neste caminho não há pesquisa na web: receita, risco e preços saem do conhecimento do modelo e o relatório avisa isso nas limitações.
''')
md('''## 1. Enviar o pacote de código
Envie `DarkNiche-Colab.zip`. Gere-o no seu computador com `python analise-mercado-yt/extras/colab/package_colab.py` (ele cria `dist/DarkNiche-Colab.zip`) ou baixe da página de releases do projeto. Não envie `.env` nem credenciais.
''')
code('''
from google.colab import files
from pathlib import Path, PurePosixPath
import io, json, os, stat, subprocess, sys, zipfile
ROOT = Path('/content/DarkNiche')
uploads = files.upload()
bundles = [data for name, data in uploads.items() if name.lower().endswith('.zip')]
if len(bundles) != 1:
    raise ValueError('Envie exatamente um ZIP do código.')
with zipfile.ZipFile(io.BytesIO(bundles[0])) as archive:
    for item in archive.infolist():
        path = PurePosixPath(item.filename)
        if (path.is_absolute() or '..' in path.parts or '\\\\' in item.filename or ':' in item.filename
                or stat.S_ISLNK(item.external_attr >> 16)
                or any(p.startswith('.') for p in path.parts)):
            raise ValueError('Pacote contém caminho não permitido.')
        target = ROOT.joinpath(*path.parts)
        if not target.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError('Caminho fora da pasta de código.')
    archive.extractall(ROOT)
del uploads, bundles
if not (ROOT / 'analise-mercado-yt/SKILL.md').is_file():
    raise ValueError('Pacote DarkNiche inválido.')
print('Código carregado; nenhuma chave importada.')
''')
md('''## 2. Dependências
A coleta básica pela API usa CPU e não precisa de ffmpeg. Transcrição e vídeo são opcionais.
''')
code('''
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', str(ROOT / 'requirements.txt'), 'ipywidgets>=8', 'openai>=1'], check=True)
print('Dependências instaladas.')
''')
md('''## 3. Persistência
Com Drive, retome usando a mesma pasta. Evite sessões simultâneas no mesmo contador e cache.
Sem Drive, baixe as evidências ao terminar: a VM do Colab é temporária.
''')
code('''
USE_DRIVE = True # @param {type:"boolean"}
if USE_DRIVE:
    from google.colab import drive
    drive.mount('/content/drive')
    STATE = Path('/content/drive/MyDrive/DarkNiche-state')
else:
    STATE = Path('/content/DarkNiche-state')
STATE.mkdir(parents=True, exist_ok=True)
os.environ['AMY_HOME'] = str(STATE / 'runtime')
os.environ.setdefault('YT_SEARCH_DAILY_BUDGET', '95')
os.environ.setdefault('YT_DAILY_BUDGET', '9500')
SKILL = ROOT / 'analise-mercado-yt'
SCRIPTS = SKILL / 'scripts'
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SKILL / 'extras/colab'))
from colab_support import migrate_legacy_state
migrated = migrate_legacy_state(Path.home() / '.analise-mercado-yt', Path(os.environ['AMY_HOME']))
if migrated:
    print('Estado local anterior preservado:', ', '.join(migrated))
from common import read_json, write_json, set_run
from selection import propose, select, require_selection, estimate_plan, require_triage
from colab_support import export_run
def command(script, *args):
    subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], check=True, cwd=ROOT)
print('Estado preparado. O contador é local; o uso em outras máquinas não é conhecido.')
''')
md('''## 4. Chave em Secrets
Crie `YOUTUBE_API_KEY` no ícone de chave do Colab e permita o acesso ao notebook.
Sem secret nem variável, use o prompt oculto. A chave fica só no ambiente da VM.
''')
code('''
from getpass import getpass
from google.colab import userdata
key_names = ('YT_API_KEY', 'YOUTUBE_API_KEY', 'YOUTUBE_DATA_API_KEY', 'YOUTUBE_DATA_API_V3_KEY')
if not any(os.environ.get(name, '').strip() for name in key_names):
    for name in key_names:
        try:
            secret_value = userdata.get(name)
        except (userdata.SecretNotFoundError, userdata.NotebookAccessError):
            continue
        if secret_value and secret_value.strip():
            os.environ[name] = secret_value.strip()
            del secret_value
            break
if not any(os.environ.get(name, '').strip() for name in key_names):
    os.environ['YOUTUBE_API_KEY'] = getpass('YouTube Data API key: ').strip()
command('doctor.py', '--no-api')
''')
md('''## 5. Criar ou retomar análise
Para retomar, informe o caminho em `EXISTING_RUN`. O pedido pode limitar idiomas e orçamento.
''')
code('''
TITLE = 'Minha análise' # @param {type:"string"}
REFERENCE = '' # @param {type:"string"}
LANGUAGES = 'pt,en,es' # @param {type:"string"}
REQUEST = 'Avaliar se vale abrir um canal neste nicho, nesses mercados.' # @param {type:"string"}
EXISTING_RUN = '' # @param {type:"string"}
if EXISTING_RUN.strip():
    if '<' in EXISTING_RUN:
        raise ValueError('Preencha EXISTING_RUN com a pasta real da análise no Drive (troque o texto entre < e >).')
    RUN = Path(EXISTING_RUN).expanduser()
    if not (RUN / 'plan.json').is_file():
        raise ValueError('Pasta existente não contém plan.json.')
else:
    from common import slug
    from datetime import date
    RUN = STATE / 'analises' / f'{slug(TITLE, 40)}-{date.today():%Y-%m}'
    if not (RUN / 'plan.json').exists():
        args = [TITLE, '--langs', LANGUAGES, '--dir', STATE / 'analises']
        if REFERENCE.strip():
            args += ['--ref', REFERENCE.strip()]
        command('init_run.py', *args)
set_run(RUN)
print('Análise:', RUN)
''')
md('''## 6. Referência inicial (opcional)
Só com canal ou vídeo de referência: até 60 uploads, cerca de 5 a 7 unidades gerais e zero buscas. Sem download de vídeo.
Sem referência (análise de nicho ou ideia), esta etapa não faz nada.
''')
code('''
plan = read_json(RUN / 'plan.json')
ref = plan.get('reference') or {}
COLLECT_REFERENCE = True # @param {type:"boolean"}
if COLLECT_REFERENCE and ref.get('value') in ('@handle_do_canal', '@handle', '@canal'):
    raise ValueError('A referência é um placeholder. Defina um canal real antes de analisar; ela não será trocada automaticamente.')
if COLLECT_REFERENCE and ref.get('value') and not (RUN / 'data/reference.json').exists():
    command('reference.py', '--run', RUN, ref['value'], '--max', '60', '--no-ytdlp')
print('Referência pronta; o modo ideia usa o seu pedido.')
''')
from flow_cells import add_cells
add_cells(md, code)

notebook = {"nbformat": 4, "nbformat_minor": 5, "metadata": {"colab": {"name": "DarkNiche.ipynb"},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}, "cells": cells}
for i, cell in enumerate(cells):
    cell["id"] = f"darkniche-{i:02d}"
path = Path(__file__).with_name('DarkNiche.ipynb')
path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(path)

# Versão de retomada: consulta uma análise que já existe no Drive, sem IA, sem chaves e sem novas buscas.
recovery = copy.deepcopy(notebook)
recovery['metadata']['colab']['name'] = 'DarkNiche-Retomar.ipynb'
for cell in recovery['cells']:
    source = ''.join(cell['source'])
    if cell['cell_type'] == 'code':
        source = source.replace("EXISTING_RUN = ''", "EXISTING_RUN = '/content/drive/MyDrive/DarkNiche-state/analises/<pasta-da-analise>'")
        source = source.replace("AI_BACKEND = 'colab'", "AI_BACKEND = 'dados'")
        source = source.replace('COLLECT_REFERENCE = True', 'COLLECT_REFERENCE = False')
        source = source.replace("REQUEST = 'Avaliar se vale abrir um canal neste nicho, nesses mercados.'", "REQUEST = 'Consultar os dados já coletados e gerar relatório técnico, sem novas buscas e sem recomendação estratégica.'")
        if source.startswith('from getpass import getpass'):
            source = "from google.colab import userdata\nprint('Modo dados: nenhuma chave do YouTube ou do Gemini é necessária para consultar os arquivos existentes.')\n"
    elif '## 4. Chave em Secrets' in source:
        source = '## 4. Sem credenciais no modo dados\nEste notebook lê só arquivos existentes. Não pede chaves nem consome cota do YouTube ou de IA.\n'
    cell['source'] = source.splitlines(True)
recovery['cells'][0]['source'] = ("# DarkNiche · retomar uma análise existente, sem IA e sem novas buscas\n"
    "Aponte `EXISTING_RUN` para a pasta da análise no Drive (`MyDrive/DarkNiche-state/analises/<pasta>`) e envie o ZIP de código na primeira célula.\n"
    "O modo dados não precisa de modelo, de Gemini API nem de crédito de assistente. Ele não avalia fit cultural nem recomenda nichos: mostra os dados coletados.\n"
    "Execute tudo, escolha os recortes e idiomas e clique em Gerar relatório dos dados. Para uma análise estratégica com IA, use o notebook principal.\n").splitlines(True)
recovery_path = path.with_name('DarkNiche-Retomar.ipynb')
recovery_path.write_text(json.dumps(recovery, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(recovery_path)
