import os
import sys
from pathlib import Path

# Disable buggy Rust hf-xet memory allocator on Windows
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

from huggingface_hub import HfApi, get_token

def main():
    token = get_token()
    api = HfApi(token=token)
    
    gguf_dir = Path("apps/qwenCoder/qwen-manimator-1-gguf")
    merged_dir = Path("apps/qwenCoder/qwen-manimator-1-merged")
    
    q4_path = gguf_dir / "qwen-manimator-1-Q4_K_M.gguf"
    q8_path = gguf_dir / "qwen-manimator-1-Q8_0.gguf"
    modelfile_path = gguf_dir / "Modelfile"
    readme_path = merged_dir / "README.md"
    
    # Ensure repos exist
    print("Verifying repositories...", flush=True)
    api.create_repo("nabin2004/qwen-Manimator-1-merged", repo_type="model", exist_ok=True)
    api.create_repo("nabin2004/qwen-Manimator-1-gguf", repo_type="model", exist_ok=True)
    
    # 1. First upload README and Modelfile to merged repo
    print("Uploading README.md to merged repo...", flush=True)
    api.upload_file(
        path_or_fileobj=str(readme_path),
        path_in_repo="README.md",
        repo_id="nabin2004/qwen-Manimator-1-merged",
        repo_type="model",
        commit_message="docs: update README with Ollama and GGUF quickstart"
    )
    
    print("Uploading Modelfile to merged repo...", flush=True)
    api.upload_file(
        path_or_fileobj=str(modelfile_path),
        path_in_repo="Modelfile",
        repo_id="nabin2004/qwen-Manimator-1-merged",
        repo_type="model",
        commit_message="feat: add Ollama Modelfile"
    )
    
    # 2. Upload Q4_K_M to merged repo
    print(f"Uploading {q4_path.name} to nabin2004/qwen-Manimator-1-merged...", flush=True)
    api.upload_file(
        path_or_fileobj=str(q4_path),
        path_in_repo=q4_path.name,
        repo_id="nabin2004/qwen-Manimator-1-merged",
        repo_type="model",
        commit_message=f"feat: add {q4_path.name}"
    )
    print(f"Uploaded {q4_path.name} to merged repo!", flush=True)
    
    # 3. Upload Q4_K_M to gguf repo
    print(f"Uploading {q4_path.name} to nabin2004/qwen-Manimator-1-gguf...", flush=True)
    api.upload_file(
        path_or_fileobj=str(q4_path),
        path_in_repo=q4_path.name,
        repo_id="nabin2004/qwen-Manimator-1-gguf",
        repo_type="model",
        commit_message=f"feat: add {q4_path.name}"
    )
    
    # 4. Upload Modelfile and README to gguf repo
    print("Uploading Modelfile to gguf repo...", flush=True)
    api.upload_file(
        path_or_fileobj=str(modelfile_path),
        path_in_repo="Modelfile",
        repo_id="nabin2004/qwen-Manimator-1-gguf",
        repo_type="model",
        commit_message="feat: add Ollama Modelfile"
    )
    if (gguf_dir / "README.md").exists():
        api.upload_file(
            path_or_fileobj=str(gguf_dir / "README.md"),
            path_in_repo="README.md",
            repo_id="nabin2004/qwen-Manimator-1-gguf",
            repo_type="model",
            commit_message="docs: add README"
        )
    
    # 5. Upload Q8_0 to both repos
    print(f"Uploading {q8_path.name} to nabin2004/qwen-Manimator-1-merged...", flush=True)
    api.upload_file(
        path_or_fileobj=str(q8_path),
        path_in_repo=q8_path.name,
        repo_id="nabin2004/qwen-Manimator-1-merged",
        repo_type="model",
        commit_message=f"feat: add {q8_path.name}"
    )
    
    print(f"Uploading {q8_path.name} to nabin2004/qwen-Manimator-1-gguf...", flush=True)
    api.upload_file(
        path_or_fileobj=str(q8_path),
        path_in_repo=q8_path.name,
        repo_id="nabin2004/qwen-Manimator-1-gguf",
        repo_type="model",
        commit_message=f"feat: add {q8_path.name}"
    )
    
    print("ALL GGUF UPLOADS COMPLETED SUCCESSFULLY!", flush=True)

if __name__ == "__main__":
    main()
