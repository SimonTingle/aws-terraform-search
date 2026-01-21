import os
import shutil
from git import Repo
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# --- CONFIGURATION ---
DB_DIR = "./local_db"
TEMP_DATA_DIR = "./temp_data"

REPOS = {
    "terraform-provider-aws": "https://github.com/hashicorp/terraform-provider-aws.git",
    "aws-ec2-guide": "https://github.com/awsdocs/amazon-ec2-user-guide.git",
    "aws-s3-guide": "https://github.com/awsdocs/amazon-s3-userguide.git",
    "aws-lambda-guide": "https://github.com/awsdocs/aws-lambda-developer-guide.git"
}

def update_status(callback, msg, percent=None):
    """Helper to send updates to UI if a callback exists."""
    if callback:
        callback(msg, percent)
    else:
        print(f"{msg}")

def run_ingestion(status_callback=None):
    """
    Runs the full ingestion process. 
    status_callback: function(message, percentage_int)
    """
    
    # 1. Clone Repos
    update_status(status_callback, "🧹 Cleaning temporary directories...", 5)
    if os.path.exists(TEMP_DATA_DIR):
        shutil.rmtree(TEMP_DATA_DIR)
    os.makedirs(TEMP_DATA_DIR)

    total_repos = len(REPOS)
    for i, (name, url) in enumerate(REPOS.items()):
        progress = 10 + int((i / total_repos) * 30) # Scale 10-40%
        update_status(status_callback, f"📥 Cloning {name}...", progress)
        Repo.clone_from(url, os.path.join(TEMP_DATA_DIR, name), depth=1)

    # 2. Load and Split
    update_status(status_callback, "📄 Loading and processing files...", 50)
    documents = []
    
    for root, dirs, files in os.walk(TEMP_DATA_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Filter out CDK for Terraform (Noise)
            if "cdktf" in file_path:
                continue

            if file.endswith(".md") or file.endswith(".markdown"):
                try:
                    source_category = "Terraform" if "terraform" in file_path else "AWS"
                    loader = TextLoader(file_path, encoding='utf-8')
                    docs = loader.load()
                    
                    for doc in docs:
                        doc.metadata["source_category"] = source_category
                        doc.metadata["file_path"] = file_path
                    
                    documents.extend(docs)
                except Exception:
                    pass

    if not documents:
        update_status(status_callback, "❌ No documents found.", 100)
        return

    update_status(status_callback, f"✂️ Splitting {len(documents)} documents...", 70)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_documents(documents)

    # 3. Embed and Store
    update_status(status_callback, "🧠 Generating Embeddings (This takes time)...", 80)
    
    # Using legacy import for safety
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    if os.path.exists(DB_DIR):
        shutil.rmtree(DB_DIR)

    # Batch process
    batch_size = 500
    total_chunks = len(chunks)
    for i in range(0, total_chunks, batch_size):
        # Calculate granular progress from 80% to 100%
        current_progress = 80 + int((i / total_chunks) * 20)
        update_status(status_callback, f"💾 Saving batch {i}/{total_chunks}...", current_progress)
        
        batch = chunks[i:i + batch_size]
        Chroma.from_documents(
            documents=batch,
            embedding=embeddings,
            persist_directory=DB_DIR
        )
    
    update_status(status_callback, "🎉 Update Complete!", 100)

if __name__ == "__main__":
    # If run directly from terminal, just print
    run_ingestion()