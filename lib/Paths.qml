pragma Singleton
import QtQuick
import Quickshell

Singleton {
    id: root

    readonly property string pluginDir: {
        var url = String(Qt.resolvedUrl("."))
        if (url.indexOf("file://") === 0) {
            try { url = decodeURIComponent(url.substring(7)) } catch (e) {}
        }
        return url.replace(/\/lib\/?$/, "")
    }

    readonly property string home: Quickshell.env("HOME")
    readonly property string cacheDir: home + "/.cache/omarchy/angelos.lyrics"
    // hand-edited word times live with the other user config, never in the plugin
    // (an update must not overwrite them) and never in the disposable cache
    readonly property string configDir: {
        const xdg = Quickshell.env("XDG_CONFIG_HOME");
        return (xdg && xdg.trim() ? xdg : home + "/.config") + "/omarchy/angelos.lyrics"
    }
    readonly property string wordTimesFile: configDir + "/word-times.json"

    function script(name) {
        return pluginDir + "/scripts/" + name
    }
}
