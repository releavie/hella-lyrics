pragma Singleton
import QtQuick
import Quickshell

// The engine's settings, as the ported code reads them: a bag on one property,
// `Config.lyrics.…`, because that is how angelOS wrote them and 43 reads in the
// engine depend on the shape.
//
// The bag exists to make one thing work: a change has to reach bindings.
//   * `lyrics` is a `var` property, so assigning it notifies;
//   * its default is frozen, so nobody can quietly mutate the singleton's own
//     object;
//   * every write goes through setLyrics(), which merges over `lyrics()` and
//     assigns a NEW object. Replacing the whole value is what re-evaluates
//     `Config.lyrics.glow !== "off"` and the rest; poking at a field of the old
//     object would notify nobody and leave the bar drawing the old mode.
Singleton {
    id: root

    // merged over this, never written through: a plain JS object's fields carry
    // no change signal, so a direct write into it would be invisible
    readonly property var defaults: Object.freeze({
        "enabled": true,
        "byWord": true,
        "onBeat": true,
        "glow": "level",            // "off" | "level"
        "glowFloor": 0.3,
        "glowLevelMin": 0.1,
        "glowLevelMax": 0.8,
        "glowRodeMin": 0.1,
        "glowRodeMax": 0.8,
        "glowTap": "main",
        "preferPlayer": "",
        // a messenger's voice message is not a song: its metadata goes to the lyrics services
        // only at the user's request (the player card's «Search lyrics»), unless this is on
        "searchInMessengers": false,
        "artwork": "cover",         // note | cover: what sits left of the line
        "offsetMs": 0,
        "wordLeadMs": 150,
        "typewriter": true,
        "screens": [],              // [] = every screen
        // the order the engine searches in; [] = the engine's own list (lrclib first,
        // then the word-timed stores and the rest as fallbacks)
        "sources": []
    })

    property var lyrics: defaults

    // "lrclib, netease, apple" → ["lrclib", "netease", "lrccx"]; unknown names dropped,
    // duplicates removed, [] when nothing usable is left (the engine's default order)
    readonly property var sourceAliases: ({
        "apple": "lrccx",
        "apple music": "lrccx",
        "apple-music": "lrccx",
        "applemusic": "lrccx",
        "lrc.cx": "lrccx",
        "lrc.cx / apple": "lrccx",
        "better lyrics": "betterlyrics",
        "better-lyrics": "betterlyrics"
    })
    readonly property var sourceNames: ["local", "player", "lrclib", "amll", "netease", "kugou", "qq", "lrccx", "musixmatch", "genius", "betterlyrics", "ovh"]
    function parseSources(value) {
        var list = Array.isArray(value) ? value : String(value || "").split(",")
        var out = []
        for (var i = 0; i < list.length; i++) {
            var s = String(list[i] || "").trim().toLowerCase()
            if (!s)
                continue
            s = sourceAliases[s] || s
            if (sourceNames.indexOf(s) >= 0 && out.indexOf(s) < 0)
                out.push(s)
        }
        return out
    }

    // patch one or more settings; always assigns a fresh object so bindings react
    function setLyrics(patch) {
        if (!patch)
            return
        var next = {}
        for (var k in root.lyrics)
            next[k] = root.lyrics[k]
        for (var j in patch)
            next[j] = patch[j]
        root.lyrics = next
    }

    // ---- paths and readiness -------------------------------------------------
    readonly property string home: Quickshell.env("HOME")
    readonly property string cacheDir: home + "/.cache/omarchy/angelos.lyrics"
    // true here, always: the ported engine has no settings file of its own to
    // wait for — the shell reads the manifest schema before the plugin loads
    readonly property bool ready: true
}
