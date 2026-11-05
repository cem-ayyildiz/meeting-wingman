"""meeting-wingman translator: NLLB-200 through CTranslate2, on GPU when there is one, else CPU.

Uses only what faster-whisper already installs (ctranslate2, tokenizers, huggingface_hub).
The model is downloaded from the Hugging Face Hub on first use.

  WINGMAN_TRANSLATE_MODEL   CTranslate2 NLLB repo or local path
                            (default: 1.3B on GPU, 600M on CPU, both int8)
  WINGMAN_TRANSLATE_DEVICE  cuda | cpu | auto  (default: auto, with CPU fallback)

NLLB-200 is licensed CC-BY-NC-4.0 (non-commercial). Point WINGMAN_TRANSLATE_MODEL at another
CTranslate2 NLLB-compatible model if that does not fit your use.
"""
import os
import sys

import ctranslate2
from huggingface_hub import snapshot_download
from tokenizers import Tokenizer

GPU_MODEL = "OpenNMT/nllb-200-distilled-1.3B-ct2-int8"
CPU_MODEL = "JustFrederik/nllb-200-distilled-600M-ct2-int8"

# ISO 639-1 (what Whisper reports) -> NLLB code. Any NLLB code (e.g. "tur_Latn") is accepted as is.
NLLB = {
    "af": "afr_Latn", "am": "amh_Ethi", "ar": "arb_Arab", "az": "azj_Latn", "be": "bel_Cyrl",
    "bg": "bul_Cyrl", "bn": "ben_Beng", "bs": "bos_Latn", "ca": "cat_Latn", "cs": "ces_Latn",
    "cy": "cym_Latn", "da": "dan_Latn", "de": "deu_Latn", "el": "ell_Grek", "en": "eng_Latn",
    "es": "spa_Latn", "et": "est_Latn", "eu": "eus_Latn", "fa": "pes_Arab", "fi": "fin_Latn",
    "fr": "fra_Latn", "ga": "gle_Latn", "gl": "glg_Latn", "gu": "guj_Gujr", "he": "heb_Hebr",
    "hi": "hin_Deva", "hr": "hrv_Latn", "hu": "hun_Latn", "hy": "hye_Armn", "id": "ind_Latn",
    "is": "isl_Latn", "it": "ita_Latn", "ja": "jpn_Jpan", "ka": "kat_Geor", "kk": "kaz_Cyrl",
    "km": "khm_Khmr", "kn": "kan_Knda", "ko": "kor_Hang", "ky": "kir_Cyrl", "lo": "lao_Laoo",
    "lt": "lit_Latn", "lv": "lvs_Latn", "mk": "mkd_Cyrl", "ml": "mal_Mlym", "mn": "khk_Cyrl",
    "mr": "mar_Deva", "ms": "zsm_Latn", "my": "mya_Mymr", "ne": "npi_Deva", "nl": "nld_Latn",
    "no": "nob_Latn", "pa": "pan_Guru", "pl": "pol_Latn", "ps": "pbt_Arab", "pt": "por_Latn",
    "ro": "ron_Latn", "ru": "rus_Cyrl", "si": "sin_Sinh", "sk": "slk_Latn", "sl": "slv_Latn",
    "so": "som_Latn", "sq": "als_Latn", "sr": "srp_Cyrl", "sv": "swe_Latn", "sw": "swh_Latn",
    "ta": "tam_Taml", "te": "tel_Telu", "th": "tha_Thai", "tl": "tgl_Latn", "tr": "tur_Latn",
    "uk": "ukr_Cyrl", "ur": "urd_Arab", "uz": "uzn_Latn", "vi": "vie_Latn", "zh": "zho_Hans",
}


def nllb_code(lang):
    if not lang:
        return None
    return lang if "_" in lang else NLLB.get(lang.lower())


def _cuda():
    try:
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


class Translator:
    def __init__(self, target):
        self.target = target
        self.tgt = nllb_code(target)
        if not self.tgt:
            raise ValueError(f"unknown target language: {target} (use an ISO code like 'de' or an NLLB code like 'deu_Latn')")
        want = os.environ.get("WINGMAN_TRANSLATE_DEVICE", "auto")
        order = ["cuda", "cpu"] if (want == "cuda" or (want == "auto" and _cuda())) else ["cpu"]
        last = None
        for dev in order:   # GPU first; on any failure (no CUDA, out of memory) fall back to CPU
            name = os.environ.get("WINGMAN_TRANSLATE_MODEL") or (GPU_MODEL if dev == "cuda" else CPU_MODEL)
            try:
                path = name if os.path.isdir(name) else snapshot_download(name)
                self.model = ctranslate2.Translator(path, device=dev,
                                                    compute_type="int8_float16" if dev == "cuda" else "int8")
                self.tok = Tokenizer.from_file(os.path.join(path, "tokenizer.json"))
                self.device, self.name = dev, name
                return
            except Exception as e:
                last = e
                print(f"translator: {name} on {dev} failed: {e}", file=sys.stderr, flush=True)
        raise RuntimeError(f"translator could not load: {last}")

    def __call__(self, text, source):
        src = nllb_code(source)
        if not text or not src or src == self.tgt:
            return None
        toks = [src] + self.tok.encode(text, add_special_tokens=False).tokens + ["</s>"]
        # A short line can send NLLB into a loop ("no, no, no, ..."): cap the output relative to
        # the input and penalise repeats.
        res = self.model.translate_batch([toks], target_prefix=[[self.tgt]], beam_size=2,
                                         max_decoding_length=min(256, 2 * len(toks) + 16),
                                         repetition_penalty=1.2, no_repeat_ngram_size=4)
        out = [t for t in res[0].hypotheses[0] if t != self.tgt]
        return self.tok.decode([self.tok.token_to_id(t) for t in out]).strip()
