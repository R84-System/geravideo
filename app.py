import os
import imageio_ffmpeg
import matplotlib
matplotlib.use('Agg')  # Evita erros de interface no servidor
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
import fastf1
import streamlit as st

# Configura o FFmpeg integrado
plt.rcParams['animation.ffmpeg_path'] = imageio_ffmpeg.get_ffmpeg_exe()

# 1. Cria a pasta de cache se não existir
os.makedirs('cache_f1', exist_ok=True)
fastf1.Cache.enable_cache('cache_f1')


# 2. Função principal para gerar o vídeo customizado
def gerar_video_customizado(ano, gp, tipo_sessao, p1_code, p2_code, volta_inicio, volta_fim, duracao_segundos, fps=30):
    total_frames = duracao_segundos * fps

    # Carrega dados da sessão
    session = fastf1.get_session(ano, gp, tipo_sessao)
    session.load(laps=True, telemetry=True, weather=False)

    # Filtra as voltas dos pilotos escolhidos
    laps_p1 = session.laps.pick_driver(p1_code)
    laps_p1 = laps_p1[(laps_p1['LapNumber'] >= volta_inicio) & (laps_p1['LapNumber'] <= volta_fim)]

    laps_p2 = session.laps.pick_driver(p2_code)
    laps_p2 = laps_p2[(laps_p2['LapNumber'] >= volta_inicio) & (laps_p2['LapNumber'] <= volta_fim)]

    if len(laps_p1) == 0 or len(laps_p2) == 0:
        raise ValueError("Não foram encontradas voltas válidas para os pilotos nesse intervalo.")

    tel1 = laps_p1.get_telemetry()
    tel2 = laps_p2.get_telemetry()

    if len(tel1) == 0 or len(tel2) == 0:
        raise ValueError("Não há telemetria disponível para este trecho.")

    # Reamostragem de tempo
    time_orig1 = np.linspace(0, 1, len(tel1))
    time_orig2 = np.linspace(0, 1, len(tel2))
    target_time = np.linspace(0, 1, total_frames)

    x1_interp = np.interp(target_time, time_orig1, tel1['X'])
    y1_interp = np.interp(target_time, time_orig1, tel1['Y'])

    x2_interp = np.interp(target_time, time_orig2, tel2['X'])
    y2_interp = np.interp(target_time, time_orig2, tel2['Y'])

    # Configura o gráfico 9:16 (Vertical / TikTok)
    fig, ax = plt.subplots(figsize=(9, 16), facecolor='#0e0e10')
    ax.set_facecolor('#0e0e10')
    ax.axis('off')

    # Desenha o traçado da pista
    ax.plot(tel1['Y'], tel1['X'], color='#33333e', linewidth=3)

    # Pontos representando os carros
    p1, = ax.plot([], [], 'o', color='#1E41FF', markersize=14, label=p1_code)
    p2, = ax.plot([], [], 'o', color='#FF8000', markersize=14, label=p2_code)

    # Título do duelo na tela
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


# 3. Interface Web Personalizável
st.set_page_config(page_title="Gerador F1 TikTok", layout="centered")

st.title("🏎️ Gerador de Duelos F1 - TikTok")
st.write("Escolha a corrida, os pilotos e o intervalo de voltas para criar o vídeo vertical.")

st.sidebar.header("⚙️ Configurações da Corrida")

# Formulário de Entradas
ano = st.sidebar.number_input("Ano da Temporada", min_value=2018, max_value=2026, value=2024)
gp = st.sidebar.text_input("Nome da Pista / GP", value="Interlagos", help="Ex: Interlagos, Monaco, Silverstone, Monza, Spa")
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

# Botão principal
if st.button("🚀 Gerar Vídeo Personalizado", type="primary"):
    try:
        with st.spinner(f"Baixando telemetria e renderizando {p1_code} vs {p2_code}... Isso pode levar de 1 a 2 minutos."):
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
        st.error(f"❌ Ocorreu um erro ao gerar o vídeo: {e}")
