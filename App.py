import fastf1
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np

# Configurar Cache
fastf1.Cache.enable_cache('cache_f1')

def gerar_video_longo(duracao_segundos=90, fps=30):
    total_frames = duracao_segundos * fps  # Ex: 90s * 30fps = 2700 frames

    # 1. Carregar sessão (Ex: GP do Brasil 2024, Corrida)
    session = fastf1.get_session(2024, 'Interlagos', 'R')
    session.load(telemetry=True)

    # Pegar telemetria das voltas 50 a 53 de dois pilotos
    laps_p1 = session.laps.pick_driver('VER').slice_by_lap(50, 53)
    laps_p2 = session.laps.pick_driver('NOR').slice_by_lap(50, 53)

    tel1 = laps_p1.get_telemetry()
    tel2 = laps_p2.get_telemetry()

    # 2. Reamostrar as coordenadas X e Y para ter EXATAMENTE o número de frames desejado
    time_orig1 = np.linspace(0, 1, len(tel1))
    time_orig2 = np.linspace(0, 1, len(tel2))
    target_time = np.linspace(0, 1, total_frames)

    # Interpolação contínua de posições
    x1_interp = np.interp(target_time, time_orig1, tel1['X'])
    y1_interp = np.interp(target_time, time_orig1, tel1['Y'])
    
    x2_interp = np.interp(target_time, time_orig2, tel2['X'])
    y2_interp = np.interp(target_time, time_orig2, tel2['Y'])

    # 3. Criar a Animação 9:16 (TikTok)
    fig, ax = plt.subplots(figsize=(9, 16), facecolor='#0e0e10')
    ax.set_facecolor('#0e0e10')
    ax.axis('off')

    # Desenhar Pista
    ax.plot(tel1['Y'], tel1['X'], color='#33333e', linewidth=3)

    # Pontos dos Carros
    p1, = ax.plot([], [], 'o', color='#1E41FF', markersize=12, label='VER')
    p2, = ax.plot([], [], 'o', color='#FF8000', markersize=12, label='NOR')
    
    timer_text = ax.text(0.5, 0.93, '', transform=ax.transAxes, color='white', 
                         fontsize=18, fontweight='bold', ha='center')

    def update(frame):
        p1.set_data([y1_interp[frame]], [x1_interp[frame]])
        p2.set_data([y2_interp[frame]], [x2_interp[frame]])
        
        # Tempo simulado no ecrã
        tempo_decorrido = (frame / fps)
        timer_text.set_text(f"Tempo de Animação: {int(tempo_decorrido)}s / {duracao_segundos}s")
        return p1, p2, timer_text

    anim = FuncAnimation(fig, update, frames=total_frames, interval=1000/fps, blit=True)
    
    # Salvar o ficheiro final de 1m30s
    anim.save('f1_batalha_interlagos.mp4', writer='ffmpeg', fps=fps)
    print(f"✅ Vídeo de {duracao_segundos} segundos ({duracao_segundos/60:.1f} min) gerado com sucesso!")

# Executar para criar um vídeo de 90 segundos (1 minuto e meio)
gerar_video_longo(duracao_segundos=90, fps=30)
