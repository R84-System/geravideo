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

# Configura o FFmpeg integrado
plt.rcParams['animation.ffmpeg_path'] = imageio_ffmpeg.get_ffmpeg_exe()


def obter_trajeto_satelite_monza(largura, altura, n_points=1200):
    """Gera pontos matemáticos calibrados para encaixar perfeitamente 
    sobre a imagem de satélite horizontal de Monza."""
    t = np.linspace(0, 2 * np.pi, n_points)
    
    # Coordenadas paramétricas ajustadas para o layout horizontal da foto de satélite
    nx = 0.50 + 0.33 * np.cos(t) - 0.05 * np.sin(2*t)
    ny = 0.50 + 0.28 * np.sin(t) + 0.06 * np.cos(3*t)
    
    # Escalando para o tamanho exato da imagem carregada
    x_track = nx * (largura * 0.68) + (largura * 0.16)
    y_track = ny * (altura * 0.52) + (altura * 0.24)
    
    return x_track, y_track


def gerar_video_satelite(pista_nome, p1_code, p2_code, duracao_segundos=30, fps=30):
    total_frames = duracao_segundos * fps

    # Tenta carregar a imagem de satélite (suporta .png ou .jpg)
    pista_path = f"assets/tracks/{pista_nome}.png"
    if not os.path.exists(pista_path):
        pista_path = f"assets/tracks/{pista_nome}.jpg"

    car1_path = f"assets/cars/{p1_code}.png"
    car2_path = f"assets/cars/{p2_code}.png"

    if not os.path.exists(pista_path):
        raise FileNotFoundError(f"Coloque a imagem de satélite em: assets/tracks/{pista_nome}.png (ou .jpg)")
    if not os.path.exists(car1_path):
        raise FileNotFoundError(f"Imagem do carro não encontrada em: {car1_path}")
    if not os.path.exists(car2_path):
        raise FileNotFoundError(f"Imagem do carro não encontrada em: {car2_path}")

    # Carregar imagem de fundo de satélite
    pista_img = Image.open(pista_path)
    largura, altura = pista_img.size

    # Obter o trajeto mapeado para a imagem
    x_track, y_track = obter_trajeto_satelite_monza(largura, altura)
    num_pts = len(x_track)

    # Posições dos dois carros na pista
    pos_p1 = np.linspace(0, num_pts * 2.0, total_frames) % num_pts
    pos_p2 = np.linspace(40, num_pts * 2.0 + 40, total_frames) % num_pts

    # Carregar carros em RGBA
    car1_raw = Image.open(car1_path).convert("RGBA")
    car2_raw = Image.open(car2_path).convert("RGBA")

    # Configuração da Figura Vertical 9:16 (TikTok/Shorts)
    fig, ax = plt.subplots(figsize=(6, 10.6), facecolor='#0b0b0e')
    ax.set_facecolor('#0b0b0e')
    
    # Limites da imagem (Invertendo o Y para o padrão de pixels da imagem)
    ax.set_xlim(0, largura)
    ax.set_ylim(altura, 0)
    ax.axis('off')

    # Exibe a foto de satélite de fundo
    ax.imshow(pista_img, extent=[0, largura, altura, 0])

    # Títulos no topo do vídeo
    ax.text(largura / 2, altura * 0.10, f"{p1_code} vs {p2_code}", 
            color='white', fontsize=22, fontweight='bold', ha='center', fontfamily='sans-serif')
    ax.text(largura / 2, altura * 0.16, f"GP DE {pista_nome.upper()} • SATELLITE BATTLE", 
            color='#e10600', fontsize=13, fontweight='bold', ha='center', fontfamily='sans-serif')

    box_p1 = [None]
    box_p2 = [None]

    def update(frame):
        if box_p1[0]: box_p1[0].remove()
        if box_p2[0]: box_p2[0].remove()

        idx1 = int(pos_p1[frame])
        idx2 = int(pos_p2[frame])

        x1, y1 = x_track[idx1], y_track[idx1]
        x2, y2 = x_track[idx2], y_track[idx2]

        # Calcular a direção do carro na curva
        idx1_next = (idx1 + 3) % num_pts
        angle1 = np.degrees(np.arctan2(y_track[idx1_next] - y1, x_track[idx1_next] - x1))

        idx2_next = (idx2 + 3) % num_pts
        angle2 = np.degrees(np.arctan2(y_track[idx2_next] - y2, x_track[idx2_next] - x2))

        # Rotacionar os carros de acordo com a imagem
        car1_rot = car1_raw.rotate(-angle1, expand=True)
        car2_rot = car2_raw.rotate(-angle2, expand=True)

        # Zoom ajustado para os carros ficarem perfeitos na imagem de satélite
        im_box1 = OffsetImage(car1_rot, zoom=0.06)
        box_p1[0] = AnnotationBbox(im_box1, (x1, y1), frameon=False, zorder=3)
        ax.add_artist(box_p1[0])

        im_box2 = OffsetImage(car2_rot, zoom=0.06)
        box_p2[0] = AnnotationBbox(im_box2, (x2, y2), frameon=False, zorder=3)
        ax.add_artist(box_p2[0])

        return box_p1[0], box_p2[0]

    anim = FuncAnimation(fig, update, frames=total_frames, interval=1000/fps, blit=False)
    nome_arquivo = f"duelo_satelite_{p1_code}_vs_{p2_code}.mp4"
    anim.save(nome_arquivo, writer='ffmpeg', fps=fps)
    plt.close(fig)

    return nome_arquivo


# --- INTERFACE STREAMLIT ---

st.set_page_config(page_title="Gerador F1 Satélite", layout="centered")

st.title("🏎️ Duelos F1 - Modo Satélite HD")
st.write("Simulação oficial usando a imagem de satélite real da pista!")

st.sidebar.header("⚙️ Configurações do Vídeo")

pistas_disponiveis = ["MONZA"]
gp_selecionado = st.sidebar.selectbox("Escolha o Circuito", pistas_disponiveis)

pilotos_disponiveis = ["VER", "HAM", "ANT"]
col1, col2 = st.sidebar.columns(2)
with col1:
    p1 = st.selectbox("Piloto 1", pilotos_disponiveis, index=0)
with col2:
    p2 = st.selectbox("Piloto 2", pilotos_disponiveis, index=1)

duracao = st.sidebar.slider("Duração do Vídeo (segundos)", min_value=15, max_value=60, value=20, step=5)

if st.button("🚀 Gerar Vídeo com Satélite", type="primary"):
    try:
        with st.spinner("Carregando imagem de satélite e renderizando a animação..."):
            arquivo_video = gerar_video_satelite(
                pista_nome=gp_selecionado,
                p1_code=p1,
                p2_code=p2,
                duracao_segundos=duracao
            )
            st.success("✅ Vídeo gerado com sucesso!")
            st.video(arquivo_video)

            with open(arquivo_video, "rb") as file:
                st.download_button("📥 Baixar MP4", data=file, file_name=arquivo_video, mime="video/mp4")
    except Exception as e:
        st.error(f"❌ Erro ao gerar vídeo: {e}")
