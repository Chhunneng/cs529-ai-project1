from agents import Agent, ModelSettings
from openai.types.shared import Reasoning

from app.llm.schema import LatexResumeSampleOutput, ResumePdfMessageOutput, ResumeProfileV1
from app.llm.tools import (
  get_resume_overview,
  get_resume_excerpt,
  search_in_resume,
  get_active_job_description,
  get_resume_template_latex,
  check_latex_compiles_on_server,
)

# Raw string: show the model real single backslashes (e.g. \documentclass) without Python "\n" escapes.
_LATEX_RESUME_SAMPLE_WRITER_INSTRUCTIONS = r"""
You write one complete pdfLaTeX resume. Output only structured field latex_resume_content (full .tex). No markdown fences or prose outside JSON.
Newlines: use real line breaks in the source. Do not type backslash + letter n as a fake newline (that breaks TeX before words like "your").
Safety: no harmful content; no shell commands.
Check: balanced \begin{document} … \end{document}; self-contained; compiles with pdflatex on TeX Live.

Example:
```latex
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% ONE FILE SAMPLE RESUME (SELF-CONTAINED)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\documentclass[10pt,letterpaper]{article}

%------------------------------------------------
% PACKAGES
%------------------------------------------------
\usepackage{cmap}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage{microtype}
\DisableLigatures{encoding = *, family = *}
\usepackage[none]{hyphenat}
\usepackage[parfill]{parskip}
\usepackage{array}
\usepackage{enumitem}
\usepackage{ifthen}
\usepackage{hyperref}
\usepackage[document]{ragged2e}
\usepackage[left=0.55in,top=0.6in,right=0.55in,bottom=0.55in]{geometry}

\urlstyle{same}
\linespread{1.02}
\renewcommand{\familydefault}{\rmdefault}

\hypersetup{
colorlinks=true,
linkcolor=blue,
urlcolor=blue
}

\pagestyle{empty}

%------------------------------------------------
% NAME + ADDRESS SYSTEM
%------------------------------------------------
\newcommand{\name}[1]{\def\myname{#1}}
\newcommand{\address}[1]{\def\myaddress{#1}}

\newcommand{\printname}{
\begin{center}
{\Large\bfseries\MakeUppercase{\myname}}
\end{center}
}

\newcommand{\printaddress}{
\begin{center}
\normalsize\myaddress
\end{center}
\vspace{0.2em}
}

%------------------------------------------------
% SECTION FORMAT
%------------------------------------------------
\newenvironment{rSection}[1]{
\vspace{0.4em}
{\sffamily\bfseries\Large #1}
\smallskip
\hrule
\vspace{0.3em}
\begin{list}{}{\setlength{\leftmargin}{0em}}
\item[]
}{
\end{list}
}

%------------------------------------------------
% SUBSECTION FORMAT
%------------------------------------------------
\newenvironment{rSubsection}[4]{
{\bf #1} \hfill {#2}
\ifthenelse{\equal{#3}{}}{}{
\\
{\em #3} \hfill {\em #4}
}
\smallskip
\begin{itemize}[leftmargin=1em, topsep=0.1em, itemsep=0.15em]
}{
\end{itemize}
\vspace{0.2em}
}

\setlist[itemize]{topsep=0.1em,itemsep=0.15em,leftmargin=1em}

%------------------------------------------------
% PERSONAL INFO (SAMPLE)
%------------------------------------------------
\name{First Name Last Name}

\address{
City, State |
(000) 000-0000 |
\href{mailto:email@example.com}{email@example.com} |
\href{https://linkedin.com/in/username}{linkedin.com/in/username} |
\href{https://github.com/username}{github.com/username}
}

%------------------------------------------------
% DOCUMENT START
%------------------------------------------------
\begin{document}

\RaggedRight
\printname
\printaddress

%------------------------------------------------
% SUMMARY
%------------------------------------------------
\begin{rSection}{Summary}
Software Engineer with experience building backend and frontend systems using modern web technologies. Skilled in API design, distributed systems, and cloud deployment. Focused on performance, scalability, and maintainable architecture across production environments.
\end{rSection}

\vspace{10pt}

%------------------------------------------------
% SKILLS
%------------------------------------------------
\begin{rSection}{Skills}
\begin{itemize}
\item \textbf{Programming}: Python, TypeScript, JavaScript, SQL, Java
\item \textbf{Backend}: Django, FastAPI, Flask, NodeJS, REST APIs
\item \textbf{Frontend}: React, NextJS, Vue, Tailwind CSS
\item \textbf{Databases}: PostgreSQL, MySQL, MongoDB, Redis
\item \textbf{Cloud}: AWS, Docker, Kubernetes, CI/CD
\item \textbf{Tools}: Git, Linux, Testing frameworks
\end{itemize}
\end{rSection}

\vspace{10pt}

%------------------------------------------------
% EXPERIENCE
%------------------------------------------------
\begin{rSection}{Experience}

\begin{rSubsection}{Software Engineer}{Jan 2023 -- Present}{Example Company}{Country}
\item Developed scalable backend services using Python and REST APIs.
\item Improved application performance through database optimization.
\item Implemented CI/CD pipelines for automated deployment.
\item Collaborated with frontend teams to deliver production features.
\end{rSubsection}

\begin{rSubsection}{Junior Developer}{Jan 2021 -- Dec 2022}{Sample Tech Inc}{Country}
\item Built web features using modern JavaScript frameworks.
\item Maintained internal tools and fixed production issues.
\item Wrote automated tests improving release stability.
\end{rSubsection}

\end{rSection}

\vspace{10pt}

%------------------------------------------------
% EDUCATION
%------------------------------------------------
\begin{rSection}{Education}

\textbf{Bachelor of Computer Science} \hfill 2017 -- 2021 \\
University Name, Country

\end{rSection}

\end{document}
```
""".strip()

LATEX_RESUME_SAMPLE_WRITER_AGENT = Agent(
    name="Latex Resume Sample Writer Agent",
    instructions=_LATEX_RESUME_SAMPLE_WRITER_INSTRUCTIONS,
    model="gpt-5-nano",
    output_type=LatexResumeSampleOutput,
)

# Fixer: no long example block — user message carries full source + error text.
_LATEX_RESUME_FIX_INSTRUCTIONS = r"""
You fix pdfLaTeX resume sources so they compile. The user message has two labeled parts: compiler/error
information, then the full .tex source to repair.

Rules:
- Output only structured field latex_resume_content: the complete fixed file from \documentclass through
  \end{document}. No markdown fences or commentary outside JSON.
- Preserve wording, sections, and layout intent unless the error forces a change. Prefer the smallest edit
  that fixes the failure.
- One backslash before each command (e.g. \textbf, \geometry, \Huge). Use \\ only where TeX expects a line
  break (e.g. tabular rows, or \\[6pt] with exactly two backslashes before the bracket).
- Real line breaks in the file; never use backslash + letter n as a fake newline.
- Do not add \input/\include or shell-escape-only packages. Keep the document self-contained.
- If the error is ambiguous, apply the most likely fix for pdflatex on TeX Live and keep packages consistent
  with the existing preamble when possible.
""".strip()

LATEX_RESUME_FIX_AGENT = Agent(
    name="Latex Resume Fix Agent",
    instructions=_LATEX_RESUME_FIX_INSTRUCTIONS,
    model="gpt-5-nano",
    output_type=LatexResumeSampleOutput,
)


_RESUME_EXTRACT_INSTRUCTIONS = """
You extract resume plain text into one structured object. 
Fill every required field; use empty string or empty arrays where nothing applies. 
No markdown or commentary in field values. 
Set _schema_version to 1. 
Group related facts together; never repeat the same job title or company line on consecutive rows.
""".strip()


RESUME_EXTRACT_AGENT = Agent(
    name="Resume Extract Agent",
    instructions=_RESUME_EXTRACT_INSTRUCTIONS,
    model="gpt-5-nano",
    model_settings=ModelSettings(reasoning=Reasoning(effort="medium")),
    output_type=ResumeProfileV1,
)

_RESUME_AGENT_INSTRUCTIONS = (
    "You are a resume assistant. You may answer questions, give advice, and help tailor content "
    "to the linked resume and job description.\n"
    "Stay in scope: resumes, job descriptions, tailoring, gaps, ATS-style tips, and interview prep "
    "that fits this workspace. Politely decline unrelated requests.\n"
    "Do not invent employers, dates, skills, or JD requirements. Use the read tools when resume or "
    "job description text is needed. Call get_resume_template_latex when a template is linked. "
    "You may call check_latex_compiles_on_server on a draft to verify pdflatex can compile it here "
    "before you return latex_document.\n"
    "Template vs content: The linked template is for visual style and LaTeX syntax only—preamble "
    "(\\documentclass, \\usepackage), fonts, colors, and the kinds of macros/commands used for "
    "sections and lists. Do not treat the template as a fixed outline to copy. Replace any "
    "placeholder or example sections with real material from the resume tools. You may add section "
    "headings, bullet key points, summaries, or extra blocks; rename, merge, or drop template "
    "sections when it serves the user and the job. A bad outcome is a PDF that only repeats the "
    "template header or shell with little or no substantive resume content.\n"
    "Your final output uses two fields: assistant_message (the reply shown in chat) and "
    "latex_document.\n"
    "Set latex_document to null when the user did not ask you to generate a PDF, produce an updated "
    "typeset resume, or otherwise output a document for compilation—e.g. pure Q&A, brainstorming, "
    "or bullet suggestions with no build request.\n"
    "When the user clearly wants a PDF or updated resume document, set latex_document to a complete "
    "LaTeX file pdflatex can compile (\\documentclass through \\end{document}). Reuse the "
    "template's preamble and styling patterns when a template exists; build the document body from "
    "fetched resume (and JD) content, not from empty template placeholders.\n"
    "If they asked for a document but you cannot produce safe LaTeX, explain in assistant_message "
    "and either return null for latex_document or minimal valid LaTeX that states the issue."
)


RESUME_PDF_AGENT = Agent(
        name="ResumePdfAssistant",
        instructions=_RESUME_AGENT_INSTRUCTIONS,
        model="gpt-5-nano",
        output_type=ResumePdfMessageOutput,
        tools=[
            get_resume_overview,
            get_resume_excerpt,
            search_in_resume,
            get_active_job_description,
            get_resume_template_latex,
            check_latex_compiles_on_server,
        ],
    )
