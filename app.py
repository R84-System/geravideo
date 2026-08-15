import streamlit as st
import os
import fastf1
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np

os.makedirs('cache_f1', exist_ok=True)
fastf1.Cache.enable_cache('cache_f1')

st.title("🏎️ Gerador de Vídeo F1 - TikTok")

if st.button("🚀 Gerar Vídeo de Interlagos (90s)"):
    with st.spinner("Gerando vídeo na nuvem... Isso pode levar de 1 a 2 minutos."):
        # Chama a função de gerar o vídeo
        nome_video = gerar_video_longo(duracao_segundos=90, fps=30)
        
        st.success("Vídeo gerado!")
        st.video(nome_video)
        
        with open(nome_video, "rb") as file:
            st.download_button(
                label="📥 Baixar MP4",
                data=file,
                file_name=nome_video,
                mime="video/mp4"
            )
