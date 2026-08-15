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


def obter_trajeto_normalizado(nome_pista, n_points=500):
    """Gera o trajeto de pontos (0 a 1) para o carro percorrer sobre a imagem."""
    t = np.linspace(0, 2 * np.pi, n_points)
    
    if "INTERLAGOS" in nome_pista.upper():
        # Curvas características de Interlagos (S do Senna, Pinheirinho, Junção)
        x = 0.5 + 0.35 * np.cos(t) + 0.08 * np.sin(2*t)
        y = 0.5 + 0.28 * np.sin(t) - 0.12 * np.cos(3*t)
    else: # MONZA por padrão
        # Retas longas e chicanes
        x = 0.5 + 0.38 * np.cos(t) + 0.12 * np.cos(3*t)
        y = 0.5 + 0.22 * np.sin(t) + 0.05 * np.sin(2*t)
        
    return x, y


def gerar_video_hd(pista_nome, p1_code, p2_code, duracao_segundos=30, fps=30):
    total_frames = duracao_segundos * fps

    # Caminhos das imagens baseados nas suas pastas
    pista_path = f"assets/tracks/{pista_nome}.jpg"
    car1_path = f"assets/cars/{p1_code}.png"
    car2_path = f"assets/cars/{p2_code}.png"

    if not os.path.exists(pista_path):
        raise FileNotFoundError(f"Imagem da pista não encontrada em: {pista_path}")
    if not os.path.exists(car1_path):
        raise FileNotFoundError(f"Imagem do carro não encontrada em: {car1_path}")
    if not os.path.exists(car2_path):
        raise FileNotFoundError(f"Imagem do carro não encontrada em: {car2_path}")

    # Carregar imagem do circuito
    pista_img = Image.open(pista_path)
    largura, altura = pista_img.size

    # Obter o trajeto e converter para os pixels da imagem
    norm_x, norm_y = obter_trajeto_normalizado(pista_nome)
    x_track = norm_x * largura
    y_track = norm_y * altura
    num_pts = len(x_track)

    # Posições simuladas dos carros
    pos_p1 = np.linspace(0, num_pts * 1.05, total_frames) % num_pts
    pos_p2 = np.linspace(5, num_pts * 1.05, total_frames) % num_pts

    # Carregar carros
    car1_raw = Image.open(car1_path).convert("RGBA")
    car2_raw = Image.open(car2_path).convert("RGBA")

    # Configuração da Figura Vertical 9:16 (TikTok)
    fig, ax = plt.subplots(figsize=(6, 10.6), facecolor='#0e0e10')
    ax.set_facecolor('#0e0e10')
    ax.imshow(pista_img, extent=[0, largura, 0, altura])
    ax.axis('off')

    # Título do vídeo
    ax.text(largura / 2, altura * 0.95, f"{p1_code} vs {p2_code}", 
            color='white', fontsize=22, fontweight='bold', ha='center')
    ax.text(largura / 2, altura * 0.92, f"GP DE {pista_nome}", 
            color='#aaaaaa', fontsize=14, ha='center')

    box_p1 = [None]
    box_p2 = [None]

    def update(frame):
        if box_p1[0]: box_p1[0].remove()
        if box_p2[0]: box_p2[0].remove()

        idx1 = int(pos_p1[frame])
        idx2 = int(pos_p2[frame])

        x1, y1 = x_track[idx1], y_track[idx1]
        x2, y2 = x_track[idx2], y_track[idx2]

        # Rotação do carro para apontar na direção da curva
        idx1_next = (idx1 + 1) % num_pts
        angle1 = np.degrees(np.arctan2(y_track[idx1_next] - y1, x_track[idx1_next] - x1))

        idx2_next = (idx2 + 1) % num_pts
        angle2 = np.degrees(np.arctan2(y_track[idx2_next] - y2, x_track[idx2_next] - x2))

        # Rodar o sprite do carro
        car1_rot = car1_raw.rotate(angle1 - 90, expand=True)
        car2_rot = car2_raw.rotate(angle2 - 90, expand=True)

        # Adicionar à imagem
        im_box1 = OffsetImage(car1_rot, zoom=0.06)
        box_p1[0] = AnnotationBbox(im_box1, (x1, y1), frameon=False)
        ax.add_artist(box_p1[0])

        im_box2 = OffsetImage(car2_rot, zoom=0.06)
        box_p2[0] = AnnotationBbox(im_box2, (x2, y2), frameon=False)
        ax.add_artist(box_p2[0])

        return box_p1[0], box_p2[0]

    anim = FuncAnimation(fig, update, frames=total_frames, interval=1000/fps, blit=False)
    nome_arquivo = f"duelo_{p1_code}_vs_{p2_code}.mp4"
    anim.save(nome_arquivo, writer='ffmpeg', fps=fps)
    plt.close(fig)

    return nome_arquivo


# --- INTERFACE STREAMLIT ---

st.set_page_config(page_title="Gerador F1 HD", layout="centered")

st.title("🏎️ Gerador de Duelos F1 - HD")
st.write("Crie simulações com os carros e circuitos oficiais!")

st.sidebar.header("⚙️ Opções do Duelo")

pistas_disponiveis = ["MONZA", "INTERLAGOS"]
gp_selecionado = st.sidebar.selectbox("Selecione o Circuito", pistas_disponiveis)

pilotos_disponiveis = ["VER", "HAM", "ANT"]
col1, col2 = st.sidebar.columns(2)
with col1:
    p1 = st.selectbox("Piloto 1", pilotos_disponiveis, index=0)
with col2:
    p2 = st.selectbox("Piloto 2", pilotos_disponiveis, index=1)

duracao = st.sidebar.slider("Duração do Vídeo (segundos)", min_value=15, max_value=60, value=30, step=15)

if st.button("🚀 Gerar Vídeo HD", type="primary"):
    try:
        with st.spinner("A renderizar animação HD com os carros na pista..."):
            arquivo_video = gerar_video_hd(
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
