> Revisão de 12/10/2026: este arquivo contém pesquisa histórica não revalidada integralmente.
> Os rótulos [F] abaixo foram herdados do autor original; não comprovam validação nesta revisão.
> Não presuma GPU, ferramentas instaladas, preços, licenças ou disponibilidade de modelos a partir dele.
> Consulte o perfil real e confirme cada dado decisivo na fonte oficial. Valores por vídeo são exemplos históricos.

> **Como usar este arquivo.** Custos, viabilidade local/solo e riscos de produção para os eixos A (automação),
> K (custo de IA) e S (solo/local), e para a seção de produção do relatório. A §11 tem o custo por vídeo de 5 estilos;
> a §12 tem as rubricas de automação, local e solo; a §13 tem os riscos de política do YouTube.
> Pesquisa de 12/10/2026 (preços mudam rápido): quando um custo decidir a recomendação, confirme o preço na página
> oficial do fornecedor (WebSearch/WebFetch) e registre a data. O perfil do usuário (hardware e ferramentas) fica em
> ~/.analise-mercado-yt/perfil.json; recalcule os custos para a stack dele, não para uma stack genérica.
>
> Sumário: §0 legenda e premissas · §1 exemplo de perfil local (TTS local e orquestração) · §2–3 TTS nuvem/local ·
> §4 LLM · §5 transcrição · §6 imagem · §7 vídeo IA · §8 motion programático · §9 música · §10 thumbnails ·
> §11 custo por vídeo · §12 rubricas · §13 riscos de política · §14 lacunas

# Referência de produção: custos, viabilidade local e riscos (canal faceless YouTube)

Data da pesquisa: 12/10/2026. Moeda: US$ (salvo indicação). Perfil do caso original: GPU de 8 GB e stack específica; não transferir para outros usuários. O perfil real está em perfil.json.

## 0. Como ler este arquivo

- **[F]** = página aberta e lida diretamente (README/doc oficial, GitHub ou platform.claude.com). Confiança alta.
- **(via busca)** = apenas snippet do WebSearch; sites de terceiros costumam divergir entre si. Confiança média/baixa, reconfirmar antes de contratar.
- **não encontrado** = não consegui confirmar. Não preencher com palpite.
- **[EST]** = estimativa minha (cálculo ou ordem de grandeza), não é dado de fonte. A skill deve tratar como intervalo, não como valor exato.
- Páginas oficiais de ElevenLabs, OpenAI, Google (ai.google.dev), Fish Audio e Hugging Face não puderam ser abertas neste ambiente (DNS bloqueado). Preços desses vêm de snippets.

### Premissas de cálculo (usadas na seção 11)

| Item | Premissa |
|---|---|
| Narração PT-BR | 150 palavras/min, cerca de 6 caracteres/palavra com espaço. 10 min = 1.500 palavras = ~10.000 caracteres. 20 min = 3.000 palavras = ~20.000 caracteres [EST] |
| Retakes de TTS | multiplicar por 1,3 no custo de nuvem [EST] |
| Energia | PC sob carga ~300 W, US$ 0,15/kWh (tarifas BR giram em R$ 0,80-1,00/kWh). 1 h de GPU = US$ 0,045 [EST, premissa] |
| Imagens por vídeo (Ken Burns) | 1 imagem a cada 6-8 s. 10 min = 75-100; 20 min = 150-200. Com 1,5x de rerolls: ~130 e ~260 gerações [EST] |
| Clipes de IA | clipe de 5 s; 1,5x de rerolls [EST] |
| LLM roteiro + pesquisa | ver seção 4 |
| "100% local" | TTS, transcrição, imagem e render locais. O LLM local de 8 GB (modelos 7-8B) escreve pior que Claude; contabilizo US$ 0 de API, mas com queda de qualidade e mais horas humanas. O OpenMontage ainda não suporta LLM local (Ollama/LM Studio "coming soon") [F] |
| "Híbrido" | LLM em nuvem (Sonnet 5.5) + TTS, transcrição e render locais + nuvem apenas no gargalo visual |
| "100% nuvem" | Opus 5.5 + ElevenLabs + imagem/vídeo em API + transcrição em nuvem |

---

## 1. Exemplo de perfil local

As duas ferramentas abaixo descrevem **um perfil real** (o do autor original: GPU NVIDIA de 8 GB, TTS local e um
orquestrador de produção). Servem de exemplo de como medir uma ferramenta local (idiomas, VRAM, licença, velocidade).
Se o perfil do usuário usa outras, ignore esta seção, compare as opções das §2 a §10 e **pesquise o preço e a licença
hoje** (`pesquisa-web.md` §2.5), registrando com `research.py`.

### 1.1 Exemplo: TTS local (OmniVoice)

| Campo | Dado | Fonte |
|---|---|---|
| O que é | Modelo TTS zero-shot multilíngue da k2-fsa: "High-Quality Voice Cloning TTS for 600+ Languages". Arquitetura non-autoregressive tipo difusão sobre tokens acústicos multicodebook; base Qwen3 0.6B segundo terceiros | [F] https://github.com/k2-fsa/OmniVoice ; paper arXiv 2604.00688 (via busca) |
| Idiomas | 646 idiomas, ~581 mil horas de treino. Os 11 pedidos estão todos presentes (horas de treino): pt 16.855; es 27.560; fr 23.675; de 21.927; it 9.402; ja 36.914; pl 912; ro 70; bg 2.191; tr 125; id 6.328 | [F] https://github.com/k2-fsa/OmniVoice/blob/master/docs/languages.md |
| Leitura prática dos idiomas | PT, ES, FR, DE, IT, JA, ID têm muito dado (milhares de horas): tendem a ser o melhor caso. PL é intermediário. **RO (70 h) e TR (125 h) têm pouquíssimo dado**: esperar pronúncia/prosódia mais fraca; testar antes de comprometer um canal nesses idiomas [EST, inferência a partir das horas] | idem |
| Qualidade | O README chama a clonagem de "state-of-the-art" mas **não publica MOS/WER por idioma**. Não achei teste independente de PT-BR. Terceiros dizem que é menos polido que serviços comerciais | [F] README; https://techsy.io/en/blog/omnivoice-review (via busca) |
| Clonagem | Referência de 3-10 s, de preferência **no mesmo idioma do texto** (referência em outro idioma deixa sotaque do idioma da referência). `ref_text` opcional (Whisper transcreve). Voz clonada pode ser salva | [F] README; HF model card (via busca) |
| Voice design | Descreve gênero, idade, tom, sotaque; **treinado só em chinês e inglês**, pode ser instável em outros | [F] README |
| Extras | Tags não verbais (`[laughter]`), correção de pronúncia por pinyin/fonemas CMU; CLI `omnivoice-infer`, `omnivoice-infer-batch`, demo web | [F] README |
| VRAM | README **não informa**. Uma review independente (1 teste) diz ~8 GB suficientes em fp16. Wrapper ComfyUI (Saganaki22) recomenda GPU CUDA. Na prática: cabe numa GPU de 8 GB, mas **não rodar junto com Whisper/imagem** | https://techsy.io/en/blog/omnivoice-review (via busca) |
| Velocidade | RTF "tão baixo quanto 0,025" (~40x tempo real). Benchmark oficial em H100 fp16, 32 passos, clonagem: RTF 0,0899 (batch 1) e 0,0115 (batch 8). Review em RTX 4090: RTF ~0,03; cold start ~14 s. Numa GPU de 8 GB, esperar RTF 0,05-0,2, ou seja 20 min de áudio em ~1-4 min [EST] | [F] README; techsy (via busca) |
| Licença | **Apache-2.0** (repo) | [F] README. Licença dos pesos e dos dados de treino: confirmar no model card HF `k2-fsa/OmniVoice` (não consegui abrir) |
| Instalação | `pip install omnivoice`, PyTorch 2.8 + CUDA recomendado | [F] README |
| Limites | Não projetado para conversa em tempo real; pronúncia de siglas/números/estrangeirismos exige normalização de texto (regra geral de TTS) [EST] | techsy (via busca) |

Nota de política: clonar voz de terceiros (ou de pessoa real sem consentimento) cai nas regras da seção 12. Use voz própria, voz criada por voice design ou voz com licença/consentimento documentado.

### 1.2 Exemplo: orquestração de produção (OpenMontage)

| Campo | Dado | Fonte |
|---|---|---|
| O que é | Sistema open-source "agentic" de produção de vídeo que roda dentro de um assistente de código (Claude Code, Cursor, Copilot, Windsurf, Codex). O agente orquestra; o repositório fornece ferramentas Python, manifestos YAML de pipeline e skills em Markdown | [F] https://github.com/calesthio/OpenMontage |
| Pipelines | Animated Explainer, Animation, Avatar Spokesperson, Cinematic, Clip Factory, Documentary Montage, Hybrid, Localization & Dub, Podcast Repurpose, Screen Demo, Talking Head (a página diz "12" mas lista 11). Fluxo comum: pesquisa, proposta, roteiro, plano de cenas, assets, edição, composição | [F] |
| O que automatiza | Pesquisa web antes do roteiro; geração de imagem, vídeo, narração e música; **legendas word-level (WhisperX)**; montagem, corte, mix de áudio, color grade; render via **Remotion (React) ou HyperFrames (HTML/GSAP)** + FFmpeg; checagens pós-render (ffprobe, amostragem de frames, loudness, legendas); portões de aprovação humana; **orçamento: estimativa, reserva e reconciliação de custo; modos observe/warn/cap; teto padrão US$ 10; aprovação por ação acima de US$ 0,50** | [F] |
| Dependências | Python 3.10+, FFmpeg, Node.js 18+ (HyperFrames exige Node 22+), `npm install` em `remotion-composer`, um assistente de código. GPU só para vídeo local (`make install-gpu`, depois `VIDEO_GEN_LOCAL_ENABLED=true` e `VIDEO_GEN_LOCAL_MODEL`, ex.: `wan2.2-ti2v-5b`, `ltx2-local`) | [F] |
| Opções locais/gratuitas | Piper TTS (offline), Stable Diffusion local, WhisperX, Archive.org/NASA/Wikimedia, Pexels/Pixabay/Unsplash (chave gratuita), Wan/Hunyuan/CogVideo/LTX local, ManimCE. Exemplos citados no README: ~US$ 1,33 por short animado de 60 s e ~US$ 4 por filme vertical de 50 s | [F] |
| TTS suportado | ElevenLabs, Google TTS, OpenAI TTS, Piper, Azure Speech, DashScope/Doubao/Fish Audio. **OmniVoice, Kokoro e Chatterbox não aparecem no README**: integrar OmniVoice exige escrever um tool wrapper (ou usar o fluxo próprio da skill). PT-BR não é citado nominalmente | [F] |
| Limites | LLM local ainda "coming soon" (precisa de LLM em nuvem); qualidade máxima exige chaves pagas; bug conhecido de `npm install` no Windows (`npx --yes npm install`). Sem seção de limites formal | [F] |
| Licença | **AGPL-3.0**. Para uso próprio (rodar localmente) não há problema; se oferecer o sistema modificado como serviço de rede, obriga a abrir o código. Os vídeos gerados não são "contaminados" pela licença (regra geral da AGPL; não é aconselhamento jurídico) | [F] |
| Atividade | ~67 mil estrelas, 455 commits, 113 issues, 286 PRs abertos. Sem data de último commit visível | [F] |

---

## 2. TTS: nuvem

Conversão usada: 1 min de fala PT-BR ~ 1.000 caracteres.

| Ferramenta | Preço | Custo de 20 min (~20k car.) | Idiomas / notas | Licença/uso comercial | Fonte |
|---|---|---|---|---|---|
| ElevenLabs API | Multilingual v2 e v3: **US$ 0,10/1k car.**; Flash/Turbo: **US$ 0,05/1k car.** (faturado em dólar, não em créditos). v3 limitado a 5.000 car. por requisição | US$ 2,00 / US$ 1,00 | ~32 idiomas (via techsy) | Comercial só em plano pago | (via busca) https://developer.puter.com/tutorials/elevenlabs-api-pricing/ ; https://modelslab.com/elevenlabs-api-pricing.md |
| ElevenLabs planos | Free US$ 0 (10k créditos, **não comercial**); Starter ~US$ 5-6 (30k); Creator ~US$ 22 (100-121k); Pro ~US$ 99 (500-600k); Scale ~US$ 299-330 (1,8-2M); Business ~US$ 990-1.320. Créditos divergem entre fontes. Regra prática: 1 crédito ~ 1 caractere no Multilingual v2 (Flash gasta menos) | Creator cobre ~5-6 vídeos de 20 min/mês | Clonagem profissional a partir do Creator | | (via busca) https://smallest.ai/blog/elevenlabs-pricing-plans-cost-what-you-get-in-2026 ; https://dupple.com/pricing/elevenlabs |
| OpenAI TTS | `tts-1`: US$ 15/1M car.; `gpt-4o-mini-tts`: US$ 0,60/1M tokens de texto + US$ 12/1M tokens de áudio (~US$ 0,015/min, estimativa) | US$ 0,30 | Multilíngue; voz sintética fixa | Comercial permitido; exige divulgar que é voz de IA ao usuário em apps | (via busca) https://costgoat.com/pricing/openai-tts ; https://developers.openai.com/api/docs/models/gpt-4o-mini-tts |
| Google Cloud TTS | Standard/WaveNet US$ 4/1M car. (4M grátis/mês WaveNet); Neural2/Polyglot US$ 16/1M (1M grátis); **Chirp 3 HD US$ 30/1M** (1M grátis); Studio US$ 160/1M; Chirp 3 Instant Custom Voice US$ 60/1M; Gemini TTS por tokens (US$ 1/1M entrada, US$ 20/1M saída de áudio, 25 tokens/s de áudio) | WaveNet US$ 0,08; Neural2 US$ 0,32; Chirp3 HD US$ 0,60; Gemini TTS ~US$ 0,60 (1.200 s x 25 tokens x US$ 20/1M) [EST] | 50+ idiomas, 700+ vozes (via OpenMontage) | Comercial permitido | (via busca) https://cloud.google.com/text-to-speech/pricing |
| Azure AI Speech | Neural US$ 15/1M car.; HD US$ 30/1M car. Franquia grátis diverge (500 mil vs 5M car./mês) | US$ 0,30 / US$ 0,60 | 140+ idiomas (regra geral, não verificado) | Comercial permitido | (via busca) https://docs.litellm.ai/docs/providers/azure_ai_speech ; https://azure.microsoft.com/pricing/details/speech/ |
| Fish Audio | API **US$ 15/1M bytes UTF-8** (1M bytes ~ 180 mil palavras ou ~12 h de fala, segundo a doc). Planos: Free (personal), Plus ~US$ 20/mês (200 min), Pro ~US$ 150/mês (1.620 min); valores de plano só em fontes de terceiros | ~US$ 0,33 (bytes PT > caracteres) [EST] | Multilíngue; modelos S1/S2 | Comercial a partir do plano pago | (via busca) https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits |
| Cartesia Sonic | ~1 crédito por caractere; Free 10-20k créditos (não comercial); Pro ~US$ 4/mês (100k); Startup ~US$ 39-49 (1,25M); Scale ~US$ 239-299 (8M); ~US$ 0,037/1k car. no Scale. **Fontes divergem** | ~US$ 0,75 | Multilíngue (lista não confirmada) | Comercial em plano pago | (via busca) https://www.cloudtalk.io/blog/cartesia-pricing/ |
| Deepgram Aura / outros | não pesquisado | | | | |

## 3. TTS: local

| Ferramenta | Idiomas | VRAM | Clonagem | Licença | Observações | Fonte |
|---|---|---|---|---|---|---|
| **OmniVoice** | 646 (inclui PT, ES, FR, DE, IT, JA, PL, RO, BG, TR, ID) | ~8 GB (1 review) | Sim, 3-10 s | Apache-2.0 | Ver 1.1 | [F] |
| **Kokoro-82M** | Inglês US/UK, ES, FR, HI, IT, JA, PT-BR, ZH (poucas vozes por idioma: ~3 PT-BR, 3 ES, 1 FR, 2 IT, 5 JA) | Mínima; roda em CPU | **Não** (vozes fixas) | **Apache-2.0** (pesos) | 82M parâmetros. Bom fallback leve e rápido; sem DE, PL, RO, BG, TR, ID | [F] https://github.com/hexgrad/kokoro ; contagem de vozes (via busca) |
| **Chatterbox Multilingual** (Resemble AI) | 23 idiomas, incluindo PT (há finetunes pt-br e pt-pt) | não informado no README (~0,5B parâmetros) | Sim, ~5 s | **MIT** | Marca d'água **Perth** inaudível em todo áudio gerado. Turbo (350M) e Nano (110M) são só inglês | [F] https://github.com/resemble-ai/chatterbox |
| **XTTS-v2 / Coqui** | 16-17 idiomas (PT, ES, FR, DE, IT, PL, TR, JA...) | ~4-6 GB (via busca) | Sim, ~6 s | Código MPL-2.0; **pesos sob CPML (Coqui Public Model License): uso apenas NÃO comercial**. Coqui encerrou atividades (dez/2023-jan/2024), então não há como comprar licença comercial | **Evitar em canal monetizado.** Risco jurídico real, ainda que a aplicação seja improvável | [F] repo (MPL-2.0, 16 idiomas); licença CPML (via busca) https://www.promptquorum.com/power-local-llm/xtts-v2-review |
| **F5-TTS** | Modelos oficiais EN/ZH (Emilia); outros idiomas por checkpoints da comunidade | ~2-3 GB fp16 (via busca) | Sim | Código MIT; **pesos CC-BY-NC** (dados Emilia) | Não usar monetizado | [F] https://github.com/SWivid/F5-TTS |
| **Orpheus TTS** (Canopy Labs) | Inglês forte; família multilíngue em "research preview" (zh, hi, ko citados); PT/ES/FR/DE não confirmados | não encontrado (3B é pesado para 8 GB sem quantização) | Limitada | Apache-2.0 (via busca) | Pouco útil para PT-BR hoje | (via busca) https://www.hackster.io/news/canopy-labs-releases-orpheus-a-permissively-licensed-llm-for-convincing-text-to-speech-afc64416767d |
| **VibeVoice** (Microsoft) | TTS-1.5B: EN/ZH. Realtime-0.5B experimental: DE, FR, IT, JA, KO, NL, PL, PT, ES | não informado (1.5B ~5,4 GB e 7B ~18 GB segundo terceiros) | Restrita | MIT, **mas código de TTS foi removido do repo em 05/09/2025 por uso indevido; "somente pesquisa", não recomendado para uso comercial/real** | Até 90 min / 4 falantes (1.5B). Não confiar | [F] https://github.com/microsoft/VibeVoice |
| **Higgs Audio v3** (Boson AI) | "100+ idiomas" (lista não publicada) | não informado (~4B parâmetros) | Sim | **Research and Non-Commercial License; uso em produção ou gerador de receita exige licença comercial** (README indica Apache-2.0 só para o código do repo) | Não usar monetizado sem licença | [F] https://github.com/boson-ai/higgs-audio |
| **Piper** | Muitos idiomas, vozes de qualidade média | CPU | Não | Licença atual do Piper (GPL) não verificada | Fallback "zero-key" do OpenMontage | [F] OpenMontage README |

Recomendação para a skill (confirme a licença hoje, `pesquisa-web.md` §2.5): entre as locais com licença permissiva, o perfil escolhe a que cobre o idioma-alvo com qualidade: OmniVoice (Apache-2.0), Kokoro (PT/ES/FR/IT/JA) e Chatterbox Multilingual (MIT) são as candidatas desta tabela. Nunca sugerir XTTS-v2, F5-TTS (pesos) e Higgs Audio v3 para canal monetizado.

---

## 4. LLM para pesquisa e roteiro

### 4.1 Calcular com o modelo e plano reais

A tabela de preços/modelos herdada foi removida: não havia evidência verificável para tratá-la como atual.
Use o provedor configurado em Codex, OpenCode, Antigravity ou Claude Code. Consulte seu preço oficial na data

da análise; não troque o modelo escolhido pelo usuário para encaixar uma tabela fixa.

Custo de tokens = entrada não cacheada × tarifa de entrada + cache × tarifa de cache + saída × tarifa de saída,
respeitando a unidade de cobrança (por milhão de tokens). Some ferramentas, imagens, buscas e retakes quando
cobrados à parte. Apresente cenários e registre as quantidades usadas; não atribua consumo medido a estimativas.

Assinatura com uso incluído pode ter custo marginal de API zero até os limites do plano; a mensalidade e os
limites continuam existindo. OpenCode com chave própria costuma cobrar pelo provedor. Um LLM acessado em
nuvem continua em nuvem mesmo quando o agente e o render rodam no PC.


## 5. Transcrição e alinhamento

| Ferramenta | Local/Nuvem | Velocidade / VRAM | Preço | Licença | Fonte |
|---|---|---|---|---|---|
| **faster-whisper** | Local | large-v2, 13 min de áudio, RTX 3070 Ti 8 GB: fp16 1m03s e 4,5 GB; fp16 batch 8: **17 s e 6,1 GB**; int8: 59 s e 2,9 GB; int8 batch 8: 16 s e 4,5 GB. Suporta `turbo`; sem benchmark de large-v3/turbo no README | US$ 0 | MIT | [F] https://github.com/SYSTRAN/faster-whisper |
| **WhisperX** | Local | Alegação do projeto: **70x tempo real** com large-v2 em batch; "<8 GB de GPU" para large-v2 com beam 5. Alinhamento word-level para EN, FR, DE, ES, IT por padrão (torchaudio) e outros idiomas via modelos do Hugging Face (PT incluso na prática, verificar); diarização exige token HF | US$ 0 | BSD-2-Clause | [F] https://github.com/m-bain/whisperX |
| Whisper large-v3 / large-v3-turbo | Local | Turbo reduz decoder de 32 para 4 camadas (mais rápido, queda mínima de qualidade). Benchmarks de terceiros em RTX 4090: ~80x tempo real turbo (single), 175x em lote 16; alinhamento WhisperX soma ~0,4-0,6x da duração. Fontes divergem muito (de 12x a 80x) | US$ 0 | MIT | (via busca) https://huggingface.co/openai/whisper-large-v3-turbo ; https://gigagpu.com/rtx-4090-24gb-whisper-benchmark/ |
| OpenAI `whisper-1` / `gpt-4o-transcribe` | Nuvem | n/a | US$ 0,006/min; `gpt-4o-mini-transcribe` US$ 0,003/min (20 min: US$ 0,12 / 0,06). Só `whisper-1` devolve timestamps por palavra e SRT/VTT | proprietária | (via busca) https://diyai.io/ai-tools/speech-to-text/openai-whisper-api-pricing-2026/ |
| Deepgram Nova-3 | Nuvem | n/a | ~US$ 0,0043/min em lote (US$ 0,26/h); streaming ~US$ 0,0077/min (20 min: US$ 0,09) | proprietária | (via busca) https://convertaudiototext.com/blog/deepgram-nova-3-explained |
| AssemblyAI Universal | Nuvem | n/a | Universal-2 US$ 0,15/h; Universal-3.5 Pro US$ 0,21/h (20 min: US$ 0,05-0,07); diarização +US$ 0,02/h | proprietária | (via busca) https://costbench.com/compare/assemblyai-vs-deepgram |

Para a skill: como o roteiro é o texto original, o uso principal de Whisper é **forçar alinhamento** (legendas word-level, sincronia de cenas). Local custa centavos de energia e roda em minutos; nuvem só se a GPU estiver ocupada.

---

## 6. Imagem

### 6.1 Local

| Modelo | VRAM mínima prática | Licença comercial | Observações | Fonte |
|---|---|---|---|---|
| **FLUX.1 [schnell]** | FP8 ~12 GB; GGUF Q4/NF4 cabe em ~6-8 GB (via busca) | **Apache-2.0** | 1-4 passos; melhor opção local limpa para 8 GB | [F] https://github.com/black-forest-labs/flux ; VRAM (via busca) https://insiderllm.com/guides/flux-locally-complete-guide/ |
| **FLUX.1 [dev]** | idem | **Non-Commercial License**. Uso comercial dos pesos exige licença da BFL (taxa por uso mensal, rastreamento via API); BFL e terceiros divergem sobre se os *outputs* podem ser usados comercialmente | Evitar sem licença | [F] BFL repo |
| FLUX.2 [dev] (32B) | ~19-20 GB só no GGUF Q4; 32 GB FP8; ~64-70 GB FP16 | Non-commercial (dev) | Não cabe em 8 GB | (via busca) https://runaihome.com/blog/flux-2-self-hosting-vram-gguf-guide-2026/ |
| FLUX.2 [klein] 4B | cabe em 12-16 GB (confirmar) | **Apache-2.0** (4B); 9B sob licença não comercial (via busca, 1 fonte) | Alternativa moderna se a GPU tiver 12-16 GB | (via busca) idem |
| **SDXL 1.0** | ~6-8 GB com otimizações [EST: conhecimento geral, não confirmado nesta busca] | CreativeML Open RAIL++-M (comercial permitido com restrições de uso) | Enorme ecossistema de LoRAs; ótimo para personagens 2D consistentes | (via busca) https://www.krea.ai/blog/is-stable-diffusion-free-where-to-get-it-and-what-it-costs-in-2026 |
| SD 3.5 (Medium/Large) | Medium ~9,9 GB; Large 11-19 GB | Stability Community License: grátis comercial **abaixo de US$ 1M de receita anual** | | (via busca) https://stability.ai/news/introducing-stable-diffusion-3-5 |
| HiDream-I1 (17B) | Mínimo oficial 16 GB; GGUF Q4 ~12 GB; Q2 ~8 GB (qualidade cai) | **MIT** (via busca) | Pesado para 8 GB | (via busca) https://comfyui-wiki.com/en/tutorial/advanced/image/hidream/i1-t2i |
| **Qwen-Image** (20B) | VRAM oficial **não informada**; DiffSynth-Studio faz offload camada a camada "dentro de 4 GB" (muito lento); FP8 disponível. Último open-weight: Qwen-Image-2512 | **Apache-2.0** | Forte em texto dentro da imagem (sobretudo chinês). Para 8 GB, só quantizado/offload | [F] https://github.com/QwenLM/Qwen-Image |

Tempo de geração por imagem em GPU de 8 GB: não medi; ordem de grandeza 30-120 s por imagem 1024x1024 com FLUX schnell GGUF ou SDXL [EST, depende da GPU]. Isso define a viabilidade local de estilo (b).

### 6.2 Nuvem (por imagem)

| Serviço | Preço | Fonte |
|---|---|---|
| Nano Banana (Gemini 2.5 Flash Image) | US$ 0,039 padrão; US$ 0,0195 batch | (via busca) https://benchlm.ai/media-pricing/nano-banana |
| Nano Banana 2 | ~US$ 0,067 | (via busca) idem |
| Nano Banana Pro (Gemini 3 Pro Image) | ~US$ 0,134 (1-2K); até US$ 0,24 (4K) | (via busca) idem |
| FLUX.2 [pro] | ~US$ 0,03 pelo primeiro megapixel; [max] ~US$ 0,07 (outra fonte: Flux 2 Pro v1.1 a US$ 0,055) | (via busca) https://pricepertoken.com/image/cheapest |
| Ideogram | Ideogram 4.0: Turbo US$ 0,03; Default US$ 0,06; Quality US$ 0,10. Ideogram 3: não encontrado | (via busca) idem |
| GPT Image (OpenAI) | Muito variável por qualidade/tamanho: de ~US$ 0,005 (mini) a ~US$ 0,04 (padrão) até US$ 0,21 (GPT Image 2, alta qualidade, 1024², via fal). `gpt-image-1` isolado: não encontrado | (via busca) https://www.cometapi.com/ai-image-api-pricing/ |
| Midjourney (plano, sem API oficial) | Basic US$ 10/mês (~3,3 h rápidas, ~200 imagens); Standard US$ 30 (15 h + relax ilimitado); Pro US$ 60 (30 h, Stealth); Mega US$ 120 (60 h). Anual -20%. Uso comercial em todos; empresas acima de US$ 1M/ano precisam de Pro/Mega. Sem automação oficial: **dificulta pipeline** | (via busca) https://eesel.ai/blog/midjourney-pricing |

---

## 7. Vídeo gerado por IA

### 7.1 Nuvem (preços por segundo; fontes secundárias divergem muito)

| Serviço | Preço aproximado | Fonte |
|---|---|---|
| Veo 3.1 | Lite ~US$ 0,03/s (720p, sem áudio); Standard com áudio US$ 0,40-0,75/s | (via busca) https://invideo.io/blog/ai-video-model-pricing ; https://coverr.co/blog/ai-video-generation-api-pricing-2026 |
| Kling 3.0 | ~US$ 0,08/s (720p, sem áudio) a ~US$ 0,14/s (1080p com áudio) em uma fonte; fal.ai lista US$ 0,168-0,392/s; outra página fal: US$ 0,112/s sem áudio e US$ 0,168/s com. Divergência real | (via busca) https://fal.ai/kling-3 ; https://fal.ai/learn/tools/seedance-2-0-vs-kling-3-0 |
| Seedance 2.0 (fal) | ~US$ 0,24-0,30/s (720p com áudio); outra fonte US$ 0,112-0,168/s | (via busca) idem |
| Runway | Gen-4 Turbo ~US$ 0,05/s (5 créditos); Gen-4 ~US$ 0,10-0,15/s; Gen-4.5 US$ 0,12-0,25/s (fontes divergem). 1 crédito = US$ 0,01 | (via busca) https://coverr.co/blog/ai-video-generation-api-pricing-2026 |
| Hailuo (MiniMax) | Hailuo 02: US$ 0,017-0,045/s; "MiniMax-H3 2K" ~US$ 0,13/s (fontes fracas). Hailuo 2.3: não encontrado | (via busca) https://www.cometapi.com/ai-video-api-pricing/ |
| Sora 2 | ~US$ 0,10/s (720p). **A fonte diz que a Videos API encerra em 24/09/2026**: tratar como indisponível e reverificar | (via busca) https://invideo.io/blog/ai-video-model-pricing |
| **Higgsfield** (assinatura por créditos) | Free (sem créditos, sem direitos comerciais); Starter ~US$ 19/mês (270 créditos, anual); Plus ~US$ 47 anual / 59 mensal (1.200); Ultra ~US$ 99 anual / 129 mensal (3.000 base). Custo por crédito: ~US$ 0,033-0,0625. **Créditos por vídeo dependem de modelo, duração e resolução: não encontrado um valor fixo.** Para precificar com precisão, consultar a tabela do próprio Higgsfield (MCP `models_explore` / `show_plans_and_credits`) antes de orçar | (via busca) https://creatify.ai/blog/higgsfield-pricing-(2026)-plans-and-what-you-ll-actually-pay |

Faixa de trabalho para a skill: **US$ 0,05-0,15/s** (Kling/Runway/Hailuo/Seedance padrão), **US$ 0,03/s** (Veo Lite, só 720p) e **US$ 0,40+/s** (Veo Standard com áudio).

### 7.2 Local

| Modelo | VRAM / tempo | Licença | Fonte |
|---|---|---|---|
| **Wan 2.2 TI2V-5B** | Oficial: **≥24 GB** com offload (`--offload_model True --convert_model_dtype --t5_cpu`); clipe 720p de 5 s "em menos de 9 min" em uma GPU de consumo (tipo RTX 4090). Guias de comunidade para 8 GB: modelo 5B/GGUF em 480p, 5-12 min por clipe de 5 s (fontes divergem: de 5-8 min a ~20 min em 12 GB) | **Apache-2.0** (o autor não reivindica direitos sobre o gerado) | [F] https://github.com/Wan-Video/Wan2.2 ; comunidade (via busca) https://wan27.org/blog/wan-2-2-vram-guide |
| Wan 2.2 A14B | ≥80 GB em GPU única (oficial); GGUF Q3-Q4 roda em 8-12 GB com offload e muito lento | Apache-2.0 | [F] idem |
| LTX-Video 2.x | FP8 ~12-24 GB a 720p; vários guias dizem que 16 GB é o realista; licença com fontes conflitantes (community license abaixo de ~US$ 10M de receita vs Apache-2.0) | **verificar** | (via busca) https://ltxworkflow.com/resources/community/ltx-23-vram-requirements-12gb-16gb-24gb |
| OpenMontage local | `wan2.2-ti2v-5b`, `ltx2-local` via `make install-gpu` | | [F] OpenMontage README |

Conclusão: com 8 GB, vídeo local é **possível mas lento e de qualidade menor** (480p, poucos segundos, clipes inconsistentes). Serve para cobrir 10-30% da linha do tempo, não 100%.

---

## 8. Motion programático

| Ferramenta | Licença | Custo de automação | Render | Fonte |
|---|---|---|---|---|
| **HyperFrames** (HeyGen) | **Apache-2.0**, "sem taxas por render nem limite comercial" | US$ 0 | Chrome headless busca cada frame + FFmpeg; determinístico. Requer Node 22+. **Não há benchmark de velocidade publicado**; estimativa: 1-3x o tempo de vídeo em 1080p30 em CPU moderna [EST] | [F] https://github.com/heygen-com/hyperframes |
| **Remotion** | Licença própria (não OSI). **Free License**: indivíduos e empresas com fins lucrativos de até 3 funcionários, inclusive para construir automações. Acima disso: Creators US$ 25/assento/mês; **Automators US$ 0,01 por render com mínimo de US$ 100/mês**; Enterprise mínimo US$ 500/mês | Para um solo/≤3 pessoas: US$ 0. "Render" aqui = chamada a `renderMedia()`/`renderStill()`, não vídeo exportado final | `npx remotion benchmark` mede concorrência; sem número publicado para vídeo de 10 min. Estimativa 1-3x tempo real [EST] | (via busca) https://www.remotion.dev/docs/terms ; https://www.remotion.dev/docs/pricing |
| **Revideo** (fork do Motion Canvas) | **MIT** (via busca) | US$ 0 | Fundador reporta 60 s de Full HD em 14,3 s num MacBook (autorreportado, ~0,24x) usando WebCodecs | (via busca) https://www.producthunt.com/products/revideo |
| **Motion Canvas** | MIT (apenas uma fonte terciária; confirmar no repo) | US$ 0 | Editor/preview no navegador, render por plugin | (via busca) https://smithery.ai/skills/davila7/motion-canvas |
| ManimCE | Citado no OpenMontage (animações matemáticas). Licença: não verificada | | | [F] OpenMontage |

Observação: no OpenMontage, Remotion e HyperFrames já são backends de render. HyperFrames evita qualquer dúvida de licença Remotion caso o canal virar uma empresa maior que 3 pessoas.

---

## 9. Música e SFX

| Fonte | Preço | Termos | Fonte |
|---|---|---|---|
| YouTube Audio Library | Grátis | Faixas sem atribuição ou CC-BY (exigem crédito na descrição). Não gera Content ID. Só vale para YouTube; usos fora (anúncios, cursos) exigem outra licença | (via busca) https://www.vidiq.com/blog/post/royalty-free-music-youtube-audio-library |
| Epidemic Sound | Creator ~US$ 9,99-17,99/mês (US$ 119,88/ano segundo uma fonte; divergem); Pro ~US$ 39,99/mês | Cobre monetização em 1 canal por plataforma; **verificar se o plano exige manter assinatura ativa** para vídeos já publicados | (via busca) https://recurdash.com/subscription-pricing/epidemic-sound |
| Artlist | **não encontrado** preço do plano padrão (só planos de crédito de IA US$ 19,99-149,99/ano em uma fonte) | | (via busca) https://saas.apppricinglab.com/product/artlist/ |
| Storyblocks | All Access ~US$ 30/mês no anual (US$ 360/ano), inclui vídeo, música e SFX; Essentials ~US$ 21/mês; outras fontes divergem (US$ 149-249/ano) | Footage e áudio ilimitados | (via busca) https://frontdeskreview.com/software/stock-media/storyblocks/ |
| Pexels / Pixabay (vídeo e foto) | Grátis. API Pexels: 200 req/h e 20.000/mês; licença Pexels permite uso comercial sem crédito obrigatório (pede crédito); proibido replicar o serviço ou revender sem alteração | Termos de Pixabay para vídeo: não confirmados | (via busca) https://help.pexels.com/hc/en-us/articles/900005852323 |
| Suno | Planos pagos dão direitos comerciais sobre as faixas geradas **enquanto assinante** (segundo guias); Pro ~US$ 10/mês (~500 músicas). Guia aponta **novos Termos em vigor desde 03/09/2026**, que condicionam o uso comercial a condições e a "download permitido": não verificado. Registro de copyright nos EUA provavelmente indisponível (falta autoria humana) | Free = não comercial | (via busca) https://terms.law/ai-output-rights/suno/ ; https://toskyrecords.com/2026/06/09/the-working-artists-guide-to-suno-paid-tiers-rights-distribution-monetization-in-2026/ |
| Udio | Acordo com a Warner (19/11/2025) para serviço licenciado em 2026; uma fonte diz que o novo serviço **não permite exportar** MP3/WAV nem publicar no YouTube. Tratar como indisponível para canais | | (via busca) https://decrypt.co/349360/warner-music-moves-from-litigation-to-licensing-with-udio |
| Gerar música local | Não pesquisado (MusicGen/Stable Audio Open etc.): **não encontrado** | | |

Recomendação: Audio Library + faixas CC0/CC-BY (com crédito automatizado na descrição) para custo zero; Epidemic/Storyblocks quando o canal já gera receita.

---

## 10. Thumbnails

| Item | Custo típico | Fonte |
|---|---|---|
| Geração da arte-base | Local (SDXL/FLUX schnell): ~US$ 0; nuvem: US$ 0,03-0,134 por tentativa (Nano Banana, Ideogram Turbo). Contar 4-8 tentativas por vídeo: US$ 0,2-1,0 [EST] | seção 6 |
| Edição / texto | Photopea (grátis, no navegador, abre PSD); Canva Free; Canva Pro ~US$ 13-15/mês (remoção de fundo, fontes, kit de marca) | (via busca) https://1of10.com/compare/canva-alternatives |
| Ferramentas de thumbnail IA dedicadas | ~US$ 0,20 por thumbnail (Thumbnail.io, plano pro) ou ~US$ 9,99/mês; fonte tem conflito de interesse | (via busca) https://thumbfa.st/posts/best-thumbnail-maker-2026-top-picks |
| Montagem programática | Pillow/ffmpeg ou HyperFrames/Remotion `renderStill()` com template fixo: US$ 0 | seção 8 |
| Humano | 15-40 min por vídeo para escolher o melhor de 4-8 variações e revisar texto [EST] | |

Atenção: thumbnail com pessoa realista gerada por IA ou rosto de pessoa real pode ter implicação de divulgação (seção 12).

---

## 11. Custo por vídeo: 5 estilos de produção

Valores em US$ por vídeo, **sem** custos fixos de assinatura (listados quando relevantes). Todos são [EST] a partir das tabelas acima e das premissas da seção 0; usar como intervalos. Horas = trabalho humano por vídeo com templates já prontos (revisão de roteiro/fatos, QA visual, publicação). Primeiro vídeo de um canal custa 2-3x em horas.

| Estilo | Duração | 100% local (energia) | Híbrido | 100% nuvem | Horas humanas |
|---|---|---|---|---|---|
| **(a) Motion graphics por código** (ícones + tipografia cinética; HyperFrames/Remotion) | 10 min | US$ 0,05-0,2 (TTS 3 min + Whisper 1 min + render 15-40 min; LLM local de qualidade menor) | US$ 1,5-3 (Sonnet 5.5 com código ~US$ 1,3-2; resto local) | US$ 3,5-6 (Opus 5.5 ~US$ 2,5-3 + ElevenLabs US$ 1-1,3) | 2-4 h |
| | 20 min | US$ 0,1-0,4 | US$ 3-6 | US$ 7-11 | 4-8 h |
| **(b) Imagens de IA + Ken Burns** | 10 min (~130 gerações) | US$ 0,1-0,3 (2-4 h de GPU) | US$ 0,7-1,5 (roteiro Sonnet + imagens/TTS locais) | US$ 7-11 (Nano Banana US$ 0,039 x 130 = US$ 5; ElevenLabs US$ 1,3; Opus US$ 1,2); com Nano Banana Pro ~US$ 20 | 1,5-3 h |
| | 20 min (~260 gerações) | US$ 0,3-0,6 (4-8 h de GPU) | US$ 1,4-2,5 | US$ 14-20 (batch -50% nas imagens: ~US$ 9-12); Pro: ~US$ 40 | 3-5 h |
| **(c) Stock footage + narração** | 10 min | US$ 0,05-0,2 (footage de Pexels/Pixabay/Archive.org, TTS local, render FFmpeg) | US$ 0,6-1,5 sem assinatura; +US$ 3-4/vídeo se Storyblocks (US$ 360/ano ÷ ~8 vídeos/mês) | US$ 3-6 (ElevenLabs + Opus + Storyblocks amortizado) | 2-4 h (casar footage com a fala é o gargalo) |
| | 20 min | US$ 0,1-0,4 | US$ 1,2-2,5 (+US$ 3-4 Storyblocks) | US$ 6-10 | 4-8 h |
| **(d) Stick figure / 2D simples** (personagens gerados 1x por canal + animação por código) | 10 min | US$ 0,2-0,6 (algumas imagens/poses locais + render) | US$ 1,5-4 | US$ 5-10 | 3-5 h |
| | 20 min | US$ 0,4-1,2 | US$ 3-7 | US$ 10-18 | 6-10 h |
| **(e) Vídeo gerado por IA (clipes)** | 10 min (cobertura 100% com clipes: ~900 s gerados com rerolls) | US$ 1-2 de energia, **mas 24-40 h de GPU em 8 GB** (180 clipes x 8-12 min): inviável a 100%; viável a ~20-30% de cobertura | Clipes de IA em ~20% da linha do tempo + imagens locais: US$ 15-30 (180 s gerados x US$ 0,08-0,15) | US$ 45-135 (900 s x US$ 0,05-0,15). Com Veo Standard a US$ 0,40/s: ~US$ 360 | 3-6 h |
| | 20 min | US$ 2-4; 50-80 h de GPU a 100% (inviável) | US$ 30-55 | US$ 90-270 (Veo Standard: ~US$ 720) | 6-12 h |

Pontos de leitura:
- O custo é dominado por **vídeo de IA** (e) e, em segundo lugar, por **imagens em nuvem premium** (b). Texto, voz e legendas são centavos a poucos dólares.
- Em (a), (c) e (d) o custo variável é quase todo o LLM. Para reduzir: Sonnet 5.5 com cache, Haiku 5.5 para triagem, batch -50% quando não for interativo.
- Custos fixos mensais opcionais: ElevenLabs Creator ~US$ 22; Midjourney Basic US$ 10; Storyblocks ~US$ 30; Epidemic ~US$ 10-18; Canva Pro ~US$ 13-15; Higgsfield Starter ~US$ 19; Remotion US$ 0 (≤3 pessoas) ou mínimo US$ 100 (Automators).
- Orçamento padrão do OpenMontage: teto US$ 10 por produção, aprovação acima de US$ 0,50 por ação: bom limite de segurança para (b) e (e).

---

## 12. Rubricas para a skill

### 12.1 Dificuldade de automação (1-5)

Pontue **+1 para cada fator verdadeiro** (base 1; máximo 5):

| # | Fator (pergunta objetiva) |
|---|---|
| F1 | O visual exige **consistência de personagem/objeto entre cenas** (mesmo rosto, mascote, produto)? |
| F2 | Exige **footage ou assets exclusivos** (gravação, captura de tela específica, licenciamento por asset, imagens de pessoas/lugares reais)? |
| F3 | Exige **checagem jurídica ou factual humana obrigatória** (saúde, finanças, notícias, política, pessoas reais, marcas)? |
| F4 | Exige **voz ou rosto humano** (entrevista, apresentador, voz de pessoa real, humor dependente de timing)? |
| F5 | Exige **sincronia fina** (lip-sync, B-roll semântico por frase, edição ao ritmo da música)? |
| F6 | Depende de **dados externos instáveis** (scraping, API de terceiros, tópico de nicho com poucas fontes em PT-BR)? |

Níveis: **1** = template fixo, dados estruturados, nada de juízo (ex.: ranking com gráficos); **2** = roteiro por LLM + visuais de template; **3** = visuais gerados com QA por cena; **4** = consistência/sincronia + revisão obrigatória; **5** = depende de pessoa, footage exclusivo ou risco jurídico alto (praticamente não automatizável).

Estimativa por estilo (para uma lista simples de curiosidades/explainers de baixo risco): (a) 2; (b) 3 (F1 se houver personagem); (c) 3 (F5: casar footage com fala); (d) 3-4 (F1 + F5); (e) 4 (F1 + F5 + rerolls).

### 12.2 Viabilidade local (sim / parcial / não)

- **Sim**: todas as etapas (roteiro, voz, visual, legenda, render) rodam na **GPU do perfil** (`hardware.vram_gb`; os cortes abaixo assumem 8 GB) em menos de ~1 dia de máquina, com **licenças comerciais permissivas** (Apache/MIT/OpenRAIL), e o LLM local atende ao nível de roteiro exigido. Perfil sem GPU: no máximo "parcial" (voz e render em CPU são lentos, e imagem e vídeo de IA vão para a nuvem).
- **Parcial**: uma etapa depende de nuvem (tipicamente o LLM de roteiro/pesquisa, vídeo de IA, imagem de alta qualidade, ou texto dentro da imagem) ou usa pesos não comerciais (XTTS-v2, F5-TTS, FLUX.1 dev, Higgs v3).
- **Não**: o núcleo do formato exige modelo só-nuvem ou >16-24 GB de VRAM (ex.: Veo, vídeo 1080p com áudio, A14B).

| Estilo | Local | Justificativa |
|---|---|---|
| (a) Motion graphics | **Sim** (LLM: parcial) | TTS local + WhisperX + HyperFrames/Remotion locais; escrever código de cenas bem exige LLM forte |
| (b) Imagens + Ken Burns | **Sim/parcial** | FLUX schnell GGUF/SDXL cabem em 8 GB; falta qualidade de texto/mãos e consistência |
| (c) Stock + narração | **Sim** | Tudo local, exceto busca semântica de footage (pode ser CLIP local) |
| (d) 2D simples | **Sim/parcial** | Poses com SDXL + LoRA; animação por código |
| (e) Vídeo de IA | **Parcial** (a 100%: **não**) | Wan 2.2 5B oficial pede 24 GB; em 8 GB, 480p e 5-12 min por clipe |

### 12.3 Viabilidade solo (sim / parcial / não)

- **Sim**: cabe em `horas_max_video` do perfil (sem perfil, ≤ ~4 h humanas por vídeo de 10 min após templates) e no ritmo `videos_mes`, sem gravação, sem entrevistas, sem licenciamento caso a caso.
- **Parcial**: 4-10 h, ou exige revisão de fatos/jurídica periódica, ou assinaturas de licença contínuas, ou revisão nativa por idioma (PT/ES/FR/DE...). Cada idioma extra multiplica o tempo de QA, porque o criador solo não consegue ouvir erros de pronúncia em RO, TR, PL, BG.
- **Não**: precisa de equipe (gravação, atores, advogado, tradutores nativos em vários idiomas, rotina diária de publicação com revisão humana).

| Estilo | Solo | Observação |
|---|---|---|
| (a) | **Sim** | Menor carga de QA visual; maior risco é se tornar "template repetitivo" |
| (b) | **Sim** | Revisar imagens por cena |
| (c) | **Parcial** | Alto risco de "conteúdo reutilizado/inautêntico"; exige comentário original |
| (d) | **Parcial** | Storyboard e posições consomem tempo |
| (e) | **Parcial/Não** | Rerolls, consistência, custo; viável só em volume baixo |

Fatores que sobem o nível para "não": F3 (nicho YMYL) + F4 (voz de pessoa real) + F2 (footage exclusivo).

---

## 13. Riscos de política do YouTube para conteúdo automatizado

### 13.1 Conteúdo inautêntico / repetitivo (monetização)

- A política de monetização foi atualizada em **15/07/2025**: "repetitious content" passou a se chamar **"inauthentic content"**, cobrindo conteúdo repetitivo ou produzido em massa. O texto oficial diz que o conteúdo monetizado deve ser trabalho do próprio criador e não ser produzido em massa, genérico, repetitivo ou manipulativo; canais "intercambiáveis" que usam o mesmo template/storyline não são elegíveis; **usar IA não desqualifica por si só**, mas conteúdo de IA baseado em templates genéricos sem perspectiva original viola a política. Aplica-se ao **canal inteiro**: se alguns vídeos violam, ou o YouTube não consegue dizer que o criador fez o conteúdo, a monetização pode ser removida do canal todo. Fonte oficial: https://support.google.com/youtube/answer/1311392 (via busca; texto resumido por snippet).
- O YouTube descreveu a mudança como "atualização menor" que formaliza regras já existentes (Rene Ritchie, via imprensa): exemplos visados são slideshows narrados quase idênticos e histórias com variações mínimas. Reação, compilação e comentário continuam monetizáveis se houver valor original relevante. (via busca) https://cined.com/youtube-set-to-crack-down-on-ai-slop-with-monetization-policy-update ; https://alternativeto.net/news/2025/7/youtube-updates-its-policy-to-demonetize-inauthentic-mass-produced-ai-generated-content
- **Não confirmados (não usar como fato; reverifique na página oficial e nas notícias dos últimos 90 dias, `pesquisa-web.md` §2.2):** relato de onda de fiscalização em janeiro/2026 (números sem fonte oficial); relato de reforma do Programa de Parcerias com limiares de entrada maiores (uma única fonte secundária, que conflita com relatos de limiares inalterados); escala de punição com prazo de 90 dias. Os requisitos vigentes do Programa de Parcerias saem sempre da página oficial, com a data de acesso.

Padrão de maior risco (consenso das fontes secundárias): pipeline totalmente automatizado, roteiros raspados ou em template, narração sintética, visuais de stock/IA genéricos, publicação diária sem revisão humana. Mitigações que a skill deve exigir: ponto de vista/análise original por vídeo, variação real de estrutura entre vídeos, passagem humana de edição, fontes citadas, ritmo de publicação compatível com revisão.

### 13.2 Rótulo de conteúdo alterado ou sintético

- Criadores devem divulgar (YouTube Studio, "AI use", em Atributos) conteúdo **realista** feito com mídia alterada/sintética que o espectador possa confundir com pessoa, lugar ou evento reais: fazer uma pessoa real parecer dizer ou fazer algo que não fez; alterar filmagem de evento/lugar real; gerar cena realista que não ocorreu; e música como foco principal do vídeo. Fontes: https://support.google.com/youtube/answer/14328491 e https://blog.youtube/news-and-events/disclosing-ai-generated-content/ (via busca).
- **Não exigem divulgação**: conteúdo claramente irreal/animação, efeitos especiais, e uso de IA como apoio de produção (roteiro, ideias, legendas automáticas). Portanto narração sintética de um canal faceless com visuais não realistas tende a **não** exigir rótulo; imagens fotorrealistas de "eventos" e vozes que imitam pessoa real exigem. Um snippet de imprensa lista "gerar sinteticamente a voz de uma pessoa para narrar" como exemplo; o escopo exato da voz sintética **genérica** é ambíguo: na dúvida, rotular. (via busca) https://www.androidcentral.com/apps-software/youtube-ai-synthetic-content-disclosure
- Em tópicos sensíveis (saúde, notícias, eleições, finanças), o rótulo vai **no player** (mais visível), e não só na descrição. YouTube pode **aplicar rótulo automaticamente** (ferramentas GenAI do próprio YouTube, metadados C2PA, detecção interna); rótulos de C2PA e de ferramentas do YouTube não podem ser removidos. Não divulgar repetidamente pode levar a rótulo manual, remoção de conteúdo ou suspensão do YPP. Fonte: https://support.google.com/youtube/answer/15447836 (via busca).
- Existe também o selo "Captured with a camera" (C2PA), irrelevante para vídeo sintético: https://support.google.com/youtube/answer/15446725 (via busca).
- Ferramentas locais podem deixar marca: Chatterbox insere marca d'água Perth em todo áudio [F]; outros geradores podem gravar C2PA. Não remover marcas para evitar rótulo.

### 13.3 Voz clonada e imitação

- Clonar a voz de uma **pessoa real sem consentimento** para fazê-la "dizer" algo é o caso central de divulgação obrigatória, além de risco de remoção por privacidade/impersonação e de ação civil (vários estados dos EUA permitem processos por voz clonada; há projeto de lei federal nos EUA sobre réplicas digitais em tramitação: **confirme o status atual**, não presuma que virou lei).
- O YouTube tem **detecção de semelhança** (face; voz em expansão segundo fontes divergentes) para criadores a partir de 18 anos, e um formulário de privacidade para depicções realistas de IA, incluindo voz. (via busca) https://techcrunch.com/2025/10/21/youtubes-likeness-detection-technology-has-officially-launched ; https://ppc.land/youtubes-ai-face-shield-now-covers-every-creator-18-and-over
- Regra para a skill: só usar (i) voz própria do criador com consentimento, (ii) voz criada por voice design/biblioteca com licença, (iii) voz de terceiro com contrato de consentimento escrito. Nunca clonar celebridades, políticos, jornalistas ou vozes extraídas via yt-dlp de terceiros.

### 13.4 Outros riscos operacionais

- **Direitos autorais** dos assets: footage do YouTube baixado via yt-dlp é conteúdo de terceiros (não "reutilizável" só por ser transformado); pode gerar Content ID e também enquadrar-se em conteúdo reutilizado. Preferir Pexels/Pixabay/Archive.org/NASA/Wikimedia com licença verificada.
- **Licenças de modelo**: XTTS-v2, F5-TTS (pesos), FLUX.1 dev, FLUX.2 dev, Higgs Audio v3 e VibeVoice (pesquisa) não são adequados para canal monetizado sem licença. Registrar a licença do modelo usado por vídeo (a skill pode gravar `license_ok: true/false` por etapa).
- **Música**: geradores de música com IA mudam termos de uso e de exportação com frequência (confirme na página oficial se o plano pago permite uso comercial e exportação). Preferir Audio Library/Epidemic.
- **Fatos**: roteiro gerado por LLM alucina; nichos YMYL (F3) exigem checagem humana com fonte primária.
- **Dependência de terceiros**: APIs de vídeo e imagem de IA mudam de preço, de termos e até encerram; confirme a disponibilidade e o preço na página oficial antes de basear um canal nelas. Revisar a tabela de custos a cada trimestre.

---

## 14. Lacunas (não encontrado ou não confirmado)

- Preço oficial de Artlist (plano padrão); Hailuo 2.3 por segundo; Ideogram 3; `gpt-image-1` isolado; créditos exatos de Higgsfield por modelo/duração.
- Qualidade de OmniVoice em PT-BR (sem MOS/WER publicado); VRAM oficial do OmniVoice; licença dos pesos no model card HF.
- VRAM de Orpheus, Chatterbox, FLUX.2 klein (confirmar), SDXL (valor geral de 6-8 GB não confirmado), Qwen-Image (sem número oficial).
- Tempo real de render de HyperFrames/Remotion para vídeo de 10-20 min no hardware do usuário (medir com um clipe de 30 s).
- Tempo de geração de imagem/TTS na GPU específica do usuário: rodar um benchmark curto na primeira execução da skill e gravar `gpu_name`, VRAM, RTF e s/imagem.
- Páginas oficiais de ElevenLabs, OpenAI, Google AI, Azure, Fish, Cartesia e Hugging Face não puderam ser abertas diretamente.
