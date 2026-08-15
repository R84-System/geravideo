import os
import imageio_ffmpeg
import matplotlib
matplotlib.use('Agg') # Evita erros de interface no servidor
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
import fastf1
import streamlit as st

# Configura o FFmpeg integrado para garantir a geração do MP4 no Streamlit Cloud
plt.rcParams['animation.ffmpeg_path'] = imageio_ffmpeg.get_ffmpeg_exe()

# 1. Cria a pasta de cache se não existir (Resolve o erro NotADirectoryError)
os.makedirs('cache_f1', exist_ok=True)
fastf1.Cache.enable_cache('cache_f1')

# 2. Função que baixa a telemetria e cria a animação
def gerar_video_longo(duracao_segundos=90, fps=30):
    total_frames = duracao_segundos * fps

    # Carrega dados da sessão (GP de Interlagos 2024, Corrida)
    session = fastf1.get_session(2024, 'Interlagos', 'R')
    session.load(telemetry=True)

    # Filtra as voltas 50 a 53 dos pilotos
    laps_p1 = session.laps.pick_driver('VER')
    laps_p1 = laps_p1[(laps_p1['LapNumber'] >= 50) & (laps_p1['LapNumber'] <= 53)]

    laps_p2 = session.laps.pick_driver('NOR')
    laps_p2 = laps_p2[(laps_p2['LapNumber'] >= 50) & (laps_p2['LapNumber'] <= 53)]

    tel1 = laps_p1.get_telemetry()
    tel2 = laps_p2.get_telemetry()

    # Reamostragem para a quantidade exata de frames desejada
    time_orig1 = np.linspace(0, 1, len(tel1))
    time_orig2 = np.linspace(0, 1, len(tel2))
    target_time = np.linspace(0, 1, total_frames)

    x1_interp = np.interp(target_time, time_orig1, tel1['X'])
    y1_interp = np.interp(target_time, time_orig1, tel1['Y'])

    x2_interp = np.interp(target_time, time_orig2, tel2['X'])
    y2_interp = np.interp(target_time, time_orig2, tel2['Y'])

    # Desenho da animação no formato 9:16 (TikTok)
    fig, ax = plt.subplots(figsize=(9, 16), facecolor='#0e0e10')
    ax.set_facecolor('#0e0e10')
    ax.axis('off')

    ax.plot(tel1['Y'], tel1['X'], color='#33333e', linewidth=3)

    p1, = ax.plot([], [], 'o', color='#1E41FF', markersize=12, label='VER')
    p2, = ax.plot([], [], 'o', color='#FF8000', markersize=12, label='NOR')

    timer_text = ax.text(0.5, 0.93, '', transform=ax.transAxes, color='white', 
                         fontsize=18, fontweight='bold', ha='center')

    def update(frame):
        p1.set_data([y1_interp[frame]], [x1_interp[frame]])
        p2.set_data([y2_interp[frame]], [x2_interp[frame]])

        tempo_decorrido = (frame / fps)
        timer_text.set_text(f"Tempo de Animação: {int(tempo_decorrido)}s / {duracao_segundos}s")
        return p1, p2, timer_text

    anim = FuncAnimation(fig, update, frames=total_frames, interval=1000/fps, blit=True)

    nome_arquivo = 'f1_batalha_interlagos.mp4'
    anim.save(nome_arquivo, writer='ffmpeg', fps=fps)
    plt.close(fig) # Libera memória

    return nome_arquivo


# 3. Interface Web do Streamlit
st.set_page_config(page_title="F1 TikTok Generator", layout="centered")

st.title("🏎️ Gerador de Vídeo F1 - TikTok")
st.write("Gere simulações táticas de 1m30s prontas para publicação.")

if st.button("🚀 Gerar Vídeo de Interlagos (90s)", type="primary"):
    with st.spinner("Buscando dados no FastF1 e renderizando o MP4... Pode levar cerca de 1 a 2 minutos."):
        nome_video = gerar_video_longo(duracao_segundos=90, fps=30)

        st.success("✅ Vídeo gerado com sucesso!")
        st.video(nome_video)

        with open(nome_video, "rb") as file:
            st.download_button(
                label="📥 Baixar MP4 (Vertical 9:16)",
                data=file,
                file_name=nome_video,
                mime="video/mp4"
            )
