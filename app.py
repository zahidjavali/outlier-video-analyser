import streamlit as st
import google.generativeai as genai
import time
import json

# --- Page Configuration ---
st.set_page_config(
    page_title="Outlier Video Analysis",
    page_icon="🎬",
    layout="wide"
)

# --- App Styling ---
st.markdown("""
<style>
    .stApp {
        background-color: #F0F2F6;
    }
    .stTabs [data-baseweb="tab-list"] {
		gap: 24px;
	}
	.stTabs [data-baseweb="tab"] {
		height: 50px;
        white-space: pre-wrap;
		background-color: #F0F2F6;
		border-radius: 4px 4px 0px 0px;
		gap: 1px;
		padding-top: 10px;
		padding-bottom: 10px;
    }
	.stTabs [aria-selected="true"] {
  		background-color: #FFFFFF;
	}
</style>""", unsafe_allow_html=True)


# --- State Management ---
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'video_file' not in st.session_state:
    st.session_state.video_file = None
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = ''
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False

# --- Helper Functions ---

def analyze_video(api_key, video_file):
    """
    Uploads a video file, polls for processing, and generates content using Gemini.
    """
    st.session_state.is_processing = True
    st.session_state.analysis_result = None
    st.session_state.error_message = ''
    
    try:
        genai.configure(api_key=api_key)
        
        # --- File Upload and Processing ---
        st.info("Uploading your video to Google AI Studio...")
        progress_bar = st.progress(0, text="Uploading...")
        
        uploaded_file = genai.upload_file(
            path=video_file.name,
            display_name=video_file.name,
            mime_type=video_file.type
        )
        progress_bar.progress(25, text=f"File '{uploaded_file.display_name}' uploaded. Processing...")

        # Poll for active state
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(5)
            uploaded_file = genai.get_file(name=uploaded_file.name)
        
        if uploaded_file.state.name == "FAILED":
            st.session_state.error_message = "Video processing failed. Please try a different file."
            st.session_state.is_processing = False
            return

        progress_bar.progress(75, text="Video processed successfully. Analyzing with Gemini...")

        # --- Content Generation ---
        model = genai.GenerativeModel(model_name="gemini-1.5-pro")
        
        prompt = """
        Extract the key events from the video, focusing on outlier moments that deviate from the main activity. 
        For each event, provide a precise timestamp, a concise description, and classify it as a 'Minor' or 'Major' outlier. 
        Structure the output as a JSON array of objects, each with 'timestamp', 'description', and 'severity' keys.
        """
        
        response = model.generate_content([prompt, uploaded_file], request_options={"timeout": 600})
        
        # Clean up the response to extract valid JSON
        cleaned_response = response.text.strip().replace("``````", "")
        st.session_state.analysis_result = json.loads(cleaned_response)
        
        progress_bar.progress(100, text="Analysis complete!")

    except Exception as e:
        st.session_state.error_message = f"An error occurred: {str(e)}"
    finally:
        st.session_state.is_processing = False


# --- UI Layout ---

# --- Sidebar ---
with st.sidebar:
    st.title("🎬 Outlier Video Analysis")
    st.markdown("This app uses the Gemini 1.5 Pro model to identify and classify outlier events in a video file.")
    
    st.session_state.api_key = st.text_input(
        "Enter your Google AI API Key", 
        type="password", 
        value=st.session_state.api_key
    )
    
    # Simple check for API key format
    is_api_key_valid = st.session_state.api_key.startswith("AIza") and len(st.session_state.api_key) > 30

    uploaded_video = st.file_uploader(
        "Upload a video file",
        type=["mp4", "mov", "avi", "mkv"],
        disabled=not is_api_key_valid
    )

    if not is_api_key_valid:
        st.warning("Please enter a valid Google AI API Key to enable file uploads.")

    analyze_button = st.button(
        "Analyze Video", 
        disabled=not uploaded_video or st.session_state.is_processing or not is_api_key_valid,
        use_container_width=True
    )
    
# --- Main Content ---
if analyze_button and uploaded_video:
    # Save the uploaded file temporarily to pass its path
    with open(uploaded_video.name, "wb") as f:
        f.write(uploaded_video.getbuffer())
    analyze_video(st.session_state.api_key, uploaded_video)


# --- Display Results ---
if st.session_state.is_processing:
    st.info("Analysis is in progress. This may take a few minutes...")

if st.session_state.error_message:
    st.error(st.session_state.error_message)

if st.session_state.analysis_result:
    st.success("Analysis Complete!")
    
    major_outliers = [item for item in st.session_state.analysis_result if item.get('severity') == 'Major']
    minor_outliers = [item for item in st.session_state.analysis_result if item.get('severity') == 'Minor']

    tab1, tab2, tab3 = st.tabs(["**Major Outliers**", "**Minor Outliers**", "**Raw JSON**"])

    with tab1:
        st.subheader(f"Found {len(major_outliers)} Major Outliers")
        if not major_outliers:
            st.info("No major outliers were detected in the video.")
        else:
            for item in major_outliers:
                st.markdown(f"**Timestamp:** `{item.get('timestamp', 'N/A')}`")
                st.markdown(f"**Description:** {item.get('description', 'No description provided.')}")
                st.divider()

    with tab2:
        st.subheader(f"Found {len(minor_outliers)} Minor Outliers")
        if not minor_outliers:
            st.info("No minor outliers were detected in the video.")
        else:
            for item in minor_outliers:
                st.markdown(f"**Timestamp:** `{item.get('timestamp', 'N/A')}`")
                st.markdown(f"**Description:** {item.get('description', 'No description provided.')}")
                st.divider()

    with tab3:
        st.subheader("Raw JSON Output from Gemini")
        st.json(st.session_state.analysis_result)
        
else:
    if not st.session_state.is_processing:
        st.info("Upload a video and click 'Analyze Video' to begin.")

