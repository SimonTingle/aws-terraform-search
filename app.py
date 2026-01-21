import streamlit as st
import os
import ingest  # Import our new ingest module
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# --- CONFIGURATION ---
DB_DIR = "./local_db"

st.set_page_config(page_title="AWS & Terraform Doc Search", layout="wide")

# --- FUNCTIONS ---
def get_github_url(local_path):
    """Converts a local file path to a clickable GitHub URL."""
    repo_map = {
        "terraform-provider-aws": "https://github.com/hashicorp/terraform-provider-aws/blob/main",
        "aws-ec2-guide": "https://github.com/awsdocs/amazon-ec2-user-guide/blob/master",
        "aws-s3-guide": "https://github.com/awsdocs/amazon-s3-userguide/blob/master",
        "aws-lambda-guide": "https://github.com/awsdocs/aws-lambda-developer-guide/blob/main"
    }
    path = local_path.replace("\\", "/")
    for folder, base_url in repo_map.items():
        if folder in path:
            relative_path = path.split(folder)[-1].lstrip("/")
            return f"{base_url}/{relative_path}"
    return None

def get_official_doc_url(local_path):
    """Attempts to generate the official Registry/AWS URL."""
    path = local_path.replace("\\", "/")
    if "terraform-provider-aws" in path and "website/docs" in path:
        filename = os.path.basename(path).replace(".html.markdown", "").replace(".markdown", "")
        if "/r/" in path and "cdktf" not in path:
            return f"https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/{filename}"
        elif "/d/" in path and "cdktf" not in path:
            return f"https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/{filename}"
    return None

@st.cache_resource
def load_db():
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    if os.path.exists(DB_DIR):
        return Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    return None

# --- SIDEBAR: UPDATE LOGIC ---
st.sidebar.title("⚙️ Settings")

# 1. Update Database Button
if st.sidebar.button("🔄 Update Database"):
    # Create a container for the progress UI
    status_container = st.status("Starting update...", expanded=True)
    progress_bar = status_container.progress(0)
    
    def ui_callback(msg, percent):
        """Bridge between ingest.py and Streamlit UI"""
        status_container.write(msg)
        if percent is not None:
            progress_bar.progress(percent)
    
    try:
        # Run the actual ingestion
        ingest.run_ingestion(status_callback=ui_callback)
        status_container.update(label="✅ Update Complete!", state="complete", expanded=False)
        st.cache_resource.clear()  # Clear cache so new DB is loaded
        st.rerun() # Refresh app
    except Exception as e:
        status_container.update(label="❌ Error", state="error")
        st.error(f"Update failed: {e}")

# --- MAIN APP ---
vector_db = load_db()

if vector_db is None:
    st.error("🔴 Database not found. Please click 'Update Database' in the sidebar.")
    st.stop() # Stop execution here

st.sidebar.success("🟢 Database Connected")
st.title("☁️ AWS & Terraform Unified Search")

# Search UI
search_source = st.sidebar.radio("Knowledge Source:", ["All", "AWS Only", "Terraform Only"])
query = st.text_input("Enter your query", placeholder="e.g., How do I create an S3 bucket with encryption?")

if query:
    filter_dict = {}
    if search_source == "AWS Only":
        filter_dict = {"source_category": "AWS"}
    elif search_source == "Terraform Only":
        filter_dict = {"source_category": "Terraform"}

    results = vector_db.similarity_search(query, k=5, filter=filter_dict if filter_dict else None)

    st.subheader("Search Results")
    if not results:
        st.warning("No results found.")
    
    for i, doc in enumerate(results):
        file_path = doc.metadata.get('file_path', 'Unknown')
        category = doc.metadata.get('source_category', 'Unknown')
        github_url = get_github_url(file_path)
        official_url = get_official_doc_url(file_path)

        with st.expander(f"Result {i+1}: {doc.page_content[:60]}..."):
            col1, col2 = st.columns([1, 1])
            with col1:
                if github_url:
                    st.link_button("📂 View Source (GitHub)", github_url)
            with col2:
                if official_url:
                    st.link_button("🌐 View Official Docs", official_url)
            
            st.markdown(f"**Source:** {category}")
            st.divider()
            st.markdown(doc.page_content)