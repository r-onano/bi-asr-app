import re
import math
from dataclasses import dataclass
from typing import Dict, Any, Tuple, List

# ----------------------------
# Manually hardcoded the Transcripts Directly from our 
# Supabase database tables here (predictions), along with 
# the full original scripts (ground truth)
# ----------------------------

TRIALS = {
    "trial_1_en_only": {
        "language": "en",
        "tier": 1,
        "reference": """Hey, I’m testing my speech transcription app right now. I’m going to speak like I normally do, not like I’m giving a presentation, so there might be pauses, restarts, and filler words. I want to see if the transcript still comes out clean. I’m also going to mention a few names and places, because that’s where transcription usually messes up. Later I’ll compare the output to this exact script and score it.
So here’s the situation. I’m texting a friend but I’m using voice instead of typing. I’m like, hey, are you free later today? I’m thinking we can grab food, maybe something quick, nothing fancy. If you’re tired we can just chill, but I want to get out of the house for a bit. Also, I might be a few minutes late because I have to finish something first.
By the way, remind me to bring my charger. My phone battery has been acting weird and I don’t trust it. If you see me forgetting, just call it out. Also, I’m trying to cut back on spending, so if we go somewhere, I’d rather not do the expensive spot. Even a simple sandwich place is fine.
Alright, I’m going to stop talking soon. One more thing, if you reply and you’re not sure on the time, just give me a window and I’ll make it work. Cool.""",
        "hypothesis": """Hey, I’m testing my speech transcription app right now. I’m going to speak like I normally do, not like I’m giving a presentation, so there might be pauses, restarts, and filler words. I want to see if the transcript still comes out clean. I’m also going to mention a few names and places, because that’s where transcription usually messes up. Later I’ll compare the output to this exact script and score it.
So here’s the situation. I’m texting a friend but I’m using voice instead of typing. I’m like, hey, are you free later today? I’m thinking we can grab food, maybe something quick, nothing fancy. If you’re tired we can just chill, but I want to get out of the house for a bit. Also, I might be a few minutes late because I have to finish something first.
By the way, remind me to bring my charger. My phone battery has been acting weird and I don’t trust it. If you see me forgetting, just call it out. Also, I’m trying to cut back on spending, so if we go somewhere, I’d rather not do the expensive spot. Even a simple sandwich place is fine.
Alright, I’m going to stop talking soon. One more thing, if you reply and you’re not sure on the time, just give me a window and I’ll make it work. Cool."""
    },

    "trial_2_zh_only": {
        "language": "zh",
        "tier": 1,
        "reference": """你好，我现在在测试一个语音转写应用。我会用平常聊天的方式来说，不会像念稿一样，所以可能会有停顿、重复，还有一些口头禅。我想看看在这种真实对话的情况下，转写出来的文字是不是还准确。之后我会把结果跟这段脚本对比并打分。
假设我在跟朋友语音聊天。我会说，今天你晚上有空吗？我想出去吃点东西，随便吃，不用太正式。如果你很累，我们也可以就近坐一会儿聊聊天。我可能会晚到几分钟，因为我还要先把一件事做完。
对了，你能提醒我带充电器吗？我手机电池最近很不稳定，我不太放心。如果你看到我忘了，就直接提醒我。还有，我最近想省点钱，所以别去太贵的地方。简单一点就行，比如面馆、饺子店，或者随便买点小吃。
最后，如果你不确定几点可以，就给我一个大概时间段，我来配合。好，那我就先说到这里。""",
        "hypothesis": """我现在在测试一个语音转写应用 我会用平常聊天的方式来说 不会像念稿一样 所以可能会有停顿、重复 还有一些口头禅 我想看看在这种真实对话的情况下 转写出来的文字是不是还准确 之后我会把结果跟这段转写 对比并打分 假设我在翻译 在跟朋友语音聊天 我会说 今天你晚上有空吗 我想出去吃点东西 随便吃不用太正式 如果你很累 我们也可以就静坐一会儿聊聊天 我可能会晚到几分钟 因为我还要把语音转写 转发给朋友 我可能会晚到几分钟 因为我还要把一件事做完 对了 你能提醒我在充电器吗 我手机电池最近很不稳定 我不太放心 如果你看到我忘了 就直接提醒我 还有 我最近想省点钱 所以别去太贵的地方 简单一点就行 比如面馆、饺子店 或者随便买点小吃 最后 如果你不确定几点可以 就给我一个大概时间段 我来配合 好 那我就先说到这里"""
    },

    "trial_3_sentence_switch": {
        "language": "mixed",
        "tier": 2,
        "reference": """Hey, I’m going to do a quick voice message like I’m talking to a friend.
你现在方便说话吗，我想跟你确认一下今天晚上的安排。
I might be running a little late because I have to finish something at home first.
如果你不想出门也没关系，我们可以改成明天或者周末。
I’m honestly just trying to get some fresh air and not stay inside all day.
我也不想花太多钱，随便吃点就行，不用去很贵的地方。
If you’re down, we can meet around seven, but I’m flexible.
你如果只能六点半或者七点半也可以，你告诉我一个时间段就行。
Also, remind me to bring my charger because my phone battery has been annoying lately.
对了，如果路上堵车我会提前跟你说，不会突然消失。
Alright, I’ll stop here, just text me back when you see this.
好，那就这样，回头见。""",
        "hypothesis": """[EN] Hey, I'm going to do a quick voice message like I'm talking to a friend. Hey, I'm going to do a quick voice message like I'm talking to a friend.
[ZH] 你現在方便說話嗎? 我想跟你確認一下今天晚上的安排。
[EN] I might be running a little late because I have to finish something at home first.
[ZH] 如果你不想出门也没关系,我们可以改成明天或者周末。
[EN] I'm honestly just trying to get some fresh air and not stay inside all day.
[ZH] 我也不想花太多钱,随便吃点就行,不用去很贵的地方。
[EN] If you're down, we can meet around 7, but I'm flexible.
[ZH] 你如果只能六點半或者七點半也可以做一個時間段就行。
[EN] Also, remind me to bring my charger because my phone battery has been annoying lately.
[ZH] 对了,如果路上堵车,我会提前跟你说,不会突然消失。
[EN]Alright. I'll stop here, just text me back when you see this.
[ZH] 最後,開頭見"""
    },

    "trial_4_phrase_switch": {
        "language": "mixed",
        "tier": 3,
        "reference": """Hey, quick question, 你现在方便吗, because I wanted to check something real fast. I’m thinking about grabbing food later, 不用太正式, just something simple and quick. If you’re tired, 我也理解, we can just do a short hangout or even reschedule.
So here’s my plan. I might be a little late, 因为我还有点事要处理, but I’ll keep you updated. If you want to pick the spot, 你来决定也行, as long as it’s not too expensive. I’m trying to save money this week, 所以别去太贵的地方, even though the nice places are tempting.
Also, I need a favor. If you remember, 你提醒我带充电器, because my phone has been dying randomly. I don’t want to be out and then suddenly my battery drops to zero. If you call and I don’t answer, 不是我故意的, it might just be my phone acting up.
Alright, let me know what time works. 如果你不确定, give me a window and I’ll adjust. Sounds good.""",
        "hypothesis": """[EN] Hey, quick question.
[ZH] 你現在方便嗎
[EN] I wanted to check something real fast. I'm thinking about grabbing food later.
[ZH] 不用太正式
[EN] us something simple and quick. If you're tired or
[ZH] We can just do a short
[EN] out or even reschedule. So here's my plan. I might be a little late.
[ZH] 因为我还有点事要处理
[EN] But I'll keep you updated. If you want to pick the spot, you know where to go.
[ZH]
[EN] not too expensive. I'm trying to save money this week for you.
[ZH] 比起太貴的地方
[EN] the nice places are campaigned. Also, I need a favor. If you remember...
[ZH] 你提醒我摘充電器"""
    },

    "trial_5_word_switch": {
        "language": "mixed",
        "tier": 3,
        "reference": """Hey, I’m sending a voice message because I’m testing my app. I’m going to talk like normal, and I’ll toss in a few Mandarin words like 今天 and then keep going. I want to see if the transcript can handle that without messing up the rest of the sentence.
So, are you free later? I’m trying to grab something quick, nothing fancy. 如果 you’re tired, that’s fine, we can just chill. I might be a few minutes late because I have to 解决 one thing first. Also, remind me to bring my 充电器, because my phone battery is really low.
I’m also trying to save money this week, so I’d rather not go to an expensive place. Even a 三明治 spot is fine. If you want to pick the place, go for it. 如果 you’re not sure on the time, just give me a window and I’ll work around it. If 交通 is bad, I’ll text you.
Alright, I’ll stop here. Just reply when you see this. 谢谢。""",
        "hypothesis": """[EN] Hey, I'm sending a voice message because I'm testing my app. I'm going to talk like normal, and I'll talk in a few minutes.
[ZH] I want to see if the transcript can handle that without messing up the rest of the sentence. So, are you free later? I'm trying to grab something quick, nothing fancy.
[EN] That's fine. We can just chill. I might be a few minutes late because I have to do Zoom.
[ZH] Also, remind me to bring my 充電器, because I need to charge my phone."""
    },

    "trial_5_part_2_zh_dominant": {
        "language": "mixed",
        "tier": 3,
        "reference": """你好，我现在继续做第五个测试的第二部分。这一段我会主要说中文句子，但是会在句子里插入一些 English 单词，而且这些插入会尽量分散，不会连续堆在一起。我想模拟那种真实聊天场景，比如我在跟朋友讲今天的安排，或者在路上临时协调时间。之后我会把转写结果跟这段脚本对比，看看系统能不能把中文主体抓稳，同时也把插入的 English 词识别出来。
我今天有点忙，不过晚上应该可以见面。你如果方便的话，我们可以七点左右在 campus 附近碰面，然后随便吃点东西，不用太正式。我不想花太多钱，所以别选太贵的 restaurant，简单一点就行，比如面馆或者快餐。要是你不想出门也没关系，我们也可以改成 tomorrow 或者周末。
对了，我手机电池最近很不稳定，你能提醒我带 charger 吗？我怕在外面突然没 battery，就会联系不到你。如果路上有 traffic，我会提前发 message，不会让你干等。还有，如果我中途突然安静了，不是我故意的，可能是我在走路或者 signal 不太好。
你也不用马上确定具体时间，如果你只能给我一个 time window 也可以，比如七点到八点之间，我来配合。好，那我先说到这里，等你回复。谢谢。""",
        "hypothesis": """[ZH] 您好,我现在继续做第五个测试的第二部分,这一段我会主要说中文句子,但是会在句子里插入一些英文字。
[EN] 而且这些插入会尽量分散,不会连续堆在一起。
[EN] the English 词识别出来
[ZH] 我今天有点忙,不过晚上应该可以见面。你如果方便的话,我们可以7点左右在KTV见面。
[EN] Thai food restaurant.
[ZH] 对了,我手机电池最近很不稳定,你能提醒我带charger吗?
[ZH] 如果路上有traffic 提前發Message"""
    }
}

# ----------------------------
# Optional libraries
# ----------------------------
# sacrebleu gives solid BLEU and chrF
# jiwer gives word error rate (WER), good for speech evaluation
try:
    import sacrebleu
except Exception:
    sacrebleu = None

try:
    from jiwer import wer as jiwer_wer
except Exception:
    jiwer_wer = None


# ----------------------------
# Text normalization
# ----------------------------
PUNCT_RE = re.compile(r"[^\w\s\u4e00-\u9fff]", flags=re.UNICODE)

def normalize_for_english(s: str) -> str:
    s = s.strip().lower()
    s = PUNCT_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def normalize_for_chinese_chars(s: str) -> str:
    # Keep only CJK chars, remove punctuation/spaces
    s = s.strip()
    chars = re.findall(r"[\u4e00-\u9fff]", s)
    return "".join(chars)

def normalize_keep_mixed(s: str) -> str:
    # For mixed trials, keep both English words and Chinese chars, remove punctuation noise
    s = s.strip().lower()
    s = re.sub(r"[“”‘’]", "", s)
    s = PUNCT_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ----------------------------
# Language extraction helpers
# ----------------------------
ENG_RE = re.compile(r"[a-zA-Z]+")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")

def extract_english_words(s: str) -> str:
    return " ".join(ENG_RE.findall(s.lower())).strip()

def extract_chinese_chars(s: str) -> str:
    return "".join(CJK_RE.findall(s)).strip()

def count_english_letters(s: str) -> int:
    return sum(1 for ch in s if ("a" <= ch.lower() <= "z"))

def count_cjk_chars(s: str) -> int:
    return len(CJK_RE.findall(s))


# ----------------------------
# Tagged transcript parsing
# ----------------------------
TAG_LINE_RE = re.compile(r"^\s*\[(EN|ZH)\]\s*(.*)\s*$")

@dataclass
class TaggedLine:
    tag: str   # "EN" or "ZH"
    text: str

def parse_tagged_lines(hyp: str) -> List[TaggedLine]:
    lines = []
    for raw in hyp.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        m = TAG_LINE_RE.match(raw)
        if m:
            tag = m.group(1)
            text = m.group(2).strip()
            lines.append(TaggedLine(tag=tag, text=text))
    return lines

def label_cleanliness(lines: List[TaggedLine]) -> Dict[str, float]:
    """
    For [EN] lines: percent of letters among (letters + cjk chars).
    For [ZH] lines: percent of cjk chars among (letters + cjk chars).
    Returns overall and per-tag.
    """
    def safe_ratio(num: int, den: int) -> float:
        return (num / den) if den > 0 else float("nan")

    stats = {
        "EN_purity_avg": float("nan"),
        "ZH_purity_avg": float("nan"),
        "overall_purity_avg": float("nan"),
        "tagged_lines": len(lines),
    }

    en_purities = []
    zh_purities = []
    all_purities = []

    for ln in lines:
        letters = count_english_letters(ln.text)
        cjk = count_cjk_chars(ln.text)
        den = letters + cjk

        if ln.tag == "EN":
            purity = safe_ratio(letters, den)
            en_purities.append(purity)
            all_purities.append(purity)
        elif ln.tag == "ZH":
            purity = safe_ratio(cjk, den)
            zh_purities.append(purity)
            all_purities.append(purity)

    def avg(xs: List[float]) -> float:
        xs = [x for x in xs if not math.isnan(x)]
        return sum(xs) / len(xs) if xs else float("nan")

    stats["EN_purity_avg"] = avg(en_purities)
    stats["ZH_purity_avg"] = avg(zh_purities)
    stats["overall_purity_avg"] = avg(all_purities)
    return stats


# ----------------------------
# Scoring
# ----------------------------
def bleu_score(ref: str, hyp: str) -> float:
    if sacrebleu is None:
        return float("nan")
    # sacrebleu expects list of references
    return sacrebleu.corpus_bleu([hyp], [[ref]]).score / 100.0

def chrf_score(ref: str, hyp: str) -> float:
    if sacrebleu is None:
        return float("nan")
    return sacrebleu.corpus_chrf([hyp], [[ref]]).score / 100.0

def word_error_rate(ref: str, hyp: str) -> float:
    if jiwer_wer is None:
        return float("nan")
    return float(jiwer_wer(ref, hyp))


def score_trial(reference: str, hypothesis: str, trial_key: str) -> Dict[str, Any]:
    # Base normalizations
    ref_mixed = normalize_keep_mixed(reference)
    hyp_mixed = normalize_keep_mixed(hypothesis)

    ref_en = normalize_for_english(extract_english_words(reference))
    hyp_en = normalize_for_english(extract_english_words(hypothesis))

    ref_zh = normalize_for_chinese_chars(reference)
    hyp_zh = normalize_for_chinese_chars(hypothesis)

    # Core metrics (full mixed)
    out = {
        "trial": trial_key,
        "bleu_mixed": bleu_score(ref_mixed, hyp_mixed),
        "chrf_mixed": chrf_score(ref_mixed, hyp_mixed),
        "wer_mixed": word_error_rate(ref_mixed, hyp_mixed),
        # Language-specific views
        "bleu_en_only": bleu_score(ref_en, hyp_en) if ref_en and hyp_en else float("nan"),
        "wer_en_only": word_error_rate(ref_en, hyp_en) if ref_en and hyp_en else float("nan"),
        "chrf_zh_only": chrf_score(ref_zh, hyp_zh) if ref_zh and hyp_zh else float("nan"),
    }

    # Extra for tagged hypotheses
    lines = parse_tagged_lines(hypothesis)
    if lines:
        purity = label_cleanliness(lines)
        out.update({
            "tagged_lines": purity["tagged_lines"],
            "EN_label_purity": purity["EN_purity_avg"],
            "ZH_label_purity": purity["ZH_purity_avg"],
            "overall_label_purity": purity["overall_purity_avg"],
        })
    else:
        out.update({
            "tagged_lines": 0,
            "EN_label_purity": float("nan"),
            "ZH_label_purity": float("nan"),
            "overall_label_purity": float("nan"),
        })

    return out


def fmt(x: float) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "NA"
    return f"{x:.4f}"


def main():
    if sacrebleu is None:
        print("Missing package: sacrebleu")
        print("Run: pip install sacrebleu")
        return
    if jiwer_wer is None:
        print("Missing package: jiwer (WER)")
        print("Run: pip install jiwer")
        print("Continuing without WER...")

    results = []
    for k, v in TRIALS.items():
        reference = v["reference"]
        hypothesis = v["hypothesis"]
        results.append(score_trial(reference, hypothesis, k))

    # Print a clean table
    headers = [
        "trial",
        "bleu_mixed",
        "chrf_mixed",
        "wer_mixed",
        "bleu_en_only",
        "wer_en_only",
        "chrf_zh_only",
        "overall_label_purity",
        "EN_label_purity",
        "ZH_label_purity",
        "tagged_lines",
    ]

    print("\nEvaluation Results\n")
    print(" | ".join(headers))
    print("-" * 140)
    for r in results:
        row = [
            r["trial"],
            fmt(r["bleu_mixed"]),
            fmt(r["chrf_mixed"]),
            fmt(r["wer_mixed"]),
            fmt(r["bleu_en_only"]),
            fmt(r["wer_en_only"]),
            fmt(r["chrf_zh_only"]),
            fmt(r["overall_label_purity"]),
            fmt(r["EN_label_purity"]),
            fmt(r["ZH_label_purity"]),
            str(r["tagged_lines"]),
        ]
        print(" | ".join(row))

    # Optional: save to CSV
    try:
        import csv
        with open("trial_scores.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            w.writeheader()
            for r in results:
                w.writerow({h: r.get(h, "") for h in headers})
        print("\nWrote: trial_scores.csv")
    except Exception as e:
        print("\nCould not write CSV:", e)


if __name__ == "__main__":
    main()
