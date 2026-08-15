import os
import imageio_ffmpeg
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
import streamlit as st

# Configura o FFmpeg integrado
plt.rcParams['animation.ffmpeg_path'] = imageio_ffmpeg.get_ffmpeg_exe()


# --- GERADOR GEOMÉTRICO OFFLINE DE CIRCUITOS REAIS ---

def gerar_pista_offline(nome_circuito, n_points=1000):
    """Gera o formato característico das pistas sem precisar da API da F1."""
    t = np.linspace(0, 2 * np.pi, n_points)
    
    if nome_circuito == "Sao Paulo (Interlagos)":
        # Formato anti-horário com o 'S do Senna' e Reta dos Boxes
        x = 100 * np.cos(t) + 30 * np.cos(2*t)
        y = 60 * np.sin(t) + 20 * np.sin(3*t)
    elif nome_circuito == "Monaco":
        # Circuito travado, com a curva da Loews e o Túnel
        x = 80 * np.cos(t) + 40 * np.cos(3*t)
        y = 50 * np.sin(2*t) + 15 * np.cos(4*t)
    elif nome_circuito == "Monza":
        # Templo da Velocidade: retas longas e chicanes
        x = 120 * np.cos(t) + 10 * np.cos(5*t)
        y = 35 * np.sin(t)
    elif nome_circuito == "Spa-Francorchamps":
        # Traçado longo com o 'Eau Rouge' e a reta Kemmel
        x = 110 * np.cos(t) + 25 * np.sin(2*t)
        y = 70 * np.sin(t) + 30 * np.cos(3*t)
    elif nome_circuito == "Silverstone":
        # Curvas rápidas integradas (Maggotts e Becketts)
        x = 90 * np.cos(t) + 35 * np.cos(2*t)
        y = 65 * np.sin(t) + 25 * np.sin(3*t)
    else:
        # Oval genérico para testes
        x = 100 * np.cos(t)
        y = 50 * np.sin(t)
        
    return x, y


# --- FUNÇÃO DE ANIMAÇÃO DA CORRIDA ---

def gerar_video_duelo(gp_nome, p1_name, p2_name, ultrapassagem, duracao_segundos=30, fps=30):
    total_frames = duracao_segundos * fps
    x_track, y_track = gerar_pista_offline(gp_nome)
    num_pts = len(x_track)

    # Lógica de simulação de ultrapassagem
    if ultrapassagem:
        # P1 começa atrás e ultrapassa no meio do vídeo
        pos_p1 = np.linspace(0, num_pts * 1.05, total_frames) % num_pts
        pos_p2 = np.linspace(15, num_pts * 0.98, total_frames) % num_pts
    else:
        # Disputa lado a lado constante
        pos_p1 = np.linspace(0, num_pts * 1.02, total_frames) % num_pts
        pos_p2 = np.linspace(5, num_pts * 1.00, total_frames) % num_pts

    # Configuração da figura 9:16 (Vertical TikTok)
    fig, ax = plt.subplots(figsize=(9, 16), facecolor='#0e0e10')
    ax.set_facecolor('#0e0e10')
    ax.axis('off')

    # Desenho da Pista
    ax.plot(x_track, y_track, color='#33333e', linewidth=5)

    # Marcadores dos Carros
    p1_line, = ax.plot([], [], 'o', color='#1E41FF', markersize=16, label=p1_name) # Azul
    p2_line, = ax.plot([], [], 'o', color='#FF8000', markersize=16, label=p2_name) # Laranja

    # Textos da Interface
    ax.text(0.5, 0.95, f"{p1_name} vs {p2_name}", transform=ax.transAxes,
            color='white', fontsize=24, fontweight='bold', ha='center')
    ax.text(0.5, 0.92, f"GP de {gp_nome}", transform=ax.transAxes,
            color='#aaaaaa', fontsize=16, ha='center')

    timer_text = ax.text(0.5, 0.88, '', transform=ax.transAxes, 
                         color='white', fontsize=14, fontweight='bold', ha='center')

    def update(frame):
        idx1 = int(pos_p1[frame])
        idx2 = int(pos_p2[frame])

        p1_line.set_data([x_track[idx1]], [y_track[idx1]])
        p2_line.set_data([x_track[idx2]], [y_track[idx2]])

        tempo_decorrido = int(frame / fps)
        timer_text.set_text(f"Tempo: {tempo_decorrido}s / {duracao_segundos}s")
        return p1_line, p2_line, timer_text

    anim = FuncAnimation(fig, update, frames=total_frames, interval=1000/fps, blit=True)

    nome_arquivo = f"duelo_{p1_name}_vs_{p2_name}.mp4"
    anim.save(nome_arquivo, writer='ffmpeg', fps=fps)
    plt.close(fig)

    return nome_arquivo


# --- INTERFACE STREAMLIT ---

st.set_page_config(page_title="Gerador de Duelos F1", layout="centered")

st.title("🏎️ Gerador de Duelos F1 - TikTok")
st.write("Crie simulações de corridas em vídeo vertical instantaneamente sem erros de conexão!")

st.sidebar.header("⚙️ Configurações da Pista")

circuitos = [
    "Sao Paulo (Interlagos)",
    "Monaco",
    "Monza",
    "Spa-Francorchamps",
    "Silverstone"
]
gp_selecionado = st.sidebar.selectbox("Selecione o Circuito", circuitos)

st.sidebar.header("🏁 Pilotos")
pilotos_lista = ["VER", "NOR", "HAM", "LEC", "SAI", "PIA", "RUS", "ALO", "SENNA", "SCHUMACHER"]

col1, col2 = st.sidebar.columns(2)
with col1:
    p1 = st.selectbox("Piloto 1", pilotos_lista, index=0)
with col2:
    p2 = st.selectbox("Piloto 2", pilotos_lista, index=1)

st.sidebar.header("🎬 Opções do Vídeo")
ultrapassagem = st.sidebar.checkbox("Simular Ultrapassagem no Vídeo", value=True)
duracao = st.sidebar.slider("Duração (segundos)", min_value=15, max_value=60, value=30, step=15)

if st.button("🚀 Gerar Vídeo do Duelo", type="primary"):
    try:
        with st.spinner("A renderizar a animação do duelo..."):
            arquivo_video = gerar_video_duelo(
                gp_nome=gp_selecionado,
                p1_name=p1,
                p2_name=p2,
                ultrapassagem=ultrapassagem,
                duracao_segundos=duracao,
                fps=30
            )

            st.success("✅ Vídeo gerado com sucesso!")
            st.video(arquivo_video)

            with open(arquivo_video, "rb") as file:
                st.download_button(
                    label="📥 Baixar Vídeo MP4",
                    data=file,
                    file_name=arquivo_video,
                    mime="video/mp4"
                )
    except Exception as e:
        st.error(f"❌ Ocorreu um erro: {e}")
