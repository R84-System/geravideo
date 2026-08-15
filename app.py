import os
import imageio_ffmpeg
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
import fastf1
from fastf1.exceptions import DataNotLoadedError
import streamlit as st

# Configura o FFmpeg integrado
plt.rcParams['animation.ffmpeg_path'] = imageio_ffmpeg.get_ffmpeg_exe()

# Configuração do diretório de cache local do FastF1
CACHE_DIR = 'cache_f1'
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)


# --- FUNÇÕES COM CACHE DO STREAMLIT ---

@st.cache_data(show_spinner=False)
def carregar_calendario(ano):
    """Carrega o calendário de GPs para o ano selecionado e devolve uma lista de opções."""
    try:
        schedule = fastf1.get_event_schedule(ano)
        # Filtra eventos de testes de pré-temporada
        if 'EventFormat' in schedule.columns:
            schedule = schedule[schedule['EventFormat'] != 'testing']
        
        opcoes = []
        for _, row in schedule.iterrows():
            nome_formatado = f"Etapa {row['RoundNumber']:02d} - {row['EventName']} ({row['Location']})"
            opcoes.append({
                "label": nome_formatado,
                "round": int(row['RoundNumber']),
                "name": str(row['EventName'])
            })
        return opcoes
    except Exception as e:
        return []


@st.cache_data(show_spinner=False, ttl=86400)
def carregar_sessao(ano, round_number, tipo_sessao):
    """Guarda a sessão em memória por 24h para evitar requisições repetidas ao servidor da F1."""
    session = fastf1.get_session(ano, round_number, tipo_sessao)
    session.load(laps=True, telemetry=True, weather=False, messages=False)
    return session


# --- FUNÇÃO PRINCIPAL DE GERAÇÃO DO VÍDEO ---

def gerar_video_customizado(ano, round_number, gp_nome, tipo_sessao, p1_code, p2_code, volta_inicio, volta_fim, duracao_segundos, fps=30):
    total_frames = duracao_segundos * fps

    # 1. Carrega a sessão oficial utilizando o cache
    try:
        session = carregar_sessao(ano, round_number, tipo_sessao)
    except Exception as e:
        raise ValueError(f"Não foi possível obter dados para o GP '{gp_nome}' ({ano}). Motivo: {e}")

    # 2. Valida se as voltas existem
    try:
        laps = session.laps
        if laps is None or len(laps) == 0:
            raise ValueError("Não existem dados de voltas registados para esta sessão.")
    except (DataNotLoadedError, AttributeError):
        raise ValueError("A telemetria não pôde ser descarregada do servidor da F1. Tente novamente dentro de instantes.")

    # 3. Filtra os pilotos selecionados
    pilotos_disponiveis = sorted(laps['Driver'].unique()) if 'Driver' in laps else []

    laps_p1 = laps.pick_driver(p1_code)
    laps_p2 = laps.pick_driver(p2_code)

    if len(laps_p1) == 0:
        raise ValueError(f"O piloto '{p1_code}' não participou nesta sessão. Pilotos disponíveis: {', '.join(pilotos_disponiveis)}")

    if len(laps_p2) == 0:
        raise ValueError(f"O piloto '{p2_code}' não participou nesta sessão. Pilotos disponíveis: {', '.join(pilotos_disponiveis)}")

    # 4. Filtra por intervalo de voltas
    laps_p1_filtered = laps_p1[(laps_p1['LapNumber'] >= volta_inicio) & (laps_p1['LapNumber'] <= volta_fim)]
    laps_p2_filtered = laps_p2[(laps_p2['LapNumber'] >= volta_inicio) & (laps_p2['LapNumber'] <= volta_fim)]

    if len(laps_p1_filtered) == 0 or len(laps_p2_filtered) == 0:
        max_volta = int(laps['LapNumber'].max())
        raise ValueError(f"Sem dados para o intervalo de voltas {volta_inicio} a {volta_fim}. O número máximo de voltas registado nesta sessão foi {max_volta}.")

    # 5. Obtém telemetria de GPS
    try:
        tel1 = laps_p1_filtered.get_telemetry()
        tel2 = laps_p2_filtered.get_telemetry()
    except (DataNotLoadedError, Exception):
        raise ValueError("A telemetria de GPS não está disponível para o intervalo de voltas selecionado.")

    if len(tel1) == 0 or len(tel2) == 0:
        raise ValueError("A telemetria do traçado para estas voltas está vazia.")

    # 6. Reamostragem dos dados para animação contínua
    time_orig1 = np.linspace(0, 1, len(tel1))
    time_orig2 = np.linspace(0, 1, len(tel2))
    target_time = np.linspace(0, 1, total_frames)

    x1_interp = np.interp(target_time, time_orig1, tel1['X'])
    y1_interp = np.interp(target_time, time_orig1, tel1['Y'])

    x2_interp = np.interp(target_time, time_orig2, tel2['X'])
    y2_interp = np.interp(target_time, time_orig2, tel2['Y'])

    # 7. Renderização no formato 9:16 (Vertical / TikTok)
    fig, ax = plt.subplots(figsize=(9, 16), facecolor='#0e0e10')
    ax.set_facecolor('#0e0e10')
    ax.axis('off')

    # Traçado da pista
    ax.plot(tel1['Y'], tel1['X'], color='#33333e', linewidth=3)

    # Carros dos dois pilotos
    p1, = ax.plot([], [], 'o', color='#1E41FF', markersize=14, label=p1_code)
    p2, = ax.plot([], [], 'o', color='#FF8000', markersize=14, label=p2_code)

    # Títulos e cronómetro
    ax.text(0.5, 0.96, f"{p1_code} vs {p2_code}", transform=ax.transAxes,
            color='white', fontsize=22, fontweight='bold', ha='center')
    ax.text(0.5, 0.93, f"{gp_nome} {ano}", transform=ax.transAxes,
            color='#aaaaaa', fontsize=14, ha='center')

    timer_text = ax.text(0.5, 0.89, '', transform=ax.transAxes, color='white', 
                         fontsize=16, fontweight='bold', ha='center')

    def update(frame):
        p1.set_data([y1_interp[frame]], [x1_interp[frame]])
        p2.set_data([y2_interp[frame]], [x2_interp[frame]])

        tempo_decorrido = (frame / fps)
        timer_text.set_text(f"Tempo: {int(tempo_decorrido)}s / {duracao_segundos}s")
        return p1, p2, timer_text

    anim = FuncAnimation(fig, update, frames=total_frames, interval=1000/fps, blit=True)

    nome_arquivo = f"f1_{p1_code}_vs_{p2_code}_{ano}_R{round_number}.mp4"
    anim.save(nome_arquivo, writer='ffmpeg', fps=fps)
    plt.close(fig)

    return nome_arquivo


# --- INTERFACE UTILIZADOR (STREAMLIT) ---

st.set_page_config(page_title="Gerador F1 TikTok", layout="centered")

st.title("🏎️ Gerador de Duelos F1 - TikTok")
st.write("Escolha a temporada, o circuito, os pilotos e o intervalo de voltas para gerar o vídeo vertical.")

st.sidebar.header("⚙️ Configurações da Corrida")

# 1. Seleção do Ano
ano = st.sidebar.number_input("Ano da Temporada", min_value=2018, max_value=2026, value=2024)

# 2. Seleção de Circuito via Menu Dropdown (buscado do calendário da F1)
lista_gps = carregar_calendario(ano)

if lista_gps:
    opcoes_labels = [item['label'] for item in lista_gps]
    gp_selecionado_label = st.sidebar.selectbox("Selecione o Grande Prêmio / Circuito", opcoes_labels)
    
    gp_info = next(item for item in lista_gps if item['label'] == gp_selecionado_label)
    round_number = gp_info['round']
    gp_nome = gp_info['name']
else:
    st.sidebar.error("Não foi possível carregar o calendário para este ano.")
    round_number = 1
    gp_nome = "GP"

# 3. Tipo de Sessão
tipo_sessao_map = {
    "Corrida (Race)": "R",
    "Qualificação (Qualifying)": "Q",
    "Treino Livre 1 (FP1)": "FP1",
    "Treino Livre 2 (FP2)": "FP2",
    "Treino Livre 3 (FP3)": "FP3",
    "Sprint": "S"
}
tipo_sessao_label = st.sidebar.selectbox("Tipo de Sessão", list(tipo_sessao_map.keys()))
tipo_sessao = tipo_sessao_map[tipo_sessao_label]

st.sidebar.header("🏁 Pilotos e Voltas")

pilotos_frequentes = ["VER", "NOR", "LEC", "HAM", "SAI", "PIA", "RUS", "ALO", "PER", "TSU", "HUL", "ALB", "GAS", "OCO", "STR", "MAG", "BOT", "ZHO", "SAR", "BEA", "LAW", "COL"]

col1, col2 = st.sidebar.columns(2)
with col1:
    p1_code = st.selectbox("Piloto 1", pilotos_frequentes, index=0)
with col2:
    p2_code = st.selectbox("Piloto 2", pilotos_frequentes, index=1)

col3, col4 = st.sidebar.columns(2)
with col3:
    volta_inicio = st.number_input("Volta Inicial", min_value=1, value=50)
with col4:
    volta_fim = st.number_input("Volta Final", min_value=1, value=53)

duracao_segundos = st.sidebar.slider("Duração do Vídeo (segundos)", min_value=15, max_value=120, value=60, step=15)

# Botão principal para acionar a geração
if st.button("🚀 Gerar Vídeo Personalizado", type="primary"):
    try:
        with st.spinner(f"A descarregar telemetria e a renderizar {p1_code} vs {p2_code}... Por favor aguarde."):
            nome_video = gerar_video_customizado(
                ano=ano,
                round_number=round_number,
                gp_nome=gp_nome,
                tipo_sessao=tipo_sessao,
                p1_code=p1_code,
                p2_code=p2_code,
                volta_inicio=volta_inicio,
                volta_fim=volta_fim,
                duracao_segundos=duracao_segundos,
                fps=30
            )

            st.success("✅ Vídeo gerado com sucesso!")
            st.video(nome_video)

            with open(nome_video, "rb") as file:
                st.download_button(
                    label="📥 Baixar Vídeo MP4",
                    data=file,
                    file_name=nome_video,
                    mime="video/mp4"
                )
    except Exception as e:
        st.error(f"❌ {e}")
