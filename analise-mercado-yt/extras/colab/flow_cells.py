"""Células do fluxo automático; usadas pelo gerador do notebook (build_notebook.py)."""


def add_cells(md, code):
    md('''## 7. IA e piloto automáticos
    Não envie plan.json: a IA conectada gera as hipóteses, o notebook coleta o mercado e a IA avalia as evidências.
    `dados` usa só um piloto já coletado, sem IA nem novas buscas; gera relatório técnico, sem recomendações.
    `colab` usa a IA disponível na sua sessão ou conta. Se estiver indisponível, escolha `gemini`, crie uma chave no AI Studio
    e salve `GEMINI_API_KEY` em Secrets. Para evitar cobrança, use um projeto Gemini na faixa gratuita.
    O notebook não ativa faturamento nem muda de provedor sozinho. A chave do YouTube não fornece IA.
    Os dados enviados ao modelo são o pedido e evidências públicas; não coloque informações privadas no pedido.
    ''')
    code('''
    AI_BACKEND = 'colab' # @param ["colab", "gemini", "dados"]
    AI_MODEL = '' # @param {type:"string"}
    PILOT_DURATION = 'longform' # @param ["medium", "long", "longform"]
    PILOT_BUDGET = 24 # @param {type:"integer"}
    from text_ai import TextAI, AIError
    from notebook_flow import initial_analysis, finish_analysis
    if AI_BACKEND == 'gemini' and not os.environ.get('GEMINI_API_KEY', '').strip():
        try:
            os.environ['GEMINI_API_KEY'] = userdata.get('GEMINI_API_KEY').strip()
        except (userdata.SecretNotFoundError, userdata.NotebookAccessError):
            raise ValueError('Crie GEMINI_API_KEY em Secrets e permita o acesso ao notebook. Use projeto gratuito para evitar cobrança.') from None
    ai = TextAI(RUN, backend=AI_BACKEND, model=AI_MODEL, max_calls=8)
    phase = initial_analysis(RUN, REQUEST, ai, duration=PILOT_DURATION, pilot_budget=PILOT_BUDGET)
    ''')
    md('''## 8. Sua única escolha durante a análise
    Veja o ranking acima, escolha recortes e mercados, veja o custo e clique em **Aprofundar seleção**.
    Esse botão coleta os dados adicionais, escreve e valida o analysis.json e gera e baixa o relatório automaticamente.
    Se houver uma seleção válida de uma sessão anterior, o fluxo retoma essa seleção sem perguntar de novo.
    `Teto buscas/gerais` cobre matriz + sondagens sem cache; perfis e piloto são informados à parte.
    Não há upload intermediário, troca de ZIP com agente nem importação manual da análise.
    ''')
    code('''
    import ipywidgets as widgets
    from IPython.display import display, clear_output
    from selection import select
    def finish_and_download():
        report = finish_analysis(RUN, REQUEST, ai)
        files.download(str(report))
        files.download(str(export_run(RUN, Path('/content/DarkNiche-analise.zip'))))
    if phase == 'selected':
        finish_and_download()
    else:
        proposal = read_json(RUN / 'proposal.json')
        data_only = AI_BACKEND == 'dados'
        recortes = widgets.SelectMultiple(options=[(f"{c.get('priority', '?')}. {c.get('label', c['id'])}", c['id']) for c in sorted(proposal['cells'], key=lambda c: c.get('priority', 999))], value=(), description='Recortes:')
        idiomas = widgets.SelectMultiple(options=[(f"{l['lang']}/{l.get('region', '?')}", l['lang']) for l in proposal['languages']], value=(), description='Mercados:')
        search_budget = widgets.BoundedIntText(value=60, min=0, max=95, description='Teto buscas:')
        unit_budget = widgets.BoundedIntText(value=500, min=0, max=9500, description='Teto gerais:')
        preview_button = widgets.Button(description='Ver custo da seleção')
        confirm_button = widgets.Button(description='Gerar relatório dos dados' if data_only else 'Aprofundar seleção', button_style='success')
        output = widgets.Output()
        previewed = None
        def choices():
            return (tuple(recortes.value), tuple(idiomas.value), (), search_budget.value, unit_budget.value)
        def preview(_):
            global previewed
            with output:
                clear_output()
                try:
                    selected = choices()
                    state = select(RUN, *selected, dry_run=True)
                    print('Matriz + sondagens sem cache:', state['scan_estimate'])
                    print('Resultados idênticos do piloto serão reutilizados.')
                    print('Modo dados: nenhuma nova busca, perfil ou chamada de IA será executada.' if data_only else 'Perfis adicionais: até 12 concorrentes + referência, 60 uploads/canal (~5 gerais/canal), fora do teto do scan.')
                    previewed = selected
                except ValueError as e:
                    previewed = None
                    print(e)
        def confirm(_):
            with output:
                clear_output()
                if previewed != choices():
                    print('Escolha os recortes e mercados e veja o custo antes de aprofundar.')
                    return
                confirm_button.disabled = True
                preview_button.disabled = True
                try:
                    select(RUN, *choices())
                    print('Escolha registrada. Gerando relatório dos dados existentes…' if data_only else 'Escolha registrada. Coletando, analisando e gerando o relatório…')
                    finish_and_download()
                    print('Concluído. O HTML e as evidências foram enviados para download.')
                except (AIError, ValueError, RuntimeError) as e:
                    print(e)
                    print('Dados e seleção preservados. Corrija a causa e clique de novo para retomar.')
                finally:
                    confirm_button.disabled = False
                    preview_button.disabled = False
        preview_button.on_click(preview)
        confirm_button.on_click(confirm)
        display(widgets.VBox([recortes, idiomas, search_budget, unit_budget, preview_button, confirm_button, output]))
    ''')
    md('''**Executar tudo:** preencha os campos antes e use Ambiente de execução → Executar tudo.
    Na primeira preparação haverá upload do código e, se você ligou o Drive, o login nele. Depois, plano, piloto e ranking
    são automáticos; o notebook termina mostrando a seleção. O botão **Aprofundar seleção** segue até o HTML.
    Se a IA, a cota ou a rede falharem, aparece um erro explícito e o estado fica salvo; não há seletor de arquivo oculto.
    Guia: `analise-mercado-yt/extras/colab/colab.md`. A faixa gratuita do Gemini depende do projeto e da conta; não é garantida
    pela chave nem por usar o Colab gratuito. [Preços oficiais](https://ai.google.dev/gemini-api/docs/pricing).
    ''')
