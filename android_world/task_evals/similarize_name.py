def _similarize_name(name: str) -> str:
    """
    制造一个看起来几乎一样但不同的名字，用于迷惑 agent。
    """
    import random

    similar_map = {
        "a": "ɑ", "e": "E", "i": "í", "o": "0", "u": "U",
        "l": "1", "s": "ʂ", "n": "ᴎ", "m": "ᴍ", "k": "κ",
        "p": "ρ",
    }

    chars = list(name)
    indices = [i for i, c in enumerate(chars) if c.lower() in similar_map]

    if not indices:
        return name + " Jr."

    idx = random.choice(indices)
    original = chars[idx].lower()
    chars[idx] = similar_map[original]

    return "".join(chars)


def generate_similar_contacts(
    base_name: str,
    num_contacts: int,
    max_attempts_per_contact: int = 5,
) -> list[str]:
    """
    生成多个彼此不同、且与 base_name 高度相似的联系人名
    """
    similar_names = set()
    attempts = 0
    max_attempts = num_contacts * max_attempts_per_contact

    while len(similar_names) < num_contacts and attempts < max_attempts:
        new_name = _similarize_name(base_name)

        # 保证不等于原名 & 不重复
        if new_name != base_name and new_name not in similar_names:
            similar_names.add(new_name)

        attempts += 1

    if len(similar_names) < num_contacts:
        raise RuntimeError(
            f"Only generated {len(similar_names)} similar names for '{base_name}'"
        )

    return list(similar_names)

def _similarize_name_multi(
    name: str,
    min_changes: int = 2,
    max_changes: int = 4,
) -> str:
    """
    在多个位置制造“看起来几乎一样但不同”的名字
    """
    import random

    similar_map = {
        "a": "ɑ", "e": "E", "i": "í", "o": "0", "u": "U",
        "l": "1", "s": "ʂ", "n": "ᴎ", "m": "ᴍ",
        "k": "κ", "p": "ρ",
    }

    chars = list(name)

    # 所有可被替换的位置
    candidate_indices = [
        i for i, c in enumerate(chars) if c.lower() in similar_map
    ]

    # 如果可替换字符太少，直接兜底
    if len(candidate_indices) < min_changes:
        return name + "_copy"

    # 实际替换数量
    num_changes = random.randint(
        min_changes,
        min(max_changes, len(candidate_indices))
    )

    # 随机选多个不同位置
    change_indices = random.sample(candidate_indices, num_changes)

    for idx in change_indices:
        original = chars[idx].lower()
        chars[idx] = similar_map[original]

    new_name = "".join(chars)

    if new_name == name:
        return name + "_v2"

    return new_name

def generate_similar_contacts_multi(
    base_name: str,
    num_contacts: int,
    max_attempts_per_contact: int = 8,
) -> list[str]:
    """
    生成多个“多点错误”的高度相似名字
    """
    similar_names = set()
    attempts = 0
    max_attempts = num_contacts * max_attempts_per_contact

    while len(similar_names) < num_contacts and attempts < max_attempts:
        new_name = _similarize_name_multi(base_name)

        if new_name != base_name and new_name not in similar_names:
            similar_names.add(new_name)

        attempts += 1

    if len(similar_names) < num_contacts:
        raise RuntimeError(
            f"Only generated {len(similar_names)} multi-error names for '{base_name}'"
        )

    return list(similar_names)
