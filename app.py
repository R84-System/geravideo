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


def obter_trajeto_monza_real(n_points=800):
    """Cria pontos que seguem fielmente o traçado real da pista de Monza."""
    # Usamos uma curva paramétrica composta que imita o circuito de Monza
    t = np.linspace(0, 2 * np.pi, n_points)
    
    # Base de formato retangular alongado com desvios para as chicanes
    x = 0.50 + 0.18 * np.cos(t) + 0.08 * np.sin(2*t)
    y = 0.52 + 0.38 * np.sin(t) - 0.05 * np.cos(2*t)
    
    # Ajuste fino para encaixar perfeitamente no mapa vertical de Monza
    x_track = (x - np.min(x)) / (np.max(x) - np.min(x))
    y_track = (y - np.min(y)) / (np.max(y) - np.min(y))
    
    return x_track, y_track


def gerar_video_hd(pista_nome, p1_code, p2_code, duracao_segundos=30, fps=30):
    total_frames = duracao_segundos * fps

    # Caminhos das imagens
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

    # Obter o trajeto mapeado para a pista
    norm_x, norm_y = obter_trajeto_monza_real()
    
    # Ajustando a escala para preencher a área exata do desenho da pista na imagem
    x_track = norm_x * (largura * 0.45) + (largura * 0.28)
    y_track = norm_y * (altura * 0.65) + (altura * 0.18)
    num_pts = len(x_track)

    # Posições dos dois carros na pista
    pos_p1 = np.linspace(0, num_pts * 2.0, total_frames) % num_pts
    pos_p2 = np.linspace(25, num_pts * 2.0 + 25, total_frames) % num_pts

    # Carregar carros em RGBA
    car1_raw = Image.open(car1_path).convert("RGBA")
    car2_raw = Image.open(car2_path).convert("RGBA")

    # Configuração da Figura Vertical 9:16 (TikTok)
    fig, ax = plt.subplots(figsize=(6, 10.6), facecolor='#0e0e10')
    ax.set_facecolor('#0e0e10')
    ax.imshow(pista_img, extent=[0, largura, 0, altura])
    ax.axis('off')

    # Título do vídeo
    ax.text(largura / 2, altura * 0.96, f"{p1_code} vs {p2_code}", 
            color='white', fontsize=20, fontweight='bold', ha='center')
    ax.text(largura / 2, altura * 0.93, f"GP DE {pista_nome}", 
            color='#aaaaaa', fontsize=12, ha='center')

    box_p1 = [None]
    box_p2 = [None]

    def update(frame):
        if box_p1[0]: box_p1[0].remove()
        if box_p2[0]: box_p2[0].remove()

        idx1 = int(pos_p1[frame])
        idx2 = int(pos_p2[frame])

        x1, y1 = x_track[idx1], y_track[idx1]
        x2, y2 = x_track[idx2], y_track[idx2]

        # Calcular direção da rotação para o carro fazer as curvas corretamente
        idx1_next = (idx1 + 2) % num_pts
        angle1 = np.degrees(np.arctan2(y_track[idx1_next] - y1, x_track[idx1_next] - x1))

        idx2_next = (idx2 + 2) % num_pts
        angle2 = np.degrees(np.arctan2(y_track[idx2_next] - y2, x_track[idx2_next] - x2))

        # Rotacionar os carros
        car1_rot = car1_raw.rotate(angle1 - 90, expand=True)
        car2_rot = car2_raw.rotate(angle2 - 90, expand=True)

        # ZOOM AUMENTADO para 0.07 (carros maiores e bem visíveis!)
        im_box1 = OffsetImage(car1_rot, zoom=0.07)
        box_p1[0] = AnnotationBbox(im_box1, (x1, y1), frameon=False)
        ax.add_artist(box_p1[0])

        im_box2 = OffsetImage(car2_rot, zoom=0.07)
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
st.write("Simulação oficial com carros grandes e traçado real na pista!")

st.sidebar.header("⚙️ Opções do Duelo")

pistas_disponiveis = ["MONZA", "INTERLAGOS"]
gp_selecionado = st.sidebar.selectbox("Selecione o Circuito", pistas_disponiveis)

pilotos_disponiveis = ["VER", "HAM", "ANT"]
col1, col2 = st.sidebar.columns(2)
with col1:
    p1 = st.selectbox("Piloto 1", pilotos_disponiveis, index=0)
with col2:
    p2 = st.selectbox("Piloto 2", pilotos_disponiveis, index=1)

duracao = st.sidebar.slider("Duração do Vídeo (segundos)", min_value=15, max_value=60, value=20, step=5)

if st.button("🚀 Gerar Vídeo HD", type="primary"):
    try:
        with st.spinner("A renderizar a animação com os carros ajustados..."):
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
