"""Tests for pdflatex log summarization."""

from app.services.latex_compile import compile_failure_detail, summarize_pdflatex_log


def test_summarize_extracts_geometry_doubled_backslash_and_hint() -> None:
    log = """numitem/enumitem.sty)
(/usr/share/texlive/texmf-dist/tex/latex/parskip/parskip.sty)

! LaTeX Error: There's no line here to end.

See the LaTeX manual or LaTeX Companion for explanation.
Type  H <return>  for immediate help.
 ...                                              
                                                  
l.9 \\\\g
       eometry{left=1in,right=1in,top=0.8in,bottom=0.8in}
!  ==> Fatal error occurred, no output PDF file produced!
"""
    d = summarize_pdflatex_log(log)
    assert d["latex_error"] == "LaTeX Error: There's no line here to end."
    assert d["line_number"] == 9
    assert d["line_context"] is not None
    assert "eometry" in d["line_context"]
    assert d["hint"] is not None
    assert "backslash" in (d["hint"] or "").lower()
    assert "log_tail" in d


def test_compile_failure_detail_puts_everything_in_message() -> None:
    log = """! LaTeX Error: There's no line here to end.
l.21 {bad}
"""
    d = compile_failure_detail(log)
    assert d["message"].startswith("LaTeX compile failed")
    assert "There's no line here to end" in d["message"]
    assert d["line_number"] == 21
    assert isinstance(d["log_tail"], str)
    assert len(d["log_tail"]) <= 3500 + 10


def test_summarize_undefined_control_sequence() -> None:
    log = """! Undefined control sequence.
l.2 \\foo
"""
    d = summarize_pdflatex_log(log)
    assert "Undefined" in (d.get("latex_error") or "")
