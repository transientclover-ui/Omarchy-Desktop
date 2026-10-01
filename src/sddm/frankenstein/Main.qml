// SPDX-FileCopyrightText: 2026 Frankenstein contributors
// SPDX-License-Identifier: MIT

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import Qt.labs.settings 1.1

Rectangle {
    id: root
    width: 1920
    height: 1080
    color: "#100c26"

    readonly property color lavender: "#e7ddff"
    readonly property color mutedLavender: "#bfb2df"
    readonly property color magenta: "#e66bb4"
    readonly property color indigo: "#6761b9"
    readonly property string defaultBackground: ThemeConfig.defaultBackground || "backgrounds/vaporwave-default.png"
    property string activeBackground: defaultBackground
    property string statusMessage: ""

    function imageUrl(path) {
        return path.indexOf("/") === 0 ? "file://" + path : Qt.resolvedUrl(path)
    }

    function isAllowedBackground(path) {
        return path === defaultBackground
                || path.indexOf("/var/lib/frankenstein/backgrounds/") === 0
    }

    function rebuildBackgrounds() {
        backgroundsModel.clear()
        backgroundsModel.append({ "path": defaultBackground, "label": qsTr("Vaporwave default") })
        var configured = String(ThemeConfig.backgrounds || "").split(",")
        for (var i = 0; i < configured.length; ++i) {
            var candidate = configured[i].trim()
            if (!candidate || candidate === defaultBackground || !isAllowedBackground(candidate))
                continue
            var parts = candidate.split("/")
            backgroundsModel.append({ "path": candidate, "label": parts[parts.length - 1] })
        }
        var selected = backgroundSettings.selectedBackground
        activeBackground = isAllowedBackground(selected) ? selected : defaultBackground
    }

    function chooseBackground(path) {
        if (!isAllowedBackground(path))
            return
        activeBackground = path
        backgroundSettings.selectedBackground = path
        backgroundSettings.sync()
    }

    function submitLogin() {
        statusMessage = qsTr("Signing in…")
        sddm.login(username.text, password.text, sessionSelector.currentIndex)
    }

    Settings {
        id: backgroundSettings
        fileName: "/var/lib/sddm/.config/frankenstein/background.ini"
        category: "Background"
        property string selectedBackground: ""
    }

    ListModel {
        id: backgroundsModel
    }

    Image {
        id: backgroundImage
        anchors.fill: parent
        source: root.imageUrl(root.activeBackground)
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: false

        onStatusChanged: {
            if (status === Image.Error && root.activeBackground !== root.defaultBackground) {
                root.activeBackground = root.defaultBackground
                backgroundSettings.selectedBackground = root.defaultBackground
                backgroundSettings.sync()
                root.statusMessage = qsTr("The selected background could not be loaded. Using the bundled default.")
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#4d100c26"
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: parent.height * 0.45
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#00100c26" }
            GradientStop { position: 1.0; color: "#d9100c26" }
        }
    }

    Column {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: Math.max(32, Math.min(parent.width, parent.height) * 0.055)
        spacing: 4

        Text {
            text: qsTr("Frankenstein")
            color: root.lavender
            font.pixelSize: Math.max(30, Math.min(root.width, root.height) * 0.046)
            font.weight: Font.DemiBold
        }

        Text {
            text: Qt.formatDateTime(new Date(), "dddd, MMMM d  •  hh:mm")
            color: root.mutedLavender
            font.pixelSize: Math.max(15, Math.min(root.width, root.height) * 0.019)

            Timer {
                interval: 30000
                running: true
                repeat: true
                onTriggered: parent.text = Qt.formatDateTime(new Date(), "dddd, MMMM d  •  hh:mm")
            }
        }
    }

    ToolButton {
        id: settingsButton
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: Math.max(24, Math.min(parent.width, parent.height) * 0.04)
        width: 48
        height: 48
        checkable: true
        text: "⚙"
        font.pixelSize: 24
        ToolTip.visible: hovered
        ToolTip.text: qsTr("Background settings")
        KeyNavigation.tab: username

        background: Rectangle {
            radius: 12
            color: settingsButton.checked || settingsButton.hovered ? "#b34b3c78" : "#8a241c49"
            border.color: "#806f61ad"
        }
        contentItem: Text {
            text: settingsButton.text
            color: root.lavender
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font: settingsButton.font
        }
    }

    Rectangle {
        id: loginPanel
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        width: Math.min(520, parent.width - 48)
        height: Math.min(570, parent.height - 90)
        radius: 24
        color: "#d421183f"
        border.width: 1
        border.color: "#806f61ad"
        z: 2

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Math.max(24, loginPanel.width * 0.075)
            spacing: 16

            Text {
                Layout.fillWidth: true
                text: qsTr("Choose your desktop")
                color: root.lavender
                font.pixelSize: 18
                font.weight: Font.DemiBold
            }

            ComboBox {
                id: sessionSelector
                Layout.fillWidth: true
                Layout.preferredHeight: 52
                model: sessionModel
                textRole: "name"
                currentIndex: sessionModel.lastIndex
                font.pixelSize: 17
                KeyNavigation.tab: username
                KeyNavigation.backtab: settingsButton

                background: Rectangle {
                    radius: 12
                    color: "#d1342859"
                    border.width: sessionSelector.activeFocus ? 2 : 1
                    border.color: sessionSelector.activeFocus ? root.magenta : "#806f61ad"
                }
            }

            Text {
                Layout.fillWidth: true
                text: sessionSelector.currentIndex >= 0
                      ? qsTr("Selected: %1").arg(sessionSelector.currentText)
                      : qsTr("Select a desktop session")
                color: root.magenta
                font.pixelSize: 14
                elide: Text.ElideRight
            }

            TextField {
                id: username
                Layout.fillWidth: true
                Layout.preferredHeight: 52
                placeholderText: qsTr("Username")
                selectByMouse: true
                font.pixelSize: 17
                KeyNavigation.tab: password
                KeyNavigation.backtab: sessionSelector
                background: Rectangle {
                    radius: 12
                    color: "#d1342859"
                    border.width: username.activeFocus ? 2 : 1
                    border.color: username.activeFocus ? root.magenta : "#806f61ad"
                }
            }

            TextField {
                id: password
                Layout.fillWidth: true
                Layout.preferredHeight: 52
                placeholderText: qsTr("Password")
                echoMode: TextInput.Password
                selectByMouse: true
                font.pixelSize: 17
                KeyNavigation.tab: loginButton
                KeyNavigation.backtab: username
                onAccepted: root.submitLogin()
                background: Rectangle {
                    radius: 12
                    color: "#d1342859"
                    border.width: password.activeFocus ? 2 : 1
                    border.color: password.activeFocus ? root.magenta : "#806f61ad"
                }
            }

            Button {
                id: loginButton
                Layout.fillWidth: true
                Layout.preferredHeight: 54
                text: qsTr("Sign in")
                font.pixelSize: 17
                font.weight: Font.DemiBold
                KeyNavigation.tab: restartButton
                KeyNavigation.backtab: password
                onClicked: root.submitLogin()
                background: Rectangle {
                    radius: 12
                    color: loginButton.down ? "#c650438c"
                                            : (loginButton.hovered ? "#df6653a4" : "#c4564796")
                    border.color: "#a79bdf"
                }
                contentItem: Text {
                    text: loginButton.text
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font: loginButton.font
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.minimumHeight: 38
                text: root.statusMessage
                color: root.mutedLavender
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: 13
            }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 12

                Button {
                    id: restartButton
                    text: qsTr("Restart")
                    KeyNavigation.tab: shutdownButton
                    KeyNavigation.backtab: loginButton
                    onClicked: sddm.reboot()
                }

                Button {
                    id: shutdownButton
                    text: qsTr("Shut down")
                    KeyNavigation.tab: settingsButton
                    KeyNavigation.backtab: restartButton
                    onClicked: sddm.powerOff()
                }
            }

            Item {
                Layout.fillHeight: true
            }
        }
    }

    Rectangle {
        id: settingsPanel
        visible: settingsButton.checked
        anchors.top: settingsButton.bottom
        anchors.right: parent.right
        anchors.margins: 24
        width: Math.min(430, parent.width - 48)
        height: Math.min(510, parent.height - settingsButton.height - 72)
        radius: 20
        color: "#f021183f"
        border.width: 1
        border.color: "#806f61ad"
        z: 4

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            Text {
                Layout.fillWidth: true
                text: qsTr("Staged backgrounds")
                color: root.lavender
                font.pixelSize: 20
                font.weight: Font.DemiBold
            }

            Text {
                Layout.fillWidth: true
                text: qsTr("Only the bundled image and images imported by Frankenstein are available here.")
                color: root.mutedLavender
                wrapMode: Text.WordWrap
                font.pixelSize: 13
            }

            ListView {
                id: backgroundList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 10
                model: backgroundsModel

                delegate: Rectangle {
                    required property string path
                    required property string label
                    width: backgroundList.width
                    height: 88
                    radius: 12
                    color: root.activeBackground === path ? "#b34b3c78" : "#80342859"
                    border.width: root.activeBackground === path ? 2 : 1
                    border.color: root.activeBackground === path ? root.magenta : "#806f61ad"

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 12

                        Image {
                            Layout.preferredWidth: 112
                            Layout.fillHeight: true
                            source: root.imageUrl(path)
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                            sourceSize.width: 224
                            sourceSize.height: 144
                        }

                        Text {
                            Layout.fillWidth: true
                            text: label
                            color: root.lavender
                            elide: Text.ElideMiddle
                            font.pixelSize: 14
                        }

                        Text {
                            text: root.activeBackground === path ? "●" : "○"
                            color: root.activeBackground === path ? root.magenta : root.mutedLavender
                            font.pixelSize: 22
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.chooseBackground(path)
                    }
                }
            }
        }
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            root.statusMessage = qsTr("Sign-in failed. Check your username, password, and selected session.")
            password.text = ""
            password.forceActiveFocus()
        }
    }

    Component.onCompleted: {
        rebuildBackgrounds()
        username.forceActiveFocus()
    }
}
