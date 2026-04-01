import re
import shlex


def parse_pdf_command(text: str) -> dict:
    """
    Parse /pdfm or /qbm command arguments.
    
    Examples:
      /pdfm -p 1-10 -c @channel -m "Title" -t 0 custom prompt here
      /qbm -p 5-15 -m "My Quiz"
      /pdfm -p 1-5 -m "Test" -i some custom prompt
    
    Returns dict:
      {
        "page_start": int,
        "page_end": int,
        "channel": str or None,
        "title": str,
        "topic_id": int or None,
        "include_image": bool,
        "prompt": str,
        "mode": "pdfm" or "qbm"
      }
    """
    result = {
        "page_start": 1,
        "page_end": 10,
        "channel": None,
        "title": "Quiz",
        "topic_id": None,
        "include_image": False,
        "prompt": "",
        "mode": "pdfm",
        "error": None,
    }

    # Detect mode
    text = text.strip()
    if text.lower().startswith("/qbm"):
        result["mode"] = "qbm"
        text = text[4:].strip()
    elif text.lower().startswith("/pdfm"):
        result["mode"] = "pdfm"
        text = text[5:].strip()

    # Extract -p page range
    p_match = re.search(r'-p\s+(\d+)[-–](\d+)', text)
    if p_match:
        result["page_start"] = int(p_match.group(1))
        result["page_end"] = int(p_match.group(2))
        text = text[:p_match.start()] + text[p_match.end():]
    else:
        # Single page: -p 5
        p_single = re.search(r'-p\s+(\d+)', text)
        if p_single:
            result["page_start"] = int(p_single.group(1))
            result["page_end"] = int(p_single.group(1))
            text = text[:p_single.start()] + text[p_single.end():]
        else:
            result["error"] = "❌ `-p` (page range) দিতে হবে। যেমন: `-p 1-10`"

    # Extract -c channel
    c_match = re.search(r'-c\s+(@\S+|-\d+|\d+)', text)
    if c_match:
        result["channel"] = c_match.group(1)
        text = text[:c_match.start()] + text[c_match.end():]

    # Extract -m "title"
    m_match = re.search(r'-m\s+"([^"]+)"', text)
    if not m_match:
        m_match = re.search(r"-m\s+'([^']+)'", text)
    if not m_match:
        m_match = re.search(r'-m\s+(\S+)', text)
    if m_match:
        result["title"] = m_match.group(1)
        text = text[:m_match.start()] + text[m_match.end():]
    else:
        result["error"] = (result.get("error") or "") + "\n❌ `-m \"Title\"` দিতে হবে।"

    # Extract -t topic_id
    t_match = re.search(r'-t\s+(\d+)', text)
    if t_match:
        result["topic_id"] = int(t_match.group(1))
        text = text[:t_match.start()] + text[t_match.end():]

    # Extract -i flag
    if re.search(r'\s-i\b', text) or text.startswith('-i'):
        result["include_image"] = True
        text = re.sub(r'\s*-i\b', '', text)

    # Remaining text = custom prompt
    result["prompt"] = text.strip()

    return result
