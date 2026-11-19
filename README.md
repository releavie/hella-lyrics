# Live Lyrics

Live synchronized lyrics in the Omarchy bar: the current line arrives
character by character while it is sung, and switches to a word-by-word karaoke
hand-off when the source carries word timings. The album cover sits to its left;
a click on the line opens a small player card with transport, a lyrics-provider
switch and sliders for opacity and how early words come up.

A port of the angelOS lyrics bar and engine by
[MixaDoDs](https://github.com/MixaDoDs/AngelOS-Dotfiles) (MIT) to the Omarchy
shell plugin system. See [`THIRD-PARTY.md`](THIRD-PARTY.md) for what was ported,
what was changed, and what is not bundled.

## What it does

- **Synced lines in the bar** — the current line, as wide as it needs (up to a
  configurable maximum) and rising into place on every line change. A line that
  still does not fit glides sideways instead of being cut off.
- **Word-by-word karaoke** — with sources that carry word timings the settled
  part of the line stays put and each new word hops in. lrclib's own per-word
  timings (its `lyricsfile`) are read too, so the bar draws the same karaoke the
  player does rather than guessing between line timestamps.
- **Beat grid** — guessed word times are aligned to the track's own beats,
  detected from the player's audio stream. A time the source supplied is never
  moved.
- **Loudness glow** — the line breathes with the music's level.
- **Album cover** — the current track's art, or a note glyph when the player
  publishes none.
- **Player card** — click the line: cover, title, artist, previous / play-pause /
  next, a provider switch with the source that actually answered, an opacity
  slider, and a “Words ahead” slider for singing along.

## Requirements

- Omarchy (the `quickshell` shell with the plugin system in `omarchy plugin`).
- An MPRIS-capable player (any browser tab playing YouTube Music counts).
- Network access to the lyrics services for fetching lyrics (lrclib first; the
  rest are fallbacks).
- `busctl` (systemd) to read the player's real MPRIS `Position`. Without it the
  plugin falls back to the shell's extrapolated position.
- Optional: `python3` + `python-numpy` for the beat grid, and `cava`,
  `pw-record`, `pw-dump`, `pactl` for the loudness glow, plus `curl` for remote
  cover art. Without them the plugin still shows synced lyrics line by line.
  See [`THIRD-PARTY.md`](THIRD-PARTY.md#runtime-dependencies-not-bundled).

On Arch the optional pieces come from the `extra` repository: `python-numpy`,
`cava`, `pipewire` and `curl`. Install them with your usual package manager —
the plugin never runs package management itself.

## Install

```bash
omarchy plugin add https://github.com/ilyamaximusaws/omarchy-live-lyrics.git --enable
```

Then place the widget: `omarchy plugin enable angelos.lyrics center` (or move it
in the bar settings). Nothing else to configure — with lyrics available for the
current track the line appears on its own.

## Remove

```bash
omarchy plugin remove angelos.lyrics
```

To keep the plugin but hide the line, disable it:

```bash
omarchy plugin disable angelos.lyrics
```

## Settings

Set through the shell's plugin settings (they live in your
`~/.config/omarchy/shell.json` entry for this widget):

| Key | Default | What it does |
|---|---|---|
| `byWord` | `true` | word-by-word karaoke when the source has word timings |
| `onBeat` | `true` | align word timings to the track's beat grid |
| `glow` | `level` | `level` — the line breathes with the music; `off` — steady |
| `artwork` | `cover` | `cover` — the album art; `note` — the note glyph |
| `opacity` | `100` | how solid the line sits in the bar, 20–100 |
| `maxWidth` | `500` | widest a line may get before it glides |
| `offsetMs` | `0` | shift the lyrics earlier (negative) or later (positive) than the player |
| `wordLeadMs` | `0` | how early a word comes up, in milliseconds: `0` lands on the sung word; positive is early, negative late |
| `provider` | — | pin one provider from the player card (`lrclib`, `netease`, `amll`, `lrccx`, `betterlyrics`, …); empty keeps the search order |
| `sources` | — | comma-separated search order, e.g. `lrclib, amll, netease, apple` |
| `preferPlayer` | — | substring of the player to prefer when several are running |
| `searchInMessengers` | `false` | search a messenger's voice messages online too, without asking per message |

The provider dropdown sits in the player card itself, so the current choice and
the source that answered are visible as soon as the card opens. Its list uses
shorter rows and keeps clear of the card edges. `opacity` and `wordLeadMs` are
always visible at the bottom of the card — there is no gear to open — and their
drags preview live, with only the release saved. `provider` is deliberately not
in the shell's settings schema: the choice belongs in the card, next to the
lyrics it changes.

The card's header has a circular-arrow reset icon that puts those three settings
back to their defaults (Auto, 100%, 0 ms) and saves them, and a close icon.
Clicking the line
again, an outside click, another panel taking over, or `shell hide angelos.lyrics`
also closes it; `shell summon angelos.lyrics '{}'` opens it.

### Sources

The built-in order is `local`, `player`, `lrclib`, `amll`, `netease`, `kugou`,
`qq`, `lrccx` (Apple Music), `musixmatch`, `genius`, `betterlyrics`, `ovh`.
Empty `sources` keeps it; otherwise only the listed sources are used, in that
order. `apple` is an alias for `lrccx` (its Apple catalogue), and names are
case-insensitive.

lrclib's `syncedLyrics` rarely carries per-word tags. Its search and get
endpoints also return a `lyricsfile` — a small YAML of the same lines with each
word's own start — and that is what the plugin reads. A worded hit is preferred
over a line-timed one of the same song, and older caches are re-checked against
lrclib once so a track cached before this support does not keep another store's
guess. A plain, line-timed LRC gets guessed word times from its syllables (one
per character where a word is written in kana, Han or Hangul); a source that
supplied its own word times is never re-estimated, and a sped-up or slowed-down
track stretches every word time with the line.

### Exact words for one song

When no source has word times, you can supply them yourself in
`~/.config/omarchy/angelos.lyrics/word-times.json`
(`$XDG_CONFIG_HOME/omarchy/angelos.lyrics/word-times.json` if set). The directory
is created on first start; see [`examples/word-times.json`](examples/word-times.json)
for the format. A track is matched by artist and title, a line by its start time
(`t`, in seconds) and optionally its `text`; `words[].text` includes the space
before a word where there is one, and `at` is the song time when that word
appears.

A custom entry wins over every network source and over the syllable guess, is
not beat-snapped, and the card says `custom word times`. Edit the file and
change track (or press «Search» in the card) to reload it. The «Words ahead»
slider still shifts these times, just as it shifts a provider's own words.

A line-timed result is shown as soon as it arrives. The word-capable sources
then get one chance each, in the same order, and the line is replaced if one
has the words' own times: word timing wins over the source order without
delaying the first line.

Pinning a provider from the player card is strict: only that source is asked,
no other store upgrades over it, and the track is fetched again the moment the
pin changes. Its answer is for that listen only: it is not written to the disk
cache, so unpinning never inherits it as the "auto" result. The card shows which
source answered and whether the words are the source's own or guessed from the
line's timing.

Sync follows the player's real MPRIS `Position` (read with `busctl` five times a
second), not the shell's wall-clock extrapolation. A player that buffers or
stalls holds the line where it is until the position moves again; an
unannounced seek snaps it at once. If the player does not expose `Position`,
the old behaviour remains.

### Messengers and voice messages

Messengers publish their voice messages over MPRIS too: the "artist" the shell
sees is the sender's name and the "title" the time the message was sent. Live
Lyrics never sends those to a lyrics service on its own — for a player that is a
messenger (Telegram, Discord, Signal, Element, Slack, WhatsApp, Threema, Skype,
Teams, Zoom), the lookup stops at files next to the track and the player's own
embedded lyrics, and nothing is written to the cache. If you actually want the
web searched for such a message, click the line to open the player card and
press its search button (it holds for that one message), or switch on the
`searchInMessengers` setting to do it automatically for every message.

## Click actions on the line

- **Left click** — open or close the player card.
- **Middle click** — play/pause without opening anything.
- **Right click** — cycle the glow off and back to level.

## Development

The plugin lives in `~/.config/omarchy/plugins/<id>`. This repository *is* the
plugin directory, so a checkout can be symlinked or copied in place.

The engine and the widget are covered by a test harness that runs its own
`quickshell` against real LRC text, a real lrclib reply and real text
measurement:

```bash
mkdir -p /tmp/qsimp/qs
cp -r /usr/share/omarchy/shell/Commons /usr/share/omarchy/shell/Ui /tmp/qsimp/qs/
QML_IMPORT_PATH=/tmp/qsimp:/usr/lib/qt6/qml quickshell -p tests
```

Every line it prints starts with `PORTTEST`; `... | grep PORTTEST` shows the
assertions and a final `PORTTEST SUMMARY <passed>/<total>`. See
[`tests/README.md`](tests/README.md) for what each section drives.

Validate the manifest before publishing:

```bash
omarchy plugin validate .
```

## License

MIT, © 2026 MixaDoDs (the original angelOS lyrics bar and engine) and
© 2026 Iliya Brook (the Omarchy port). Full text in [`LICENSE`](LICENSE).
