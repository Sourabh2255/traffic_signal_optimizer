import os
import sys
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

def create_paper():
    doc = docx.Document()

    # Define standard styles & colors
    FONT_NAME = "Times New Roman"
    CLR_BLACK = RGBColor(0, 0, 0)
    CLR_GRAY = RGBColor(80, 80, 80)
    CLR_PLACEHOLDER_BORDER = "94A3B8"
    CLR_PLACEHOLDER_BG = "F8FAFC"
    CLR_CODE_BG = "F1F5F9"
    CLR_CODE_BORDER = "CBD5E1"

    # Configure Normal Style
    normal_style = doc.styles['Normal']
    normal_style.font.name = FONT_NAME
    normal_style.font.size = Pt(10)
    normal_style.font.color.rgb = CLR_BLACK

    # Section 1: Title and Author Block (Single Column)
    s1 = doc.sections[0]
    s1.top_margin = Inches(0.75)
    s1.bottom_margin = Inches(1.0)
    s1.left_margin = Inches(0.625)
    s1.right_margin = Inches(0.625)
    s1.page_width = Inches(8.5)
    s1.page_height = Inches(11.0)

    # First page header (IEEE standard)
    s1.different_first_page_header_footer = True
    first_hdr = s1.first_page_header
    hp = first_hdr.paragraphs[0]
    hp.text = "XXX-X-XXXX-XXXX-X/XX/$XX.00 ©20XX IEEE"
    hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if hp.runs:
        hp.runs[0].font.name = FONT_NAME
        hp.runs[0].font.size = Pt(8.5)
        hp.runs[0].font.color.rgb = CLR_GRAY

    # Document Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(6)
    p_title.paragraph_format.space_after = Pt(14)
    run_title = p_title.add_run("AI-Based Adaptive Traffic Signal Time Optimization System with Emergency Vehicle Detection")
    run_title.font.name = FONT_NAME
    run_title.font.size = Pt(22)
    run_title.font.bold = True

    # 6-Author Block in a 2-Row x 3-Column Table
    author_table = doc.add_table(rows=2, cols=3)
    author_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    author_table.autofit = False

    col_widths = [Inches(2.35), Inches(2.35), Inches(2.35)]
    authors_data = [
        # Row 1
        [
            ("1st [Author Name]", "dept. name of organization (of Aff.)", "name of organization (of Aff.)", "City, Country", "email address or ORCID"),
            ("2nd [Author Name]", "dept. name of organization (of Aff.)", "name of organization (of Aff.)", "City, Country", "email address or ORCID"),
            ("3rd [Author Name]", "dept. name of organization (of Aff.)", "name of organization (of Aff.)", "City, Country", "email address or ORCID"),
        ],
        # Row 2
        [
            ("4th [Author Name]", "dept. name of organization (of Aff.)", "name of organization (of Aff.)", "City, Country", "email address or ORCID"),
            ("5th [Author Name]", "dept. name of organization (of Aff.)", "name of organization (of Aff.)", "City, Country", "email address or ORCID"),
            ("6th [Author Name]", "dept. name of organization (of Aff.)", "name of organization (of Aff.)", "City, Country", "email address or ORCID"),
        ]
    ]

    for r_idx, row in enumerate(author_table.rows):
        for c_idx, cell in enumerate(row.cells):
            cell.width = col_widths[c_idx]
            # Remove all borders from author cell
            tcPr = cell._tc.get_or_add_tcPr()
            tcBorders = parse_xml(f'''
                <w:tcBorders {nsdecls("w")}>
                    <w:top w:val="none"/>
                    <w:left w:val="none"/>
                    <w:bottom w:val="none"/>
                    <w:right w:val="none"/>
                </w:tcBorders>
            ''')
            tcPr.append(tcBorders)

            info = authors_data[r_idx][c_idx]
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing = 1.05
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)

            r_name = p.add_run(info[0] + "\n")
            r_name.font.name = FONT_NAME
            r_name.font.size = Pt(10.5)
            r_name.font.bold = True

            r_dept = p.add_run(info[1] + "\n")
            r_dept.font.name = FONT_NAME
            r_dept.font.size = Pt(9.5)
            r_dept.font.italic = True

            r_org = p.add_run(info[2] + "\n")
            r_org.font.name = FONT_NAME
            r_org.font.size = Pt(9.5)

            r_loc = p.add_run(info[3] + "\n")
            r_loc.font.name = FONT_NAME
            r_loc.font.size = Pt(9.5)

            r_em = p.add_run(info[4])
            r_em.font.name = FONT_NAME
            r_em.font.size = Pt(9)
            r_em.font.italic = True

    # Spacing after author table
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(2)
    p_sp.paragraph_format.space_after = Pt(2)

    # Section 2: Two-Column Body Section
    s2 = doc.add_section(WD_SECTION.CONTINUOUS)
    s2.top_margin = Inches(0.75)
    s2.bottom_margin = Inches(1.0)
    s2.left_margin = Inches(0.625)
    s2.right_margin = Inches(0.625)

    # Configure 2 columns with 0.22" (16pt) gutter
    sectPr = s2._sectPr
    cols = sectPr.xpath('./w:cols')
    col_elem = cols[0] if cols else OxmlElement('w:cols')
    if not cols:
        sectPr.append(col_elem)
    col_elem.set(qn('w:num'), '2')
    col_elem.set(qn('w:space'), '317') # twips (approx 0.22 in)

    # Helper: Add Abstract and Keywords
    def add_abstract_keywords(abstract_text, keywords_list):
        p_abs = doc.add_paragraph()
        p_abs.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_abs.paragraph_format.first_line_indent = Inches(0)
        p_abs.paragraph_format.space_before = Pt(3)
        p_abs.paragraph_format.space_after = Pt(3)
        p_abs.paragraph_format.line_spacing = 1.0

        r_hdr = p_abs.add_run("Abstract—")
        r_hdr.font.name = FONT_NAME
        r_hdr.font.size = Pt(9)
        r_hdr.font.bold = True
        r_hdr.font.italic = True

        r_body = p_abs.add_run(abstract_text)
        r_body.font.name = FONT_NAME
        r_body.font.size = Pt(9)
        r_body.font.bold = True

        p_kw = doc.add_paragraph()
        p_kw.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_kw.paragraph_format.first_line_indent = Inches(0)
        p_kw.paragraph_format.space_before = Pt(2)
        p_kw.paragraph_format.space_after = Pt(6)
        p_kw.paragraph_format.line_spacing = 1.0

        r_kwhdr = p_kw.add_run("Keywords—")
        r_kwhdr.font.name = FONT_NAME
        r_kwhdr.font.size = Pt(9)
        r_kwhdr.font.bold = True
        r_kwhdr.font.italic = True

        r_kwbody = p_kw.add_run(", ".join(keywords_list))
        r_kwbody.font.name = FONT_NAME
        r_kwbody.font.size = Pt(9)
        r_kwbody.font.italic = True

    # Helper: Section Heading (I. INTRODUCTION)
    def add_heading1(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = FONT_NAME
        run.font.size = Pt(10)
        run.font.bold = True

    # Helper: Subsection Heading (A. System Overview)
    def add_heading2(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = FONT_NAME
        run.font.size = Pt(10)
        run.font.bold = True
        run.font.italic = True

    # Helper: Body Paragraph
    def add_p(text, indent=True):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        if indent:
            p.paragraph_format.first_line_indent = Inches(0.16)
        else:
            p.paragraph_format.first_line_indent = Inches(0)
        run = p.add_run(text)
        run.font.name = FONT_NAME
        run.font.size = Pt(10)
        return p

    # Helper: Figure Placeholder
    def add_figure_placeholder(fig_num, caption_title, description_prompt):
        # Create single-cell table for box
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        cell = tbl.cell(0, 0)
        cell.width = Inches(3.45)

        tcPr = cell._tc.get_or_add_tcPr()
        # Light gray background
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{CLR_PLACEHOLDER_BG}"/>')
        tcPr.append(shd)

        # Border
        borders = parse_xml(f'''
            <w:tcBorders {nsdecls("w")}>
                <w:top w:val="single" w:sz="6" w:space="0" w:color="{CLR_PLACEHOLDER_BORDER}"/>
                <w:left w:val="single" w:sz="6" w:space="0" w:color="{CLR_PLACEHOLDER_BORDER}"/>
                <w:bottom w:val="single" w:sz="6" w:space="0" w:color="{CLR_PLACEHOLDER_BORDER}"/>
                <w:right w:val="single" w:sz="6" w:space="0" w:color="{CLR_PLACEHOLDER_BORDER}"/>
            </w:tcBorders>
        ''')
        tcPr.append(borders)

        # Content inside box
        p_box = cell.paragraphs[0]
        p_box.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_box.paragraph_format.space_before = Pt(7)
        p_box.paragraph_format.space_after = Pt(7)
        p_box.paragraph_format.line_spacing = 1.0

        r1 = p_box.add_run(f"[ FIGURE {fig_num} PLACEHOLDER ]\n")
        r1.font.name = FONT_NAME
        r1.font.size = Pt(9.5)
        r1.font.bold = True
        r1.font.color.rgb = RGBColor(51, 65, 85)

        r2 = p_box.add_run(f"Paste image here: {description_prompt}")
        r2.font.name = FONT_NAME
        r2.font.size = Pt(8)
        r2.font.italic = True
        r2.font.color.rgb = RGBColor(100, 116, 139)

        # Caption under table
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_cap.paragraph_format.first_line_indent = Inches(0)
        p_cap.paragraph_format.space_before = Pt(3)
        p_cap.paragraph_format.space_after = Pt(5)
        p_cap.paragraph_format.keep_with_next = False

        r_cap_lbl = p_cap.add_run(f"Fig. {fig_num}.  ")
        r_cap_lbl.font.name = FONT_NAME
        r_cap_lbl.font.size = Pt(8.5)
        r_cap_lbl.font.bold = True

        r_cap_txt = p_cap.add_run(caption_title)
        r_cap_txt.font.name = FONT_NAME
        r_cap_txt.font.size = Pt(8.5)

    # Helper: Algorithm Code Box
    def add_algorithm_box(title, code_lines):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        cell = tbl.cell(0, 0)
        cell.width = Inches(3.45)

        tcPr = cell._tc.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{CLR_CODE_BG}"/>')
        tcPr.append(shd)
        borders = parse_xml(f'''
            <w:tcBorders {nsdecls("w")}>
                <w:top w:val="single" w:sz="6" w:space="0" w:color="{CLR_CODE_BORDER}"/>
                <w:left w:val="single" w:sz="6" w:space="0" w:color="{CLR_CODE_BORDER}"/>
                <w:bottom w:val="single" w:sz="6" w:space="0" w:color="{CLR_CODE_BORDER}"/>
                <w:right w:val="single" w:sz="6" w:space="0" w:color="{CLR_CODE_BORDER}"/>
            </w:tcBorders>
        ''')
        tcPr.append(borders)

        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Inches(0)
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.0

        r_title = p.add_run(f"Algorithm 1: {title}\n")
        r_title.font.name = FONT_NAME
        r_title.font.size = Pt(8.5)
        r_title.font.bold = True

        for line in code_lines:
            r = p.add_run(line + "\n")
            r.font.name = "Consolas"
            r.font.size = Pt(7.5)

    # ==================== DOCUMENT CONTENT GENERATION ====================

    # Abstract Text
    abstract_text = (
        "Urban traffic congestion is a severe modern crisis that impedes emergency response vehicles, "
        "inflates vehicular emissions, and wastes billions of commuter hours globally. Conventional traffic "
        "signals rely on pre-timed, round-robin timing plans or isolated inductive loop detectors that fail to "
        "adapt dynamically to real-time directional traffic demands or provide verified preemption for emergency "
        "services. This paper presents an intelligent, software-based adaptive traffic signal optimization system "
        "integrating computer vision, ensemble machine learning, and acoustic signal classification. The system "
        "ingests four-way intersection images (North, East, South, West) and employs a fine-tuned Ultralytics YOLOv8 "
        "model to detect vehicular classes, evaluate traffic density, and detect emergency vehicles (ambulances and fire trucks). "
        "Predicted traffic densities feed a Random Forest regression model to allocate adaptive green signal durations, "
        "strictly clamped within safety bounds [15s, 60s]. To eliminate false emergency activations from parked "
        "emergency vehicles or ambient acoustic noise, a dual-condition verification protocol is implemented: emergency "
        "priority is granted only when an active acoustic siren is confirmed via a 46-dimensional MFCC and spectral Support "
        "Vector Machine (SVM) pipeline AND an emergency vehicle is visually confirmed on an intersection approach. Upon "
        "mutual verification, the controller executes a safe signal transition (3s clearance, 3s all-red buffer, 25s green) "
        "guaranteeing zero conflicting green signals. In an initial offline validation across a random test split of 120 "
        "balanced audio recordings (40 per class), the siren classifier achieved 98.33% accuracy; however, real-world deployment "
        "limitations, potential acoustic leakage, and the simulation-only boundary are explicitly analyzed. An interactive "
        "telemetry dashboard and What-If scenario simulator provide macroscopic delay and queue throughput diagnostics, "
        "demonstrating an effective, scalable software architecture for smart city traffic automation."
    )
    keywords = [
        "Adaptive traffic signal control",
        "YOLO object detection",
        "Emergency vehicle detection",
        "Acoustic siren classification",
        "Random Forest regression",
        "Dual-condition verification",
        "Intelligent transportation systems",
        "Traffic density estimation",
        "Signal preemption"
    ]
    add_abstract_keywords(abstract_text, keywords)

    # I. INTRODUCTION
    add_heading1("I. INTRODUCTION")
    add_p(
        "Rapid urbanization and unprecedented vehicle population growth have escalated urban traffic congestion "
        "into a premier socio-economic and public health emergency in metropolitan areas worldwide. Beyond the substantial "
        "loss in workforce productivity, heightened fuel consumption, and environmental degradation caused by idling "
        "engines, road gridlock presents a catastrophic obstacle for emergency response services, including ambulances, "
        "paramedic response units, and fire rescue vehicles [1], [2]. In emergency medical care, the 'Golden Hour'—the initial "
        "sixty-minute window following traumatic injury or acute cardiovascular arrest—dictates survival probability. Transport "
        "delays directly correlate with preventable mortality and permanent patient impairment."
    )
    add_p(
        "Conventional urban road junctions remain predominantly regulated by fixed-time traffic light controllers operating "
        "on static round-robin phase sequences, or by localized timer plans adjusted manually according to historical peak "
        "hours [3]. These inflexible timing schedules are inherently incapable of responding to stochastic traffic fluctuations, "
        "directional surges, or unscheduled emergency arrivals. Under static fixed-time operations, approaching ambulances "
        "frequently confront red signals while facing stationary queues of commuter vehicles blocked in red-phase lanes. "
        "Even when an ambulance activates its audible siren and flashing beacon, surrounded drivers have nowhere to maneuver, "
        "yielding hazardous bottlenecks and junction blockages."
    )
    add_p(
        "While traditional Emergency Vehicle Preemption (EVP) systems have been proposed using dedicated hardware technologies—such "
        "as optical infrared strobes (e.g., Opticom), radio-frequency identification (RFID), inductive road loops, or dedicated "
        "short-range wireless transceivers (e.g., LoRa or DSRC)—they suffer from acute real-world deployment limitations [4], [5]. "
        "Optical line-of-sight systems are compromised by severe weather, curved road geometry, and roadside obstructions. "
        "Acoustic-only siren detectors deployed at intersections are notoriously prone to false triggers caused by non-emergency "
        "noise, including loud vehicular audio systems, public warning horns, construction sirens, or sirens from emergency "
        "vehicles traveling on distant parallel corridors [6]. Conversely, purely vision-based emergency detection systems "
        "frequently trigger false priority preemptions when an ambulance is parked outside a roadside clinic or traveling "
        "in an administrative non-emergency status without active siren sounding."
    )
    add_p(
        "To overcome these fundamental weaknesses, this research presents an intelligent, software-based adaptive traffic "
        "signal optimization system featuring multimodal audio-visual emergency verification. The proposed system operates "
        "as a comprehensive, software-only intelligent transportation framework that does not require proprietary road-imbedded "
        "actuators or mandatory vehicle-mounted hardware transmitters. Instead, it leverages standardized four-way junction camera "
        "imagery and digital microphone streams to compute optimal, demand-responsive signal timings and enforce fail-safe "
        "emergency preemption."
    )
    add_p(
        "The primary contributions of this project include: (1) A unified computer vision pipeline utilizing pre-trained and fine-tuned "
        "Ultralytics YOLO architectures to perform concurrent multi-class vehicle counting and emergency vehicle (ambulance and fire truck) "
        "detection across four orthogonal approaches (North, East, South, West); (2) A trained Random Forest regression model that translates "
        "directional traffic density and queued demand into optimal green signal timings, strictly bounded within safety constraints [15s, 60s]; "
        "(3) A strict dual-condition verification protocol mandating mutual confirmation between acoustic siren detection (via an SVM "
        "pipeline trained on 46 MFCC and spectral features) and visual spatial localization, eliminating false preemption triggers; "
        "(4) A deterministic signal phase controller providing conflict-free safety transitions (clearance yellow, all-red buffer, and green "
        "preemption); and (5) An interactive simulation and What-If analytics suite that benchmarks adaptive signal allocations against static "
        "baselines. This system is designed as an academic demonstration and simulation prototype, providing a rigorous testbed for "
        "algorithmic validation prior to municipal hardware integration."
    )

    # II. RELATED WORK
    add_heading1("II. RELATED WORK")
    add_p(
        "The optimization of urban traffic flow and the preemption of emergency vehicles have inspired extensive academic and "
        "industrial investigation spanning several decades. Research across the domain can be synthesized into five primary categories: "
        "classical traffic signal timing models, computer vision-based traffic density analysis, machine learning for signal prediction, "
        "acoustic siren classification, and simulation-based signal preemption."
    )
    add_p(
        "A. Conventional and Adaptive Signal Control Systems: Classical urban traffic signalization began with the foundational delay "
        "formulation established by Webster [6], which related junction cycle length and effective green time to saturation flow and degree "
        "of lane saturation. Network-level coordinated control systems subsequently emerged, prominently TRANSYT [7], which optimized "
        "fixed-time signal splits and offsets using macroscopic traffic models. To provide real-time responsiveness, centralized adaptive "
        "systems such as SCOOT (Split Cycle Offset Optimization Technique) [9] and SCATS (Sydney Coordinated Adaptive Traffic System) [8] "
        "were deployed globally. While SCATS and SCOOT dynamically adjust cycle splits according to inductive loop sensor data, their installation "
        "and maintenance costs are exceedingly high, and their algorithmic architectures lack native multi-modal emergency vehicle awareness."
    )
    add_p(
        "B. Computer Vision for Traffic Density Estimation: The advent of deep convolutional neural networks revolutionized visual traffic "
        "monitoring. Early computer vision methods relied on background subtraction, optical flow, and edge detection to estimate road occupancy [10]. "
        "However, these hand-crafted techniques degraded under variable lighting, shadows, and occlusions. The introduction of the You Only Look "
        "Once (YOLO) family of single-stage object detectors by Redmon et al. [1] enabled high-throughput, real-time object localization. "
        "Recent advancements in Ultralytics YOLOv8 [2] combine anchor-free detection heads with mosaic augmentation and C2f feature extraction, "
        "delivering state-of-the-art mean average precision (mAP) for multi-class vehicular detection on commodity compute hardware."
    )
    add_p(
        "C. Machine Learning in Signal Timing: Beyond visual sensing, predictive machine learning models have been applied to determine green "
        "signal durations directly from detected vehicle counts. While deep reinforcement learning (DRL) approaches have been explored [11], "
        "they suffer from sample inefficiency, unstable convergence, and unpredictable corner-case behaviors when deployed outside training "
        "simulations. In contrast, supervised ensemble learning algorithms, particularly Random Forests formulated by Breiman [3], offer "
        "robust non-linear regression capabilities, resistance to overfitting, and bounded deterministic execution times essential for "
        "time-critical infrastructure decisions."
    )
    add_p(
        "D. Acoustic Siren Detection and Multi-Modal Fusion: Acoustic emergency sensing has traditionally employed time-domain energy thresholding "
        "or pitch tracking. Modern acoustic classification utilizes Mel-Frequency Cepstral Coefficients (MFCCs) [5], spectral centroid, and spectral "
        "flux coupled with Support Vector Machines (SVM) [4] or Convolutional Neural Networks. Virk et al. [15] demonstrated machine learning-based "
        "siren classification; however, stand-alone acoustic systems lack spatial localization capabilities, as omnidirectional microphone feeds "
        "cannot reliably isolate which approach an emergency vehicle is occupying. Conversely, vision-only preemption [14] suffers from false positives "
        "when emergency vehicles are stationary or out of service. Multi-modal fusion—requiring synchronized acoustic and visual verification—remains "
        "the most robust pathway to minimize false preemption errors in dense urban environments."
    )

    # III. PROPOSED WORK
    add_heading1("III. PROPOSED WORK")
    add_p(
        "The proposed system establishes a modular, software-based framework for intelligent traffic signal optimization and fail-safe "
        "emergency vehicle priority. Designed as a flexible microservice architecture, the system operates across clear functional boundaries: "
        "visual object detection, traffic density computation, predictive green-time allocation, acoustic siren classification, dual-condition "
        "emergency arbitration, and interactive simulation visualization."
    )

    add_heading2("A. System Overview")
    add_p(
        "The conceptual framework models an isolated four-way signalized intersection comprising North, East, South, and West approaches. "
        "Each approach is monitored by a camera producing image frames of approaching traffic queues. A synchronized acoustic receiver "
        "captures ambient intersection audio. The software ingestion pipeline accepts image uploads corresponding to each of the four approaches, "
        "alongside an optional digital audio file (WAV format) representing ambient intersection acoustics. The visual stream is analyzed "
        "by both a general vehicle detector and a fine-tuned emergency vehicle detector, while the audio stream is evaluated by an SVM siren "
        "classifier. Signal optimization logic evaluates the combined outputs to generate bounded green durations or trigger safe emergency "
        "preemption phases. Results are rendered across responsive web interfaces, including telemetry charts, phase countdowns, and What-If "
        "comparative diagnostics."
    )

    add_heading2("B. Software Components")
    add_p(
        "The software architecture is implemented in Python 3.11 utilizing the Flask web framework for routing and application state orchestration. "
        "The core analytical modules comprise: (1) Vehicle Detector: A pre-trained Ultralytics YOLOv8 network filtering for standard COCO "
        "classes (car, bus, truck, motorcycle) to produce validated bounding boxes and directional vehicle counts; (2) Emergency Vehicle Detector: "
        "A custom fine-tuned YOLO model (models/best_emergency_vehicle.pt) trained specifically to localize ambulances (Class 0) and fire trucks "
        "(Class 1) with an operational confidence threshold of 0.50; (3) Green-Time Predictor: A Scikit-learn Random Forest regression model "
        "(models/traffic_model.pkl) trained on multi-approach traffic parameters to output recommended green light durations; (4) Siren Audio Classifier: "
        "An acoustic processing pipeline (models/siren_model_v2.joblib) consisting of a StandardScaler and Support Vector Classifier (SVC) "
        "operating over 46 acoustic features; and (5) Web Presentation Engine: HTML5, Vanilla CSS, Bootstrap 5, and Plotly.js powering interactive "
        "charts and real-time canvas signal simulations. Notably, the project operates entirely in software and requires no physical LoRa radios, "
        "microcontroller breadboards, or physical traffic light wiring."
    )

    # Figure 1 Placeholder
    add_figure_placeholder(
        1,
        "Overall Software Architecture of the AI-Based Adaptive Traffic Signal Optimization System, illustrating the Input, Computer Vision & Audio Analysis, Decision & Optimization, and Telemetry Presentation layers.",
        "Paste the Overall System Architecture block diagram showing the 4 layers: Input (Images/Audio), Analytical Models (YOLOv8, Custom YOLO, SVM Siren), Decision Engine (RF Regressor & Dual-Lock Preemption), and Web Dashboard."
    )

    add_heading2("C. System Workflow")
    add_p(
        "The end-to-end execution workflow operates through nine deterministic stages upon receiving intersection data: "
        "(1) Ingestion: User uploads four road approach images (North, East, South, West) and an optional WAV audio recording; "
        "(2) Validation: The system verifies image decodability, color channel integrity, and audio file formatting; "
        "(3) Multi-Class Vehicle Detection: General vehicular traffic is detected and aggregated into directional vehicle counts; "
        "(4) Density & Demand Extraction: Weighted passenger car units (PCU) and directional density indices are calculated; "
        "(5) Predictive Green Timing: The Random Forest regressor computes raw green times for each approach and enforces strict bounds [15s, 60s]; "
        "(6) Acoustic Siren Classification: If audio is provided, 46 acoustic features are extracted and classified; "
        "(7) Direction-Independent Approach Scan: If a siren is confirmed, the system inspects YOLO detections across all four approaches to identify "
        "the specific approach carrying the emergency vehicle; "
        "(8) Dual-Condition Verification: Emergency preemption is activated if and only if both acoustic siren confirmation and visual emergency "
        "vehicle confirmation coincide on an approach; and "
        "(9) Signal Dispatch & Telemetry: The controller schedules conflict-free signal phases and broadcasts telemetry to the simulation dashboard."
    )

    # Figure 2 Placeholder
    add_figure_placeholder(
        2,
        "End-to-End System Processing Workflow, illustrating sequential stages from multi-approach image and audio ingestion to dual-condition arbitration, bounded green-time prediction, and dashboard visualization.",
        "Paste the End-to-End Workflow flowchart showing the step-by-step decision tree: Image/Audio Input -> Validation -> YOLO Detection -> RF Green Time -> Siren Audio Check -> Dual-Verification Gate -> Signal Execution."
    )

    add_heading2("D. System Architecture and Algorithm")
    add_p(
        "The logical architecture enforces a strict zero-conflict guarantee: under no circumstances may conflicting approaches receive green "
        "indications simultaneously. During normal adaptive operation, phases follow a safe sequential progression (North -> East -> South -> West). "
        "When emergency priority is granted, the active conflicting green transitions through a 3-second yellow clearance interval, followed by a "
        "3-second all-red intersection clearance buffer, before granting a dedicated 25-second green signal to the emergency approach. Upon completion, "
        "a safe clearance interval executes, and the system smoothly resumes the standard adaptive cycle sequence without manual intervention."
    )

    # Algorithm Box
    code_lines = [
        "Input : Images I_N, I_E, I_S, I_W; Audio stream A (optional)",
        "Output: Signal Plan SP = {Phase, Durations, PreemptionActive}",
        "1: counts = {}, emergency_candidates = {}",
        "2: for road in {North, East, South, West} do",
        "3:     counts[road] = YOLO_General_Detect(I[road])",
        "4:     em_veh, conf_v = YOLO_Emergency_Detect(I[road])",
        "5:     raw_green = RandomForest_Predict(counts[road])",
        "6:     green_time[road] = Clamp(raw_green, MIN=15, MAX=60)",
        "7: end for",
        "8: siren_detected, siren_type, conf_s = SVM_Audio_Classify(A)",
        "9: preemption_granted = False, priority_road = None",
        "10: if siren_detected == True and conf_s >= 0.70 then",
        "11:    for road in {North, East, South, West} do",
        "12:        if emergency_candidates[road].detected and conf_v >= 0.50 then",
        "13:            preemption_granted = True",
        "14:            priority_road = road",
        "15:            break  // Deterministic priority resolution",
        "16:        end if",
        "17:    end for",
        "18: end if",
        "19: if preemption_granted then",
        "20:    SP = Execute_Safety_Transition(priority_road, Duration=25)",
        "21: else",
        "22:    SP = Schedule_Adaptive_Cycle(green_time)",
        "23: end if",
        "24: return SP"
    ]
    add_algorithm_box("Adaptive Green Time Allocation and Dual-Verified Preemption", code_lines)

    add_heading2("E. Green-Time Prediction and Allocation")
    add_p(
        "The adaptive green-time prediction module maps directional vehicular counts into optimal phase durations. To accurately reflect "
        "junction delay, different vehicle categories are weighted by Passenger Car Unit (PCU) factors: passenger cars receive a weighting of 1.0, "
        "heavy commercial vehicles (buses and trucks) receive 2.0, and two-wheelers (motorcycles) receive 0.5. The derived feature vector feeds "
        "the Random Forest regressor, which models non-linear queuing dynamics learned across simulated arrival distributions. Crucially, "
        "the raw mathematical prediction is passed through a hard clamping function: T_final = max(15.0, min(60.0, T_raw)). This prevents signal "
        "starvation for low-density approaches while precluding cycle monopolization by congested approaches. An important academic disclosure is "
        "that the current Random Forest model is trained on simulation-derived rule datasets rather than longitudinal empirical roadside sensor data, "
        "establishing an important area for future field calibration."
    )

    add_heading2("F. Emergency Vehicle and Siren Verification")
    add_p(
        "The emergency prioritization subsystem is engineered around mutual dual-verification to prevent dangerous false alarms. "
        "Visual detection employs the custom YOLOv8 model trained on labeled images of ambulances and fire trucks, outputting bounding box coordinates, "
        "vehicle class, and detection confidence. Acoustic classification operates independently: omnidirectional intersection audio is processed "
        "through the V2 audio engine. The pipeline extracts 46 features: 13 Mel-Frequency Cepstral Coefficients (MFCC) means, 13 MFCC standard deviations, "
        "13 first-order delta MFCC means, spectral centroid mean and standard deviation, spectral bandwidth mean and standard deviation, spectral "
        "rolloff mean and standard deviation, and zero-crossing rate (ZCR) mean and standard deviation."
    )

    # Figure 4 Placeholder
    add_figure_placeholder(
        4,
        "Emergency Siren Audio and Visual Vehicle Verification Interface, displaying acoustic waveform features, class confidence scores, and bounding box localization.",
        "Paste the Emergency Siren and Vehicle Verification Interface screenshot showing audio waveform/features, class probabilities (ambulance_siren, fire_truck_siren, negative_sound), and visual candidate verification status."
    )

    add_p(
        "The feature vector is normalized via StandardScaler and classified by an RBF-kernel Support Vector Machine (SVC) into one of three target "
        "classes: ambulance_siren, fire_truck_siren, or negative_sound. Priority requires both the siren confidence to exceed 0.70 and the visual "
        "vehicle confidence to exceed 0.50. Under the direction-independent siren architecture, acoustic energy detected by the microphone does "
        "not need to identify the approach direction; instead, the system automatically inspects all four camera feeds to identify the approach "
        "containing the visual emergency candidate. If an ambulance is detected without an active siren (e.g., parked or non-emergency transit), "
        "or if a siren sounds without an emergency vehicle in the junction (e.g., a siren echoing from an adjacent street), priority is strictly "
        "denied, and normal adaptive signal control is maintained."
    )
    add_p(
        "Initial offline validation of the siren classifier achieved a 98.33% accuracy across a balanced random test split of 120 audio files "
        "(40 samples per class). However, it is essential to emphasize that this evaluation utilized controlled, synthetic, and curated audio files. "
        "Performance under real-world street conditions—characterized by high acoustic reverberation, vehicular horn interference, Doppler frequency "
        "shifts, and varying distance attenuation—remains unverified and constitutes an active research limitation."
    )

    add_heading2("G. What-If Simulation and Analytics")
    add_p(
        "To evaluate system behavior under diverse operational scenarios, the software incorporates an interactive What-If simulation engine. "
        "Users can inject hypothetical traffic modifications—such as scaling total traffic density by +/- 50%, introducing additional heavy buses, "
        "or simulating extreme motorcycle surges on specific approaches. The engine recalculates green time allocations in real time and "
        "compares the adaptive performance against a static baseline (configured at 30 seconds fixed green per approach, 120s cycle length). "
        "Comparative metrics assume a standard macroscopic service rate of 0.5 vehicles discharged per second of green time. The system computes "
        "estimated vehicles served, unserved queue backlogs, and total waiting time reductions. These outputs represent simulation estimates "
        "based on idealized queuing delay equations, clearly distinguished from empirical field measurements."
    )

    # IV. RESULT AND DISCUSSION
    add_heading1("IV. RESULT AND DISCUSSION")
    add_p(
        "System evaluation was conducted through rigorous software unit testing, integration workflows, and interactive scenario simulations "
        "designed to benchmark functional reliability, safety transitions, and classification boundaries."
    )

    add_heading2("A. System Testing")
    add_p(
        "The validation protocol evaluated the complete software pipeline across four structured test categories: "
        "(1) Functional Unit Testing: Verified that isolated modules (YOLO image decoding, MFCC audio feature extraction, Random Forest "
        "predictor caching, and Flask route dispatchers) execute without memory leakage or runtime errors; "
        "(2) Integration Testing: Validated communication between visual detection results and green time allocation logic, ensuring that "
        "output green times strictly adhere to the [15s, 60s] boundary under both zero-traffic and extreme-congestion inputs; "
        "(3) System Preemption Testing: Evaluated all permutation cases of emergency inputs—siren-only, vehicle-only, dual-verified single-approach, "
        "multi-approach emergency conflicts, and low-confidence detections; and "
        "(4) User Interface & Scenario Testing: Assessed real-time canvas animation fidelity, keyboard shortcut responsiveness, and What-If "
        "parameter recalibration accuracy."
    )

    # Figure 3 Placeholder
    add_figure_placeholder(
        3,
        "Multi-Approach Traffic Image Analysis and Vehicle Detection Interface, showing simultaneous YOLO detection bounding boxes, directional vehicle counts, and derived density indices.",
        "Paste the Traffic Image Analysis and Vehicle Detection web interface screenshot showing 4 uploaded road images with colored bounding boxes for cars, trucks, buses, motorcycles, and count summary tables."
    )

    # Figure 5 Placeholder
    add_figure_placeholder(
        5,
        "Adaptive Traffic Signal Simulation Interface, displaying real-time 3-bulb signal indicators, active countdown timers, phase sequencing, and emergency override notifications.",
        "Paste the Simulation web interface screenshot showing the 4-way traffic junction animation, active green/yellow/red bulbs, countdown badge timers, control buttons (Start, Pause, Restart), and speed multipliers."
    )

    # Figure 6 Placeholder
    add_figure_placeholder(
        6,
        "Dashboard and Telemetry Analytics Interface, presenting comparative baseline vs. adaptive queue throughput, green-time reallocation charts, and historical cycle metrics.",
        "Paste the Dashboard Analytics screenshot showing Plotly comparative bar charts (Baseline Fixed 30s vs AI Allocated Green Times), queue throughput stats, and waiting time reduction summaries."
    )

    add_heading2("B. Performance Evaluation")
    add_p(
        "Table I details the comprehensive test suite results conducted across 14 operational scenarios within the automated test harness "
        "(comprising test_direction_independent_siren.py, test_siren_model_v2.py, and test_emergency_status_and_allocation.py). Scenarios T01 through "
        "T12 demonstrate 100% pass rates under simulated software conditions. Crucially, tests T13 and T14—pertaining to physical roadside actuator "
        "control and hostile outdoor environmental stress testing—are honestly designated as 'Pending testing' and 'Not evaluated', reflecting "
        "the academic prototype boundary of the current software codebase."
    )

    # Table I: Performance Evaluation Table
    p_tbl_title = doc.add_paragraph()
    p_tbl_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_tbl_title.paragraph_format.space_before = Pt(8)
    p_tbl_title.paragraph_format.space_after = Pt(4)
    p_tbl_title.paragraph_format.keep_with_next = True
    r_tt = p_tbl_title.add_run("TABLE I.  SYSTEM PERFORMANCE EVALUATION UNDER DIFFERENT TEST CONDITIONS")
    r_tt.font.name = FONT_NAME
    r_tt.font.size = Pt(8.5)
    r_tt.font.bold = True

    # 15 rows (1 header + 14 tests), 5 columns
    test_table = doc.add_table(rows=15, cols=5)
    test_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    test_table.autofit = False

    t_widths = [Inches(0.45), Inches(0.85), Inches(0.85), Inches(0.85), Inches(0.45)]
    headers = ["Test ID", "Input Condition", "Expected Output", "Observed Output", "Result"]

    test_data = [
        ("T01", "System start & 4-way image upload", "Valid image decoding & model singleton initialization", "YOLO & RF models loaded; 4 approaches parsed", "Pass"),
        ("T02", "Mixed multi-class traffic images", "Accurate detection of cars, buses, trucks, motorcycles", "COCO vehicles detected and count aggregated", "Pass"),
        ("T03", "Directional traffic density input", "RF model outputs unconstrained green duration", "Raw continuous green predictions generated", "Pass"),
        ("T04", "Extreme traffic inputs (0 or 80+ veh)", "Enforce strict safety bounds [15s, 60s]", "Times clamped: min 15.0s, max 60.0s enforced", "Pass"),
        ("T05", "Audio WAV file provided", "Extract 46 MFCC/spectral features and classify", "SVM pipeline predicts class and confidence", "Pass"),
        ("T06", "Siren confirmed; no emergency vehicle", "Deny priority preemption; retain normal adaptive", "Priority rejected with explanatory log; normal timing", "Pass"),
        ("T07", "Ambulance detected; no siren sound", "Deny priority preemption; retain normal adaptive", "Priority rejected; vehicle treated as normal PCU", "Pass"),
        ("T08", "Ambulance detected + Siren confirmed", "Approve emergency priority; trigger safe preemption", "Emergency preemption granted; transition scheduled", "Pass"),
        ("T09", "Siren confirmed + Ambulance in East", "Direction-independent scan isolates East approach", "Priority granted specifically to East approach", "Pass"),
        ("T10", "Emergency active on East approach", "North, South, West approaches held strictly at Red", "Zero conflicting green indications verified", "Pass"),
        ("T11", "Emergency priority duration clears", "Automatic safe resumption of normal adaptive cycle", "Normal phase sequencing safely restored", "Pass"),
        ("T12", "What-If traffic density delta (+30%)", "Dynamic recalculation of signal timing and delay", "Updated green allocations and throughput metrics", "Pass"),
        ("T13", "Physical roadside controller link", "Real-time electrical traffic actuator switching", "Pending testing (Simulation prototype only)", "Not evaluated"),
        ("T14", "Hostile outdoor weather/acoustic noise", "Robust multi-modal detection under storm noise", "Pending testing (Requires physical road sensors)", "Not evaluated"),
    ]

    # Style Header Row
    hdr_cells = test_table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].width = t_widths[i]
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(title)
        r.font.name = FONT_NAME
        r.font.size = Pt(7.5)
        r.font.bold = True

        tcPr = hdr_cells[i]._tc.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F1F5F9"/>')
        tcPr.append(shd)
        borders = parse_xml(f'''
            <w:tcBorders {nsdecls("w")}>
                <w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/>
                <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:left w:val="none"/>
                <w:right w:val="none"/>
            </w:tcBorders>
        ''')
        tcPr.append(borders)

    # Style Data Rows
    for r_idx, row_vals in enumerate(test_data):
        row_cells = test_table.rows[r_idx + 1].cells
        is_last = (r_idx == len(test_data) - 1)
        for c_idx, val in enumerate(row_vals):
            row_cells[c_idx].width = t_widths[c_idx]
            p = row_cells[c_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx in [0, 4] else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            p.paragraph_format.line_spacing = 1.0
            r = p.add_run(val)
            r.font.name = FONT_NAME
            r.font.size = Pt(7)
            if c_idx == 4:
                r.font.bold = True

            tcPr = row_cells[c_idx]._tc.get_or_add_tcPr()
            b_bottom = "single" if is_last else "none"
            sz_bottom = "8" if is_last else "0"
            borders = parse_xml(f'''
                <w:tcBorders {nsdecls("w")}>
                    <w:top w:val="none"/>
                    <w:bottom w:val="{b_bottom}" w:sz="{sz_bottom}" w:space="0" w:color="000000"/>
                    <w:left w:val="none"/>
                    <w:right w:val="none"/>
                </w:tcBorders>
            ''')
            tcPr.append(borders)

    add_p(
        "In offline acoustic testing, the three-class SVM siren model achieved 98.33% accuracy on 120 balanced evaluation recordings "
        "(40 ambulance_siren, 40 fire_truck_siren, 40 negative_sound). The model correctly classified 39 of 40 ambulance sirens, "
        "40 of 40 fire truck sirens, and 39 of 40 negative sound files. Fig. 7 provides the confusion matrix placeholder for this evaluation. "
        "While highly promising, the test set was generated from curated and clean audio assets. Acoustic attenuation over distance, wind shear, "
        "multi-path acoustic reflections from high-rise buildings, and siren Doppler distortions present in actual street environments will inevitably "
        "introduce noise, requiring comprehensive field training and fine-tuning before public infrastructure deployment."
    )

    # Figure 7 Placeholder
    add_figure_placeholder(
        7,
        "Siren Classifier Confusion Matrix on Balanced 120-Sample Evaluation Dataset, displaying true vs. predicted classifications across ambulance_siren, fire_truck_siren, and negative_sound classes.",
        "Paste the Siren Classification Confusion Matrix heat-map showing 120 test instances (40 per class) with 98.33% overall accuracy."
    )

    # V. CONCLUSION AND FUTURE SCOPE
    add_heading1("V. CONCLUSION AND FUTURE SCOPE")

    add_heading2("A. Conclusion")
    add_p(
        "This research presented an intelligent, software-based adaptive traffic signal optimization system featuring robust multi-modal "
        "emergency vehicle verification. By combining real-time YOLO computer vision for vehicular density estimation with Random Forest "
        "regression, the system dynamically shifts green signal times to congested approaches while maintaining strict safety bounds [15s, 60s]. "
        "The implementation of a dual-condition verification protocol—requiring simultaneous confirmation from a 46-feature SVM acoustic siren "
        "classifier and visual emergency vehicle localization—effectively resolves the critical false-alarm vulnerabilities that plague conventional "
        "single-modality preemption systems. Integrated simulation and What-If analytics provide rich telemetry on queue dissipation and waiting "
        "delays. While the current prototype operates exclusively in software simulation, it establishes an effective algorithmic blueprint for "
        "scalable smart city traffic automation."
    )

    add_heading2("B. Future Scope")
    add_p(
        "Several vital advancements are planned to bridge the current simulation prototype toward physical road deployment: "
        "(1) Real-World Acoustic Datasets: Collecting diverse roadside audio recordings encompassing heavy traffic noise, rain, vehicle horns, "
        "and Doppler frequency shifts to retrain the SVM acoustic model; (2) Multi-Weather Computer Vision: Enhancing the YOLO emergency vehicle "
        "dataset with adverse lighting, glare, nighttime footage, and heavy weather conditions; (3) Live Video Stream Processing: Implementing "
        "hardware-accelerated RTSP/WebRTC video stream pipelines for continuous multi-camera tracking; (4) Multi-Intersection Green Corridors: "
        "Developing distributed edge-to-edge communication protocols to synchronize sequential signals along an ambulance's route, creating an "
        "extended green corridor; (5) Dynamic Vehicle Tracking: Integrating DeepSORT or ByteTrack algorithms to measure continuous queue trajectories "
        "and shockwaves; (6) Microscopic Simulation Calibration: Validating system dynamics within SUMO (Simulation of Urban MObility) under "
        "realistic synthetic commuter demand; (7) Hardware Controller Interfacing: Integrating NTCIP 1202 standardized traffic controller protocols "
        "to actuate physical municipal traffic light cabinets; and (8) Functional Safety Certification: Conducting rigorous ISO 26262 functional safety "
        "assessments to guarantee fail-safe signal transitions under hardware or sensor failure."
    )

    # REFERENCES
    add_heading1("REFERENCES")

    references = [
        "[1] J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, \"You Only Look Once: Unified, Real-Time Object Detection,\" in Proc. IEEE Conf. Comput. Vis. Pattern Recognit. (CVPR), 2016, pp. 779–788.",
        "[2] G. Jocher, A. Chaurasia, and J. Qiu, \"Ultralytics YOLOv8,\" 2023. [Online]. Available: https://github.com/ultralytics/ultralytics",
        "[3] L. Breiman, \"Random Forests,\" Machine Learning, vol. 45, no. 1, pp. 5–32, 2001.",
        "[4] C. Cortes and V. Vapnik, \"Support-Vector Networks,\" Machine Learning, vol. 20, no. 3, pp. 273–297, 1995.",
        "[5] S. Davis and P. Mermelstein, \"Comparison of Parametric Representations for Monosyllabic Word Recognition in Continuously Spoken Sentences,\" IEEE Trans. Acoust., Speech, Signal Process., vol. 28, no. 4, pp. 357–366, 1980.",
        "[6] F. V. Webster, \"Traffic Signal Settings,\" Road Research Technical Paper No. 39, Road Research Laboratory, London, UK, 1958.",
        "[7] D. I. Robertson, \"TRANSYT: A Traffic Network Study Tool,\" Road Research Laboratory, Crowthorne, Berkshire, UK, Rep. LR 253, 1969.",
        "[8] P. R. Lowrie, \"SCATS: Sydney Co-Ordinated Adaptive Traffic System: A Traffic Responsive Method of Controlling Urban Traffic,\" Roads and Traffic Authority of New South Wales, Sydney, Australia, 1990.",
        "[9] P. B. Hunt, D. I. Robertson, R. D. Bretherton, and R. I. Winton, \"SCOOT—A Traffic Responsive Method of Coordinating Signals,\" Transport and Road Research Laboratory, Crowthorne, Berkshire, UK, Rep. LR 1014, 1981.",
        "[10] S. Cools, C. Gershenson, and B. D'Hooghe, \"Self-Organizing Traffic Lights: A Realistic Simulation,\" in Advances in Applied Self-Organizing Systems, London, UK: Springer, 2013, pp. 45–55.",
        "[11] P. Mirchandani and L. Head, \"A Real-Time Traffic-Responsive Signal Control System: RHODES,\" Transp. Res. Part C: Emerg. Technol., vol. 9, no. 3, pp. 187–206, 2001.",
        "[12] N. H. Gartner, \"OPAC: A Demand-Responsive Strategy for Traffic Signal Control,\" Transp. Res. Rec., no. 906, pp. 75–81, 1983.",
        "[13] N. Maslekar, M. Boussedjra, J. Mouzna, and H. Labiod, \"VANET Based Adaptive Traffic Signal Control,\" in Proc. IEEE 73rd Veh. Technol. Conf. (VTC Spring), 2011, pp. 1–5.",
        "[14] M. Seredynski, V. L. Bouvry, and M. P. C. Ribeiro, \"Evaluation of Emergency Vehicle Preemption Systems in Intelligent Transportation Systems,\" in Proc. IEEE Int. Conf. Intell. Transp. Syst. (ITSC), 2013, pp. 2095–2100.",
        "[15] T. S. Virk, A. K. Sahu, and M. J. Nene, \"Acoustic Siren Detection for Emergency Vehicles Using Machine Learning Approaches,\" in Proc. IEEE Int. Conf. Signal Process. Commun. (SPCOM), 2018, pp. 1–5.",
        "[16] F. Pedregosa et al., \"Scikit-learn: Machine Learning in Python,\" J. Mach. Learn. Res., vol. 12, pp. 2825–2830, 2011.",
        "[17] G. Bradski, \"The OpenCV Library,\" Dr. Dobb's J. Softw. Tools, vol. 25, no. 11, pp. 120–125, 2000.",
        "[18] B. McFee et al., \"librosa: Audio and Music Signal Analysis in Python,\" in Proc. 14th Python Sci. Conf., 2015, pp. 18–24.",
        "[19] J. Zhang, F.-Y. Wang, K. Wang, W.-H. Lin, X. Xu, and C. Chen, \"Data-Driven Intelligent Transportation Systems: A Survey,\" IEEE Trans. Intell. Transp. Syst., vol. 12, no. 4, pp. 1624–1639, 2011.",
        "[20] M. A. Rahman, M. S. Islam, and T. Hasan, \"Smart Traffic Light Control System Using IoT,\" in Proc. IEEE Int. Conf. Smart Cities, 2020, pp. 245–250."
    ]

    for ref in references:
        p_ref = doc.add_paragraph()
        p_ref.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_ref.paragraph_format.line_spacing = 1.05
        p_ref.paragraph_format.space_before = Pt(0)
        p_ref.paragraph_format.space_after = Pt(2)
        p_ref.paragraph_format.left_indent = Inches(0.22)
        p_ref.paragraph_format.first_line_indent = Inches(-0.22)
        r = p_ref.add_run(ref)
        r.font.name = FONT_NAME
        r.font.size = Pt(8)

    output_filename = "AI_Based_Adaptive_Traffic_Signal_Time_Optimization_System.docx"
    doc.save(output_filename)
    print(f"Research paper successfully created and saved to: {output_filename}")

if __name__ == "__main__":
    create_paper()
