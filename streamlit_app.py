import streamlit as st
import json
from datetime import datetime, date
import time
import streamlit.components.v1 as components
from supabase import create_client, Client
import urllib.parse

# Lê secrets (seguro no cloud)
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
tabela = st.secrets["supabase"]["tabela"]

supabase: Client = create_client(url, key)

# Número de WhatsApp (com DDI)
WHATSAPP_NUMBER = st.secrets["whatsapp"]["numero"]


def salvar_resposta(nome, data_nascimento, genero, celular, dores, sensacao_corpo, sono, energia, rotina, estatica, resultado, resposta_json):
    
    # Converte para datetime
    data_dt = datetime.strptime(data_nascimento, "%d/%m/%Y")
    # Formata no padrão ISO para Supabase
    data_iso = data_dt.strftime("%Y-%m-%d")

    data = {
        "nome": nome,
        "data_nascimento": data_iso,
        "genero": genero,
        "celular": celular,
        "dores": dores,
        "sensacao_corpo": sensacao_corpo,
        "sono": sono,
        "energia": energia,
        "rotina": rotina,
        "estatica": estatica,
        "resultado": resultado,
        "resposta_json": resposta_json
    }

    try:
        supabase.table(tabela).insert(data).execute()
    except:
        print("erro salvar db")


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
BANNER_LOGO_URL = "https://i.postimg.cc/85S4mr1V/logo-Buddha-Spa-Unidades-ai-5.png"  # defina aqui a URL do logo se quiser exibir
BANNER_TITLE = "Buddha Spa Partage Santana"
BANNER_SUBTITLE = "Avaliação de Bem-Estar"

def render_banner():
    st.markdown('<div class="chat-shell"><div class="banner-card">', unsafe_allow_html=True)
    
    st.markdown(f'<h4 class="banner-title"><center>{BANNER_TITLE}</center></h4>', unsafe_allow_html=True)
    st.markdown(f'<p class="banner-sub"><center>{BANNER_SUBTITLE}</center></p>', unsafe_allow_html=True)
    
    
    #cols = st.columns([1, 2])
    #with cols[0]:
    #    if BANNER_LOGO_URL:
    #        st.image(BANNER_LOGO_URL, width=400)
    #    #else:
    #        #st.markdown('<div class="logo-ph">Logo do Buddha Spa</div>', unsafe_allow_html=True)
    #with cols[1]:
    #    st.markdown(f'<h4 class="banner-title">{BANNER_TITLE}</h4>', unsafe_allow_html=True)
    #    st.markdown(f'<p class="banner-sub">{BANNER_SUBTITLE}</p>', unsafe_allow_html=True)
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
#Dourado: https://i.postimg.cc/ZnhqR4FH/Design-sem-nome-1.png
#Marsala: https://i.postimg.cc/BZ5c46Jj/Design-sem-nome.png
ASSISTANT_AVATAR = "https://i.postimg.cc/ZnhqR4FH/Design-sem-nome-1.png"  # ou URL de imagem, ex: "https://seu-dominio/logo.png"
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
GA4_ID = "G-E0YMPLJW9S"            # <-- substitua pelo seu ID GA4
GA_ID = "G-E0YMPLJW9S"            # <-- substitua pelo seu ID GA4
PIXEL_ID = "821834817180823"       # <-- substitua pelo seu Pixel ID

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
    try {{ if (typeof fbq  === 'function') fbq('Lead', '{name}', {payload}); }} catch(e){{}}
    </script>
    """, height=0)
#Daniel
st.markdown(
    f"""
    <!-- Global site tag (gtag.js) - Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{GA_ID}');
    </script>
    """,
    unsafe_allow_html=True
)
def track_eventDaniel(event_name: str, params: dict = None):
    params_js = "{}" if not params else str(params).replace("'", '"')
    components.html(
        f"""
        <script>
        if (typeof gtag !== 'undefined') {{
            gtag('event', '{event_name}', {params_js});
        }}
        </script>
        """,
        height=0,
    )

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
    {"chave": "data_nascimento", "tipo": "date", "mensagem": "{nome}, poderia informar a sua data de nascimento?"},
    {"chave": "genero", "tipo": "radio", "mensagem": "Agora, {nome}, poderia me dizer qual genero você se identifica?", "opcoes": ["Feminino", "Masculino", "Outro", "Prefiro não informar"]},
    {"chave": "celular", "tipo": "text", "mensagem": "Por fim, {nome}, compartilha comigo seu número de WhatsApp, por favor?"},
    
    
    {"chave": "dores", "tipo": "radio", "mensagem": "Você tem sentido algum desconforto físico frequente? Qual mais te incomoda?", "opcoes": ["Nos ombros e pescoço", "Na lombar", "Nas pernas", "Cabeça pesada" ,"Me sinto bem"]},
    {"chave": "sensacao_corpo", "tipo": "radio", "mensagem": "Me conta, você tem sentido alguma dessas sensações?", "opcoes": ["Bem cansado, meio pesado(a)..", "Tenho sentido bastante inchaço", "Sinto tensões musculares", "Estou bem, me sinto leve"]},
    {"chave": "sono", "tipo": "radio", "mensagem": "Qual frase resume seu sono, {nome}?", "opcoes": ["Tenho dificuldade para dormir", "Meu sono está irregular, acordo a noite e perco o sono", "Quanto mais eu durmo, mais quero dormir", "Durmo bem, acordo descansado(a)"]},
    
     
    {"chave": "energia", "tipo": "radio", "mensagem": "Qual dessas frase mais representa você no final de um dia?", "opcoes": ["Chego no final do dia estressado(a) ou irritado(a) mentalmente", "Chego cansado(a) fisicamente", "Chego no final do dia esgotado(a) ou sobrecarregado(a)", "Me sinto cansado, mas nada demais", "Chego bem disposto(a) no final do dia"]},
    {"chave": "rotina", "tipo": "radio", "mensagem": "Escolha qual opção você mais se identifica no dia a dia", "opcoes": ["Minha rotina é bem acelerada", "Sou multi tarefa, estou sempre fazendo muitas coisas",  "Me sinto bem com minha rotina", "Olha, tenho uma rotina tranquila"]},
    #{"chave": "tempo_livre", "tipo": "radio", "mensagem": "E nos tempos livres, {nome}, o que você faz?", "opcoes": ["Quando tenho tempo livre, descanso", "Passo dia todo em casa", "Nessas horas eu procuro tá com amigos, familia..", "Eu gosto de me manter ativo, fazer algo..", "Eu me vejo diferente das opções"]},
    
    #{"chave": "ambiente", "tipo": "radio", "mensagem": "Quando você está na sua casa, como você se sente?", "opcoes": ["Me sinto leve, olho ao redor e tudo está organizado e no lugar", "As vezes tá tudo bagunçado e eu arrumo rapidinho", "Tá tudo bagunçado mas eu não tenho energia para arrumar", "Me sinto cansado, parece que tem algo pesado"]},
    {"chave": "estatica", "tipo": "radio", "mensagem": "Quando você encosta em algo metálico, toma choque?", "opcoes": ["Quase toda vez", "Não é sempre, mas tomo sim..", "Não, não estou tomando choques.."]},
    
    #{"chave": "objetivo", "tipo": "radio", "mensagem": "Hoje, o que mais está te incomodando, {nome}?", "opcoes": ["As dores que sinto", "A qualidade do meu sono", "Meu estresse está demais", "O inchaço do meu corpo" ,"Minha energia está muito baixa", "Meu sentimento quando estou em casa", "Não tenho clareza", "Nada está me incomodando.."]},
    
    #{"chave": "cpf", "tipo": "text", "mensagem": "Você me informa o seu CPF, por favor?"},
    #{"chave": "nome_completo", "tipo": "text", "mensagem": "{nome}, preciso também do seu nome completo, por gentileza"},
]


# Mensagens iniciais (aparecem antes da primeira pergunta)
INTRO_SEQUENCE = [
    {"text": "Que bom ter você aqui comigo hoje!", "typing_delay": 0.03, "pause": 0.4},
    {"text": "Quero te conhecer um pouco mais e saber como anda sua rotina. Assim consigo personalizar algo específico para você..", "typing_delay": 0.025, "pause": 0.4},
    #{"text": "Assim consigo te recomendar algo que realmente faça diferença.", "typing_delay": 0.025, "pause": 0.3},
    #{"text": "Vamos começar... :D", "typing_delay": 0.025, "pause": 0.4},
]


# Pausas configuráveis antes de algumas perguntas (opcional)
# Preencha com a chave da pergunta e a mensagem desejada
PAUSE_MESSAGES = {
    # string simples
    #"energia": "{nome}, vamos conversar agora sobre a sua disposição.. ",
    # ou com tempos
    #"energia": {"text": "E quanto à sua disposição?", "typing_delay": 0.02, "pause": 0.7},
    #"ambiente": {"text": "Agora eu quero entender um pouco do seu ambiente.", "typing_delay": 0.02, "pause": 0.7},
    "dores": {"text": "Vou te fazer algumas perguntas sobre como você vem se sentindo últimamente.. ", "typing_delay": 0.02, "pause": 0.7},
    "cpf": {"text": "Obrigado pelas informações, estou consolidando tudo, enquanto faço isso, vou aproveitar e pedir mais 2 informações..", "typing_delay": 0.02, "pause": 0.7},
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

    # 👇 Normaliza o nome se já existir
    if "nome" in st.session_state.chat_respostas:
        nome = st.session_state.chat_respostas["nome"].strip()
        if nome:  # evita erro se for string vazia
            primeiro_nome = nome.split(" ")[0]  # pega só o primeiro
            st.session_state.chat_respostas["nome"] = (
                primeiro_nome[:1].upper() + primeiro_nome[1:].lower()
            )

    atual = perguntas[st.session_state.chat_step]
    chave = atual["chave"]
    tipo = atual["tipo"]
    msg = atual["mensagem"].format(**st.session_state.chat_respostas)

    # Pausa configurável antes da pergunta (com digitação)
    if chave in PAUSE_MESSAGES and chave not in st.session_state.pause_shown:
        pause_meta = PAUSE_MESSAGES[chave]
        if isinstance(pause_meta, dict):
            text = pause_meta.get("text", "")
            tdelay = pause_meta.get("typing_delay")
            ppause = pause_meta.get("pause")
        else:
            text = str(pause_meta)
            tdelay = None
            ppause = None
        send_assistant_message(text, tdelay, ppause)
        st.session_state.pause_shown.add(chave)
        st.rerun()


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
    track_event('generate_lead', {"step": "Analise_respostas", "q_key": "Analise_respostas"})
    st.rerun()

else:
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        st.success("Avaliação finalizada! Aqui estão suas sugestões personalizadas:")

        rRlx = rShiatsu = rDrenagem = rBanhoImersao = rOleoSono = rOleoEnergia = 0

        r = st.session_state.chat_respostas
        recomendacoes = []

        if "dores" in r:
            if  "ombros e pescoço" in r["dores"] or "lombar" in r["dores"]:
                rShiatsu += 1
            elif "pernas" in r["dores"]:
                rDrenagem += 1
            elif "Cabeça pesada" in r["dores"] or "Me sinto bem" in r["dores"]:
                rRlx += 1
        
        if "sensacao_corpo" in r:
            if  "Bem cansado, meio pesado(a)" in r["sensacao_corpo"] or "Estou bem, me sinto leve" in r["sensacao_corpo"]:
                rRlx += 1
            elif "inchaço" in r["sensacao_corpo"]:
                rDrenagem += 1
            elif "tensões musculares" in r["sensacao_corpo"]:
                rShiatsu += 1

        if "sono" in r:
            rRlx += 1
            if  "dificuldade para dormir" in r["sono"] or "sono está irregular" in r["sono"]:
                rOleoSono += 1
            elif  "Quanto mais eu durmo, mais quero dormir" in r["sono"]:
                rOleoEnergia += 1
        
        if "energia" in r:
            if  "irritado(a) mentalmente" in r["energia"] or "Me sinto cansado, mas nada demais" in r["energia"] or "Chego bem disposto(a) no final do dia" in r["energia"]:
                rRlx += 1
            elif "Chego cansado(a) fisicamente" in r["energia"] or "esgotado(a) ou sobrecarregado(a)" in r["energia"]:
                rShiatsu += 1

        if "rotina" in r:
            rRlx += 1
        
        if "estatica" in r:
            if  "Quase toda vez" in r["estatica"] or "Não é sempre, mas tomo sim" in r["estatica"]:
                rBanhoImersao += 1
        
        #========== GERANDO RECOMENDAÇÃO ===============
        recomendacoes.append(st.session_state.chat_respostas["nome"]+", vou compartilhar o que elaborei exclusivamente para você..")

        drenagem = relxante = shiatsu = miniday = mencare = False

        texto = ""
        if r.get("genero") != "Masculino":
            
            if rDrenagem > 0:
                recomendacoes.append("**Drenagem Linfática:** por estimular o sistema linfático vai ajudar na desintoxicação do corpo e alívio dos inchhaços")
                #texto += "**Drenagem Linfática:** por estimular o sistema linfático vai ajudar na desintoxicação do corpo e alívio dos inchhaços"
                drenagem = True
            
            if rRlx > 0 and rBanhoImersao > 0:
                recomendacoes.append("**Mini Day Spa**: Vai ajudar a trazer mais calma e desacelerar a rotina do dia a dia. Experiência de 1h30min iniciando com delicioso banho de imersão na hidromassagem e em seguida deliciosa massagem relaxante corporal de 60 minutos.")
                #texto += "**Mini Day Spa**: Vai ajudar a trazer mais calma e desacelerar a rotina do dia a dia. Experiência de 1h30min iniciando com delicioso banho de imersão na hidromassagem e em seguida deliciosa massagem relaxante corporal de 60 minutos."
                miniday = True
        else:
            if rRlx <= 2:
                recomendacoes.append("**Relaxante Mencare:** terapia desenvolvida especialmente para pele masculina que visa ajudar a desacelerar..")
                recomendacoes.append("**Shiatsu:** Vai ajudar a reestabelecer equilíbrio energático e aliviar desconfortos físicos")
                #texto += "**Relaxante Mencare:** terapia desenvolvida especialmente para pele masculina que visa ajudar a desacelerar.."
                #texto += "**Shiatsu:** Vai ajudar a reestabelecer equilíbrio energático e aliviar desconfortos físicos"
                mencare = True
                shiatsu = True
            else:
                #recomendacoes.append("**Relaxante 90min:** Vai ajudar a acalmar e equilibrar o corpo e a mente.")
                texto = "**Relaxante 90min:** Vai ajudar a acalmar e equilibrar o corpo e a mente."
                if rBanhoImersao > 0:
                    #recomendacoes.append("Combinado com escalda pés com sais de banhos exclusivos que ajudam a regular a bioeletrecidade do corpo, ajuda na reduçaõ dos choques em contato com metal..")
                    texto += "Combinado com escalda pés com sais de banhos exclusivos que ajudam a regular a bioeletrecidade do corpo, ajuda na reduçaõ dos choques em contato com metal.."
                recomendacoes.append(texto)
                relxante = True

        if rOleoSono > 0:
            recomendacoes.append("**Óleo Essencial Sono:** Para melhorar a qualidade do sono.")
            #texto += "**Óleo Essencial Sono:** Para melhorar a qualidade do sono."
        elif rOleoEnergia >0:
            recomendacoes.append("**Óleo Essencial Energia:** Para melhorar disposição ao acordar.")
            #texto += "**Óleo Essencial Energia:** Para melhorar disposição ao acordar."

        
        #recomendacoes.append(texto)
        CUPOM_AVALIACAO = "AVALIACAO50"
        RECOMENDACAO_RESUMIDA = ""
        if(drenagem):
            RECOMENDACAO_RESUMIDA += "Drenagem Linfática, "
        if(miniday):
            RECOMENDACAO_RESUMIDA += "Mini Day Spa, "
        if(mencare):
            RECOMENDACAO_RESUMIDA += "Mencare e Shiatsu, "
        if(relxante):
            RECOMENDACAO_RESUMIDA += "Relaxante 90 minutos, "
        
        if rOleoSono >=0:
            RECOMENDACAO_RESUMIDA += "Óleo Sono"
        elif rOleoEnergia >= 0:
            RECOMENDACAO_RESUMIDA += "Óleo Energia"

        recomendacoes.append("Use o copom **"+CUPOM_AVALIACAO+"** para ter um bônus de R$50 para sua jornada de cuidar de sí. Esse cupom é válido até 15/10/25 e não reversível em dinheiro.")
        for rec in recomendacoes:
            with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
                st.markdown(rec)
            #st.write("- ", rec)
                #send_assistant_message(rec)

        st.divider()
        #st.subheader("Resumo das respostas")
        #st.json(st.session_state.chat_respostas)
        #st.write("Em breve, nossa equipe entrará em contato via WhatsApp ✨")

        texto_corrido = " ".join(recomendacoes)

        salvar_resposta(nome=r.get("nome"), 
                        data_nascimento=r.get("data_nascimento"),
                        genero=r.get("genero"),
                        celular=r.get("celular"), 
                        dores=r.get("dores"),
                        sensacao_corpo=r.get("sensacao_corpo"),
                        sono=r.get("sono"), 
                        energia=r.get("energia"),rotina=r.get("rotina"),estatica=r.get("estatica"),
                        resultado=texto_corrido, 
                        resposta_json=st.session_state.chat_respostas)

        # Botão para reiniciar após apresentar o resultado
        # Mensagem padrão
        
        mensagem = f"Olá! Acabei de finalizar a avaliação no Buddha Spa Partage Santana. Me deram esse cupom {CUPOM_AVALIACAO} e me recomendaram {RECOMENDACAO_RESUMIDA}"
        mensagem_encoded = urllib.parse.quote(mensagem)
        wa_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={mensagem_encoded}"
        

        # Botão que abre em nova aba
        # Botão como link estilizado
        st.markdown(
            f"""
            <a href="{wa_url}" target="_blank">
                <button style="padding:10px 20px; border:none; border-radius:8px; background-color:#25D366; color:white; font-size:16px; cursor:pointer;">
                    📲 Fale com nosso time
                </button>
            </a>
            """,
            unsafe_allow_html=True
        )
                
        
        #if st.button("🔄 Reiniciar conversa", key="restart_after_result"):
        #    restart_keep_personal()
        
        track_eventDaniel("tutorial_complete", {"method": "resultado_chat"})
        track_event('generate_lead', {"step": "Recomendacao", "q_key": texto_corrido})

# Fecha wrapper do chat
st.markdown('</div>', unsafe_allow_html=True)
