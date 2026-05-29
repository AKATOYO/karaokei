# 🎤 AI Karaoke: Separador y Sincronizador

Aplicación web construida con Streamlit que utiliza Inteligencia Artificial para separar la voz de la música en cualquier canción y generar una pista de karaoke con la letra sincronizada en tiempo real.

## ¿Cómo funciona?
1. **Separación de Fuentes**: Utiliza [Spleeter](https://github.com/deezer/spleeter) de Deezer para aislar la voz y el acompañamiento musical.
2. **Sincronización de Letra**: Usa [WhisperX](https://github.com/m-bain/whisperX) para transcribir la voz y alinear cada palabra con su marca de tiempo exacta (forced alignment).
3. **Visualización**: Un reproductor HTML5/JS resalta las palabras en tiempo real mientras suena la música de fondo.

## Despliegue en Streamlit Cloud
1. Sube este repositorio a GitHub.
2. Ve a [Streamlit Cloud](https://streamlit.io/cloud) y conecta tu cuenta de GitHub.
3. Despliega la aplicación seleccionando este repositorio. ¡Streamlit instalará automáticamente las dependencias de `requirements.txt` y `packages.txt`!

## Ejecución Local
```bash
git clone https://github.com/tu-usuario/karaoke-ai-app.git
cd karaoke-ai-app
pip install -r requirements.txt
streamlit run app.py
