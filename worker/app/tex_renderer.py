from __future__ import annotations

from pathlib import Path

from app.resume_fill_models import ResumeFillAtsV1


def _latex_escape(s: str) -> str:
    out = []
    for ch in s:
        if ch in "\\&%$#_{}~^":
            out.append(
                {
                    "\\": r"\textbackslash{}",
                    "&": r"\&",
                    "%": r"\%",
                    "$": r"\$",
                    "#": r"\#",
                    "_": r"\_",
                    "{": r"\{",
                    "}": r"\}",
                    "~": r"\textasciitilde{}",
                    "^": r"\textasciicircum{}",
                }[ch]
            )
        else:
            out.append(ch)
    return "".join(out)


def _itemize(lines: list[str]) -> str:
    if not lines:
        return r"\begin{itemize}\item (none)\end{itemize}"
    body = "".join(rf"\item {_latex_escape(x)}" for x in lines)
    return rf"\begin{{itemize}}{body}\end{{itemize}}"


def render_ats_v1(*, template_tex: str, data: ResumeFillAtsV1) -> str:
    h = data.header
    links = " \\quad | \\quad ".join(
        rf"\href{{{_latex_escape(x.url)}}}{{{_latex_escape(x.label)}}}" for x in h.links
    )
    if not links:
        links = ""

    exp_blocks: list[str] = []
    for ex in data.experience:
        bullets = _itemize(ex.bullets)
        t = _latex_escape(ex.title)
        co = _latex_escape(ex.company)
        loc = _latex_escape(ex.location)
        st = _latex_escape(ex.start)
        en = _latex_escape(ex.end)
        exp_blocks.append(
            rf"\textbf{{{t}}} \hfill {st} -- {en}\\"
            rf"\textit{{{co}}} \hfill {loc}\\"
            rf"{bullets}\vspace{{6pt}}"
        )
    experience = "\n".join(exp_blocks) if exp_blocks else "(none)"

    edu_blocks: list[str] = []
    for ed in data.education:
        sch = _latex_escape(ed.school)
        deg = _latex_escape(ed.degree)
        st = _latex_escape(ed.start)
        en = _latex_escape(ed.end)
        edu_blocks.append(rf"\textbf{{{sch}}} \hfill {st} -- {en}\\" rf"\textit{{{deg}}}")
    education = "\n".join(edu_blocks) if edu_blocks else "(none)"

    skills = _itemize(data.skills)

    out = template_tex
    out = out.replace("<<FULL_NAME>>", _latex_escape(h.full_name))
    out = out.replace("<<EMAIL>>", _latex_escape(h.email))
    out = out.replace("<<PHONE>>", _latex_escape(h.phone))
    out = out.replace("<<LOCATION>>", _latex_escape(h.location))
    out = out.replace("<<LINKS>>", links)
    out = out.replace("<<SUMMARY>>", _latex_escape(data.summary))
    out = out.replace("<<EXPERIENCE>>", experience)
    out = out.replace("<<EDUCATION>>", education)
    out = out.replace("<<SKILLS>>", skills)
    return out


def load_template_tex(base_dir: Path, storage_path: str) -> str:
    path = base_dir / storage_path / "template.tex"
    return path.read_text(encoding="utf-8")
