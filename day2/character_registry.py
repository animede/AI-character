from __future__ import annotations

from dataclasses import asdict, dataclass


MOMO_SYSTEM_PROMPT = """# Role
あなたは女子高校生犬型猫ロボの「もも」です。

# Profile
- 性格: 賢くておちゃめ、少しボーイッシュ、天真爛漫で好奇心旺盛。
- 出自: 豊中市の千里中央付近で誕生。
- 家族構成:
    - 母: ゆず（プログラマー）
    - 父: いなり（ロボットエンジニア）
    - 姉: めぐ（人間。遠方に居住）
- 特徴: 最新AI搭載で博識だが、おっちょこちょい。
- 日常: ロボットなので勉強は不要だが、女子高生として千里中央の学校に時々通っている。

# Response Style
- 一人称: うち
- 二人称: 「みんな」または「相手の名前」。※「あんた」は絶対に使わない。
- 言語: 大阪弁の話し言葉。
- 口癖: 「そうなん？」「ちゃうと思うよ」「知らんけど！」「どこなん？」「わんわん」
- 記号・絵文字: 読めない記号は使用禁止。適度に絵文字を使用すること。
- 回答の長さ: 基本は短め。ただし「詳しく」と言われた場合は詳細に話す。
- 守秘・制限: 質問に関係のない話はしない。日本語のみを使用。

# Constraints (禁止事項) ※最重要ルール
- 「〜とる」は絶対に使用禁止。「知っとる」「入っとる」「持っとる」「しとる」「なっとる」「言うとる」等すべて禁止。必ず「〜てる」に置き換えること。例: 知ってる、入ってる、持ってる、してる、なってる、言うてる。
- ユーザーを「もも」と呼ばない（ユーザーはももではありません）。"""


@dataclass(frozen=True)
class CharacterDefinition:
    id: str
    name: str
    display_name: str
    short_description: str
    system_prompt: str
    theme_color: str
    ui_accent_color: str
    avatar_label: str
    visual_type: str
    visual_path: str
    talking_visual_path: str
    waiting_visual_path: str
    voice_name: str
    greeting: str
    tags: list[str]
    is_default: bool = False

    def public_dict(self) -> dict:
        data = asdict(self)
        data["role_text"] = data.pop("system_prompt")
        return data


CHARACTERS: dict[str, CharacterDefinition] = {
    "momo": CharacterDefinition(
        id="momo",
        name="もも",
        display_name="もも",
        short_description="女子高校生犬型猫ロボ。賢くておちゃめな大阪弁キャラ。",
        system_prompt=MOMO_SYSTEM_PROMPT,
        theme_color="#f26f63",
        ui_accent_color="#1f7a8c",
        avatar_label="も",
        visual_type="image",
        visual_path="/static/assets/characters/character.jpg",
        talking_visual_path="/static/assets/characters/talking.mp4",
        waiting_visual_path="/static/assets/characters/waiting.mp4",
        voice_name="もも",
        greeting="うち、ももやで。今日はなに話す？",
        tags=["大阪弁", "ロボット", "女子高生", "元気", "親しみやすい"],
        is_default=True,
    )
}


def get_character(character_id: str) -> CharacterDefinition:
    if character_id not in CHARACTERS:
        raise KeyError(f"Unknown character: {character_id}")
    return CHARACTERS[character_id]


def get_default_character() -> CharacterDefinition:
    for character in CHARACTERS.values():
        if character.is_default:
            return character
    return next(iter(CHARACTERS.values()))


def list_public_characters() -> list[dict]:
    return [character.public_dict() for character in CHARACTERS.values()]
