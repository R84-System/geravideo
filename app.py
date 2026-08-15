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

# Cache local do FastF1
os.makedirs('cache_f1', exist_ok=True)
fastf1.Cache.enable_cache('cache_f1')


@st.cache_data(show_spinner=False)
def carregar_calendario(ano):
    """Carrega automaticamente o calendário oficial do ano selecionado via FastF1."""
    try:
        schedule = fastf1.get_event_schedule(ano)
        # Filtra etapas válidas (remove sessões de testes de pré-temporada)
        schedule = schedule[schedule['EventFormat'] != 'testing']
        
        opcoes = []
        for _, row in schedule.iterrows():
            nome_formatado = f"Etapa {row['RoundNumber']:02d} - {row['EventName']} ({row['Location']})"
            opcoes.append({
                "label": nome_formatado,
                "round": int(row['RoundNumber']),
                "name": row['EventName']
            })
        return opcoes
    except Exception:
        return []


def gerar_video_customizado(ano, round_number, gp_nome, tipo_sessao, p1_code, p2_code, volta_inicio, volta_fim, duracao_segundos, fps=30):
    total_frames = duracao_segundos * fps

    # 1. Carrega a sessão oficial pelo número da etapa
    try:
        session = fastf1.get_session(ano, round_number, tipo_sessao)
        session.load(laps=True, telemetry=True, weather=False, messages=False)
    except Exception as e:
        raise ValueError(f"Não foi possível descarregar os dados para o {gp_nome} ({ano}). Erro: {e}")

    # 2. Valida se as voltas foram carregadas
    try:
        laps = session.laps
        if laps is None or len(laps) == 0:
            raise ValueError("Nenhum dado de volta foi encontrado para esta sessão.")
    except DataNotLoadedError:
        raise ValueError("A telemetria não pôde ser carregada do servidor da F1. Tente novamente em alguns instantes.")

    # 3. Filtra os pilotos selecionados
    pilotos_disponiveis = sorted(laps['Driver'].unique()) if 'Driver' in laps else []

    try:
        laps_p1 = laps.pick_driver(p1_code)
        laps_p2 = laps.pick_driver(p2_code)
    except Exception as e:
        raise ValueError(f"Erro ao filtrar pilotos na sessão: {e}")

    if len(laps_p1) == 0:
        raise ValueError(f"O piloto '{p1_code}' não participou desta sessão. Pilotos presentes: {', '.join(pilotos_disponiveis)}")

    if len(laps_p2) == 0:
        raise ValueError(f"O piloto '{p2_code}' não participou desta sessão. Pilotos presentes: {', '.join(pilotos_disponiveis)}")

    # 4. Filtra o intervalo de voltas
    laps_p1 = laps_p1[(laps_p1['LapNumber'] >= volta_inicio) & (laps_p1['LapNumber'] <= volta_fim)]
    laps_p2 = laps_p2[(laps_p2['LapNumber'] >= volta_inicio) & (laps_p2['LapNumber'] <= volta_fim)]

    if len(laps_p1) == 0 or len(laps_p2) == 0:
        max_volta = int(laps['LapNumber'].max())
        raise ValueError(f"Sem dados para as voltas {volta_inicio} a {volta_fim}. O número máximo de voltas registado nesta sessão foi {max_volta}.")

    # 5. Obtém telemetria dos dois carros
    try:
        tel1 = laps_p1.get_telemetry()
        tel2 = laps_p2.get_telemetry()
    except DataNotLoadedError:
        raise ValueError("A telemetria de GPS não está disponível para o intervalo de voltas selecionado.")

    if len(tel1) == 0 or len(tel2) == 0:
        raise ValueError("A telemetria do traçado para estas voltas está vazia.")

    # 6. Reamostragem para animação fluida
    time_orig1 = np.linspace(0, 1, len(tel1))
    time_orig2 = np.linspace(0, 1, len(tel2))
    target_time = np.linspace(0, 1, total_frames)

    x1_interp = np.interp(target_time, time_orig1, tel1['X'])
    y1_interp = np.interp(target_time, time_orig1, tel1['Y'])

    x2_interp = np.interp(target_time, time_orig2, tel2['X'])
    y2_interp = np.interp(target_time, time_orig2, tel2['Y'])

    # 7. Renderização da Figura 9:16 (Vertical TikTok)
    fig, ax = plt.subplots(figsize=(9, 16), facecolor='#0e0e10')
    ax.set_facecolor('#0e0e10')
    ax.axis('off')

    # Desenho do traçado
    ax.plot(tel1['Y'], tel1['X'], color='#33333e', linewidth=3)

    # Posição dos carros
    p1, = ax.plot([], [], 'o', color='#1E41FF', markersize=14, label=p1_code)
    p2, = ax.plot([], [], 'o', color='#FF8000', markersize=14, label=p2_code)

    # Legendas
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


# --- Interface Web Streamlit ---
st.set_page_config(page_title="Gerador F1 TikTok", layout="centered")

st.title("🏎️ Gerador de Duelos F1 - TikTok")
st.write("Escolha a temporada, selecione o circuito no menu e configure a animação.")

st.sidebar.header("⚙️ Configurações da Corrida")

# 1. Seleção do Ano
ano = st.sidebar.number_input("Ano da Temporada", min_value=2018, max_value=2026, value=2024)

# 2. Carregamento dinâmico de todos os circuitos do ano
lista_gps = carregar_calendario(ano)

if lista_gps:
    opcoes_labels = [item['label'] for item in lista_gps]
    gp_selecionado_label = st.sidebar.selectbox("Selecione o Grande Prêmio / Circuito", opcoes_labels)
    
    # Obtém o número e nome oficial do GP selecionado
    gp_info = next(item for item in lista_gps if item['label'] == gp_selecionado_label)
    round_number = gp_info['round']
    gp_nome = gp_info['name']
else:
    st.sidebar.error("Não foi possível carregar a lista de circuitos para este ano.")
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

# Botão principal
if st.button("🚀 Gerar Vídeo Personalizado", type="primary"):
    try:
        with st.spinner(f"A descarregar telemetria e a gerar o vídeo de {p1_code} vs {p2_code}..."):
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
