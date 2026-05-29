import streamlit as st
import os
import base64
import gc
import psutil
import json

# Configuración de la página
st.set_page_config(page_title="AI Karaoke Separator", layout="wide")
st.title("🎤 AI Karaoke: Separador y Sincronizador")
st.markdown("Sube una canción generada por IA y obtén una pista de Karaoke con la letra sincronizada en tiempo real.")

# 1. Use cache_resource for ML models to avoid reloading them
@st.cache_resource(show_spinner=False)
def load_spleeter_model():
    from spleeter.separator import Separator
    return Separator('spleeter:2stems')

@st.cache_resource(show_spinner=False)
def load_whisperx_model():
    device = "cpu"
    compute_type = "int8"
    model = whisperx.load_model("base", device, compute_type=compute_type)
    return model

# 2. Removed @st.cache_data from processing functions. 
# Caching file paths to temp directories causes FileNotFoundErrors later.
def separate_vocals(audio_path, output_dir):
    separator = load_spleeter_model()
    separator.separate_to_file(audio_path, output_dir)
    
    base_name = os.path.basename(audio_path).split('.')[0]
    # FIX: Changed 'output_path' to 'output_dir'
    accompaniment_path = os.path.join(output_dir, base_name, 'accompaniment.wav')
    vocals_path = os.path.join(output_dir, base_name, 'vocals.wav')
    
    if not os.path.exists(accompaniment_path) or not os.path.exists(vocals_path):
        raise FileNotFoundError("Spleeter failed to generate output files.")
        
    return accompaniment_path, vocals_path

def sync_lyrics(vocals_path):
    model = load_whisperx_model()
    device = "cpu"
    
    audio = whisperx.load_audio(vocals_path)
    # FIX: Updated WhisperX API usage
    result = model.transcribe(audio, language=None)
    
    # Free memory after transcription
    del model
    gc.collect()
    
    # Align words
    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
    
    # Free memory after alignment
    del model_a
    gc.collect()
    
    karaoke_data = []
    # FIX: Handle missing 'words' key safely
    for segment in result.get("segments", []):
        for word_info in segment.get("words", []):
            # Ensure start and end exist
            if "start" in word_info and "end" in word_info:
                karaoke_data.append({
                    "word": word_info.get("word", "") + " ",
                    "start": float(word_info["start"]),
                    "end": float(word_info["end"])
                })
    return karaoke_data

# Interfaz de carga de archivos
uploaded_file = st.file_uploader("🎵 Sube tu archivo de audio (MP3 o WAV)", type=["mp3", "wav"])

if uploaded_file is not None:
    temp_dir = "temp_audio"
    os.makedirs(temp_dir, exist_ok=True)
    temp_audio_path = os.path.join(temp_dir, uploaded_file.name)
    
    with open(temp_audio_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.audio(uploaded_file, format='audio/wav')
    
    if st.button("🚀 Procesar Karaoke", type="primary"):
        # Check available memory
        mem = psutil.virtual_memory()
        if mem.available < 500 * 1024 * 1024: # Less than 500MB
            st.warning("⚠️ Low memory available. Processing might fail on this server.")
            
        try:
            # Paso 1: Separación
            with st.status("Separando voz y música...", expanded=True) as status:
                accompaniment_path, vocals_path = separate_vocals(temp_audio_path, temp_dir)
                st.write("✅ Separación completada.")
                
                # Paso 2: Sincronización de letra
                st.write("⏳ Sincronizando letra con la voz (esto puede tardar un poco)...")
                lyrics_data = sync_lyrics(vocals_path)
                status.update(label="✅ ¡Procesamiento completado!", state="complete", expanded=False)
            
            # Save results to session state
            st.session_state['accompaniment_path'] = accompaniment_path
            st.session_state['lyrics_data'] = lyrics_data
            
            # Clean up original upload and vocals to save disk space on server
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
            if os.path.exists(vocals_path):
                os.remove(vocals_path)
                
        except Exception as e:
            st.error(f"Error durante el procesamiento: {str(e)}")
            st.info("💡 Tip: Los modelos de IA requieren mucha memoria RAM. Si el servidor se queda sin memoria, intente con un audio más corto.")

# Reproductor de Karaoke
if 'accompaniment_path' in st.session_state and 'lyrics_data' in st.session_state:
    st.divider()
    st.subheader("🎶 Pista de Karaoke")
    
    accompaniment_path = st.session_state['accompaniment_path']
    
    # Verify file still exists (temp files might be cleared)
    if not os.path.exists(accompaniment_path):
        st.error("El archivo de acompañamiento se ha perdido. Por favor, procesa el audio nuevamente.")
    else:
        # Read and encode to Base64
        with open(accompaniment_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
            audio_base64 = base64.b64encode(audio_bytes).decode()
        
        # Warning for large files
        if len(audio_bytes) > 10 * 1024 * 1024: # > 10MB
            st.warning("⚠️ El archivo de audio es grande. Si el reproductor no carga, intenta con un audio más corto o comprímelo.")

        lyrics_json = json.dumps(st.session_state['lyrics_data'])

        # FIX: Added animation frame cancellation on pause/end
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
                let animationFrameId = null;

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

                    animationFrameId = requestAnimationFrame(updateKaraoke);
                }}

                // Control de la animación para no consumir CPU infinitamente
                audioPlayer.addEventListener('play', () => {{
                    if (!animationFrameId) updateKaraoke();
                }});

                audioPlayer.addEventListener('pause', () => {{
                    if (animationFrameId) {{
                        cancelAnimationFrame(animationFrameId);
                        animationFrameId = null;
                    }}
                }});

                audioPlayer.addEventListener('ended', () => {{
                    if (animationFrameId) {{
                        cancelAnimationFrame(animationFrameId);
                        animationFrameId = null;
                    }}
                }});
            </script>
        </body>
        </html>
        """
        
        st.components.v1.html(karaoke_html, height=400)
