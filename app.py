import streamlit as st
import google.generativeai as genai
import time
import os
from pytube import YouTube
from urllib.error import HTTPError

# --- Page Configuration ---
st.set_page_config(
    page_title="YouTube Script & Strategy Analyzer",
    page_icon="📈",
    layout="wide"
)

# --- App Styling ---
st.markdown("""
<style>
    .stApp {
        background-color: #F0F2F6;
    }
    .stProgress > div > div > div > div {
        background-color: #1c83e1;
    }
</style>""", unsafe_allow_html=True)

# --- State Management ---
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = ''
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False

# --- Helper Functions ---

def analyze_youtube_video(api_key, video_url):
    """
    Downloads audio from a YouTube URL, uploads it, and generates a strategic analysis.
    """
    st.session_state.is_processing = True
    st.session_state.analysis_result = None
    st.session_state.error_message = ''
    progress_bar = st.progress(0, text="Analysis initiated...")
    audio_filepath = None
    
    try:
        progress_bar.progress(5, text="Connecting to YouTube...")
        yt = YouTube(video_url)
        audio_stream = yt.streams.filter(only_audio=True).first()
        progress_bar.progress(10, text=f"Downloading audio for '{yt.title}'...")
        audio_filepath = audio_stream.download(filename='temp_audio.mp4')
        
        genai.configure(api_key=api_key)
        
        progress_bar.progress(25, text="Uploading audio to Google AI Studio...")
        uploaded_file = genai.upload_file(
            path=audio_filepath,
            display_name=yt.title,
            mime_type="audio/mp4"
        )
        
        progress_bar.progress(50, text="File uploaded. Processing audio...")
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(5)
            uploaded_file = genai.get_file(name=uploaded_file.name)
        
        if uploaded_file.state.name == "FAILED":
            raise Exception("Video processing failed in Google AI Studio. The file may be corrupt or in an unsupported format.")

        progress_bar.progress(75, text="Audio processed. Analyzing with Gemini 1.5 Pro...")
        model = genai.GenerativeModel(model_name="gemini-1.5-pro")
        
        prompt = f"""
        You are a world-class YouTube strategy consultant. Your task is to analyze the provided audio from the YouTube video titled "{yt.title}". 
        Based on the transcript, which you will infer from the audio, perform a comprehensive analysis of its core components.
        Provide a detailed, structured, and actionable critique in Markdown format.
        
        ### Hook Analysis (First 15-30 Seconds)
        - **Effectiveness Score (1-10):**
        - **Critique:** Does the hook grab attention? Is it clear who the video is for and what problem it solves?
        - **Suggestion:** How could the hook be made more compelling?

        ### Core Content & Structure
        - **Clarity of Message:** Is the video's central promise clear and well-delivered?
        - **Pacing & Engagement:** Does the video maintain momentum? Does it use storytelling or examples?
        - **Value Delivery:** Does the content deliver on the hook's promise?

        ### Call to Action (CTA)
        - **Clarity & Strength:** Is there a clear CTA? Is it compelling and easy to follow?
        - **Placement:** Is the CTA placed effectively?
        - **Suggestion:** How could the CTA be improved?

        ### Overall Summary & Strategic Recommendations
        - Provide a final summary of the video's strengths and weaknesses.
        - List the top 3 most impactful, actionable recommendations for the creator.
        """
        
        response = model.generate_content([prompt, uploaded_file], request_options={"timeout": 600})
        st.session_state.analysis_result = response.text
        
        progress_bar.progress(100, text="Analysis complete!")

    except HTTPError as e:
        if e.code == 429:
            st.session_state.error_message = ("**YouTube Rate Limit Exceeded (HTTP 429)**. The Streamlit server is making too many requests to YouTube. Please wait a few minutes and try again.")
        else:
            st.session_state.error_message = f"A YouTube-related error occurred: {str(e)}"
    except Exception as e:
        st.session_state.error_message = f"An unexpected error occurred: {str(e)}"
    finally:
        st.session_state.is_processing = False
        if audio_filepath and os.path.exists(audio_filepath):
             os.remove(audio_filepath)

# --- UI Layout ---
with st.sidebar:
    st.title("📈 YouTube Script Analyzer")
    st.markdown("Use Gemini 1.5 Pro to analyze a YouTube video's script, hook, structure, and CTA, just by providing a URL.")
    
    st.session_state.api_key = st.text_input("Enter your Google AI API Key", type="password", value=st.session_state.api_key)
    video_url = st.text_input("Enter YouTube Video URL")

    is_api_key_valid = st.session_state.api_key.startswith("AIza") and len(st.session_state.api_key) > 30

    analyze_button = st.button("Analyze Video", disabled=not video_url or st.session_state.is_processing or not is_api_key_valid, use_container_width=True)
    
    if not is_api_key_valid:
        st.warning("Please enter a valid Google AI API Key to enable analysis.")

# --- Main Content Logic ---

# **THIS IS THE CORRECTED/RE-ADDED BLOCK THAT TRIGGERS THE ANALYSIS**
if analyze_button:
    analyze_youtube_video(st.session_state.api_key, video_url)

st.header("📊 Analysis Results")

if st.session_state.is_processing:
    # The progress bar is now inside the function, so this is just a fallback.
    st.info("Analysis is in progress. Depending on the video length, this can take a few minutes...")

if st.session_state.error_message:
    st.error(st.session_state.error_message)

if st.session_state.analysis_result:
    st.markdown(st.session_state.analysis_result)
else:
    if not st.session_state.is_processing:
        st.info("Enter a YouTube URL and click 'Analyze Video' to see a strategic breakdown.")
