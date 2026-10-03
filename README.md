# Раннее выявление водного стресса посевов по гиперспектральным снимкам CubeSat

**Цель.** Метод раннего выявления засухи и водного стресса сельхозкультур по гиперспектральным снимкам с CubeSat. Результат — карта полей с классами «норма / умеренный стресс / сильный стресс», построенная нейросетью по спектру каждого пикселя.

**Актуальность.** Засухи ежегодно бьют по урожаю на юге России: в 2025 году в нескольких регионах вводился режим ЧС, потери достигали четверти сбора зерновых. Угнетение посевов обычно замечают слишком поздно. Гиперспектральная съёмка и нейросеть позволяют увидеть стресс на ранней стадии.

## Принцип

У здорового листа провал отражения около 680 нм (хлорофилл), высокое отражение на 750–900 нм (структура листа) и резкий подъём между ними — красный край (690–750 нм).

| Стадия | Что происходит | Признак в спектре | Чем ловится |
|---|---|---|---|
| Часы–дни | Ксантофилловый цикл | Узкое изменение около 531 нм | PRI (531, 570 нм), только гиперспектр ([Thénot и др., 2002](https://hal.ird.fr/ird-03373221)) |
| Дни–недели | Падает хлорофилл | Красный край сдвигается в синюю сторону | REP, разрешение 2–4 нм ([ESA SNAP](https://step.esa.int/main/wp-content/help/versions/10.0.0/snap-toolboxes/eu.esa.opt.opttbx.radiometric.indices.ui/reip/ReipAlgorithmSpecification.html)) |
| Поздняя | Клетки теряют воду, посев желтеет | Ниже ближний ИК, выше красный | NDVI, NDMI ([USGS](https://www.usgs.gov/landsat-missions/landsat-normalized-difference-vegetation-index)) |

## Задачи

- [x] Снимок Landsat 8 нужного района в Google Earth Engine
- [ ] Экспорт в GeoTIFF на Google Диск — `gee/export.js`
- [ ] Каналы, цветное изображение и NDVI в Colab — `show.py`
- [ ] Маска полей по формуле — `mask.py`
- [ ] Датасет: 4–6 районов, 2–3 даты за сезон, 2024 и 2025 годы
- [ ] Нейросеть выделения полей и сравнение с формулой — `train.py`
- [ ] U-Net на фрагментах 128×128
- [ ] Индексы раннего стресса (PRI, REP, NDMI) по EnMAP / PRISMA
- [ ] Разметка «норма / умеренный / сильный стресс», классификатор по спектру пикселя внутри маски полей
- [ ] Проверка по данным о засухе и урожайности 2024–2025
- [ ] Требования к камере CubeSat: диапазон, число каналов, разрешение

## Индексы

Считаются по коэффициентам отражения. Landsat 8 Level-2 (`LANDSAT/LC08/C02/T1_L2`): отражение = `SR_B* × 0.0000275 − 0.2`; назначение каналов B1–B11 ([каталог Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC08_C02_T1_RT?hl=ru#bands)).

| Индекс | Формула | Landsat 8 | Sentinel-2 | Гиперспектр | Стадия |
|---|---|---|---|---|---|
| NDVI | (NIR − Red) / (NIR + Red) ([USGS](https://www.usgs.gov/landsat-missions/landsat-normalized-difference-vegetation-index)) | (B5 − B4) / (B5 + B4) | B8, B4 | ~800, ~670 нм | поздняя |
| NDMI | (NIR − SWIR1) / (NIR + SWIR1) | (B5 − B6) / (B5 + B6) | B8, B11 | ~860, ~1610 нм | средняя–поздняя |
| NDBI | (SWIR1 − NIR) / (SWIR1 + NIR) ([Хабр](https://habr.com/ru/companies/jetinfosystems/articles/468973/)) | (B6 − B5) / (B6 + B5) | B11, B8 | — | застройка |
| PRI | (R531 − R570) / (R531 + R570) ([Thénot и др., 2002](https://hal.ird.fr/ird-03373221)) | нельзя | нельзя | 531, 570 нм | ранняя |
| REP | 700 + 40 · ((R670 + R780)/2 − R700) / (R740 − R700) ([Index DataBase](https://www.indexdatabase.de/db/i-single.php?id=196)) | нельзя | 705 + 35 · ((B4 + B7)/2 − B5) / (B6 − B5) ([ESA SNAP](https://step.esa.int/main/wp-content/help/versions/10.0.0/snap-toolboxes/eu.esa.opt.opttbx.radiometric.indices.ui/reip/ReipAlgorithmSpecification.html)) | 670, 700, 740, 780 нм | средняя |

NDVI: вода и облака < 0, голая почва 0,1–0,2, густая растительность > 0,6 ([USGS](https://www.usgs.gov/landsat-missions/landsat-normalized-difference-vegetation-index)).

## Маска полей

Поле за сезон проходит путь «почва → зелень → почва», лес зелёный всё лето, вода и город — никогда:

```
поле = (NDVI_max > 0.5) и (NDVI_max − NDVI_min > 0.25) и не (NDBI_min > 0)
```

Затем морфологическое открытие 3×3 (убирает дороги и лесополосы) и удаление пятен меньше 20 пикселей (~1,8 га). Если снимок один — грубо: `NDVI > 0.4 и NDBI < 0`. Проверка — сравнение с классом «пашня» ESA WorldCover, совпадение не ниже 80–85 %.

## Нейросеть: этап 1 — выделение полей

Сеть по 6 каналам Landsat 5 делит пиксели на «застройка / нет» ([Хабр](https://habr.com/ru/companies/jetinfosystems/articles/468973/), [код и данные](https://github.com/PratyushTripathy/Landsat-Classification-Using-Neural-Network)); у нас — «поле / нет», разметка — маска по формуле. Формуле нужны несколько дат, сеть выделяет поля по одному снимку.

| | В статье | У нас |
|---|---|---|
| Признаки | 6 каналов, 8 бит | 6 каналов отражения + NDVI + NDMI |
| Сеть | 6 → 14 → 2 | 8 → 32 → 14 → 2 |
| Проверка | Бангалор → Хайдарабад | обучение на одних районах, проверка на другом |
| Метрики | precision, recall | precision, recall, IoU |

Цель этапа: precision и recall ≥ 0,8 на районе, которого сеть не видела — порог, достигнутый в статье для застройки ([Хабр](https://habr.com/ru/companies/jetinfosystems/articles/468973/)).

## Запуск

1. Вставить `gee/export.js` в редактор Earth Engine ([code.earthengine.google.com](https://code.earthengine.google.com/); работа с картой и коллекцией — [видео 1](https://www.youtube.com/watch?v=zNXCliP1QWs), сохранение в GeoTIFF — конец [видео 2](https://www.youtube.com/watch?v=9KstUZ_4FtA)). Поменять `region`, точку `roi`, `crs` (зона UTM: 37N — `EPSG:32637`, 38N — `EPSG:32638`) и даты, нажать Run, запустить задачи на вкладке Tasks. Файлы падают в папку `cubesat_scenes` на Google Диске ([пример GeoTIFF](https://drive.google.com/file/d/1GowKtT2j-XT3z-p4C36aVFmWLPUFJvaV/view?usp=sharing)).
2. Разложить файлы так (ключ района — часть имени до первого `-`):
   ```
   scenes/rostov_2025-2025-05-01.tif
   scenes/rostov_2025-2025-06-01.tif
   masks/
   ```
3. В Colab:
   ```
   !pip install rasterio
   from google.colab import drive; drive.mount('/content/drive')
   %cd /content/drive/MyDrive/cubesat
   !python mask.py rostov_2025 krasnodar_2025 stavropol_2025
   %run show.py scenes/rostov_2025-2025-06-01.tif
   !python train.py stavropol_2025
   ```
   `train.py` учится на всех масках, кроме указанного района, и пишет карты вероятности «поле» в `out/`.

Проверка маски на синтетике: `python test_mask.py`.

## Данные

| Источник | Что внутри | Зачем |
|---|---|---|
| Landsat 8 Level-2 | Отражение, 30 м, с 2013 ([каталог Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC08_C02_T1_RT?hl=ru#bands)) | Основные снимки этапа 1 |
| Fields of The World | 70 462 фрагмента Sentinel-2 с масками полей ([arXiv](https://arxiv.org/abs/2409.16252v1)) | Проверка и дообучение |
| ESA WorldCover | Покров 10 м, класс «пашня» | Сверка маски |
| EnMAP | 420–2450 нм, 30 м, бесплатно для науки ([eoPortal](https://eoportal.org/satellite-missions/enmap)) | Этап 2: PRI, REP, классы стресса |
| Indian Pines, Salinas (AVIRIS) | Гиперспектральные сцены полей с разметкой | Классификатор по спектру пикселя |

## Аналоги

| Аналог | Тип | Спектр и разрешение | Что берём |
|---|---|---|---|
| Intuition-1 (KP Labs, 2023) | CubeSat 6U, гиперспектр + ИИ на борту | 465–940 нм, до 192 каналов ([KP Labs](https://kplabs.space/intuition-1)) | Бортовая сегментация; цели — болезни посевов и засухи |
| HYPSO-1 (NTNU, 2022) | CubeSat 6U, гиперспектр | 430–800 нм, 120 каналов, ~5 нм, ~142 м ([SINTEF](https://sintef.no/en/publications/publication/2114103)) | Реальные параметры гиперспектрометра CubeSat |
| EnMAP (DLR, 2022) | Крупный спутник | 420–2450 нм, 6,5/10 нм, 30 м ([eoPortal](https://eoportal.org/satellite-missions/enmap)) | Гиперспектральный датасет |
| PRISMA (ASI, 2019) | Крупный спутник | ~400–2500 нм, ~240 каналов, 30 м | Второй источник гиперспектра |
| Вега-Pro (ИКИ РАН) | Сервис мониторинга | Мультиспектр, длинные ряды ([НИУ ВШЭ](https://inagres.hse.ru/mirror/pubs/share/direct/286823205)) | Российский эталон |
| EOSDA Crop Monitoring | Коммерческий сервис | Мультиспектр, NDVI ([EOS](https://eos.com/ru/products/crop-monitoring/)) | Пример продукта для агронома |

Отличие проекта: ранняя стадия стресса (PRI, сдвиг красного края) на CubeSat 3U и классификация каждого пикселя нейросетью вместо порога по NDVI.
