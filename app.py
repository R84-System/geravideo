import os
import imageio_ffmpeg
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
import fastf1
import streamlit as st

# Configura FFmpeg
plt.rcParams['animation.ffmpeg_path'] = imageio_ffmpeg.get_ffmpeg_exe()

# --- CACHE: Baixa o traçado da pista uma única vez ---
@st.cache_data(show_spinner=True)
def obter_trajeto_pista(ano, round_number):
    """Baixa apenas a telemetria do mapa da pista (estático)."""
    session = fastf1.get_session(ano, round_number, 'R')
    # Carrega apenas o necessário para ter o mapa (a volta mais rápida tem o traçado completo)
    session.load(laps=True, telemetry=True, weather=False, messages=False)
    lap = session.laps.pick_fastest()
    tel = lap.get_telemetry()
    return tel['X'].values, tel['Y'].values

# --- SIMULAÇÃO: Faz os carros andarem no traçado ---
def gerar_video_simulado(ano, round_number, gp_nome, p1_name, p2_name, duracao_segundos, fps=30):
    total_frames = duracao_segundos * fps
    
    # Obtém o traçado real da pista
    x_track, y_track = obter_trajeto_pista(ano, round_number)
    num_pontos_pista = len(x_track)
    
    # Lógica de Simulação: Velocidade constante com pequenas variações
    # Carro 1 é levemente mais rápido
    vel_p1 = 1.05 
    vel_p2 = 1.00
    
    # Criar posições indexadas ao longo da pista
    pos_p1 = np.linspace(0, vel_p1 * num_pontos_pista, total_frames) % num_pontos_pista
    pos_p2 = np.linspace(0, vel_p2 * num_pontos_pista, total_frames) % num_pontos_pista
    
    # Renderização
    fig, ax = plt.subplots(figsize=(9, 16), facecolor='#0e0e10')
    ax.set_facecolor('#0e0e10')
    ax.axis('off')
    
    # Desenha a pista
    ax.plot(y_track, x_track, color='#33333e', linewidth=4)
    
    # Carros
    p1, = ax.plot([], [], 'o', color='#1E41FF', markersize=16, label=p1_name)
    p2, = ax.plot([], [], 'o', color='#FF8000', markersize=16, label=p2_name)
    
    # Textos
    ax.text(0.5, 0.95, f"{p1_name} vs {p2_name}", transform=ax.transAxes, color='white', fontsize=20, ha='center')
    ax.text(0.5, 0.90, f"{gp_nome} - Simulação", transform=ax.transAxes, color='#aaaaaa', fontsize=12, ha='center')

    def update(frame):
        idx1 = int(pos_p1[frame])
        idx2 = int(pos_p2[frame])
        p1.set_data([y_track[idx1]], [x_track[idx1]])
        p2.set_data([y_track[idx2]], [x_track[idx2]])
        return p1, p2

    anim = FuncAnimation(fig, update, frames=total_frames, interval=1000/fps, blit=True)
    
    nome_arquivo = "simulacao_f1.mp4"
    anim.save(nome_arquivo, writer='ffmpeg', fps=fps)
    plt.close(fig)
    return nome_arquivo

# --- UI STREAMLIT ---
st.title("🏎️ Simulador de Duelos F1 (Traçados Reais)")

ano = st.number_input("Ano", 2024, 2025, 2024)
# (Pode adicionar aqui a lógica de selecionar GP que fizemos antes)
gp_escolhido = st.selectbox("Selecione o Circuito", ["Sao Paulo", "Monaco", "Silverstone", "Spa"])

if st.button("Gerar Duelo Simulado"):
    try:
        # Nota: Para simplificar, o round_number aqui é fixo, mas você pode usar o mapa do calendário que fizemos antes
        round_map = {"Sao Paulo": 21, "Monaco": 8, "Silverstone": 12, "Spa": 14}
        video = gerar_video_simulado(ano, round_map[gp_escolhido], gp_escolhido, "VER", "NOR", 30)
        st.video(video)
    except Exception as e:
        st.error(f"Erro na simulação: {e}")
