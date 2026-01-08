"""
Paper Digest Portal - With Embedded Video Player
"""

import json
import gradio as gr
from huggingface_hub import hf_hub_download

DATASET_ID = "brianxiadong0627/paper-digest-videos"


def load_metadata():
    try:
        path = hf_hub_download(repo_id=DATASET_ID, filename="metadata.json", repo_type="dataset")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error: {e}")
        return {"weeks": {}, "last_updated": None}


def get_weeks():
    m = load_metadata()
    w = list(m.get("weeks", {}).keys())
    return sorted(w, reverse=True) if w else ["No data"]


def show_papers(week):
    m = load_metadata()
    papers = m.get("weeks", {}).get(week, [])
    
    if not papers:
        return "No papers for this week. Run `apd publish` first."
    
    result = f"# 📚 Week {week}\n\n"
    
    for i, p in enumerate(papers, 1):
        video_url = p.get('video_url', '')
        
        # Create embedded video player HTML if video exists
        video_html = ""
        if video_url:
            # Convert blob URL to resolve URL for video streaming
            if '/blob/' in video_url:
                video_url = video_url.replace('/blob/', '/resolve/')
            video_html = f"""
<video controls width="100%" style="max-width:640px; margin:10px 0; border-radius:8px;">
  <source src="{video_url}" type="video/mp4">
  Your browser does not support video playback. <a href="{video_url}">Download video</a>
</video>
"""
        
        result += f"""
## {i}. {p.get('title', 'Untitled')}

**Paper ID:** `{p.get('paper_id')}`

[📄 PDF]({p.get('pdf_url', '#')}) | [🤗 HuggingFace Paper]({p.get('hf_url', '#')})

{video_html}

---
"""
    return result


# Simple Interface
demo = gr.Interface(
    fn=show_papers,
    inputs=gr.Dropdown(choices=get_weeks(), label="📅 Select Week", value=get_weeks()[0] if get_weeks() else None),
    outputs=gr.Markdown(label="Papers"),
    title="📚 Paper Digest Portal",
    description="Weekly AI/ML paper video overviews powered by NotebookLM. Videos play directly in browser!",
    allow_flagging="never",
)

demo.launch()
