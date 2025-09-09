import streamlit as st
import json
from datetime import datetime, date
import time
import streamlit.components.v1 as components


st.set_page_config(page_title="Chat de Avaliação - Buddha Spa", layout="centered")

# CSS leve para alinhar inputs (chat do usuário)
def _inject_css():
    st.markdown(
        """
        <style>

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Fundo geral branco (mobile-first) */
        html, body, [data-testid="stAppViewContainer"] { background: #ffffff !important; }

        /* Zera fundo do container padrão e controla largura via cards */
        .main .block-container {
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          padding-top: 0 !important;
          padding-left: 0 !important;
          padding-right: 0 !important;
          max-width: 860px; /* desktop */
          margin: 0 auto !important;
        }

        /* Cartões brancos centralizados (banner e chat) */
        .banner-card, .chat-wrapper {
          background: #ffffff;
          border: 1px solid rgba(0,0,0,.12);
          border-radius: 16px;
          padding: 16px 18px;
          box-shadow: 0 1px 2px rgba(0,0,0,.04);
          margin: 12px auto;
        }

        /* Placeholder de logo e textos do banner */
        .logo-ph { height: 72px; width: 180px; border: 1px dashed rgba(0,0,0,.25); border-radius: 10px;
                   display:flex; align-items:center; justify-content:center; color:#777; font-size:14px; }
        .banner-title { margin: 0 0 4px 0; font-weight: 700; font-size: 22px; color:#2b2b2b; }
        .banner-sub { margin: 0; color:#555; }
        /* Garante que o logo no banner não estoure no mobile */
        .banner-card img { max-height: 72px; width: auto !important; }

        /* Ajustes finos do chat */
        .stChatMessage { margin-bottom: 0.6rem; }
        .stChatMessage .stMarkdown { margin: 0; }
        /* Inputs na bolha do usuário */
        [data-testid="chat-message-user"] .stTextInput,
        [data-testid="chat-message-user"] .stRadio,
        [data-testid="chat-message-user"] .stDateInput { margin-top: .25rem; }
        [data-testid="chat-message-user"] .stRadio > div { gap: .35rem !important; }
        [data-testid="chat-message-user"] label { margin-bottom: .15rem; }

        /* Mobile first tweaks */
        @media (max-width: 680px){
          .banner-card, .chat-wrapper { margin: 8px; padding: 12px 12px; border-radius: 12px; }
          .banner-title { font-size: 18px; }
          .banner-sub { font-size: 13px; }
          .stChatMessage { margin-bottom: .5rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

_inject_css()

# Config do banner/topo
BANNER_LOGO_URL = "https://yt3.googleusercontent.com/mtlhWqg9IZ6b0FNeCGwdwUNlsiDLR9XG5pmC1GpBoYWW8sZpvv4sqcECGKkTAJvw1qhyguljsb4=s160-c-k-c0x00ffffff-no-rj"  # defina aqui a URL do logo se quiser exibir
BANNER_TITLE = "Avaliação de Bem-Estar – Buddha Spa Partage Santana"
BANNER_SUBTITLE = "Autoavaliação rápida para recomendações personalizadas"

def render_banner():
    st.markdown('<div class="chat-shell"><div class="banner-card">', unsafe_allow_html=True)
    cols = st.columns([1, 2])
    with cols[0]:
        if BANNER_LOGO_URL:
            st.image(BANNER_LOGO_URL, use_container_width=True)
        else:
            st.markdown('<div class="logo-ph">Logo do Buddha Spa</div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f'<h4 class="banner-title">{BANNER_TITLE}</h4>', unsafe_allow_html=True)
        st.markdown(f'<p class="banner-sub">{BANNER_SUBTITLE}</p>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

# 🔄 Botão de reinício rápido na barra lateral
# Reinicia mantendo dados pessoais e pula para as próximas perguntas

def restart_keep_personal():
    # Preserva apenas dados pessoais já respondidos
    saved_personal = {}
    if "chat_respostas" in st.session_state:
        for k in PERSONAL_KEYS:
            if k in st.session_state["chat_respostas"]:
                saved_personal[k] = st.session_state["chat_respostas"][k]
    # Reset controlado
    st.session_state.chat_respostas = saved_personal
    st.session_state.chat_history = []
    st.session_state.processing_done = False
    st.session_state.pause_shown = set()
    st.session_state.question_shown = set()
    # Não repetir intro ao reiniciar
    st.session_state.intro_done = True
    st.session_state.intro_index = 0
    # Avança para a primeira pergunta não respondida, independente da ordem
    st.session_state.chat_step = find_next_unanswered(0)
    st.rerun()



# Avatares fixos (troque a URL/emoji pelo logo da unidade, se quiser)
ASSISTANT_AVATAR = "🧘‍♀️"  # ou URL de imagem, ex: "https://seu-dominio/logo.png"
USER_AVATAR = "👤"  # ou URL de imagem do usuário/placeholder
# Controla se mostra o botão inline de reinício em cada pergunta
SHOW_INLINE_RESTART = False

# Chaves pessoais (não devem ser re-perguntadas se já respondidas)
PERSONAL_KEYS = ["nome", "cpf", "data_nascimento", "genero", "celular"]

# Helper: encontra o índice da próxima pergunta não respondida
def find_next_unanswered(start_index: int = 0) -> int:
    for i in range(start_index, len(perguntas)):
        if perguntas[i]["chave"] not in st.session_state.chat_respostas:
            return i
    return len(perguntas)

# Configs de digitação e pausas
DEFAULT_TYPING_DELAY = 0.02  # segundos por caractere
DEFAULT_PAUSE = 0.6         # pausa após a mensagem

# ===== Analytics (GA4 + Meta Pixel) =====
GA4_ID = "G-XXXXXXXXXX"            # <-- substitua pelo seu ID GA4
PIXEL_ID = "123456789012345"       # <-- substitua pelo seu Pixel ID

def inject_tracking_scripts():
    if st.session_state.get("tracking_loaded"):
        return
    components.html(f"""
    <script async src='https://www.googletagmanager.com/gtag/js?id={GA4_ID}'></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{GA4_ID}');
    </script>
    <script>
      !function(f,b,e,v,n,t,s){{if(f.fbq)return;n=f.fbq=function(){{n.callMethod? n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
      if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
      t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}}(window, document,'script','https://connect.facebook.net/en_US/fbevents.js');
      fbq('init', '{PIXEL_ID}');
      fbq('track', 'PageView');
    </script>
    <noscript><img height='1' width='1' style='display:none' src='https://www.facebook.com/tr?id={PIXEL_ID}&ev=PageView&noscript=1'/></noscript>
    """, height=0)
    st.session_state["tracking_loaded"] = True

def track_event(name: str, params: dict | None = None):
    # Nunca envie PII! Apenas metadados (ex.: step, q_key)
    payload = json.dumps(params or {})
    components.html(f"""
    <script>
    try {{ if (typeof gtag === 'function') gtag('event', '{name}', {payload}); }} catch(e){{}}
    try {{ if (typeof fbq  === 'function') fbq('trackCustom', '{name}', {payload}); }} catch(e){{}}
    </script>
    """, height=0)


# Função para simular digitação e registrar no histórico
def send_assistant_message(content: str, typing_delay: float | None = None, pause: float | None = None):
    typing_delay = DEFAULT_TYPING_DELAY if typing_delay is None else typing_delay
    pause = DEFAULT_PAUSE if pause is None else pause

    # Cria a bolha no histórico ANTES de digitar, para que fique fixa no chat
    st.session_state.chat_history.append({"role": "assistant", "content": ""})
    idx = len(st.session_state.chat_history) - 1

    # Dispara form_complete uma única vez ao entrar no resultado final
    if not st.session_state.get("complete_tracked"):
        st.session_state.complete_tracked = True

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        placeholder = st.empty()
        typed = ""
        for ch in str(content):
            typed += ch
            placeholder.markdown(typed)
            # Atualiza o histórico em tempo real para manter a mensagem fixa
            st.session_state.chat_history[idx]["content"] = typed
            time.sleep(typing_delay)
        # Garante o texto final
        st.session_state.chat_history[idx]["content"] = str(content)

    if pause > 0:
        time.sleep(pause)

# Funções de máscara (formatação em tempo real)
def mask_cpf_in_state():
    val = st.session_state.get('cpf', '')
    digits = ''.join(c for c in val if c.isdigit())[:11]
    if len(digits) <= 3:
        f = digits
    elif len(digits) <= 6:
        f = f"{digits[:3]}.{digits[3:6]}"
    elif len(digits) <= 9:
        f = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}"
    else:
        f = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"
    st.session_state['cpf'] = f


def mask_phone_in_state():
    val = st.session_state.get('celular', '')
    digits = ''.join(c for c in val if c.isdigit())[:11]
    if len(digits) == 0:
        f = ''
    elif len(digits) <= 2:
        f = f"({digits}"
    elif len(digits) <= 7:
        f = f"({digits[:2]}) {digits[2:7]}"
    else:
        f = f"({digits[:2]}) {digits[2:7]}-{digits[7:11]}"
    st.session_state['celular'] = f

# Versões puras (funções que retornam a máscara para uso imediato)
def mask_cpf(val: str) -> str:
    digits = ''.join(c for c in str(val) if c.isdigit())[:11]
    if len(digits) <= 3:
        return digits
    if len(digits) <= 6:
        return f"{digits[:3]}.{digits[3:6]}"
    if len(digits) <= 9:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}"
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"


def mask_phone(val: str) -> str:
    digits = ''.join(c for c in str(val) if c.isdigit())[:11]
    if len(digits) == 0:
        return ''
    if len(digits) <= 2:
        return f"({digits}"
    if len(digits) <= 7:
        return f"({digits[:2]}) {digits[2:7]}"
    return f"({digits[:2]}) {digits[2:7]}-{digits[7:11]}"


# Inicializa estados
if "chat_step" not in st.session_state:
    st.session_state.chat_step = 0
    st.session_state.chat_respostas = {}
    st.session_state.chat_history = []
    st.session_state.processing_done = False
    st.session_state.intro_done = False
    st.session_state.pause_shown = set()
    st.session_state.question_shown = set()

# Lista de perguntas como um fluxo de conversa
perguntas = [
    {"chave": "nome", "tipo": "text", "mensagem": "Me fala, como eu posso te chamar?"},
    {"chave": "data_nascimento", "tipo": "date", "mensagem": "{nome}, você pode me informar a sua data de nascimento?"},
    {"chave": "genero", "tipo": "radio", "mensagem": "Agora, {nome}, eu preciso que me diga qual é o seu sexo biológico", "opcoes": ["Feminino", "Masculino","Não binário", "Outros", "Prefiro não informar"]},
    {"chave": "celular", "tipo": "text", "mensagem": "{nome}, você me infora o seu WhatsApp, por favor?"},
    

    
    
    
    {"chave": "dores", "tipo": "checkboxes", "mensagem": "Você sente algum desconforto físico frequente?", "opcoes": ["Ombros/pescoço", "Lombar", "Pernas/pés", "Não sinto dores recorrentes"]},
    {"chave": "sensacao_corpo", "tipo": "radio", "mensagem": "Qual sensação você sente mais no corpo?", "opcoes": ["Peso ou inchaço", "Tensão muscular", "Corpo leve"]},
    {"chave": "sono", "tipo": "radio", "mensagem": "Como você descreveria seu sono?", "opcoes": ["Durmo bem, acordo descansado(a)", "Tenho dificuldade para dormir", "Durmo, mas acordo cansado(a)", "Sono irregular"]},
    
    {"chave": "cpf", "tipo": "text", "mensagem": "Muito obrigado pelas respostas, agora me diga seu CPF."},
    
    {"chave": "energia", "tipo": "radio", "mensagem": "Como está sua energia no dia a dia?", "opcoes": ["Me sinto bem disposto(a)", "Canso com facilidade", "Sinto-me estressado(a)", "Me sinto sem energia"]},
    {"chave": "rotina", "tipo": "radio", "mensagem": "Como você descreveria sua rotina?", "opcoes": ["Corrida e estressante", "Moderada", "Tranquila", "Sedentária"]},
    {"chave": "tempo_livre", "tipo": "radio", "mensagem": "O que você prefere fazer no tempo livre?", "opcoes": ["Descansar", "Atividades sociais", "Se manter ativo"]},
    {"chave": "ambiente", "tipo": "radio", "mensagem": "Sua casa costuma ser um ambiente...", "opcoes": ["Leve e organizado", "Pesado ou bagunçado"]},
    {"chave": "estatica", "tipo": "radio", "mensagem": "Você costuma levar pequenos choques (energia estática)?", "opcoes": ["Sim", "Não"]},
    {"chave": "objetivo", "tipo": "radio", "mensagem": "O que você gostaria de melhorar primeiro?", "opcoes": ["Reduzir dores", "Melhorar o sono", "Reduzir estresse", "Aumentar energia", "Reduzir inchaço", "Ambiente mais leve"]},
]


# Mensagens iniciais (aparecem antes da primeira pergunta)
INTRO_SEQUENCE = [
    {"text": "Que bom ter você aqui comigo hoje!", "typing_delay": 0.03, "pause": 0.3},
    {"text": "Antes de te indicar algo, quero te conhecer um pouco mais sobre você e como anda sua rotina.", "typing_delay": 0.025, "pause": 0.3},
    {"text": "Assim consigo te recomendar algo que realmente faça diferença.", "typing_delay": 0.025, "pause": 0.4},
    {"text": "Vamos começar... :D", "typing_delay": 0.025, "pause": 0.4},
]


# Pausas configuráveis antes de algumas perguntas (opcional)
# Preencha com a chave da pergunta e a mensagem desejada
PAUSE_MESSAGES = {
    # string simples
    "sono": "Agora vamos falar rapidinho sobre seu sono, ok?",
    # ou com tempos
    "dores": {"text": "Vamos falar agora sobre dores... ", "typing_delay": 0.02, "pause": 0.7},
}

# Banner antes do chat
render_banner()

inject_tracking_scripts()

# Wrapper branco para a área de conversa
st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)


# Exibe histórico de mensagens com avatares consistentes
for msg in st.session_state.chat_history:
    avatar = ASSISTANT_AVATAR if msg["role"] == "assistant" else USER_AVATAR
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# Mensagens de boas-vindas após renderizar histórico (garante persistência visual)
if st.session_state.chat_step == 0 and not st.session_state.get("intro_done", False):
    if "intro_index" not in st.session_state:
        st.session_state.intro_index = 0
    idx = st.session_state.intro_index
    if idx < len(INTRO_SEQUENCE):
        meta = INTRO_SEQUENCE[idx]
        send_assistant_message(meta.get("text", ""), meta.get("typing_delay"), meta.get("pause"))
        st.session_state.intro_index += 1
        if st.session_state.intro_index < len(INTRO_SEQUENCE):
            st.rerun()
        else:
            st.session_state.intro_done = True
            st.rerun()

# Lógica do passo atual
if st.session_state.chat_step < len(perguntas):
    # Pula perguntas já respondidas (inclusive pessoais), mesmo que a ordem mude
    while st.session_state.chat_step < len(perguntas) and perguntas[st.session_state.chat_step]["chave"] in st.session_state.chat_respostas:
        st.session_state.chat_step += 1
    if st.session_state.chat_step >= len(perguntas):
        st.rerun()

    atual = perguntas[st.session_state.chat_step]
    chave = atual["chave"]
    tipo = atual["tipo"]
    msg = atual["mensagem"].format(**st.session_state.chat_respostas)

    # Exibe a pergunta com digitação (bolha do assistente) e só então mostra o input
    if "question_shown" not in st.session_state or chave not in st.session_state.question_shown:
        send_assistant_message(msg)
        track_event('generate_lead', {"step": "Perguntas", "q_key": chave})
        st.session_state.question_shown = st.session_state.get("question_shown", set())
        st.session_state.question_shown.add(chave)
        st.rerun()

    with st.chat_message("user", avatar=USER_AVATAR):
        # Mensagem da pergunta com efeito de digitação (uma única vez)
        if chave not in st.session_state.question_shown:
            send_assistant_message(msg)
            st.session_state.question_shown.add(chave)
            st.rerun()

        # Opção inline para reiniciar mantendo dados pessoais (controlada por flag)
        if SHOW_INLINE_RESTART:
            if st.button("🔄 Reiniciar conversa (manter dados pessoais)", key=f"restart_inline_{chave}"):
                restart_keep_personal()

        resposta = None
        if tipo == "text":
            if chave == "celular":
                st.session_state[chave] = mask_phone(st.session_state.get(chave, ""))
                resposta = st.text_input("", key=chave, placeholder="(99) 99999-9999", label_visibility="collapsed")
            elif chave == "cpf":
                st.session_state[chave] = mask_cpf(st.session_state.get(chave, ""))
                resposta = st.text_input("", key=chave, placeholder="999.999.999-99", label_visibility="collapsed")
            else:
                resposta = st.text_input("", key=chave, label_visibility="collapsed")
        elif tipo == "radio":
            resposta = st.radio("", atual["opcoes"], key=chave, label_visibility="collapsed")
        elif tipo == "checkboxes":
            selecionadas = []
            for i, opc in enumerate(atual["opcoes"]):
                key_opt = f"{chave}_{i}"
                checked = st.checkbox(opc, key=key_opt)
                if checked:
                    selecionadas.append(opc)
            # Regra: se "Não sinto dores recorrentes" for marcado, desmarca os outros
            if "Não sinto dores recorrentes" in atual.get("opcoes", []):
                idx_none = atual["opcoes"].index("Não sinto dores recorrentes")
                if st.session_state.get(f"{chave}_{idx_none}"):
                    for i, opc in enumerate(atual["opcoes"]):
                        if i != idx_none:
                            st.session_state[f"{chave}_{i}"] = False
                    selecionadas = ["Não sinto dores recorrentes"]
            resposta = selecionadas
        elif tipo == "date":
            resposta = st.date_input("", key=chave, format="DD/MM/YYYY", min_value=date(1900, 1, 1), max_value=date.today(), label_visibility="collapsed")

        # Habilita Responder apenas quando há uma resposta válida
        ready = (tipo == "checkboxes" and len(resposta) > 0) or (tipo != "checkboxes" and resposta)
        if ready and st.button("Responder"):
            # Validações e autoformatação de celular/CPF
            if chave == "celular":
                phone_raw = str(resposta).strip()
                phone_digits = ''.join(c for c in phone_raw if c.isdigit())
                if len(phone_digits) == 11:
                    ddd, p1, p2 = phone_digits[:2], phone_digits[2:7], phone_digits[7:]
                    resposta = f"({ddd}) {p1}-{p2}"
                else:
                    st.error("Por favor, informe o celular com 11 dígitos (formato: (99) 99999-9999).")
                    st.stop()
            if chave == "cpf":
                cpf_raw = str(resposta).strip()
                cpf_digits = ''.join(c for c in cpf_raw if c.isdigit())
                if len(cpf_digits) == 11:
                    resposta = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"
                else:
                    st.error("Por favor, informe o CPF com 11 dígitos (formato: 999.999.999-99).")
                    st.stop()

            if tipo == "date":
                resposta_formatada = resposta.strftime("%d/%m/%Y")
                st.session_state.chat_respostas[chave] = resposta_formatada
            else:
                st.session_state.chat_respostas[chave] = resposta

            # Evita duplicar a pergunta no histórico (já foi exibida via send_assistant_message)
            if "question_shown" not in st.session_state or chave not in st.session_state.question_shown:
                st.session_state.chat_history.append({"role": "assistant", "content": msg})
            st.session_state.chat_history.append({"role": "user", "content": str(st.session_state.chat_respostas[chave])})
            st.session_state.chat_step += 1
            st.rerun()

elif not st.session_state.processing_done:
    # Sequência de processamento/validação antes do resultado final
    nome = st.session_state.chat_respostas.get("nome", "")
    nome = nome.strip() if isinstance(nome, str) else ""
    if nome:
        primeiro_nome_raw = nome.split(" ")[0]
    else:
        primeiro_nome_raw = "Você"
    primeiro_nome = (primeiro_nome_raw[:1].upper() + primeiro_nome_raw[1:].lower()) if primeiro_nome_raw else "Você"

    track_event('generate_lead', {"step": "Analise_respostas", "q_key": "Analise_respostas"})

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        st.markdown(f"Obrigado pelas informações, **{primeiro_nome}**! Vou iniciar a análise do que você me respondeu.")
        status = st.empty()
        progress = st.progress(0)
        etapas = [
            ("Analisando rotina...", 25),
            ("Analisando estado emocional...", 55),
            ("Consolidando resultado...", 85),
            ("Finalizando...", 100),
        ]
        for texto, pct in etapas:
            status.markdown(texto)
            time.sleep(0.9)
            progress.progress(pct)
        status.markdown("Pronto!")

    # Persistir mensagens no histórico
    #st.session_state.chat_history.append({"role": "assistant", "content": f"Obrigado pelas informações, **{primeiro_nome}**! Vou iniciar a análise do que você me respondeu."})
    #st.session_state.chat_history.append({"role": "assistant", "content": "Analisando rotina..."})
    #st.session_state.chat_history.append({"role": "assistant", "content": "Analisando estado emocional..."})
    #st.session_state.chat_history.append({"role": "assistant", "content": "Consolidando resultado..."})

    st.session_state.processing_done = True
    st.rerun()

else:
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        st.success("Avaliação finalizada! Aqui estão suas sugestões personalizadas:")

        r = st.session_state.chat_respostas
        recomendacoes = []

        if "dores" in r:
            if "Ombros/pescoço" in r["dores"]:
                recomendacoes.append("💆 Massagem relaxante para pescoço e ombros.")
            if "Lombar" in r["dores"]:
                recomendacoes.append("🧘 Terapia para aliviar tensão lombar.")
            if "Pernas/pés" in r["dores"]:
                recomendacoes.append("🦵 Drenagem linfática pode ser ideal para você.")

        if r.get("sono") == "Tenho dificuldade para dormir":
            recomendacoes.append("😴 Aromaterapia pode melhorar seu sono.")

        if r.get("energia") == "Me sinto sem energia":
            recomendacoes.append("⚡ Sessões revigorantes para aumentar sua energia.")

        texto_corrido = " ".join(recomendacoes)
        track_event('generate_lead', {"step": "Recomendacao", "q_key": texto_corrido})

        for rec in recomendacoes:
            st.write("- ", rec)

        st.divider()
        st.subheader("Resumo das respostas")
        st.json(st.session_state.chat_respostas)
        st.write("Em breve, nossa equipe entrará em contato via WhatsApp ✨")

        # Botão para reiniciar após apresentar o resultado
        if st.button("🔄 Reiniciar conversa", key="restart_after_result"):
            restart_keep_personal()


# Fecha wrapper do chat
st.markdown('</div>', unsafe_allow_html=True)
