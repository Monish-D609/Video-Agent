import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def create_seminar_guide():
    doc = docx.Document()

    # 1-inch margins
    for s in doc.sections:
        s.top_margin = Inches(1)
        s.bottom_margin = Inches(1)
        s.left_margin = Inches(1)
        s.right_margin = Inches(1)

    # Color Palette
    PRIMARY = RGBColor(27, 54, 93)     # Deep Navy
    SECONDARY = RGBColor(15, 118, 110) # Teal Accent
    BODY_COLOR = RGBColor(33, 37, 41)  # Charcoal
    CALLOUT_BG = "F8FAFC"              # Light Slate
    HEADER_BG = "0F172A"               # Dark Navy

    # Title
    t_para = doc.add_paragraph()
    t_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_main = t_para.add_run("SEMINAR PRESENTATION GUIDE & SCRIPT\n")
    r_main.font.name = "Arial"
    r_main.font.size = Pt(22)
    r_main.font.bold = True
    r_main.font.color.rgb = PRIMARY

    r_sub = t_para.add_run("Video Agent: Multimodal Meeting & Video Intelligence Assistant\nStructured Seminar Guide for Cloud Computing Faculty Review\n")
    r_sub.font.name = "Arial"
    r_sub.font.size = Pt(13)
    r_sub.font.color.rgb = SECONDARY

    # Overview Box
    meta_table = doc.add_table(rows=4, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_data = [
        ("Presentation Format", "12-15 Minute Project Seminar + 5 Minute Live Demo & Viva"),
        ("Presenter / Student", "Monish D (Semester 5 - Cloud Computing)"),
        ("Project Scope", "Full-Stack AI Application with Production AWS Cloud Architecture"),
        ("Core Phase Breakdown", "Phase 1: Local Development | Phase 2: Frontend | Phase 3: Backend | Phase 4: Cloud (AWS) | Phase 5: Deployment")
    ]
    for i, (k, v) in enumerate(meta_data):
        row = meta_table.rows[i]
        c0, c1 = row.cells[0], row.cells[1]
        c0.width, c1.width = Inches(2.3), Inches(4.2)
        c0.text, c1.text = k, v
        c0.paragraphs[0].runs[0].font.bold = True
        c0.paragraphs[0].runs[0].font.size = Pt(9.5)
        c1.paragraphs[0].runs[0].font.size = Pt(9.5)
        set_cell_background(c0, "F1F5F9")
        set_cell_margins(c0, 60, 60, 100, 100)
        set_cell_margins(c1, 60, 60, 100, 100)

    doc.add_paragraph("")

    def add_sec_heading(title, subtitle=None):
        h = doc.add_heading(title, level=1)
        h.runs[0].font.name = "Arial"
        h.runs[0].font.size = Pt(16)
        h.runs[0].font.bold = True
        h.runs[0].font.color.rgb = PRIMARY
        h.paragraph_format.space_before = Pt(16)
        h.paragraph_format.space_after = Pt(4)
        if subtitle:
            p_sub = doc.add_paragraph(subtitle)
            p_sub.runs[0].font.italic = True
            p_sub.runs[0].font.size = Pt(10)
            p_sub.runs[0].font.color.rgb = SECONDARY
            p_sub.paragraph_format.space_after = Pt(8)

    def add_sub_heading(title):
        h = doc.add_heading(title, level=2)
        h.runs[0].font.name = "Arial"
        h.runs[0].font.size = Pt(12.5)
        h.runs[0].font.bold = True
        h.runs[0].font.color.rgb = SECONDARY
        h.paragraph_format.space_before = Pt(10)
        h.paragraph_format.space_after = Pt(3)

    def add_script_box(what_to_say, what_to_show, key_takeaways):
        box_table = doc.add_table(rows=3, cols=2)
        box_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        fields = [
            ("🗣️ What to Say (Speaker Script)", what_to_say),
            ("🖥️ What to Show (Visual / Slide)", what_to_show),
            ("🎯 Technical Punchline for Faculty", key_takeaways)
        ]
        for idx, (label, content) in enumerate(fields):
            row = box_table.rows[idx]
            c0, c1 = row.cells[0], row.cells[1]
            c0.width, c1.width = Inches(2.2), Inches(4.3)
            c0.text, c1.text = label, content
            c0.paragraphs[0].runs[0].font.bold = True
            c0.paragraphs[0].runs[0].font.size = Pt(9.5)
            c1.paragraphs[0].runs[0].font.size = Pt(9.5)
            set_cell_background(c0, "F8FAFC")
            set_cell_margins(c0, 70, 70, 90, 90)
            set_cell_margins(c1, 70, 70, 90, 90)
        doc.add_paragraph("")

    # --- INTRODUCTION ---
    add_sec_heading("Seminar Strategy: Balancing AI with Cloud Architecture", 
                    "How to frame the presentation so your cloud faculty sees rigorous cloud engineering alongside applied AI.")
    
    doc.add_paragraph(
        "Your faculty is looking for applied cloud engineering: compute sizing, storage persistence, security posture, "
        "cost governance, and automated deployment pipelines. Do not introduce the project solely as a 'chatbot' or 'AI project'. "
        "Frame it as: 'A cloud-native multimodal media intelligence platform engineered on AWS under production constraints.'"
    )

    doc.add_paragraph("Present the project using this 5-Phase Narrative Arc:")
    doc.add_paragraph("1. Phase 1 — Local Development: Problem formulation, prototype pipeline, audio chunking, and baseline latency.", style='List Bullet')
    doc.add_paragraph("2. Phase 2 — Frontend Architecture: Single-page React application, responsive UX, and browser localStorage resilience.", style='List Bullet')
    doc.add_paragraph("3. Phase 3 — Backend & Orchestration: FastAPI asynchronous pipeline worker, hybrid STT routing, and ChromaDB vector RAG.", style='List Bullet')
    doc.add_paragraph("4. Phase 4 — Cloud Infrastructure (AWS): Zero-NAT networking, EBS gp3 swap safeguards, S3 state sync, and SSM zero-secret security.", style='List Bullet')
    doc.add_paragraph("5. Phase 5 — Production Deployment: AWS CDK Infrastructure as Code, Docker containerization, and Cloudflare HTTPS mobile access.", style='List Bullet')

    # --- PHASE 1 ---
    add_sec_heading("Phase 1: Local Development & Pipeline Prototyping", "Duration: ~2 Minutes")
    add_script_box(
        "\"Good morning ma'am. In Phase 1, the objective was to solve a major productivity pain point: hours of unsearchable video and meeting recordings. "
        "During local prototyping, we designed the core audio pipeline using yt-dlp and FFmpeg to normalize incoming media into 16 kHz mono WAV audio. "
        "We identified two critical bottlenecks early: first, memory spikes when running PyTorch STT models on long audio, which we resolved by implementing a 10-minute audio chunking algorithm via pydub. "
        "Second, we recognized that traditional English-only models fail on Indian bilingual dialogue, so we integrated Sarvam AI's Saaras speech API alongside local OpenAI Whisper. "
        "Once verified locally, we focused on transforming this pipeline into an automated, stateless cloud architecture.\"",
        "Slide showing the Audio Ingestion Flowchart:\n• YouTube URL / File Upload ➔ FFmpeg 16 kHz WAV Conversion ➔ 10-min Pydub Chunking ➔ Dual-engine STT (Whisper / Sarvam AI) ➔ LLaMA 3.3 Summarizer ➔ ChromaDB Vector Index.",
        "Demonstrates sound algorithmic planning: audio normalization, chunking to eliminate buffer overflows, and modular component testing before cloud deployment."
    )

    # --- PHASE 2 ---
    add_sec_heading("Phase 2: Frontend Engineering & Client-Side Resilience", "Duration: ~2 Minutes")
    add_script_box(
        "\"In Phase 2, we built the presentation layer using React with Vite. Rather than a basic prototype, we implemented a responsive, dark-mode single-page dashboard tailored for both desktop and mobile screens. "
        "Key architectural features include:\n"
        "1. Real-time stage polling: Users see visual feedback as the video transitions through Downloading, Transcribing, Summarizing, and Indexing.\n"
        "2. Client-side caching: We implemented a two-tier storage manager in localStorage (storage.js). Previous chat sessions and summaries are cached directly on the client. Even if the network drops or the server is stopped, the user never sees a blank screen.\n"
        "3. Production bundling: The React application is compiled into static production assets (frontend/dist) and statically mounted by the FastAPI backend, eliminating the overhead of running a separate Node.js server in the cloud.\"",
        "Slide with screenshots of the Web UI on both Laptop and Mobile Phone:\n• Left side: Responsive dashboard showing summary cards and action checklists.\n• Right side: Interactive Q&A chat with exact timestamp citations.",
        "Highlights full-stack engineering: single-server static mounting (saving cloud resources) and client-side offline resilience with localStorage."
    )

    # --- PHASE 3 ---
    add_sec_heading("Phase 3: Backend Services & AI Orchestration", "Duration: ~3 Minutes")
    add_script_box(
        "\"Phase 3 encapsulates the backend services written in FastAPI and Python 3.11. "
        "The backend serves two primary roles: API orchestration and background worker management.\n"
        "When a user triggers a video processing job, the request returns immediately with a unique job key while the heavy processing runs in a daemonized background thread. "
        "This prevents HTTP connection timeouts during long video transcriptions.\n"
        "For question-answering, we implemented Retrieval-Augmented Generation (RAG). Transcripts are embedded into 384-dimensional dense vectors using Hugging Face's all-MiniLM-L6-v2 model and stored in ChromaDB. "
        "To ensure multi-tenant data isolation, each video gets its own ChromaDB collection (video_<key>), preventing transcripts from different meetings from bleeding into each other during cosine similarity search.\"",
        "Slide showing the Backend Architecture & Threading Model:\n• FastAPI REST Controller (/process, /chat, /status, /health)\n• Background Thread Pipeline Worker with Mutex Job Locks\n• ChromaDB Isolated Collection Architecture (video_<key>)\n• Cloudflare Workers AI (LLaMA 3.3 70B) Inference integration.",
        "Answers how long-running jobs are managed without blocking the server, and proves data isolation principles in vector retrieval."
    )

    # --- PHASE 4 ---
    add_sec_heading("Phase 4: Cloud Architecture on AWS", "Duration: ~4 Minutes (CORE CLOUD FOCUS)")
    add_script_box(
        "\"Phase 4 is the core cloud architecture. As cloud engineers, deploying an application is not just about spinning up a server; it is about security, availability, and financial engineering.\n"
        "We designed the AWS environment under strict Free Tier and budget constraints:\n"
        "1. Compute & Memory Protection: We provisioned an Amazon EC2 t3.small instance running Amazon Linux 2023. To prevent Out-Of-Memory kernel panics when PyTorch and Whisper run simultaneously on 2 GB of RAM, our cloud-init script provisions a dedicated 2 GB swap file on the 25 GB gp3 EBS root volume.\n"
        "2. Zero-NAT Network Design: Instead of a multi-subnet VPC with managed NAT Gateways—which incur an idle cost of $32.40 per month each—we routed through public subnets with Internet Gateways and tightly restricted Security Groups, achieving $0.00 in idle networking fees.\n"
        "3. Zero-Secret Architecture: Sensitive API tokens for Cloudflare and Sarvam are stored in AWS Systems Manager (SSM) Parameter Store as encrypted SecureString parameters. No credentials exist in git or CloudFormation templates.\n"
        "4. Keyless Remote Access: Port 22 (SSH) is completely closed in the Security Group. Administrative terminal access is managed exclusively via AWS SSM Session Manager over encrypted HTTPS using IAM roles.\n"
        "5. State Synchronization to S3: Because EC2 compute is ephemeral, we wrote an automated S3 synchronization daemon that backs up JSON transcripts and session state to a private S3 bucket on shutdown and restores them seamlessly upon startup.\"",
        "Slide showing the AWS Architecture Diagram:\n• Default VPC with 0 NAT Gateways\n• Security Group (Port 8000 Web, Port 22 CLOSED)\n• EC2 (t3.small) + 25 GB gp3 EBS with 2 GB Swap\n• SSM Parameter Store (SecureString) + Session Manager\n• Amazon S3 Private Backup Bucket + Lifecycle Rules\n• AWS Budgets ($5.00/mo cap with email alerts) & CloudWatch (7-day retention).",
        "This is your strongest slide for the cloud faculty. It demonstrates mastery of AWS cost optimization, IAM least-privilege, and production infrastructure design."
    )

    # --- PHASE 5 ---
    add_sec_heading("Phase 5: Production Deployment & Cloud Delivery", "Duration: ~3 Minutes")
    add_script_box(
        "\"Finally, Phase 5 encompasses deployment automation and production delivery.\n"
        "1. Infrastructure as Code (IaC): The entire AWS footprint was authored using AWS CDK v2 in Python. With a single declarative command, CDK synthesizes and provisions the IAM policies, S3 bucket, EC2 instance, and Budget alarms in 170 seconds without manual console clicking.\n"
        "2. Multi-Stage Docker Containerization: We created a Docker image that pre-caches Whisper AI weights and embedding models in the container layer, reducing cold-start latency from minutes to seconds.\n"
        "3. Mobile Production URL: To make the application accessible on mobile phones without awkward IP addresses or port numbers (:8000), we deployed an automated Cloudflare HTTPS tunnel directly on the EC2 instance. This provides an enterprise-grade, SSL-encrypted URL that anyone—including you, ma'am—can open on an iPhone or Android phone.\n"
        "4. Lifecycle Cost Management: We developed stop.ps1 and start.ps1 automation scripts. Running stop.ps1 immediately triggers an S3 state sync and pauses the EC2 instance, halting all compute and IPv4 billing to $0.00 when not in use.\"",
        "Slide showing Deployment Automation & Verification:\n• AWS CDK synthesis and deployment output (CREATE_COMPLETE in 170s)\n• Docker multi-stage build diagram\n• Live HTTPS URL on mobile phone\n• Automated PowerShell start/stop lifecycle commands.",
        "Connects DevOps automation (IaC + Docker) with real-world accessibility and financial management."
    )

    # --- LIVE DEMO GUIDE ---
    add_sec_heading("Live Demonstration Script (3-5 Minutes)", "Exact step-by-step walkthrough to show your faculty.")
    
    demo_table = doc.add_table(rows=6, cols=3)
    demo_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    d_headers = ["Step", "Action & Screen to Show", "What to Explain to Faculty"]
    for j, h in enumerate(d_headers):
        c = demo_table.rows[0].cells[j]
        c.text = h
        c.paragraphs[0].runs[0].font.bold = True
        c.paragraphs[0].runs[0].font.size = Pt(9.5)
        c.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(c, HEADER_BG)
        set_cell_margins(c, 70, 70, 80, 80)

    demo_steps = [
        ("1. Cloud Verification", "Open AWS Management Console (EC2 Dashboard & S3)", "Show the t3.small EC2 instance running in ap-south-1 with Project: video-agent tags, the private S3 backup bucket, and the closed Port 22 in the Security Group."),
        ("2. Launch Live App", "Open the HTTPS link on your laptop and offer it to her phone", "Open https://occupations-bold-accompanied-formula.trycloudflare.com. Point out that the site has a valid green-padlock SSL certificate with no port numbers."),
        ("3. Process Media", "Upload an audio file or YouTube video clip", "Click Process. Show the real-time progress indicator updating from Transcribing to Summarizing to Indexing. Explain that this is running on the EC2 Docker container."),
        ("4. Review & Chat", "Show generated Executive Summary and Ask a Question in Chat", "Display the structured markdown summary and action items. In the chat box, ask a question about the video; show how the RAG engine cites the exact video timestamp."),
        ("5. Cost & Lifecycle", "Show stop.ps1 in the terminal", "Explain: 'When the seminar ends, running stop.ps1 will sync our new session data to S3 and stop the instance, ensuring 0 ongoing compute charges.'")
    ]
    for idx, (s, a, e) in enumerate(demo_steps, start=1):
        row = demo_table.rows[idx]
        for c_idx, text in enumerate([s, a, e]):
            cell = row.cells[c_idx]
            cell.text = text
            cell.paragraphs[0].runs[0].font.size = Pt(9)
            if idx % 2 == 1:
                set_cell_background(cell, CALLOUT_BG)
            set_cell_margins(cell, 60, 60, 80, 80)

    doc.add_paragraph("")

    # --- ANTICIPATED FACULTY QUESTIONS ---
    add_sec_heading("Anticipated Faculty Questions & Winning Technical Answers", "Common questions cloud evaluators ask, and how to answer them authoritatively.")

    qa_list = [
        ("Q1: Why did you deploy on EC2 instead of AWS Lambda serverless functions?",
         "Answer: \"AWS Lambda has strict serverless execution constraints: a hard 15-minute timeout, a 250 MB unzipped deployment package limit, and ephemeral /tmp storage. "
         "Our application runs local PyTorch and Whisper AI models (>1.5 GB), FFmpeg system binaries, and a persistent ChromaDB vector database. "
         "Running this on an EC2 instance with Docker Compose eliminates package limits, allows 10+ minute audio transcriptions without timeout, and provides predictable, cost-effective computing under the AWS Free Tier.\""),
        
        ("Q2: Why did you choose a Zero-NAT network architecture?",
         "Answer: \"A standard AWS multi-tier VPC deploys EC2 instances in private subnets behind a NAT Gateway. However, an AWS NAT Gateway incurs an idle baseline cost of approximately $32.40 per month plus data processing charges. "
         "For an academic project with strict budget limits, we engineered a Zero-NAT architecture by placing the instance in a public subnet with an Internet Gateway, while enforcing ironclad security using Security Groups: inbound traffic is restricted strictly to web port 8000, and SSH (Port 22) is completely blocked in favor of AWS SSM Session Manager.\""),

        ("Q3: How do you handle secrets and API keys on the cloud server?",
         "Answer: \"We adhered to twelve-factor app and DevSecOps best practices. No secrets exist in our git repository, Dockerfiles, or CloudFormation templates. "
         "Instead, sensitive keys for Cloudflare and Sarvam AI are stored as encrypted SecureString parameters in AWS Systems Manager (SSM) Parameter Store. "
         "During EC2 bootstrap (cloud-init), the instance uses its scoped IAM role to fetch the parameters into memory and write a permissions-restricted .env file (chmod 600) on the server.\""),

        ("Q4: If the EC2 instance is stopped to save costs, how is data not lost?",
         "Answer: \"EC2 compute is stateless, but our state is backed by an Amazon S3 persistence layer. We created an automated script (s3_sync.sh) that synchronizes JSON transcripts, summaries, and ChromaDB session metadata to a private S3 bucket during instance shutdown. "
         "When start.ps1 is executed, the cloud-init service automatically pulls the latest state from S3 before launching the Docker container. Furthermore, we filter out raw audio files to keep S3 storage well within the 5 GB Free Tier.\""),

        ("Q5: How does the application prevent out-of-memory errors on a small t3.small instance?",
         "Answer: \"A t3.small instance has 2 GB of physical RAM. Concurrent execution of PyTorch, Whisper inference, and vector embeddings can cause memory spikes of up to 2.8 GB. "
         "To prevent kernel Out-Of-Memory (OOM) crashes, our bootstrap script provisions a dedicated 2 GB swap file (/swapfile) on the 25 GB gp3 EBS root volume. This gives the instance 4 GB of virtual memory headroom with zero extra infrastructure cost.\"")
    ]

    for q, a in qa_list:
        p_q = doc.add_paragraph()
        r_q = p_q.add_run(q)
        r_q.bold = True
        r_q.font.color.rgb = PRIMARY
        p_q.paragraph_format.space_before = Pt(8)
        p_q.paragraph_format.space_after = Pt(2)

        p_a = doc.add_paragraph(a)
        p_a.runs[0].font.size = Pt(9.5)
        p_a.paragraph_format.space_after = Pt(6)

    # Save
    out_path = "c:/Users/Monish D/Desktop/SEM 5/Projects/Cloud/Video-Agent/SEMINAR_PRESENTATION_GUIDE.docx"
    doc.save(out_path)
    print("Successfully generated SEMINAR_PRESENTATION_GUIDE.docx")

if __name__ == "__main__":
    create_seminar_guide()
