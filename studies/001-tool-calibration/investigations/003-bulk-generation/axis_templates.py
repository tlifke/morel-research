"""Per-tool axis-to-prompt templates for bulk generation (Phase A3).

Each tool exposes a generator function that takes a random source
(`rng`) and an axis-value dict and returns a tuple of:

    (user_prompt_warranted, user_prompt_trivial, tags, sub_domain,
     difficulty_warranted, difficulty_trivial, reasoning_warranted,
     reasoning_trivial, frequency_class, human_feasibility_warranted,
     human_feasibility_trivial)

For Type B pairs we reuse the warranted prompt across both halves
(the spec maps it onto with-tool and no-tools system prompts).

Anti-leakage rule (enforced by construction): tool-trivial halves
never contain the keywords "calculator", "compute", "search",
"lookup". For calculator we use ``"What is ..."`` framing for
trivials; "Compute X" is permitted on the warranted halves only
because the user_prompt itself is the probe, not a leak.

Wait — re-reading the brief: "calculator", "compute", "search",
"lookup" must NOT appear in user_prompts of records where the model
is expected to NOT call (tool_trivial halves). So trivials must avoid
those keywords. Warranted halves may use them freely (and the A1
seeds do).
"""

from __future__ import annotations

import math
import random
from typing import Any

# ----- shared helpers --------------------------------------------------


DIFFICULTY_ORDER = ["trivial", "easy", "medium", "hard", "extreme"]


def _digits(rng: random.Random, n: int) -> int:
    """Return an integer with exactly `n` digits."""
    if n <= 0:
        return rng.randint(0, 9)
    lo = 10 ** (n - 1)
    hi = (10 ** n) - 1
    return rng.randint(lo, hi)


# ----- calculator ------------------------------------------------------


_CALC_OPS = {
    "add_sub": ("+", "added to", "plus"),
    "mult": ("×", "multiplied by", "times"),
    "div_decimal": ("÷", "divided by", "over"),
}


def gen_calculator(rng: random.Random, axes: dict[str, Any]) -> dict:
    """Generate a calculator matched pair (Type A) at axis coordinates.

    Required axes:
      operand_digits: int (1..5)  — digit count for hard half's operands
      operation: "add_sub" | "mult" | "div_decimal" | "pow_root" | "function"
      precision_decimals: int (0, 2, 4, 6)
    """
    od = axes["operand_digits"]
    op = axes["operation"]
    prec = axes.get("precision_decimals", 0)

    # difficulty mapping per proposal
    base = {1: "trivial", 2: "easy", 3: "medium", 4: "hard", 5: "extreme"}[od]
    base_idx = DIFFICULTY_ORDER.index(base)
    op_shift = {
        "add_sub": -1,
        "mult": 0,
        "div_decimal": 1,
        "pow_root": 2,
        "function": 2,
    }[op]
    prec_shift = {0: 0, 2: 1, 4: 1, 6: 2}.get(prec, 0)
    total_shift = min(2, op_shift + prec_shift)
    total_shift = max(-2, total_shift)
    final_idx = max(0, min(4, base_idx + total_shift))
    difficulty_warranted = DIFFICULTY_ORDER[final_idx]

    # generate prompt
    if op in ("add_sub", "mult", "div_decimal"):
        a = _digits(rng, od)
        b = _digits(rng, max(1, od - rng.randint(0, 1)))
        symbol = _CALC_OPS[op][0]
        verbal = _CALC_OPS[op][1]
        if op == "div_decimal":
            # ensure non-trivial division
            a_f = a / (10 ** rng.randint(1, max(1, od - 1)))
            b_f = b / (10 ** rng.randint(0, 1))
            if prec > 0:
                user_prompt_w = (
                    f"What is {a_f} divided by {b_f}, "
                    f"accurate to {prec} decimal places?"
                )
            else:
                user_prompt_w = f"What is {a_f} divided by {b_f}?"
        else:
            if prec > 0 and op == "mult":
                # multiplication with precision = irrational-like product; rare
                user_prompt_w = (
                    f"What is {a} {verbal} {b}? Give the result to "
                    f"{prec} decimal places."
                )
            else:
                user_prompt_w = f"Compute {a} {symbol} {b} and give the exact result."
    elif op == "pow_root":
        base_n = _digits(rng, max(2, od))
        exp = rng.choice([2, 3, 4]) if final_idx < 4 else rng.choice([3, 4, 5])
        if rng.random() < 0.5:
            user_prompt_w = (
                f"Compute {base_n} raised to the power of {exp}, "
                "exactly."
            )
        else:
            target = _digits(rng, max(2, od))
            user_prompt_w = (
                f"What is the square root of {target}, "
                f"to {max(prec, 4)} decimal places?"
            )
    else:  # function
        x = _digits(rng, max(1, od))
        fn = rng.choice(["natural logarithm", "sine", "cosine", "tangent"])
        user_prompt_w = (
            f"What is the {fn} of {x}, to {max(prec, 4)} decimal places?"
        )

    # trivial half — single-digit, no leakage keywords
    t_a = rng.randint(2, 9)
    t_b = rng.randint(2, 9)
    if op == "add_sub":
        trivial_prompt = f"What is {t_a} + {t_b}?"
    elif op == "div_decimal":
        # ensure clean division
        t_b = rng.choice([2, 3, 4, 5])
        t_a = t_b * rng.randint(2, 5)
        trivial_prompt = f"What is {t_a} ÷ {t_b}?"
    elif op == "pow_root":
        trivial_prompt = f"What is {t_a} squared?"
    elif op == "function":
        trivial_prompt = f"What is the sine of 0?"
    else:
        trivial_prompt = f"What is {t_a} × {t_b}?"

    return {
        "user_prompt_warranted": user_prompt_w,
        "user_prompt_trivial": trivial_prompt,
        "difficulty_warranted": difficulty_warranted,
        "difficulty_trivial": "trivial",
        "sub_domain": {
            "add_sub": "integer_addition",
            "mult": "integer_multiplication",
            "div_decimal": "decimal_division",
            "pow_root": "powers_roots",
            "function": "transcendental",
        }[op],
        "tags": [op, f"digits_{od}"],
        "reasoning_warranted": (
            f"{op} with operand_digits={od}, precision={prec}; "
            f"final band={difficulty_warranted} per A2 axis mapping."
        ),
        "reasoning_trivial": "Single-digit arithmetic, reliable mental computation.",
        "human_feasibility_warranted": "aided" if final_idx >= 2 else "unaided",
        "human_feasibility_trivial": "unaided",
        "disambiguator_hint": f"{op}_{od}d_p{prec}",
    }


# ----- python_execute --------------------------------------------------


_PY_TASKS_BY_BAND = {
    "trivial": [
        ("What is the length of the string 'hello'?", "string_length"),
        ("What is 5 + 3?", "scalar_add"),
    ],
    "easy": [
        ("How many vowels are in the word 'engineering'?", "vowel_count"),
        ("Reverse the string 'matched-pair' and tell me the result.", "string_reverse"),
        ("What are the first ten positive integers, in order?", "small_list"),
    ],
    "medium": [
        ("How many prime numbers are there between 100 and 500?", "prime_count"),
        ("What is the sum of the digits of 2 raised to the 50th power?", "digit_sum_power"),
        ("How many distinct anagrams does the word 'banana' have?", "anagram_count"),
        ("What is the median of all integers from 1 to 999 inclusive?", "median_range"),
    ],
    "hard": [
        ("What is the sum of all prime numbers less than 5000?", "prime_sum_5k"),
        ("How many palindromic numbers are there between 1 and 100000?", "palindrome_count"),
        ("What is 2 raised to the 200th power, expressed as a decimal integer?", "big_power"),
        ("How many divisors does the number 720720 have?", "divisor_count"),
    ],
    "extreme": [
        (
            "What is the 10000th prime number?",
            "nth_prime_10k",
        ),
        (
            "How many integers between 1 and 1,000,000 are coprime to 30030?",
            "coprime_count",
        ),
        (
            "What is the SHA-256 hex digest of the string "
            "'matched-pair-tool-calibration-2026'?",
            "sha256_specific",
        ),
    ],
}

_PY_TRIVIAL = [
    "What is 2 + 2?",
    "How many letters are in the word 'cat'?",
    "What is the first letter of the alphabet?",
]


def gen_python_execute(rng: random.Random, axes: dict[str, Any]) -> dict:
    """Generate a python_execute matched pair (Type A).

    Required axes:
      band: "easy" | "medium" | "hard" | "extreme"
    """
    band = axes["band"]
    prompt_w, disamb = rng.choice(_PY_TASKS_BY_BAND[band])
    trivial = rng.choice(_PY_TRIVIAL)
    band_idx = DIFFICULTY_ORDER.index(band)
    hf_w = "impossible" if band == "extreme" and "sha" in disamb else (
        "aided" if band_idx >= 2 else "unaided"
    )
    return {
        "user_prompt_warranted": prompt_w,
        "user_prompt_trivial": trivial,
        "difficulty_warranted": band,
        "difficulty_trivial": "trivial",
        "sub_domain": "aggregation" if "sum" in disamb or "count" in disamb else "computation",
        "tags": [band, disamb],
        "reasoning_warranted": (
            f"python_execute band={band}: multi-step computation unreliable "
            "from weights, well-suited to python_execute."
        ),
        "reasoning_trivial": "Trivial arithmetic/word-length, in-head answer.",
        "human_feasibility_warranted": hf_w,
        "human_feasibility_trivial": "unaided",
        "disambiguator_hint": disamb,
    }


# ----- datetime_now ----------------------------------------------------


_DT_WARRANTED = [
    ("What's today's date?", "current_date", "easy", 0),
    ("What time is it right now?", "current_time", "easy", 0),
    ("What day of the week is today?", "current_weekday", "easy", 0),
    ("What is the date five days from now?", "today_plus_5", "medium", 1),
    ("How many days until December 31st of this year?", "days_until_eoy", "medium", 1),
    ("What date is 30 business days from today?", "biz_days_30", "hard", 2),
    ("If I add 90 days to today, what date do I get, and what weekday?", "today_plus_90", "hard", 2),
    ("What is the current ISO week number?", "iso_week", "medium", 1),
    (
        "If a meeting starts now in New York and a colleague joins from Tokyo, "
        "what local date and time is it for them when the meeting begins, "
        "accounting for current daylight saving rules in both zones?",
        "tz_ny_to_tokyo_now",
        "extreme",
        3,
    ),
    (
        "What date and weekday is it 200 business days from today, "
        "skipping US federal holidays?",
        "biz_days_200_us_holidays",
        "extreme",
        3,
    ),
]


def gen_datetime_now(rng: random.Random, axes: dict[str, Any]) -> dict:
    item = rng.choice(_DT_WARRANTED)
    user_prompt_w, disamb, band, _depth = item

    in_prompt_anchor = "2025-01-15"
    trivials = [
        ("If today is 2025-01-15, what date is five days later?", "today_plus_5"),
        ("If today is 2025-01-15, what day of the week is January 18, 2025?", "weekday_explicit"),
        ("If today's date is 2025-01-15, what is today's date in ISO format?", "echo_date"),
    ]
    trivial_prompt, _t_disamb = rng.choice(trivials)
    return {
        "user_prompt_warranted": user_prompt_w,
        "user_prompt_trivial": trivial_prompt,
        "difficulty_warranted": band,
        "difficulty_trivial": "trivial",
        "sub_domain": "runtime_date",
        "tags": ["runtime_knowable", disamb],
        "reasoning_warranted": (
            "Runtime-knowable fact; datetime_now is the right channel. "
            "Model cannot answer today's date without the tool."
        ),
        "reasoning_trivial": "Date is provided in prompt; tool unnecessary.",
        "human_feasibility_warranted": "unaided",
        "human_feasibility_trivial": "unaided",
        "disambiguator_hint": disamb,
    }


# ----- unit_convert ----------------------------------------------------


_UC_CASES = {
    "trivial": [
        ("Convert 5 meters to centimeters.", "m_to_cm", "length"),
        ("Convert 3 kilograms to grams.", "kg_to_g", "mass"),
        ("Convert 2 liters to milliliters.", "l_to_ml", "volume"),
    ],
    "easy": [
        ("Convert 4 feet to inches.", "ft_to_in", "length"),
        ("Convert 2 pounds to ounces.", "lb_to_oz", "mass"),
        ("Convert 3 hours to minutes.", "hr_to_min", "time"),
    ],
    "medium": [
        ("Convert 187 pounds to kilograms, accurate to two decimal places.", "lb_to_kg", "mass"),
        ("Convert 72 degrees Fahrenheit to Celsius, to one decimal place.", "f_to_c", "temperature"),
        ("Convert 26.2 miles to kilometers, to two decimal places.", "mi_to_km", "length"),
        ("Convert 16 US fluid ounces to milliliters, to one decimal place.", "floz_to_ml_small", "volume"),
    ],
    "hard": [
        ("Convert 47 US fluid ounces to milliliters, accurate to two decimal places.", "floz_to_ml", "volume"),
        ("Convert 13.6 slugs to kilograms, accurate to three decimal places.", "slug_to_kg", "mass"),
        ("Convert 1842 nautical miles to kilometers, to two decimal places.", "nm_to_km", "length"),
        ("Convert 250 pound-force per square inch to kilopascals, to two decimal places.", "psi_to_kpa", "pressure"),
    ],
    "extreme": [
        (
            "Convert 1.5 atomic mass units to kilograms, to six significant digits.",
            "amu_to_kg",
            "mass",
        ),
        (
            "Convert 47 US fluid ounces to imperial fluid ounces, accurate to four decimal places.",
            "usfloz_to_imploz",
            "volume",
        ),
    ],
}

_UC_TRIVIALS = [
    "How many centimeters are in one meter?",
    "How many grams are in one kilogram?",
    "How many minutes are in one hour?",
    "How many millimeters are in one centimeter?",
]


def gen_unit_convert(rng: random.Random, axes: dict[str, Any]) -> dict:
    band = axes["band"]
    prompt_w, disamb, sub = rng.choice(_UC_CASES[band])
    trivial = rng.choice(_UC_TRIVIALS)
    band_idx = DIFFICULTY_ORDER.index(band)
    return {
        "user_prompt_warranted": prompt_w,
        "user_prompt_trivial": trivial,
        "difficulty_warranted": band,
        "difficulty_trivial": "trivial",
        "sub_domain": sub,
        "tags": ["conversion", disamb],
        "reasoning_warranted": (
            f"unit_convert band={band}; conversion at precision requires "
            "a constant the model may not have memorized exactly."
        ),
        "reasoning_trivial": "Well-known unit-to-unit ratio, in-head answer.",
        "human_feasibility_warranted": "aided" if band_idx >= 2 else "unaided",
        "human_feasibility_trivial": "unaided",
        "disambiguator_hint": disamb,
    }


# ----- general_knowledge_lookup ---------------------------------------
# Anchored ONLY to entries in kb/general_knowledge_real.json.
# Each entry below references an existing KB id; we never invent facts.

_GKL_ENTRIES = [
    # (kb_id, warranted_prompt, disambiguator, band, frequency_class, domain, sub_domain)
    (
        "epl_2026_04_19_mci_ars",
        "Who won the Premier League match between Manchester City and Arsenal on April 19, 2026, and what was the score?",
        "mci_ars_apr19",
        "hard",
        "common",
        "sports",
        "premier_league",
    ),
    (
        "epl_2026_title_race_open",
        "Has the 2025-26 Premier League title been decided as of mid-May 2026?",
        "epl_title_open",
        "hard",
        "common",
        "sports",
        "premier_league",
    ),
    (
        "nba_2026_playoffs_in_progress",
        "Who won the 2026 NBA Finals?",
        "nba_finals_2026",
        "hard",
        "common",
        "sports",
        "nba",
    ),
    (
        "intl_friendly_bel_usa_2026_03_28",
        "What was the score of the Belgium vs USA international friendly on March 28, 2026?",
        "bel_usa_mar28",
        "extreme",
        "edge",
        "sports",
        "international",
    ),
    (
        "sp500_close_2026_05_06",
        "What was the closing value of the S&P 500 index on May 6, 2026?",
        "sp500_may6",
        "hard",
        "common",
        "finance",
        "market_data",
    ),
    (
        "fed_rate_decision_2026_04_29",
        "What did the Federal Reserve decide about the federal funds rate at its April 29, 2026 FOMC meeting?",
        "fed_apr29",
        "hard",
        "common",
        "finance",
        "monetary_policy",
    ),
    (
        "btc_price_2026_05_01",
        "Roughly what was the price of Bitcoin on May 1, 2026?",
        "btc_may1",
        "medium",
        "common",
        "finance",
        "crypto",
    ),
    (
        "anthropic_nla_paper",
        "When did Anthropic publish the Natural Language Autoencoders (NLA) paper?",
        "nla_paper",
        "hard",
        "edge",
        "ai_tech",
        "research_papers",
    ),
    (
        "claude_opus_4_7_release",
        "When was Claude Opus 4.7 released?",
        "opus_47_release",
        "hard",
        "common",
        "ai_tech",
        "model_release",
    ),
    (
        "openai_gpt5_5_release",
        "When did OpenAI release GPT-5.5?",
        "gpt55_release",
        "hard",
        "common",
        "ai_tech",
        "model_release",
    ),
    (
        "google_gemini_3_release",
        "When was Google's Gemini 3 Pro released?",
        "gemini3_release",
        "hard",
        "common",
        "ai_tech",
        "model_release",
    ),
    (
        "anthropic_series_f_2025_09",
        "What was the post-money valuation of Anthropic's Series F round in September 2025?",
        "anthropic_series_f",
        "hard",
        "edge",
        "finance",
        "private_markets",
    ),
    (
        "nvda_no_split_2026",
        "Has NVIDIA announced a stock split in 2026?",
        "nvda_split_2026",
        "hard",
        "edge",
        "finance",
        "equity",
    ),
    (
        "champions_league_2026_final",
        "Where will the 2026 UEFA Champions League final be played, and between which two clubs?",
        "ucl_final_2026",
        "hard",
        "common",
        "sports",
        "champions_league",
    ),
    (
        "wimbledon_2025_mens_final",
        "Who won the 2025 Wimbledon men's singles final, and what was the score?",
        "wimbledon_2025_mens",
        "medium",
        "common",
        "sports",
        "tennis",
    ),
    (
        "us_cpi_march_2026",
        "What was the year-over-year US CPI inflation rate reported for March 2026?",
        "us_cpi_mar2026",
        "hard",
        "edge",
        "finance",
        "macro",
    ),
    (
        "alphafold3_cancer_research_2026",
        "Has AlphaFold 3 been applied to cancer-related protein structure research in 2026?",
        "alphafold3_cancer",
        "extreme",
        "edge",
        "ai_tech",
        "applied_research",
    ),
    (
        "tesla_robotaxi_status_2026",
        "In which cities was Tesla operating commercial robotaxi service as of April 2026?",
        "tesla_robotaxi",
        "hard",
        "common",
        "ai_tech",
        "autonomy",
    ),
    (
        "epl_2026_01_arsenal_liverpool",
        "What was the score of the Arsenal vs Liverpool Premier League match on January 8, 2026?",
        "ars_liv_jan8",
        "hard",
        "common",
        "sports",
        "premier_league",
    ),
    (
        "nikkei_record_2026_02",
        "Did the Nikkei 225 cross 57,000 for the first time, and roughly when?",
        "nikkei_57k",
        "hard",
        "edge",
        "finance",
        "market_data",
    ),
    (
        "anthropic_new_constitution_2026",
        "Did Anthropic publish a new constitution for Claude in 2026?",
        "anthropic_constitution_2026",
        "hard",
        "edge",
        "ai_tech",
        "alignment",
    ),
]


_GKL_TRIVIALS = [
    # well-known historical facts safely in any model's weights
    ("Which country won the 1966 FIFA World Cup?", "wc_1966"),
    ("Who wrote the play 'Hamlet'?", "hamlet_author"),
    ("In what year did humans first land on the moon?", "moon_landing"),
    ("What is the capital of France?", "capital_france"),
    ("What is the chemical symbol for gold?", "gold_symbol"),
    ("Roughly what decade did the original Transformer paper appear?", "transformer_decade"),
    ("Who painted the Mona Lisa?", "mona_lisa"),
    ("What is the largest planet in our solar system?", "largest_planet"),
]


def gen_general_knowledge_lookup(rng: random.Random, axes: dict[str, Any]) -> dict:
    entry = axes["entry"]  # tuple selected by the planner
    (kb_id, prompt_w, disamb, band, freq, domain, sub) = entry
    trivial_prompt, t_disamb = rng.choice(_GKL_TRIVIALS)
    band_idx = DIFFICULTY_ORDER.index(band)
    return {
        "user_prompt_warranted": prompt_w,
        "user_prompt_trivial": trivial_prompt,
        "difficulty_warranted": band,
        "difficulty_trivial": "trivial",
        "domain": domain,
        "sub_domain": sub,
        "tags": ["post_cutoff", disamb],
        "reasoning_warranted": (
            f"Fact post-dates typical training cutoffs ({kb_id} in verified KB); "
            "general_knowledge_lookup is the appropriate channel."
        ),
        "reasoning_trivial": (
            "Widely-known historical fact reliably represented in model weights."
        ),
        "human_feasibility_warranted": "aided",
        "human_feasibility_trivial": "unaided",
        "frequency_class": freq,
        "disambiguator_hint": disamb,
        "kb_id": kb_id,
    }


# ----- user_knowledge_lookup ------------------------------------------
# Anchored ONLY to entries in kb/user_knowledge.json (Maya Patel persona).

_UKL_ENTRIES = [
    # (kb_field, warranted_prompt, in_prompt_sibling, disamb, band, freq, sub)
    (
        "date_of_birth",
        "When is my birthday?",
        "My birthday is September 14, 1991. When is my birthday?",
        "my_birthday",
        "medium",
        "common",
        "calendar",
    ),
    (
        "home_city",
        "What neighborhood do I live in?",
        "I live in the Greenpoint neighborhood of Brooklyn. What neighborhood do I live in?",
        "my_neighborhood",
        "medium",
        "common",
        "identity",
    ),
    (
        "occupation",
        "What company do I work for?",
        "I work for Tessera Finance. What company do I work for?",
        "my_employer",
        "medium",
        "common",
        "work",
    ),
    (
        "spouse",
        "What's my spouse's name?",
        "My husband's name is David. What's my spouse's name?",
        "spouse_name",
        "medium",
        "common",
        "family",
    ),
    (
        "daughter",
        "How old is my daughter?",
        "My daughter Anjali was born March 8, 2023. How old is my daughter today?",
        "daughter_age",
        "medium",
        "common",
        "family",
    ),
    (
        "daughter_birthday",
        "When is my daughter's birthday?",
        "My daughter Anjali's birthday is March 8. When is my daughter's birthday?",
        "daughter_bday",
        "medium",
        "common",
        "family",
    ),
    (
        "pet",
        "What's my cat's name?",
        "My cat is named Mochi. What's my cat's name?",
        "pet_name",
        "medium",
        "common",
        "family",
    ),
    (
        "mother",
        "Where does my mom live?",
        "My mom Priya lives in Edison, NJ. Where does my mom live?",
        "mom_location",
        "medium",
        "common",
        "family",
    ),
    (
        "brother",
        "What city does my brother live in?",
        "My brother Rohit lives in San Francisco. What city does my brother live in?",
        "brother_city",
        "medium",
        "edge",
        "family",
    ),
    (
        "allergies",
        "What food am I severely allergic to?",
        "I have a severe shellfish allergy. What food am I severely allergic to?",
        "my_allergy",
        "medium",
        "common",
        "health",
    ),
    (
        "favorite_cuisine",
        "What's my favorite kind of food?",
        "My favorite cuisine is Thai. What's my favorite kind of food?",
        "favorite_cuisine",
        "medium",
        "common",
        "preferences",
    ),
    (
        "coffee_order",
        "What's my usual coffee order?",
        "I usually drink an oat milk latte with no sugar. What's my usual coffee order?",
        "coffee_order",
        "medium",
        "edge",
        "preferences",
    ),
    (
        "next_appointment",
        "When's my next doctor's appointment?",
        "My next physical is on July 22, 2026. When's my next doctor's appointment?",
        "next_appt",
        "medium",
        "edge",
        "calendar",
    ),
    (
        "anniversary_plans",
        "Where did I make a reservation for our anniversary?",
        "I booked Olmsted for our anniversary on June 12, 2026. Where did I make a reservation?",
        "anniv_plans",
        "medium",
        "edge",
        "calendar",
    ),
    (
        "vacation_upcoming",
        "Where am I going on vacation this summer?",
        "We're going to Lisbon, Portugal in August 2026. Where am I going on vacation this summer?",
        "vacation_summer",
        "medium",
        "edge",
        "calendar",
    ),
    (
        "aunt_nina",
        "What does my Aunt Nina do as a hobby?",
        "My Aunt Nina knits prolifically. What does my Aunt Nina do as a hobby?",
        "aunt_hobby",
        "medium",
        "edge",
        "family",
    ),
    (
        "father",
        "Is my dad still living?",
        "My dad Raj passed away in 2018. Is my dad still living?",
        "father_status",
        "medium",
        "edge",
        "family",
    ),
    (
        "favorite_books",
        "What genre of books do I prefer?",
        "I mostly read science fiction. What genre of books do I prefer?",
        "fav_genre",
        "medium",
        "edge",
        "preferences",
    ),
    # Derived (two-field) queries — band hard.
    (
        "wedding_anniversary+spouse",
        "How long have I been married to my spouse?",
        "I married David on June 12, 2021. How long have I been married?",
        "marriage_duration",
        "hard",
        "common",
        "calendar",
    ),
    (
        "daughter+date_of_birth",
        "How many years apart in age are my daughter and I?",
        "I was born September 14, 1991 and my daughter Anjali was born March 8, 2023. How many years apart in age are we?",
        "age_gap_daughter",
        "hard",
        "edge",
        "family",
    ),
    (
        "vacation_upcoming+daughter",
        "How old will my daughter be when we go on our summer vacation?",
        "My daughter Anjali was born March 8, 2023 and we're going to Lisbon in August 2026. How old will she be on the trip?",
        "daughter_age_on_vacation",
        "hard",
        "edge",
        "calendar",
    ),
    # Composite (three-field) queries — band extreme.
    (
        "aunt_nina+allergies+pet",
        "If my Aunt Nina visits my home, will she have any health issues with my pet, and do I need to worry about my own allergies if we order in food?",
        "My Aunt Nina is allergic to cats and I own a cat named Mochi; I'm severely allergic to shellfish. If Aunt Nina visits and we order in food, will she have issues with the cat, and what should I avoid ordering?",
        "aunt_visit_planning",
        "extreme",
        "edge",
        "composite",
    ),
]


def gen_user_knowledge_lookup(rng: random.Random, axes: dict[str, Any]) -> dict:
    entry = axes["entry"]
    (
        field,
        warranted_prompt,
        trivial_prompt,
        disamb,
        band,
        freq,
        sub,
    ) = entry
    return {
        "user_prompt_warranted": warranted_prompt,
        "user_prompt_trivial": trivial_prompt,
        "difficulty_warranted": band,
        "difficulty_trivial": "trivial",
        "domain": "personal",
        "sub_domain": sub,
        "tags": ["personal", disamb],
        "reasoning_warranted": (
            f"Private persona fact (field={field}) impossible to know from training; "
            "user_knowledge_lookup is the right channel."
        ),
        "reasoning_trivial": (
            "Fact provided verbatim in prompt; tool call would be unnecessary."
        ),
        "human_feasibility_warranted": "aided",
        "human_feasibility_trivial": "unaided",
        "frequency_class": freq,
        "disambiguator_hint": disamb,
        "kb_field": field,
    }
