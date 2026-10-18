"""
Plugin: saida_audio — switch Windows' sound output by voice.

  "coloca o volume no fone" / "deixa o som no fone"            → headset
  "coloca o volume na caixa de som" / "deixa o som na caixa"   → speakers

It changes the Windows DEFAULT playback device (same as picking it in the
sound flyout), so every app follows — and ATENA follows too, because she
tracks the Windows default output.

Edit the keyword lists below if your devices are renamed.
"""

import ctypes
from ctypes import POINTER, c_int, c_void_p, c_wchar_p

# Words that identify each device in its Windows name (lower-case).
FONE = ["realtek"]                                  # Realtek HD Audio 2nd output
CAIXA = ["lg ultragear", "amd high definition"]     # LG ULTRAGEAR (monitor speakers)

PLUGIN = {
    "name": "saida_audio",
    "description": (
        "Switches where the computer's sound comes out. target='fone' when the user "
        "says 'coloca/deixa o volume no fone', 'som no fone', 'muda para o headset'; "
        "target='caixa' for 'coloca/deixa o volume na caixa de som', 'som na caixa', "
        "'muda para as caixas'. Answer in one short sentence."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {"target": {"type": "STRING", "description": "fone | caixa"}},
        "required": ["target"],
    },
}


def _policy_config():
    import comtypes
    from comtypes import GUID, IUnknown, STDMETHOD, HRESULT, CoCreateInstance, CLSCTX_ALL

    class IPolicyConfig(IUnknown):
        _iid_ = GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")
        _methods_ = [
            STDMETHOD(HRESULT, "GetMixFormat", [c_wchar_p, POINTER(c_void_p)]),
            STDMETHOD(HRESULT, "GetDeviceFormat", [c_wchar_p, c_int, POINTER(c_void_p)]),
            STDMETHOD(HRESULT, "ResetDeviceFormat", [c_wchar_p]),
            STDMETHOD(HRESULT, "SetDeviceFormat", [c_wchar_p, c_void_p, c_void_p]),
            STDMETHOD(HRESULT, "GetProcessingPeriod", [c_wchar_p, c_int, c_void_p, c_void_p]),
            STDMETHOD(HRESULT, "SetProcessingPeriod", [c_wchar_p, c_void_p]),
            STDMETHOD(HRESULT, "GetShareMode", [c_wchar_p, c_void_p]),
            STDMETHOD(HRESULT, "SetShareMode", [c_wchar_p, c_void_p]),
            STDMETHOD(HRESULT, "GetPropertyValue", [c_wchar_p, c_void_p, c_void_p]),
            STDMETHOD(HRESULT, "SetPropertyValue", [c_wchar_p, c_void_p, c_void_p]),
            STDMETHOD(HRESULT, "SetDefaultEndpoint", [c_wchar_p, c_int]),
            STDMETHOD(HRESULT, "SetEndpointVisibility", [c_wchar_p, c_int]),
        ]

    try:
        comtypes.CoInitialize()
    except Exception:
        pass
    clsid = GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}")
    return CoCreateInstance(clsid, IPolicyConfig, CLSCTX_ALL)


def _render_devices():
    """[(id, name)] of active playback devices."""
    from pycaw.pycaw import AudioUtilities
    out = []
    for d in AudioUtilities.GetAllDevices():
        try:
            did = d.id or ""
            name = d.FriendlyName or ""
            state = str(getattr(d, "state", "")).lower()
            if did.startswith("{0.0.0.") and name and ("active" in state or state in ("1", "")):
                out.append((did, name))
        except Exception:
            continue
    return out


def run(parameters: dict, player=None, session_memory=None) -> str:
    target = (parameters.get("target") or "").strip().lower()
    keys = CAIXA if ("caixa" in target or "speaker" in target or "monitor" in target) else FONE
    label = "caixa de som" if keys is CAIXA else "fone"
    try:
        devices = _render_devices()
    except Exception as e:
        return f"Could not list audio devices: {e}"
    match = next(((i, n) for i, n in devices if any(k in n.lower() for k in keys)), None)
    if match is None:
        names = "; ".join(n for _, n in devices) or "none"
        return f"No output device matches '{label}'. Available: {names}"
    dev_id, dev_name = match
    try:
        pc = _policy_config()
        for role in (0, 1, 2):          # console, multimedia, communications
            pc.SetDefaultEndpoint(dev_id, role)
    except Exception as e:
        return f"Could not switch the output: {e}"
    if player:
        try:
            player.write_log(f"SYS: Saída de som → {dev_name}")
        except Exception:
            pass
    return f"Sound output switched to the {label} ({dev_name})."
