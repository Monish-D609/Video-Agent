import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def create_report():
    doc = docx.Document()

    # Set 1-inch margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Styles
    PRIMARY = RGBColor(27, 54, 93)     # Deep Navy
    SECONDARY = RGBColor(70, 80, 95)   # Charcoal Slate
    BODY_COLOR = RGBColor(33, 37, 41)
    ACCENT_BG = "F1F5F9"               # Slate 100
    HEADER_BG = "1E293B"               # Slate 800

    # Title
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = title.add_run("PROJECT REPORT: VIDEO AGENT\n")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(24)
    run_title.font.bold = True
    run_title.font.color.rgb = PRIMARY

    sub = title.add_run("Cloud-Integrated Multimodal Video & Meeting Intelligence Assistant\n")
    sub.font.name = "Arial"
    sub.font.size = Pt(14)
    sub.font.color.rgb = SECONDARY

    # Metadata banner table
    meta_table = doc.add_table(rows=5, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_data = [
        ("Course / Domain", "Cloud Computing & Applied Artificial Intelligence"),
        ("Student / Developer", "Monish D"),
        ("Repository Branch", "Cloud-Integrated (Git commit: 4c1c425)"),
        ("Target Cloud Platform", "Amazon Web Services (AWS) — Region ap-south-1 (Mumbai)"),
        ("IaC Tooling", "AWS Cloud Development Kit (CDK v2 - Python)")
    ]
    for i, (k, v) in enumerate(meta_data):
        row = meta_table.rows[i]
        c0, c1 = row.cells[0], row.cells[1]
        c0.width, c1.width = Inches(2.2), Inches(4.3)
        c0.text, c1.text = k, v
        c0.paragraphs[0].runs[0].font.bold = True
        c0.paragraphs[0].runs[0].font.size = Pt(10)
        c1.paragraphs[0].runs[0].font.size = Pt(10)
        set_cell_background(c0, ACCENT_BG)
        set_cell_margins(c0, 60, 60, 100, 100)
        set_cell_margins(c1, 60, 60, 100, 100)

    doc.add_paragraph("")

    def add_heading(text, level):
        h = doc.add_heading(text, level=level)
        h.runs[0].font.name = "Arial"
        if level == 1:
            h.runs[0].font.size = Pt(16)
            h.runs[0].font.bold = True
            h.runs[0].font.color.rgb = PRIMARY
            h.paragraph_format.space_before = Pt(16)
            h.paragraph_format.space_after = Pt(6)
        elif level == 2:
            h.runs[0].font.size = Pt(13)
            h.runs[0].font.bold = True
            h.runs[0].font.color.rgb = SECONDARY
            h.paragraph_format.space_before = Pt(12)
            h.paragraph_format.space_after = Pt(4)
        return h

    # 1. Executive Summary
    add_heading("1. Executive Summary", 1)
    p = doc.add_paragraph(
        "In educational and enterprise environments, video and audio recordings (technical meetings, lectures, workshops) "
        "contain high-density knowledge but are fundamentally unsearchable and time-consuming to consume linearly. "
        "Video Agent is an end-to-end, cloud-deployed multimodal AI assistant that automates the ingestion, audio normalization, "
        "bilingual transcription, summarization, and semantic vector indexing of recorded media."
    )
    p.paragraph_format.space_after = Pt(6)

    p2 = doc.add_paragraph(
        "The system incorporates state-of-the-art AI services: local OpenAI Whisper (base) for English speech, "
        "Sarvam AI Speech API for code-mixed Indian languages (Hinglish/Hindi), Cloudflare Workers AI (Meta LLaMA 3.3 70B) "
        "for structured meeting minutes, and Hugging Face embeddings (all-MiniLM-L6-v2) with ChromaDB for interactive Q&A (RAG)."
    )
    p2.paragraph_format.space_after = Pt(6)

    p3 = doc.add_paragraph(
        "The complete architecture is deployed to Amazon Web Services (AWS) using declarative Infrastructure as Code (AWS CDK in Python). "
        "To satisfy strict institutional and student financial constraints, the system is engineered with a Zero-NAT network architecture, "
        "SSM Parameter Store zero-secret governance, keyless SSM Session Manager administration (Port 22 closed), "
        "S3 persistent backup synchronization, and script-driven EC2 lifecycle cost automation."
    )

    # 2. Problem Statement & Objectives
    add_heading("2. Problem Statement & Objectives", 1)
    add_heading("2.1 The Problem", 2)
    doc.add_paragraph("• Unsearchable Knowledge Archives: Linear video review wastes valuable developer and student hours.", style='List Bullet')
    doc.add_paragraph("• Accent & Multilingual Gaps: Standard STT models struggle with Indian-accented English and code-mixed Hinglish conversations.", style='List Bullet')
    doc.add_paragraph("• Cloud Cost Overruns: Deploying containerized AI backends naively triggers substantial idle charges from NAT Gateways (~$32.40/mo), ALBs, and managed database instances.", style='List Bullet')

    add_heading("2.2 Project Objectives", 2)
    doc.add_paragraph("1. Automated Ingestion: Ingest YouTube URLs or local media files (.mp4, .mp3, .wav, .m4a) with automatic 16 kHz WAV conversion and 10-minute audio chunking.", style='List Number')
    doc.add_paragraph("2. Bilingual Speech Recognition: Support both native English and Hinglish dialogue with dynamic model routing.", style='List Number')
    doc.add_paragraph("3. Automated Insight Extraction: Produce structured markdown summaries, key decisions, and action items via LLM.", style='List Number')
    doc.add_paragraph("4. Conversational Vector RAG: Enable interactive natural language question answering with exact timestamp citations.", style='List Number')
    doc.add_paragraph("5. Zero-Waste Cloud Engineering: Deploy on AWS within Free Tier parameters using automated start/stop cost controls and budget alarms.", style='List Number')

    # 3. System Architecture
    add_heading("3. System Architecture & High-Level Design", 1)
    p_arch = doc.add_paragraph(
        "The solution is architected as a modular, three-tier cloud deployment comprising a React Single-Page Application (SPA), "
        "a containerized FastAPI orchestration service on Amazon EC2, and managed AWS services for storage, security, and governance."
    )

    arch_table = doc.add_table(rows=5, cols=3)
    arch_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Tier", "Component & Technology", "Responsibilities & Functionality"]
    for j, h in enumerate(headers):
        cell = arch_table.rows[0].cells[j]
        cell.text = h
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(cell, HEADER_BG)
        set_cell_margins(cell, 100, 100, 120, 120)

    arch_rows = [
        ("Presentation", "React (Vite) Single-Page Application", "Provides a dark-themed UI for YouTube URL input, drag-and-drop file upload, real-time stage progress tracking, and conversational chat with citations."),
        ("Application & AI", "FastAPI + Docker on Amazon EC2 (t3.small)", "Executes media download (yt-dlp), audio conversion (FFmpeg), local Whisper STT, Sarvam AI API dispatch, and ChromaDB vector indexing."),
        ("Cloud Persistence", "Amazon S3 Bucket (Private)", "Stores JSON transcripts, summaries, and session state. Synchronized via lifecycle scripts during instance startup and shutdown (raw audio filtered out)."),
        ("Cloud Governance", "AWS SSM, IAM, CloudWatch, Budgets", "Manages encrypted API tokens (SecureString), provides keyless terminal access (Session Manager), monitors logs (7-day retention), and enforces $5.00/mo spend limit.")
    ]
    for i, row_data in enumerate(arch_rows, start=1):
        row = arch_table.rows[i]
        for j, val in enumerate(row_data):
            cell = row.cells[j]
            cell.text = val
            cell.paragraphs[0].runs[0].font.size = Pt(9.5)
            if i % 2 == 1:
                set_cell_background(cell, ACCENT_BG)
            set_cell_margins(cell, 80, 80, 100, 100)

    # 4. AWS Cloud Infrastructure Details
    add_heading("4. AWS Cloud Infrastructure & Services Utilized", 1)
    doc.add_paragraph(
        "All cloud resources were provisioned using AWS CDK v2 in Python (infra/video_agent_stack.py). "
        "The following AWS services were selected and configured:"
    )

    aws_services = [
        ("Amazon EC2 (t3.small)", "Application host running Amazon Linux 2023. Configured with User Data cloud-init to install Docker, pull SSM parameters, restore S3 state, and auto-start the container via systemd."),
        ("Amazon EBS (25 GB gp3)", "High-performance root filesystem (3,000 IOPS, 125 MB/s). Provisioned with an internal 2 GB swap file (/swapfile) to ensure memory stability during PyTorch AI inference without OOM termination."),
        ("Amazon S3 (Private Bucket)", "Dedicated bucket with server-side encryption for persistent transcript and vector index backups. Configured with auto_delete_objects=True for clean teardown."),
        ("AWS SSM Parameter Store", "Secure, encrypted storage for Cloudflare and Sarvam AI tokens using SecureString. Zero secrets are committed to git or synthesized templates."),
        ("AWS SSM Session Manager", "Enables browser and CLI shell access over HTTPS. Eliminates SSH key pairs and allows Port 22 to remain completely closed in the Security Group."),
        ("AWS IAM", "Least-privilege instance roles strictly scoped to project-specific S3 bucket ARNs and /video-agent/* SSM parameter paths."),
        ("Amazon CloudWatch", "Captures application and container logs with an enforced 7-day retention policy to prevent ongoing log storage charges."),
        ("AWS Budgets", "Configured with a hard $5.00/month cap and automated email alerts at 80% ($4.00) and 100% ($5.00) spend thresholds."),
        ("Amazon VPC (Default VPC / Zero-NAT)", "Leverages default public subnets with direct Internet Gateway routing, completely avoiding NAT Gateways (~$32.40/month savings)."),
        ("AWS CDK & CloudFormation", "Declarative Infrastructure as Code (IaC) enabling one-click deployment, updates, and automated teardown.")
    ]
    for name, desc in aws_services:
        p_svc = doc.add_paragraph()
        r_name = p_svc.add_run(f"• {name}: ")
        r_name.bold = True
        r_name.font.color.rgb = PRIMARY
        p_svc.add_run(desc)
        p_svc.paragraph_format.space_after = Pt(3)

    # 5. Financial Engineering & Cost Breakdown
    add_heading("5. Financial Engineering & Cost Breakdown", 1)
    doc.add_paragraph(
        "A cornerstone of the architecture is strict cost containment. The table below outlines the AWS Free Tier allowances "
        "and estimated monthly costs under 24/7 continuous operation versus an on-demand workflow utilizing the provided stop/start scripts:"
    )

    cost_table = doc.add_table(rows=9, cols=5)
    cost_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_headers = ["AWS Resource", "Free Tier Allowance", "Project Configuration", "Est. Cost (24/7 Run)", "Est. Cost (~4h/day)"]
    for j, h in enumerate(c_headers):
        cell = cost_table.rows[0].cells[j]
        cell.text = h
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(9)
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(cell, HEADER_BG)
        set_cell_margins(cell, 80, 80, 80, 80)

    cost_data = [
        ("EC2 Compute (t3.small)", "750h t2.micro/t3.micro", "1x t3.small (ap-south-1)", "$15.18 / mo", "$2.53 / mo"),
        ("EBS gp3 Storage", "30 GB-months free", "25 GB gp3 volume", "$0.00 (Free Tier)", "$0.00 (Free Tier)"),
        ("S3 Backup Storage", "5 GB Standard free", "< 50 MB JSON text backup", "$0.00 (Free Tier)", "$0.00 (Free Tier)"),
        ("SSM Parameter Store", "Unlimited standard", "4 Standard SecureStrings", "$0.00", "$0.00"),
        ("SSM Session Manager", "Free tier eligible", "IAM-based shell access", "$0.00", "$0.00"),
        ("CloudWatch Logs", "5 GB ingestion free", "< 100 MB (7-day retention)", "$0.00", "$0.00"),
        ("AWS Budgets", "2 free budgets", "1 budget + 2 email alerts", "$0.00", "$0.00"),
        ("Public IPv4 Address", "N/A ($0.005/hr in-use)", "Assigned to active EC2", "$3.60 / mo", "$0.60 / mo")
    ]
    for i, row_data in enumerate(cost_data, start=1):
        row = cost_table.rows[i]
        for j, val in enumerate(row_data):
            cell = row.cells[j]
            cell.text = val
            cell.paragraphs[0].runs[0].font.size = Pt(8.5)
            if i % 2 == 1:
                set_cell_background(cell, ACCENT_BG)
            set_cell_margins(cell, 60, 60, 60, 60)

    # 6. Technical Challenges & Engineering Solutions
    add_heading("6. Technical Challenges & Engineering Solutions", 1)
    challenges = [
        ("YouTube Datacenter IP Blocking", "YouTube blocks unauthenticated video downloads originating from AWS EC2 IP ranges with a 'Sign in to confirm you're not a bot' challenge. Added detection logic guiding users to extract via the 'Upload file' tab (using residential connection) and added automated cookies.txt support to yt-dlp."),
        ("Memory Constraints on t3.small", "Running Whisper AI and PyTorch concurrently with FastAPI in 2 GB RAM risked kernel OOM termination. Configured a 2 GB dedicated swap file on gp3 EBS during bootstrap and pre-cached model weights in the Docker build layer."),
        ("PowerShell 5.1 Character Encoding", "Windows PowerShell 5.1 defaulted to Windows-1252 ANSI decoding, failing on UTF-8 emojis and ampersands. Refactored all management scripts (stop.ps1, start.ps1, destroy.ps1) to use pure ASCII string literals and clean parameters."),
        ("State Loss on Instance Stop", "Stopping the EC2 instance releases ephemeral state. Implemented scripts/s3_sync.sh to automatically backup JSON transcripts to S3 at shutdown and restore them on boot, excluding bandwidth-heavy audio files.")
    ]
    for title_c, desc_c in challenges:
        p_c = doc.add_paragraph()
        r_tc = p_c.add_run(f"• {title_c}: ")
        r_tc.bold = True
        p_c.add_run(desc_c)

    # 7. Verification & Live Deployment Results
    add_heading("7. Verification & Live Deployment Results", 1)
    doc.add_paragraph("• AWS Stack Status: VideoAgentStack deployed successfully in 170.84 seconds (CREATE_COMPLETE).", style='List Bullet')
    doc.add_paragraph("• Public IP & Instance: Instance i-0c5e2c780148ce1bf running at 13.126.118.92.", style='List Bullet')
    doc.add_paragraph("• Live Health Check: GET http://13.126.118.92:8000/health returns HTTP 200 OK ({\"status\":\"ok\"}).", style='List Bullet')
    doc.add_paragraph("• Web UI: GET http://13.126.118.92:8000/ serves the production React SPA with single-server routing.", style='List Bullet')
    doc.add_paragraph("• Lifecycle Control: Verified scripts/stop.ps1 successfully transitions instance to stopped state, releasing IPv4 and compute billing.", style='List Bullet')

    # 8. Conclusion
    add_heading("8. Conclusion", 1)
    doc.add_paragraph(
        "Video Agent demonstrates the successful convergence of applied multimodal AI with cloud-native engineering on AWS. "
        "By utilizing Infrastructure as Code (AWS CDK), containerization, zero-secret parameter management, and cost-aware architectural patterns, "
        "the project provides an accessible, high-performance meeting intelligence assistant that satisfies real-world academic and production standards."
    )

    doc.save("c:/Users/Monish D/Desktop/SEM 5/Projects/Cloud/Video-Agent/PROJECT_REPORT.docx")
    print("Successfully generated PROJECT_REPORT.docx")

if __name__ == "__main__":
    create_report()
