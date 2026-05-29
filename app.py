import streamlit as st
import spleeter
import whisperx
import json
import os
import base64
from pydub import AudioSegment

# Configuración de la página
st.set_page_config(page_title="AI Karaoke Separator", layout="wide")
st.title("🎤 AI Karaoke: Separador y Sincronizador")
st.markdown("Sube una canción generada por IA y obtén una pista de Karaoke con la letra sincronizada en tiempo real.")

# Función para separar voz y música usando Spleeter
@st.cache_data(show_spinner=False)
def separate_vocals(audio_path, output_dir):
    from spleeter.separator import Separator
    separator = Separator('spleeter:2stems')
    separator.separate_to_file(audio_path, output_dir)
    # Spleeter crea una subcarpeta con el nombre del archivo original
    accompaniment_path = os.path.join(output_dir, os.path.basename(audio_path).split('.')[0], 'accompaniment.wav')
    vocals_path = os.path.join(output_path, os.path.basename(audio_path).split('.')[0], 'vocals.wav')
    return accompaniment_path, vocals_path

# Función para sincronizar la letra usando WhisperX
@st.cache_data(show_spinner=False)
def sync_lyrics(vocals_path):
    device = "cpu" # Usamos CPU para compatibilidad con Streamlit Cloud gratuito
    compute_type = "int8" 
    
    model = whisperx.load_model("base", device, compute_type=compute_type)
    audio = whisperx.load_audio(vocals_path)
    result = model.transcribe(audio, batch_size=8)
    
    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device)
    
    karaoke_data = []
    for segment in result["segments"]:
        for word_info in segment["words"]:
            karaoke_data.append({
                "word": word_info["word"] + " ",
                "start": float(word_info["start"]),
                "end": float(word_info["end"])
            })
    return karaoke_data

# Interfaz de carga de archivos
uploaded_file = st.file_uploader("🎵 Sube tu archivo de audio (MP3 o WAV)", type=["mp3", "wav"])

if uploaded_file is not None:
    # Guardar el archivo subido temporalmente
    temp_dir = "temp_audio"
    os.makedirs(temp_dir, exist_ok=True)
    temp_audio_path = os.path.join(temp_dir, uploaded_file.name)
    
    with open(temp_audio_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.audio(uploaded_file, format='audio/wav')
    
    if st.button("🚀 Procesar Karaoke", type="primary"):
        # Paso 1: Separación
        with st.status("Separando voz y música...", expanded=True) as status:
            accompaniment_path, vocals_path = separate_vocals(temp_audio_path, temp_dir)
            st.write("✅ Separación completada.")
            
            # Paso 2: Sincronización de letra
            st.write("⏳ Sincronizando letra con la voz (esto puede tardar un poco)...")
            lyrics_data = sync_lyrics(vocals_path)
            status.update(label="✅ ¡Procesamiento completado!", state="complete", expanded=False)
        
        # Guardar los resultados en session_state para que no se pierdan al re-renderizar
        st.session_state['accompaniment_path'] = accompaniment_path
        st.session_state['lyrics_data'] = lyrics_data

# Reproductor de Karaoke (si el procesamiento ha terminado)
if 'accompaniment_path' in st.session_state and 'lyrics_data' in st.session_state:
    st.divider()
    st.subheader("🎶 Pista de Karaoke")
    
    # Leer el archivo de acompañamiento y codificarlo en Base64 para HTML5
    accompaniment_path = st.session_state['accompaniment_path']
    with open(accompaniment_path, "rb") as audio_file:
        audio_bytes = audio_file.read()
        audio_base64 = base64.b64encode(audio_bytes).decode()
    
    lyrics_json = json.dumps(st.session_state['lyrics_data'])

    # Código HTML/JS para el reproductor sincronizado
    karaoke_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background: #0e1117; color: white; text-align: center; padding: 20px; }}
            .word {{ font-size: 2rem; transition: color 0.1s, transform 0.1s; display: inline-block; color: #adb5bd; }}
            .word.active {{ color: #00ff00; font-weight: bold; transform: scale(1.2); text-shadow: 0 0 10px #00ff00; }}
            .word.sung {{ color: #495057; }}
            audio {{ width: 100%; margin-bottom: 30px; }}
        </style>
    </head>
    <body>
        <audio id="karaoke-audio" controls>
            <source src="data:audio/wav;base64,{audio_base64}" type="audio/wav">
        </audio>
        <div id="karaoke-container"></div>

        <script>
            const lyricsData = {lyrics_json};
            const container = document.getElementById('karaoke-container');
            const audioPlayer = document.getElementById('karaoke-audio');

            // Renderizar palabras
            lyricsData.forEach((item, index) => {{
                const span = document.createElement('span');
                span.className = 'word';
                span.id = `word-${{index}}`;
                span.innerText = item.word;
                container.appendChild(span);
            }});

            // Bucle de sincronización
            function updateKaraoke() {{
                const currentTime = audioPlayer.currentTime;
                
                lyricsData.forEach((item, index) => {{
                    const wordElement = document.getElementById(`word-${{index}}`);
                    
                    if (currentTime >= item.start && currentTime <= item.end) {{
                        wordElement.classList.add('active');
                        wordElement.classList.remove('sung');
                    }} else if (currentTime > item.end) {{
                        wordElement.classList.remove('active');
                        wordElement.classList.add('sung');
                    }} else {{
                        wordElement.classList.remove('active', 'sung');
                    }}
                }});

                requestAnimationFrame(updateKaraoke);
            }}

            audioPlayer.addEventListener('play', updateKaraoke);
        </script>
    </body>
    </html>
    """
    
    # Renderizar el componente HTML en Streamlit
    st.components.v1.html(karaoke_html, height=400)
