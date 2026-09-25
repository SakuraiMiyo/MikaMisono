# 未花出图提示词系统（形象锁定版）

> 老师 2026-09-13 给的形象依据：Danbooru 官方 wiki（Animagine XL 4.0 按 Danbooru 标签训练，标签即真相）
>
> 角色 tag: mika_(blue_archive) ← 注意不是 misono_mika
> 粉→淡蓝渐变超长发 + 右侧单丸子头 + 发花，金瞳，粉色光环，低位天使翼
> 制服: 白披肩 + 无袖双排扣荷叶边连衣裙 + 白裤袜 + 黑高跟鞋

分层结构: 质量 → 角色(锁定) → 外貌(锁定) → 服装 → 表情动作 → 构图 → 场景
出图时只拼「表情 / 构图 / 场景」这三层可变部分，其余全部锁定，保证形象稳定。

## 提示词

```python
QUALITY = "masterpiece, best quality"

# 锁定层: 角色识别 + 外貌特征, 任何场景都不改
CHARACTER = "mika_(blue_archive), blue archive, 1girl, solo, halo"
APPEARANCE = (
    "very long hair, gradient hair, multicolored hair, pink hair, blue hair, "
    "single side up, hair bun, hair flower, yellow eyes"
)

OUTFITS = {
    "uniform": (
        "white capelet, sleeveless dress, frilled dress, double-breasted, "
        "white skirt, white pantyhose, black pumps, low angel wings"
    ),
    "white_dress": (
        "white dress, sleeveless dress, frilled dress, bare shoulders, "
        "jewelry, low angel wings"
    ),
    "casual": "casual clothes, pink cardigan, white skirt, low angel wings",
}

EXPRESSIONS = {
    "smile": "smile, open mouth, :d",
    "gentle": "light smile, closed mouth",
    "smug": "smirk, half-closed eyes",
    "shy": "blush, embarrassed",
    "wink": "wink, smile, open mouth",
    "peace": "v, peace sign, smile",
}

COMPOSITIONS = {
    "portrait": "portrait, upper body",
    "bust": "bust",
    "full": "full body, standing",
    "cowboy": "cowboy shot",
}

SCENES = {
    "sakura": "outdoors, cherry blossoms, petals, spring",
    "church": "church, stained glass, indoors",
    "teaparty": "tea party, teacup, table, afternoon tea",
    "sunset": "sunset, sky, cloud, backlight",
    "classroom": "classroom, indoors, school",
    "city_night": "city lights, night, outdoors",
}

SIZES = {"portrait": (832, 1216), "square": (1024, 1024), "landscape": (1216, 832)}

DEFAULT_NEGATIVE = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, "
    "extra digit, fewer digits, cropped, worst quality, low quality, "
    "jpeg artifacts, signature, watermark, username, blurry, artist name, "
    "grey hair, brown eyes, blue eyes"
    # 末尾三个发色瞳色 tag 用于防止形象漂移: 未花是粉发金瞳
)


def build_prompt(outfit="uniform", expression="smile", composition="portrait",
                 scene="sakura", extra=""):
    parts = [
        QUALITY,
        CHARACTER,
        OUTFITS[outfit],
        APPEARANCE,
        EXPRESSIONS[expression],
        COMPOSITIONS[composition],
        SCENES[scene],
    ]
    if extra:
        parts.append(extra)
    return ", ".join(p for p in parts if p)


PRESETS = {
    "sakura_portrait": dict(outfit="uniform", expression="smile", composition="portrait", scene="sakura"),
    "church_fullbody": dict(outfit="uniform", expression="gentle", composition="full", scene="church"),
    "whitedress_teaparty": dict(outfit="white_dress", expression="wink", composition="cowboy", scene="teaparty"),
    "sunset_smile": dict(outfit="casual", expression="peace", composition="cowboy", scene="sunset"),
}
```

## 使用备忘

- 出图时锁死 CHARACTER / APPEARANCE，只改 EXPRESSIONS / COMPOSITIONS / SCENES。
- negative 末尾的 grey hair / brown eyes / blue eyes 是防漂移用的，别删（本尊是粉发金瞳）。
- 竖版优先：832×1216；方形 1024×1024；横版 1216×832。
- 待补：halo 只锁了形状没锁颜色，可考虑补色标，免得偶尔被染成金晕。
