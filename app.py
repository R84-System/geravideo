import os
import imageio_ffmpeg
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
import fastf1
import streamlit as st

# Configura o FFmpeg integrado
plt.rcParams['animation.ffmpeg_path'] = imageio_ffmpeg.get_ffmpeg_exe()

# Cache local do FastF1
os.makedirs('cache_f1', exist_ok=True)
fastf1.Cache.enable_cache('cache_f1')


def gerar_video_customizado(ano, gp, tipo_sessao, p1_code, p2_code, volta_inicio, volta_fim, duracao_segundos, fps=30):
    total_frames = duracao_segundos * fps

    # Tenta obter a sessão
    try:
        session = fastf1.get_session(ano, gp, tipo_sessao)
        session.load(laps=True, telemetry=True, weather=False)
    except Exception as e:
        raise ValueError(f"Não foi possível descarregar os dados do GP '{gp}' ({ano}). Verifique se o nome do GP está correto (ex: 'Sao Paulo', 'Monaco', 'Silverstone').")

    if not hasattr(session, 'laps') or session.laps is None or len(session.laps) == 0:
        raise ValueError("A sessão foi encontrada, mas não existem dados de voltas disponíveis para esta etapa.")

    # Filtra os pilotos
    laps_p1 = session.laps.pick_driver(p1_code)
    laps_p2 = session.laps.pick_driver(p2_code)

    if len(laps_p1) == 0:
        pilotos_disponiveis = ", ".join(sorted(session.laps['Driver'].unique()))
        raise ValueError(f"O piloto '{p1_code}' não foi encontrado nesta sessão. Pilotos disponíveis: {pilotos_disponiveis}")

    if len(laps_p2) == 0:
        pilotos_disponiveis = ", ".join(sorted(session.laps['Driver'].unique()))
        raise ValueError(f"O piloto '{p2_code}' não foi encontrado nesta sessão. Pilotos disponíveis: {pilotos_disponiveis}")

    # Filtra o intervalo de voltas
    laps_p1 = laps_p1[(laps_p1['LapNumber'] >= volta_inicio) & (laps_p1['LapNumber'] <= volta_fim)]
    laps_p2 = laps_p2[(laps_p2['LapNumber'] >= volta_inicio) & (laps_p2['LapNumber'] <= volta_fim)]

    if len(laps_p1) == 0 or len(laps_p2) == 0:
        max_volta = int(session.laps['LapNumber'].max())
        raise ValueError(f"Sem dados para o intervalo de voltas {volta_inicio} a {volta_fim}. O número máximo de voltas registado nesta sessão foi {max_volta}.")

    tel1 = laps_p1.get_telemetry()
    tel2 = laps_p2.get_telemetry()

    if len(tel1) == 0 or len(tel2) == 0:
        raise ValueError("Não foi possível extrair a telemetria das voltas selecionadas.")

    # Reamostragem para animação
    time_orig1 = np.linspace(0, 1, len(tel1))
    time_orig2 = np.linspace(0, 1, len(tel2))
    target_time = np.linspace(0, 1, total_frames)

    x1_interp = np.interp(target_time, time_orig1, tel1['X'])
    y1_interp = np.interp(target_time, time_orig1, tel1['Y'])

    x2_interp = np.interp(target_time, time_orig2, tel2['X'])
    y2_interp = np.interp(target_time, time_orig2, tel2['Y'])

    # Figura 9:16 (Vertical)
    fig, ax = plt.subplots(figsize=(9, 16), facecolor='#0e0e10')
    ax.set_facecolor('#0e0e10')
    ax.axis('off')

    # Traçado
    ax.plot(tel1['Y'], tel1['X'], color='#33333e', linewidth=3)

    # Carros
    p1, = ax.plot([], [], 'o', color='#1E41FF', markersize=14, label=p1_code)
    p2, = ax.plot([], [], 'o', color='#FF8000', markersize=14, label=p2_code)

    # Textos
    ax.text(0.5, 0.96, f"{p1_code} vs {p2_code}", transform=ax.transAxes,
            color='white', fontsize=22, fontweight='bold', ha='center')
    ax.text(0.5, 0.93, f"{gp} {ano}", transform=ax.transAxes,
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

    nome_arquivo = f"f1_{p1_code}_vs_{p2_code}_{gp}.mp4"
    anim.save(nome_arquivo, writer='ffmpeg', fps=fps)
    plt.close(fig)

    return nome_arquivo


# Interface Web (Streamlit)
st.set_page_config(page_title="Gerador F1 TikTok", layout="centered")

st.title("🏎️ Gerador de Duelos F1 - TikTok")
st.write("Escolha a corrida, os pilotos e o intervalo de voltas para criar o vídeo vertical.")

st.sidebar.header("⚙️ Configurações da Corrida")

ano = st.sidebar.number_input("Ano da Temporada", min_value=2018, max_value=2026, value=2024)
gp = st.sidebar.text_input("Nome da Pista / GP", value="Sao Paulo", help="Ex: Sao Paulo, Monaco, Silverstone, Monza, Spa")
tipo_sessao = st.sidebar.selectbox("Tipo de Sessão", ["R", "Q", "FP1", "FP2", "FP3"], index=0, help="R = Corrida, Q = Qualificação")

st.sidebar.header("🏁 Pilotos e Voltas")
col1, col2 = st.sidebar.columns(2)
with col1:
    p1_code = st.text_input("Piloto 1 (3 letras)", value="VER").upper()
with col2:
    p2_code = st.text_input("Piloto 2 (3 letras)", value="NOR").upper()

col3, col4 = st.sidebar.columns(2)
with col3:
    volta_inicio = st.number_input("Volta Inicial", min_value=1, value=50)
with col4:
    volta_fim = st.number_input("Volta Final", min_value=1, value=53)

duracao_segundos = st.sidebar.slider("Duração do Vídeo (segundos)", min_value=15, max_value=120, value=60, step=15)

if st.button("🚀 Gerar Vídeo Personalizado", type="primary"):
    try:
        with st.spinner(f"A carregar a telemetria e a gerar o vídeo de {p1_code} vs {p2_code}..."):
            nome_video = gerar_video_customizado(
                ano=ano,
                gp=gp,
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
