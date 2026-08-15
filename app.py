import os
import imageio_ffmpeg
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image
import numpy as np
import streamlit as st
import fastf1

# Configura o FFmpeg integrado para salvar o vídeo corretamente
plt.rcParams['animation.ffmpeg_path'] = imageio_ffmpeg.get_ffmpeg_exe()

@st.cache_data
def carregar_telemetria_f1(ano, gp, p1_code, p2_code):
    """Baixa e processa os dados reais de telemetria da F1 usando FastF1 com carregamento completo."""
    session = fastf1.get_session(ano, gp, 'R')
    # O carregamento precisa incluir telemetry=True e laps=True para evitar erros
    session.load(telemetry=True, laps=True, weather=False, messages=False)
    
    # Pega a volta mais rápida de cada piloto para simular o traçado e posições
    lap_p1 = session.laps.pick_driver(p1_code).pick_fastest()
    lap_p2 = session.laps.pick_driver(p2_code).pick_fastest()
    
    tel_p1 = lap_p1.get_telemetry()
    tel_p2 = lap_p2.get_telemetry()
    
    return tel_p1, tel_p2

def gerar_video_telemetria(p1_code, p2_code, ano=2023, gp='Monza', duracao_segundos=25, fps=30):
    total_frames = duracao_segundos * fps

    car1_path = f"assets/cars/{p1_code}.png"
    car2_path = f"assets/cars/{p2_code}.png"

    if not os.path.exists(car1_path) or not os.path.exists(car2_path):
        raise FileNotFoundError("Coloque as imagens dos carros na pasta assets/cars/ (ex: VER.png, HAM.png)")

    # Puxa os dados reais da pista
    tel1, tel2 = carregar_telemetria_f1(ano, gp, p1_code, p2_code)
    
    x1, y1 = tel1['X'].values, tel1['Y'].values
    x2, y2 = tel2['X'].values, tel2['Y'].values

    # Normalizar as coordenadas para a tela vertical (9:16)
    all_x = np.concatenate([x1, x2])
    all_y = np.concatenate([y1, y2])
    
    min_x, max_x = np.min(all_x), np.max(all_x)
    min_y, max_y = np.min(all_y), np.max(all_y)

    def map_coords(x, y):
        nx = (x - min_x) / (max_x - min_x + 1e-5)
        ny = (y - min_y) / (max_y - min_y + 1e-5)
        # Centraliza no formato vertical 9:16
        px = nx * 400 + 100
        py = (1 - ny) * 600 + 250
        return px, py

    px1, py1 = map_coords(x1, y1)
    px2, py2 = map_coords(x2, y2)

    n_pts = len(px1)
    indices = np.linspace(0, n_pts - 1, total_frames).astype(int)

    car1_raw = Image.open(car1_path).convert("RGBA")
    car2_raw = Image.open(car2_path).convert("RGBA")

    # Configuração da tela vertical 9:16
    fig, ax = plt.subplots(figsize=(6, 10.6), facecolor='#0b0b0e')
    ax.set_facecolor('#0b0b0e')
    ax.set_xlim(0, 600)
    ax.set_ylim(0, 1060)
    ax.axis('off')

    # Desenha o traçado oficial da pista baseado na telemetria
    ax.plot(px1, py1, color='#1f242d', linewidth=28, solid_capstyle='round', zorder=1)
    ax.plot(px1, py1, color='#ffffff', linewidth=5, alpha=0.95, zorder=2)

    # Títulos do Vídeo
    ax.text(300, 970, f"{p1_code} vs {p2_code}", color='white', fontsize=22, fontweight='bold', ha='center', fontfamily='sans-serif')
    ax.text(300, 930, f"GP DE MONZA • TELEMETRIA REAL", color='#e10600', fontsize=13, fontweight='bold', ha='center', fontfamily='sans-serif')

    box_p1 = [None]
    box_p2 = [None]

    def update(frame):
        if box_p1[0]: box_p1[0].remove()
        if box_p2[0]: box_p2[0].remove()

        idx = indices[frame]
        
        cx1, cy1 = px1[idx], py1[idx]
        cx2, cy2 = px2[idx], py2[idx]

        # Ângulo de rotação do carro acompanhando a direção da pista
        next_idx = min(idx + 2, n_pts - 1)
        angle1 = np.degrees(np.arctan2(py1[next_idx] - cy1, px1[next_idx] - cx1))
        angle2 = np.degrees(np.arctan2(py2[next_idx] - cy2, px2[next_idx] - cx2))

        c1_rot = car1_raw.rotate(angle1 - 90, expand=True)
        c2_rot = car2_raw.rotate(angle2 - 90, expand=True)

        box_p1[0] = AnnotationBbox(OffsetImage(c1_rot, zoom=0.06), (cx1, cy1), frameon=False, zorder=3)
        box_p2[0] = AnnotationBbox(OffsetImage(c2_rot, zoom=0.06), (cx2, cy2), frameon=False, zorder=3)
        
        ax.add_artist(box_p1[0])
        ax.add_artist(box_p2[0])

        return box_p1[0], box_p2[0]

    anim = FuncAnimation(fig, update, frames=total_frames, interval=1000/fps, blit=False)
    nome_arquivo = f"duelo_real_{p1_code}_vs_{p2_code}.mp4"
    anim.save(nome_arquivo, writer='ffmpeg', fps=fps)
    plt.close(fig)

    return nome_arquivo


# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="F1 Race Replay - Duelos", layout="centered")

st.title("🏎️ Duelos F1 - Telemetria Real")
st.write("Simulação oficial usando os dados exatos da F1!")

st.sidebar.header("⚙️ Configurações")
p1 = st.sidebar.selectbox("Piloto 1", ["VER", "HAM", "LEC", "NOR"], index=0)
p2 = st.sidebar.selectbox("Piloto 2", ["HAM", "VER", "LEC", "NOR"], index=1)
duracao = st.sidebar.slider("Duração (segundos)", 15, 40, 20)

if st.button("🚀 Gerar Vídeo com Dados Reais", type="primary"):
    try:
        with st.spinner("Baixando dados oficiais da F1 e renderizando o vídeo..."):
            arquivo_video = gerar_video_telemetria(p1, p2, ano=2023, gp='Monza', duracao_segundos=duracao)
            st.success("✅ Vídeo gerado com sucesso!")
            st.video(arquivo_video)

            with open(arquivo_video, "rb") as file:
                st.download_button("📥 Baixar MP4", data=file, file_name=arquivo_video, mime="video/mp4")
    except Exception as e:
        st.error(f"❌ Erro ao processar: {e}")
