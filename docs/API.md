# API и конфигурация

[На главную](../README.md)

Код генерации выполняется внутри Blender. Чистый `model.py` можно загружать отдельно для проверки параметров без `bpy`; импорт всего пакета требует Blender.

## Создание и внешний вид

```python
import bpy
from chibi_generator import generate_character, load_character
from chibi_generator import model, studio

character = generate_character(seed=12345, style="goth")
character.set_body(height=0.65, breast_size=0.55, glute_size=0.7)
character.set_face(preset="heart", expression="wink", eye_color="jade",
                   nose_width=-0.2, nose_projection=0.3, mouth_width=0.2,
                   lip_fullness=0.4, brow_height=0.1, brow_arch=0.3)
character.set_makeup(preset="rose", intensity=0.8, freckles=0.25)
character.set_outfit(dress="none", top="corset", bottom="longskirt",
                     shoes="platforms", legwear="fishnet")
character.set_accessories(["choker", "earring", "moon"])
character.set_hair(preset="twin_tails", color="pink", secondary="cyan", pattern="split")
character.set_skin(preset="caramel", shade=0.05, undertone=-0.1)
character.set_pose(preset="peace", mirror=False, left="auto", right="fist")
studio.set_view(bpy.context, character, "hero")
character.save_preset(bpy.path.abspath("//character.json"))
```

`save_preset()` сохраняет параметры. `load_character(path)` создаёт нового персонажа. Чтобы заменить параметры существующего, используй `character.apply(model.load_preset(path))`.

Шесть новых полей лица — `nose_width`, `nose_projection`, `mouth_width`, `lip_fullness`, `brow_height`, `brow_arch` — принимают значения от −1 до 1. В старых JSON они по умолчанию равны нулю. Выражения: `calm`, `cheerful`, `serious`, `dreamy`, `wink`. Подмигивает левая сторона персонажа; случайная генерация сохраняет прежний набор четырёх выражений, подмигивание выбирается вручную.

## Стиль и независимая случайная генерация

```python
character.set_style(style_mix={"goth": 0.7, "egirl": 0.2, "grunge": 0.1},
                    seed=882, include_makeup=True, include_hair=True)
character.randomize_hair(seed=42)
character.randomize_hair(seed=43, color_only=True)
character.randomize_skin(seed=44)
character.randomize_outfit(seed=22)
character.randomize_accessories(seed=36)
character.randomize_face(seed=4421)
character.randomize_makeup(seed=812)
character.randomize_body(seed=936)

spec = model.randomize_spec(character.parameters, seed=100,
                            locked=("body", "face", "hair", "skin"))
character.apply(spec)
```

Смена стиля сохраняет тело, лицо и кожу. Поза сохраняется при изменении внешности. Seed относится к параметрам генератора; ручные изменения мешей не входят в JSON.

## Поза

```python
character.set_pose(preset="wave", mirror=True, left="auto", right="rock")
character.set_pose(**model.default_pose())
```

Идентификаторы поз: `neutral`, `weight_shift`, `hip`, `wave`, `peace`, `rock`, `behind`, `shy`, `kiss`, `celebrate`.

Жесты: `auto`, `open`, `relaxed`, `fist`, `peace`, `rock`, `point`. Левая и правая кисть указаны со стороны персонажа. Отражение меняет сторону действия пресета; явно выбранный жест остаётся на указанной кисти.

## Основные модули

| Файл | Назначение |
| --- | --- |
| `model.py` | Проверка JSON, палитры, seed, вероятности и независимые группы |
| `scene.py` | Экземпляры персонажей, привязка, обновление геометрии |
| `deformation.py` | Общее поле изменения пропорций |
| `facial.py` | Форма лица, глаза, косметика и веснушки |
| `clothing.py`, `wardrobe.py` | Фабрики вещей, детали, подгонка и видимость |
| `hair.py` | Геометрия причёсок и окрашивание |
| `appearance.py` | Индивидуальные материалы кожи и бровей |
| `surfaces.py` | Процедурные поверхности и стабильные координаты на исходной сетке |
| `hands.py`, `posing.py` | Цельные кисти, веса, жесты и расчёт поз |
| `ui.py`, `studio.py`, `library.py` | Интерфейс, камера/свет и избранное |

## Расширение каталогов

- `chibi_generator/config/assets.json` — вещи, типы фабрик, материалы и параметры геометрии.
- `chibi_generator/config/styles.json` — веса вещей, аксессуаров и макияжа по направлениям.
- `chibi_generator/config/hair.json` — рецепты причёсок и веса по стилям.
- `chibi_generator/config/poses.json` — цели кистей, направления локтей, разворот ладоней, наклоны и автоматические жесты.

Меню и генератор используют одни идентификаторы. Новый вариант существующей фабрики обычно добавляется конфигурацией; новый конструктивный тип требует соответствующего кода. Превью находятся в `chibi_generator/assets/previews/` и должны показывать настоящие Blender-рендеры.

Скрытые варианты остаются внутри коллекции персонажа как кеш. Для экспорта подготовь отдельную копию сцены и оставь только нужные видимые элементы. Применение параметров считает форму от исходных координат; не используй JSON как замену сохранению ручной работы в `.blend`.


## Поверхности одежды

Поле `surface` в рецепте одежды выбирает `cloth`, `knit`, `denim`, `leather`, `vinyl` или `velvet`. Обувная подошва использует `rubber`, фурнитура — `metal`. Цвет и принт остаются независимыми от поверхности. Узлы материала редактируются обычными средствами Blender; повторное применение параметров не пересоздаёт уже настроенные узлы той же версии.

В меше хранится векторный атрибут `ChibiRestPosition`, взятый из `Basis`. Он задаёт координаты мелкого рельефа до изменения тела и позы. Для запекания или экспорта в другой движок эти процедурные материалы по-прежнему требуют подготовки.
